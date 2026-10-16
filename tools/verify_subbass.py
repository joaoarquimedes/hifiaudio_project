#!/usr/bin/env python3
"""Export the actual KiCad design and verify the SubBass HW1 component proposal.

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
NAMES = ['time', 'vp', 'vn', 'ctrl', 'before', 'after', 'adj_pos', 'adj_neg', 'vin', 'vcc_sup', 'vref', 'drain']
VECTORS = ['time', 'v(+v)', 'v(-v)', 'v(/subbass/ctrl_passa)',
           'v(/subbass/vout_hp_sub)', 'v(/subbass/vout_sub_mute)',
           'v(/subbass/mute_subbass/adj_pos)', 'v(/subbass/mute_subbass/adj_neg)', 'v(/subbass/vin_sub)', 'v(/subbass/mute_subbass/vcc_sup)', 'v(/subbass/mute_subbass/vref_1v)', 'v(/subbass/mute_subbass/sw_drain)']

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
        vectors = ['frequency', 'v(/subbass/vin_sub)', VECTORS[4], VECTORS[5],
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

def validate(data, release=None, cutoff=None, always_off=False):
    check(data['time'][-1]>=.999999,'transient did not reach 1 s')
    check(all(math.isfinite(x) for col in data.values() for x in col),'non-finite data')
    invalid_since=None
    for i,t in enumerate(data['time']):
        bad=data['adj_pos'][i]<.497 or data['adj_neg'][i]>.503 or data['vcc_sup'][i]<2.15
        if bad:
            if invalid_since is None:invalid_since=t
            if t-invalid_since>.0008:check(data['ctrl'][i]<.8,'mute did not assert after allowed detection delay')
        else:invalid_since=None
    e=edges(data)
    if always_off:check(max(data['ctrl'])<.8,'must remain muted without both valid rails')
    if release is not None:
        on=next((x['time_s'] for x in e if x['state']),None)
        check(on is not None and abs(on-release)<.0015,f'release {on}, expected {release}')
    if cutoff is not None:
        off=next((x['time_s'] for x in e if not x['state']),None)
        check(off is not None and abs(off-cutoff)<.0004,f'cutoff {off}, expected {cutoff}')
    return e

def execute_case(out,base,name,vp,vn,vin='DC 0',release=None,cutoff=None,always_off=False,
                 step='20u',load=None,ac=False,ic_params=None,cap=None,injection=None):
    text=source(source(source(base,'V1',vp),'V2',vn),'V3',vin)
    text=re.sub(r'\bGND\b','0',text)  # SPICE ground convention, same schematic ground net
    if load:text=re.sub(r'(?m)^(R8\s+\S+\s+\S+)\s+.*$',rf'\g<1> {load}',text)
    if cap:text=re.sub(r'(?m)^(C10\s+\S+\s+\S+)\s+.*$',rf'\g<1> {cap}',text)
    for ref,params in (ic_params or {}).items():
        text,n=re.subn(rf'(?m)^({ref}\s+.*)$',lambda m:m[1]+' '+params,text);check(n==1,'missing '+ref)
    analysis='.ac dec 100 0.1 1000' if ac else f'.tran 100u 1 0 {step}'
    extra=''
    if injection:
        # 6.8mA * (90ns width + 10ns edge-area) = 680pC.
        extra=f'IINJECT 0 /subbass/VOUT_SUB_MUTE PULSE(0 {injection*0.0068:g} .61187 10n 10n 90n 2)\n'
    text=text.replace('.end',extra+analysis+'\n.end')
    netlist,datafile=out/(name+'.cir'),out/(name+'.csv');netlist.write_text(text)
    r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(netlist),'--csv',str(datafile)]+(['--ac'] if ac else []),capture_output=True,text=True,timeout=120)
    (out/(name+'.worker.txt')).write_text(r.stdout+r.stderr)
    check(r.returncode==0,f'{name}: simulator failed; inspect {name}.log')
    d=series(datafile)
    if ac:return d,{'status':'PASS','analysis':'AC'}
    e=validate(d,release,cutoff,always_off)
    return d,{'status':'PASS','max_step_s':float(step[:-1])*1e-6,'rows':len(d['time']),'edges':e,'before_peak':peak(d,'before',0,1),'after_peak':peak(d,'after',0,1),'max_drain_current_A':max(abs((a-b)/680) for a,b in zip(d['after'],d['drain']))}

def main(output):
    out=output.resolve();out.mkdir(parents=True,exist_ok=True)
    r=subprocess.run(['kicad-cli','sch','export','netlist','--format','spice','--output',str(out/'nominal.cir'),str(ROOT/'hifi_audio.kicad_sch')],capture_output=True,text=True)
    check(r.returncode==0,r.stdout+r.stderr);base=(out/'nominal.cir').read_text()
    check('LTC2909_STUDY' in base and 'ADG5412F_STUDY' in base,'physical proposal not present')
    check('SUBBASS_MUTE_CTRL' not in base and 'SUBBASS_MUTE_SWITCH' not in base,'ideal blocks still active')
    for ref,value in [('R3','28.1k'),('R4','28.1k'),('C3','100n'),('C4','200n'),('R6','11.3k'),('R7','22.6k'),('C5','1u'),('C6','1u')]:
        check(bool(re.search(rf'(?m)^{ref}\s+\S+\s+\S+\s+{re.escape(value)}\s*$',base)),f'filter {ref} changed')
    report={'status':'RUNNING','scope':'HW1 component proposal; local approximations, not vendor or bench validation','kicad':subprocess.check_output(['kicad-cli','version'],text=True).strip(),'ngspice_library':library_path(),'method':'gear','max_step_s':20e-6,'cases':{},'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'subbass.kicad_sch',ROOT/'mute_subbass.kicad_sch',ROOT/'spice/SubBass/subbass_hardware.lib']}}
    def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name,vp,vn,vin='DC 0',**kwargs):
        print(name,flush=True)
        try:d,result=execute_case(out,base,name,vp,vn,vin,**kwargs)
        except Exception as exc:
            report['status']='FAIL';report['cases'][name]={'status':'FAIL','error':str(exc)};save();raise
        report['cases'][name]=result;save();return d,result
    startup,r=run('startup_shutdown',pulse(),pulse(),release=.3091333,cutoff=.6118667)
    r['startup_before']=peak(startup,'before',.09,.2);r['startup_after']=peak(startup,'after',.09,.2)
    r['shutdown_before']=peak(startup,'before',.61,.65);r['shutdown_after']=peak(startup,'after',.615,.65)
    check(r['startup_after']['abs_V']<.001 and r['shutdown_after']['abs_V']<.001,'unacceptable ramp transient after mute')
    fine,_=run('startup_shutdown_10us',pulse(),pulse(),release=.3091333,cutoff=.6118667,step='10u')
    check(abs(edges(startup)[0]['time_s']-edges(fine)[0]['time_s'])<100e-6,'timestep-dependent release')
    run('positive_first',pulse(.1),pulse(.12),release=.3288667,cutoff=.6118667)
    run('negative_first',pulse(.12),pulse(.1),release=.3291333,cutoff=.6121333)
    run('positive_missing','DC 0',pulse(),always_off=True)
    run('negative_missing',pulse(),'DC 0',always_off=True)
    run('both_missing','DC 0','DC 0',always_off=True)
    normal=pwl([(0,0),(.1,0),(.11,15),(1,15)])
    fault=pwl([(0,0),(.1,0),(.11,15),(.45,15),(.46,0),(.5,0),(.51,15),(1,15)])
    for name,vp,vn,recover,off in [('positive_fault',fault,normal,.7091333,.4518667),('negative_fault',normal,fault,.7088667,.4521333)]:
        d,r=run(name,vp,vn,'DC 0 SIN(0 2.828 20 150m) AC 1',release=.3091333,cutoff=off,step='10u' if name=='negative_fault' else '20u')
        ee=edges(d);check(len(ee)==3 and abs(ee[2]['time_s']-recover)<.002,'recovery must restart full timeout')
        check(peak(d,'after',.47,.5)['abs_V']<.001,'fault not isolated after detection')
    abrupt=pwl([(0,0),(.1,0),(.11,15),(.45,15),(.450001,0),(.5,0),(.500001,15),(1,15)])
    for name,vp,vn in [('positive_abrupt',abrupt,normal),('negative_abrupt',normal,abrupt)]:
        d,r=run(name,vp,vn,'DC 0 SIN(0 2.828 20 150m) AC 1',step='10u')
        r['early_fault_output_peak']=peak(d,'after',.45,.4508)
        check(r['max_drain_current_A']<.03,'drain current exceeds 30mA absolute limit')
        check(sample(d,'ctrl',.451)<.8,'abrupt fault detection too late')
        check(peak(d,'after',.46,.49)['abs_V']<.001,'abrupt fault not isolated after allowed latency')
    slow=pwl([(0,0),(.02,0),(.32,15),(1,15)])
    run('slow_ramp',slow,slow,release=.4795)
    run('undervoltage','DC 11.5','DC 15',always_off=True)
    noise=pwl([(0,0),(.1,0),(.11,15),(.4,15),(.41,12.8),(.43,13.1),(.45,12.8),(.47,13.1),(.49,12.8),(.55,15),(1,15)])
    d,r=run('requalification',noise,normal,release=.3091333)
    check(len(edges(d))==3 and sample(d,'ctrl',.6)<.8 and sample(d,'ctrl',.8)>2,'noise retrigger / timeout incorrect')
    # Real part has timeout tolerance, no 1V Schmitt hysteresis in this mode.
    run('minimum_timeout',pulse(),pulse(),release=.2591333,ic_params={'XU4':'TRESET=150m'})
    run('maximum_timeout',pulse(),pulse(),release=.3691333,ic_params={'XU4':'TRESET=260m'})
    # Worst combinations of threshold/reference and 0.1% divider resistors.
    # For temporal assertions derive the resulting crossing values from actual pin parameters.
    for name,th,ref in [('low_trip_corner',.5075,.985),('high_trip_corner',.4925,1.015)]:
        d,r=run(name,pulse(),pulse(),ic_params={'XU4':f'VTH={th} VREF={ref}'})
        check(len(edges(d))==2,'corner must qualify and then mute')
    d,r=run('nominal_audio','DC 15','DC 15','DC 0 SIN(0 2.828 20) AC 1')
    check(min(d['ctrl'])>2,'nominal DC operating point not enabled')
    r['audio_before']=peak(d,'before',.7,1);r['audio_after']=peak(d,'after',.7,1)
    check(2.45<r['audio_after']['abs_V']<2.55,'20Hz amplitude not preserved')
    d,r=run('capacitive_load_1u','DC 15','DC 15','DC 0 SIN(0 2.828 20) AC 1',cap='1u')
    check(2.45<peak(d,'after',.7,1)['abs_V']<2.55,'capacitive stress unstable or unexpected gain')
    d,r=run('dc_rejection','DC 15','DC 15','DC 1');r['steady_output']=peak(d,'after',.7,1)
    check(r['steady_output']['abs_V']<.001,'DC rejection failed')
    # Deliberate pessimistic charge packet; NOT proof of real charge injection accuracy.
    for sign in [-1,1]:
        d,r=run('charge_packet_'+('negative' if sign<0 else 'positive'),pulse(),pulse(),injection=sign)
        r['injection_peak']=peak(d,'after',.61186,.62)
        check(r['injection_peak']['abs_V']<.0085,'680pC charge-packet bound exceeded')
    # Model-specific Ron/leakage corners, without pretending to include THD or noise.
    d,r=run('leakage_corner',pulse(),pulse(),ic_params={'XU5':'RON=16.5 IOFF=50n CFEED=13p'})
    check(peak(d,'after',.09,.2)['abs_V']<.001,'50nA leakage corner exceeds 1mV target')
    for load in [None,'2k']:
        name='ac_10k' if load is None else 'ac_2k';d,r=run(name,'DC 15','DC 15','DC 0 AC 1',ac=True,load=load)
        table=[];rl=10000 if load is None else 2000
        for freq in [1,5,10,20,40,100,1000]:
            i=min(range(len(d['frequency'])),key=lambda i:abs(d['frequency'][i]-freq));f=d['frequency'][i]
            before=complex(d['before_real'][i],d['before_imag'][i]);after=complex(d['after_real'][i],d['after_imag'][i]);lp=complex(d['lp_real'][i],d['lp_imag'][i]);expected=1/complex(1+690/rl,2*math.pi*f*690*100e-9)
            check(abs(abs(after/before)-abs(expected))<1e-4,'unexpected physical mute insertion loss')
            table.append({'frequency_Hz':f,'before_dB':20*math.log10(abs(before)),'after_dB':20*math.log10(abs(after)),'lp_dB':20*math.log10(abs(lp)),'phase_deg':math.degrees(math.atan2(after.imag,after.real))})
        r['response']=table
        check(-3.2<next(x for x in table if abs(x['frequency_Hz']-40)<.5)['lp_dB']<-2.8,'40Hz filter changed')
    # Pin safety and current budgets across the actual tested waveforms.
    for name in ['startup_shutdown','positive_first','negative_first','positive_missing','negative_missing','slow_ramp']:
        d=series(out/(name+'.csv'));check(min(d['adj_neg'])>-.3,'negative monitor exceeds input absolute minimum')
    report['status']='FUNCTIONAL_PASS_WITH_LIMITATIONS'
    report['hardware_approval']='NOT_APPROVED: bench tests and abrupt-fault assessment required'
    report['critical_findings']={name:report['cases'][name]['early_fault_output_peak'] for name in ['positive_abrupt','negative_abrupt']}
    save();print(f"FUNCTIONAL CHECKS COMPLETE: {len(report['cases'])}; hardware NOT APPROVED. Results: {out}")

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
