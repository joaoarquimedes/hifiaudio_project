#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8,<4"]
# ///
"""Plot a completed verify_subbass.py run: uv run tools/plot_subbass.py RUN_DIR."""
import argparse
import csv
import json
from pathlib import Path
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('run_dir',type=Path)
p.add_argument('--output',type=Path,default=None)
a=p.parse_args();out=a.output or a.run_dir;out.mkdir(parents=True,exist_ok=True)
result=json.loads((a.run_dir/'results.json').read_text())
if result['status'] not in ['PASS','FUNCTIONAL_PASS_WITH_LIMITATIONS']:raise SystemExit('Refusing to plot an incomplete / failed run as approved')

def load(name):
    with (a.run_dir/(name+'.csv')).open() as f:
        rows=list(csv.DictReader(f))
    return {k:[float(r[k]) for r in rows] for k in rows[0]}
plt.rcParams.update({'font.size':10})
fig,ax=plt.subplots(5,1,figsize=(12,12),sharex=True,layout='constrained')
d=load('startup_shutdown');t=[x*1000 for x in d['time']]
fig.suptitle('SubBass — mute automático com supervisão dos dois trilhos\nHW2: modelos locais; comparador sem atraso temporal · não aprovado para fabricação',fontsize=14)
ax[0].plot(t,d['vp'],label='+V');ax[0].plot(t,d['vn'],label='−V');ax[0].set_ylabel('Trilhos (V)')
ax[1].plot(t,d['adj_pos'],label='ADJ1 (+V)');ax[1].plot(t,d['adj_neg'],label='ADJ2 (−V)');ax[1].axhline(.5,color='#777',ls=':',label='Limiar nominal 0,5 V');ax[1].set_ylabel('Sensores (V)')
ax[2].plot(t,d['ctrl'],label='CTRL_PASSA / RST',color='#b28400');ax[2].set_ylabel('Controle (V)')
ax[3].plot(t,d['before'],label='Antes de S1',color='#2875b8');ax[3].plot(t,d['after'],label='Após S1',color='#c43d3d');ax[3].set_ylabel('Áudio (V)')
ax[4].plot(t,[v*1e6 for v in d['after']],label='Após S1 — ampliado',color='#c43d3d');ax[4].set_ylabel('Áudio (µV)');ax[4].set_xlabel('Tempo (ms)')
for x in ax:x.grid(alpha=.25);x.legend(loc='upper right',ncol=3);x.set_xlim(0,1000);x.axvspan(309.14,611.87,color='#65b96e',alpha=.08)
fig.savefig(out/'mute_automatico.png',dpi=150)
plt.close(fig)
fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
fig.suptitle('Mute automático — perda de um trilho durante passagem de áudio\nEntrada 20 Hz / 2,828 Vp, iniciada aos 150 ms; recuperação exige novo atraso',fontsize=13)
for name,color,label in [('positive_fault','#2674b8','Falha +V'),('negative_fault','#9a59a6','Falha −V')]:
 d=load(name);t=[x*1000 for x in d['time']]
 axs[0].plot(t,d['vp'] if name=='positive_fault' else d['vn'],label=label,color=color)
 axs[1].plot(t,d['ctrl'],label=label,color=color)
 axs[2].plot(t,d['after'],label=label,color=color,alpha=.8)
for ax in axs:ax.grid(alpha=.25);ax.legend(loc='upper right');ax.set_xlim(0,1000)
axs[0].set_ylabel('Trilho afetado (V)');axs[1].set_ylabel('CTRL_PASSA (V)');axs[2].set_ylabel('Após S1 (V)');axs[2].set_xlabel('Tempo (ms)')
fig.savefig(out/'falhas_trilhos.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
fig.suptitle('SubBass — resposta AC da cascata e perda da chave\nAlimentação DC ±15 V; análise no ponto de operação energizado',fontsize=13)
for name,label in [('ac_10k','Carga 10 kΩ'),('ac_2k','Carga 2 kΩ')]:
 d=load(name);gain=[];phase=[]
 for ar,ai,vr,vi in zip(d['after_real'],d['after_imag'],d['vin_real'],d['vin_imag']):
  h=complex(ar,ai)/complex(vr,vi);gain.append(20*math.log10(abs(h)));phase.append(math.degrees(math.atan2(h.imag,h.real)))
 ax[0].semilogx(d['frequency'],gain,label=label);ax[1].semilogx(d['frequency'],phase,label=label)
for x in ax:x.grid(which='both',alpha=.2);x.legend();x.axvline(10,ls=':',color='#777');x.axvline(40,ls=':',color='#777')
ax[0].set_ylabel('Ganho (dB)');ax[1].set_ylabel('Fase (°)');ax[1].set_xlabel('Frequência (Hz)');ax[0].set_ylim(-65,3)
fig.savefig(out/'resposta_ac.png',dpi=150);plt.close(fig)
print(out)
