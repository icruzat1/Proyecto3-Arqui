#!/usr/bin/env python3
"""Plot recorded A utilization points, without interpolation of passing designs."""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

root=Path(__file__).resolve().parents[1];source=root/'evidence/gf180_sweeps/summary.json'
d=json.loads(source.read_text());points=sorted([r for r in d['rows'] if r['variant']=='a' and r['period_ns']==100],key=lambda r:r['core_util_percent'])
assert [r['core_util_percent'] for r in points]==[30,40,50], 'Wait for all utilization points'
out=source.parent/'plots';out.mkdir(exist_ok=True)
x=[r['core_util_percent'] for r in points]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(10.8,4.8),layout='constrained')
fig.suptitle('Variante A · 100 ns · barrido de utilización',fontsize=15,fontweight='bold')
for key,label,color,marker in [('max_timing_violations_per_corner','Setup/hold, peor esquina','#bd3c35','o'),('antenna_violations','Antenas','#d17b13','s'),('routing_drc','DRC de ruteo','#426b9c','^')]:
    y=[r[key] for r in points];assert all(isinstance(v,(int,float)) for v in y)
    axes[0].plot(x,y,color=color,marker=marker,label=label,linewidth=1.6)
axes[0].set_ylabel('Número de violaciones');axes[0].set_ylim(bottom=-.3);axes[0].yaxis.set_major_locator(MaxNLocator(integer=True));axes[0].legend(loc='best',fontsize=9)
area=[r['die_area_um2']/1e6 for r in points]
axes[1].plot(x,area,color='#718399',linewidth=1.4)
for xx,yy,r in zip(x,area,points):
    color='#177552' if r['strict_pass'] else '#bd3c35';axes[1].scatter([xx],[yy],color=color,s=65,zorder=3)
    axes[1].annotate(f"{yy:.4f}\n{'PASS' if r['strict_pass'] else 'FAIL'}",(xx,yy),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
axes[1].set_ylabel('Área del die (mm²)');axes[1].margins(y=.28)
for ax in axes:ax.set_xlabel('Utilización inicial FP_CORE_UTIL (%)');ax.set_xticks(x);ax.grid(axis='y',alpha=.2)
fig.supxlabel('Hold incluye removal del reset. PASS exige también límites eléctricos y controles físicos.',fontsize=9)
fig.savefig(out/'utilizacion_A.png',dpi=180);fig.savefig(out/'utilizacion_A.svg');plt.close(fig)
(out/'provenance.json').write_text(json.dumps({'source':str(source.relative_to(root)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'points':[r['tag'] for r in points]},indent=2)+'\n')
print('PASS utilization plot')
