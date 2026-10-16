#!/usr/bin/env python3
"""Export the actual KiCad design and verify the SubBass functional study.

Python standard library only; no changes to source schematics. Writes generated
netlists, CSVs, logs and JSON to --output (default: a fresh temporary directory).
Use NGSPICE_LIBRARY when libngspice is not on the system library search path.
Shared API: https://github.com/ngspice/ngspice/blob/master/src/include/ngspice/sharedspice.h
"""
import argparse
import bisect
import csv
import ctypes as C
import ctypes.util
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['time', 'vp', 'vn', 'ctrl', 'before', 'after', 'valid', 'timer', 'vin']
VECTORS = ['time', 'v(+v)', 'v(-v)', 'v(/subbass/ctrl_passa)',
           'v(/subbass/vout_hp_sub)', 'v(/subbass/vout_sub_mute)',
           'v(/subbass/rail_ok)', 'v(/subbass/mute_timer)', 'v(/subbass/vin_sub)']

class Complex(C.Structure):
    _fields_ = [('real', C.c_double), ('imag', C.c_double)]

class Vector(C.Structure):
    _fields_ = [('name', C.c_char_p), ('type', C.c_int), ('flags', C.c_short),
                ('real', C.POINTER(C.c_double)), ('complex', C.POINTER(Complex)),
                ('length', C.c_int)]

def library_path():
    explicit = os.environ.get('NGSPICE_LIBRARY')
    if explicit:
        return explicit
    cli = shutil.which('kicad-cli')
    if cli:
        base = Path(cli).resolve().parent.parent
        for folder in [base/'shared/lib', base/'lib']:
            found = sorted(folder.glob('libngspice.so*'))
            if found:
                return str(found[0])
    found = ctypes.util.find_library('ngspice')
    if found:
        return found
    raise RuntimeError('libngspice not found; set NGSPICE_LIBRARY to its absolute path')

class NgSpice:
    def __init__(self):
        self.log = []
        self.path = library_path()
        self.lib = C.CDLL(self.path)
        @C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
        def output(value, ident, user):
            self.log.append(value.decode(errors='replace'))
            return 0
        @C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
        def exiting(status, immediate, quit_requested, ident, user):
            self.log.append(f'CONTROLLED EXIT status={status}')
            return 0
        self.callbacks = [output, exiting]  # callbacks must stay alive
        self.lib.ngSpice_Init.argtypes = [C.c_void_p]*7
        self.lib.ngSpice_Init(output, None, exiting, None, None, None, None)
        self.lib.ngSpice_Command.argtypes = [C.c_char_p]
        self.lib.ngGet_Vec_Info.argtypes = [C.c_char_p]
        self.lib.ngGet_Vec_Info.restype = C.POINTER(Vector)
        self.command('set nomoremode')
        self.command('set ngbehavior=ltpsa')
        self.command('version')
        for model in sorted((Path(self.path).resolve().parent/'ngspice').glob('*.cm')):
            self.command('codemodel '+str(model))
    def command(self, value):
        self.log.append('COMMAND '+value)
        result = self.lib.ngSpice_Command(value.encode())
        if result:
            raise RuntimeError(f'ngspice command failed ({result}): {value}')
    def vector(self, name):
        ptr = self.lib.ngGet_Vec_Info(name.encode())
        if not ptr:
            raise RuntimeError('Missing vector '+name)
        vec = ptr.contents
        if vec.real:
            return [vec.real[i] for i in range(vec.length)]
        return [complex(vec.complex[i].real, vec.complex[i].imag) for i in range(vec.length)]

def worker(netlist, output, ac):
    ng = NgSpice()
    try:
        ng.command('source '+str(netlist.resolve()))
        ng.command('run')
        names = ['frequency', 'vin', 'before', 'after', 'lp'] if ac else NAMES
        vectors = ['frequency', VECTORS[-1], VECTORS[4], VECTORS[5],
                   'v(/subbass/vout_sub)'] if ac else VECTORS
        data = [ng.vector(v) for v in vectors]
        if ac:
            fields = ['frequency', 'vin_real', 'vin_imag', 'before_real', 'before_imag',
                      'after_real', 'after_imag', 'lp_real', 'lp_imag']
            rows = [[float(x[0].real)] + [item for v in x[1:] for item in (v.real,v.imag)]
                    for x in zip(*data)]
        else:
            fields, rows = names, zip(*data)
        with output.open('w', newline='') as f:
            w = csv.writer(f); w.writerow(fields); w.writerows(rows)
        errors = [s for s in ng.log if any(k in s.lower() for k in
                  ['simulation(s) aborted', 'timestep too small', 'fatal error', 'error:', 'controlled exit'])]
        if errors:
            raise RuntimeError('\n'.join(errors))
    finally:
        output.with_suffix('.log').write_text('\n'.join(ng.log)+'\n')

def source(text, ref, value):
    # Preserve nodes exported by KiCad, replace only source waveform.
    pattern = rf'(?m)^({ref}\s+\S+\s+\S+)\s+.*$'
    text, count = re.subn(pattern, lambda m: m[1]+' '+value, text)
    assert count == 1, (ref, count)
    return text

def pulse(delay=.1, width=.5):
    return f'PULSE(0 15 {delay:g} 10m 10m {width:g} 4)'

def pwl(points):
    return 'PWL('+' '.join(f'{t:g} {v:g}' for t,v in points)+')'

def series(reader):
    rows = list(csv.DictReader(reader.open()))
    return {k: [float(r[k]) for r in rows] for k in rows[0]}

def sample(data, name, t):
    x, y = data['time'], data[name]
    i = bisect.bisect_left(x, t)
    if i == 0: return y[0]
    if i == len(x): return y[-1]
    f = (t-x[i-1])/(x[i]-x[i-1])
    return y[i-1] + f*(y[i]-y[i-1])

def edges(data, name='ctrl'):
    result = []
    for i in range(1,len(data['time'])):
        a,b = data[name][i-1:i+1]
        if (a>2.5) != (b>2.5):
            t0,t1=data['time'][i-1:i+1]
            result.append({'time_s':t0+(2.5-a)*(t1-t0)/(b-a), 'state':int(b>2.5)})
    return result

def peak(data, name, a, b):
    values = [(abs(v),t,v) for t,v in zip(data['time'],data[name]) if a<=t<=b]
    p,t,v = max(values)
    return {'abs_V':p, 'time_s':t, 'value_V':v}

def check(condition, message):
    if not condition: raise AssertionError(message)

def validate(data, release, cutoff=None, always_off=False):
    check(data['time'][-1] >= .999999, 'transient did not reach 1 s')
    check(all(math.isfinite(x) for col in data.values() for x in col), 'non-finite data')
    for vp,vn,c in zip(data['vp'],data['vn'],data['ctrl']):
        # Includes 20 us numerical allowance at the hysteretic boundary.
        check(not(c>2.5 and (vp<11.95 or vn>-11.95)), 'audio enabled with an unhealthy rail')
    e = edges(data)
    if always_off:
        check(max(data['ctrl'])<.1, 'must remain muted without both rails')
    if release is not None:
        on = next((x['time_s'] for x in e if x['state']), None)
        check(on is not None and abs(on-release)<.001, f'release {on}, expected {release}')
    if cutoff is not None:
        off = next((x['time_s'] for x in e if not x['state']), None)
        check(off is not None and abs(off-cutoff)<.0001, f'cutoff {off}, expected {cutoff}')
    return e

def execute_case(out, base, name, vp, vn, vin, release=None, cutoff=None,
                 always_off=False, step='20u', load=None, ac=False):
    text = source(source(source(base,'V1',vp),'V2',vn),'V3',vin)
    if load: text = re.sub(r'(?m)^(R8\s+\S+\s+\S+)\s+.*$', rf'\g<1> {load}',text)
    analysis = '.ac dec 100 0.1 1000' if ac else f'.tran 100u 1 0 {step}'
    text = text.replace('.end', analysis+'\n.end')
    netlist, datafile = out/(name+'.cir'), out/(name+'.csv')
    netlist.write_text(text)
    r = subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(netlist),
                        '--csv',str(datafile)]+(['--ac'] if ac else []),capture_output=True,text=True)
    (out/(name+'.worker.txt')).write_text(r.stdout+r.stderr)
    check(r.returncode==0, f'{name}: simulator failed; see {name}.log / worker.txt')
    d = series(datafile)
    if ac: return d, {'status':'PASS','analysis':'AC'}
    e = validate(d,release,cutoff,always_off)
    return d, {'status':'PASS','rows':len(d['time']),'edges':e,
               'before_peak':peak(d,'before',0,1),'after_peak':peak(d,'after',0,1)}

def main(output):
    out = output.resolve();out.mkdir(parents=True,exist_ok=True)
    # No reliance on a hand-maintained duplicate netlist.
    r=subprocess.run(['kicad-cli','sch','export','netlist','--format','spice','--output',str(out/'nominal.cir'),str(ROOT/'hifi_audio.kicad_sch')],capture_output=True,text=True)
    check(r.returncode==0,r.stdout+r.stderr)
    base=(out/'nominal.cir').read_text()
    check('XU4 +V -V GND /subbass/CTRL_PASSA /subbass/RAIL_OK /subbass/MUTE_TIMER SUBBASS_MUTE_CTRL' in base,'supervisor not connected as expected')
    check(not re.search(r'^V4\s',base,re.M),'obsolete fixed-time control still present')
    check('XS1 /subbass/VOUT_HP_SUB /subbass/VOUT_SUB_MUTE /subbass/CTRL_PASSA GND SUBBASS_MUTE_SWITCH' in base,'series mute is not connected correctly')
    report={'status':'RUNNING','kicad':subprocess.check_output(['kicad-cli','version'],text=True).strip(),
            'ngspice_library':library_path(),'method':'gear','max_step_s':20e-6,'cases':{},
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'subbass.kicad_sch',ROOT/'Bancada_Simulacao.kicad_sch',ROOT/'spice/SubBass/subbass_mute.lib']}}
    def run(name,vp,vn,vin='DC 0',**kwargs):
        print(name,flush=True)
        try:
            d,result=execute_case(out,base,name,vp,vn,vin,**kwargs)
        except Exception as exc:
            report['status']='FAIL';report['cases'][name]={'status':'FAIL','error':str(exc)}
            (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
            raise
        report['cases'][name]=result
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        return d,result
    # Full TI macromodel in every case; offsets/transients are exploratory at low rails.
    startup,result=run('startup_shutdown',pulse(),pulse(),release=.3086667,cutoff=.612)
    result['startup_before']=peak(startup,'before',.09,.2);result['startup_after']=peak(startup,'after',.09,.2)
    result['shutdown_before']=peak(startup,'before',.61,.65);result['shutdown_after']=peak(startup,'after',.6121,.65)
    check(result['startup_after']['abs_V']<50e-6,'startup leakage exceeds 50 uV')
    check(result['shutdown_after']['abs_V']<50e-6,'shutdown leakage exceeds 50 uV')
    fine,fres=run('startup_shutdown_10us',pulse(),pulse(),release=.3086667,cutoff=.612,step='10u')
    check(abs(edges(startup)[0]['time_s']-edges(fine)[0]['time_s'])<50e-6,'delay depends on timestep')
    run('positive_first',pulse(.1),pulse(.12),release=.3286667,cutoff=.612)
    run('negative_first',pulse(.12),pulse(.1),release=.3286667,cutoff=.612)
    run('positive_missing','DC 0',pulse(),always_off=True)
    run('negative_missing',pulse(),'DC 0',always_off=True)
    run('both_missing','DC 0','DC 0',always_off=True)
    # Loss of either rail while audio is passing, followed by recovery.
    normal=pwl([(0,0),(.1,0),(.11,15),(1,15)])
    fault=pwl([(0,0),(.1,0),(.11,15),(.45,15),(.46,0),(.5,0),(.51,15),(1,15)])
    for name,vp,vn in [('positive_fault',fault,normal),('negative_fault',normal,fault)]:
        d,r=run(name,vp,vn,'DC 0 SIN(0 2.828 20 150m) AC 1',release=.3086667,cutoff=.452)
        ee=edges(d);check(len(ee)==3 and abs(ee[2]['time_s']-.7086667)<.001,'fault recovery must restart full delay')
        check(peak(d,'after',.46,.5)['abs_V']<100e-6,'fault not isolated')
    shortdip=pwl([(0,0),(.1,0),(.11,15),(.2,15),(.20001,0),(.20011,0),(.20012,15),(1,15)])
    run('qualification_reset',shortdip,normal,release=.4001187)
    # Deadband after good power must not cause repeated toggling; crossing 12 V resets.
    hysteresis=pwl([(0,0),(.1,0),(.11,15),(.4,15),(.41,12.4),(.43,12.6),(.45,12.4),(.47,12.6),(.49,12.4),(.5,11.8),(.55,11.8),(.56,12.6),(.65,12.6),(.66,15),(1,15)])
    d,r=run('hysteresis',hysteresis,normal,release=.3086667)
    check(sample(d,'ctrl',.48)>4.9 and sample(d,'ctrl',.64)<.1,'hysteresis / requalification incorrect')
    check(len(edges(d))==3,'chattering or missing recovery')
    slow=pwl([(0,0),(.02,0),(.32,15),(1,15)])
    run('slow_ramp',slow,slow,release=.48)
    run('undervoltage','DC 11.5','DC 15',always_off=True)
    run('wrong_polarity','DC 15','DC -15',always_off=True)
    d,r=run('nominal_audio','DC 15','DC 15','DC 0 SIN(0 2.828 20) AC 1')
    check(min(d['ctrl'])>4.9,'nominal DC OP should enable mute')
    r['audio_before']=peak(d,'before',.7,1);r['audio_after']=peak(d,'after',.7,1)
    gain=r['audio_after']['abs_V']/r['audio_before']['abs_V']
    check(abs(gain-10000/10001)<1e-5,'unexpected series-switch loss')
    check(2.6<r['audio_after']['abs_V']<2.75,'unexpected 20 Hz output amplitude')
    d,r=run('dc_rejection','DC 15','DC 15','DC 1')
    r['steady_output']=peak(d,'after',.7,1)
    check(r['steady_output']['abs_V']<.001,'1 V DC input is not rejected by the subsonic stage')
    for load in [None,'2k']:
        name='ac_10k' if load is None else 'ac_2k'
        d,r=run(name,'DC 15','DC 15','DC 0 AC 1',ac=True,load=load)
        table=[]
        for frequency in [1,5,10,20,40,100,1000]:
            i=min(range(len(d['frequency'])),key=lambda i:abs(d['frequency'][i]-frequency))
            before=complex(d['before_real'][i],d['before_imag'][i]);after=complex(d['after_real'][i],d['after_imag'][i]);lp=complex(d['lp_real'][i],d['lp_imag'][i])
            record={'frequency_Hz':d['frequency'][i], 'before_dB':20*math.log10(abs(before)), 'after_dB':20*math.log10(abs(after)), 'lp_dB':20*math.log10(abs(lp)),'phase_deg':math.degrees(math.atan2(after.imag,after.real))}
            table.append(record)
            load_ohms = float(load[:-1])*1000 if load else 10000
            check(abs(abs(after/before)-load_ohms/(load_ohms+1))<1e-5,'AC mute loss')
        r['response']=table
        at20=next(x for x in table if abs(x['frequency_Hz']-20)<.5)
        check(-.7<at20['after_dB']<-.35,'20 Hz cascade gain outside expected range')
        at40=next(x for x in table if abs(x['frequency_Hz']-40)<.5)
        check(-3.2<at40['lp_dB']<-2.8,'low-pass cutoff shifted')
    report['status']='PASS'
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"PASS: {len(report['cases'])} cases. Results: {out}")

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=None)
    p.add_argument('--worker',type=Path,help=argparse.SUPPRESS)
    p.add_argument('--csv',type=Path,help=argparse.SUPPRESS)
    p.add_argument('--ac',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.worker:
        worker(args.worker,args.csv,args.ac)
    else:
        main(args.output or Path(tempfile.mkdtemp(prefix='subbass_checks_')))
