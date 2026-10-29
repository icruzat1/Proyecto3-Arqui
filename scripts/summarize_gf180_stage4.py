#!/usr/bin/env python3
"""Archive initial GF180 results and draw geometry directly from the DEF pins."""
from collections import Counter
import gzip
import hashlib
import html
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/gf180_stage4'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    summary={'scope':'Initial mapped synthesis and floorplan through custom IO placement; no placement/CTS/routing signoff',
             'clock_period_ns':100,'target_core_utilization_percent':40,'physical_signoff':False,
             'timing_closed':False,'floorplan_runs_passed':True,'runs':{}}
    artifacts={}
    def copy(p,dest):
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dest)
        artifacts[p.relative_to(ROOT).as_posix()]={'archived':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest)}
    svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 640">',
         '<rect width="1100" height="640" fill="#f7f9fc"/>',
         '<g font-family="Arial,sans-serif" fill="#15243b">',
         '<text x="40" y="35" font-size="24">Primer floorplan GF180 · A y B a la misma escala</text>',
         '<text x="40" y="61" font-size="14">Contorno, núcleo y terminales extraídos del DEF. No muestra colocación ni ruteo de señales.</text>']
    for v,origin in [('a',90),('b',550)]:
        run=ROOT/f'config/gf180/runs/stage4_100ns_u40_floorplan_{v}'
        snapshot=json.loads((run/'input_sha256.json').read_text())
        assert all(sha(ROOT/n)==h for n,h in snapshot.items()), 'Stale floorplan inputs'
        syn=next(run.glob('*-yosys-synthesis'))
        io=next(run.glob('*-odb-customioplacement'))
        pdn=next(run.glob('*-openroad-generatepdn'))
        sta=next(run.glob('*-openroad-staprepnr'))
        s=json.loads((syn/'state_out.json').read_text())['metrics']
        metrics=json.loads((io/'state_out.json').read_text())['metrics']
        net=json.loads((syn/'asic_top.nl.v.json').read_text())
        counts=Counter(c['type'] for c in net['modules']['asic_top']['cells'].values())
        assert all(t.startswith('gf180mcu_fd_sc_mcu7t5v0__') for t in counts)
        top=[{'cell':t,'count':n,'cell_area_um2':float(net['modules'][t]['attributes']['area'])} for t,n in counts.most_common(5)]
        text=(io/'asic_top.def').read_text()
        pins=text.split('PINS 30 ;',1)[1].split('END PINS',1)[0]
        pinblocks=re.findall(r'\s+- (\S+) \+ NET .*?;',pins,re.S)
        assert len(pinblocks)==30
        assert metrics['design__power_grid_violation__count']==0
        entry={'input_sha256':snapshot,'synthesis_cell_count':s['design__instance__count'],
               'synthesis_cell_area_um2':s['design__instance__area'],
               'mapped_sequential_cells':metrics['design__instance__count__class:sequential_cell'],
               'top_five_cells_by_count':top,'floorplan_metrics':metrics,
               'signal_terminals':28,'power_terminals':2,
               'synthesis_netlist_sha256':sha(syn/'asic_top.nl.v'),
               'floorplan_def_sha256':sha(io/'asic_top.def'),
               'warning_count':metrics['design__lint_warning__count']}
        summary['runs'][v]=entry
        dest=OUT/v
        for step in [syn,io,pdn]:
            for name in ['config.json','state_out.json','COMMANDS']:
                if (step/name).exists():copy(step/name,dest/step.name/name)
            for p in step.glob('*.log'):copy(p,dest/step.name/p.name)
        for corner in sta.iterdir():
            if corner.is_dir():
                for name in ['wns.max.rpt','wns.min.rpt','tns.max.rpt','tns.min.rpt','ws.max.rpt','ws.min.rpt','checks.rpt']:
                    if (corner/name).exists():copy(corner/name,dest/'pre_pnr_sta'/corner.name/name)
        copy(next(run.glob('*-verilator-lint/verilator-lint.log')),dest/'lint.log')
        copy(run/'input_sha256.json',dest/'input_sha256.json')
        for src in [syn/'asic_top.nl.v',io/'asic_top.def']:
            target=dest/(src.name+'.gz');target.write_bytes(gzip.compress(src.read_bytes(),mtime=0))
            artifacts[src.relative_to(ROOT).as_posix()]={'archived':target.relative_to(ROOT).as_posix(),
                'uncompressed_sha256':sha(src),'compressed_sha256':sha(target)}
        scale=.27;base=520
        box=list(map(float,metrics['design__die__bbox'].split()));core=list(map(float,metrics['design__core__bbox'].split()))
        w,h=box[2]*scale,box[3]*scale
        svg += [f'<text x="{origin}" y="{base-h-35}" font-size="21">Memoria {v.upper()}</text>',
                f'<text x="{origin}" y="{base-h-14}" font-size="13">{box[2]:.2f} × {box[3]:.2f} µm</text>',
                f'<rect x="{origin}" y="{base-h}" width="{w}" height="{h}" fill="#e2eaf3" stroke="#15243b" stroke-width="2"/>',
                f'<rect x="{origin+core[0]*scale}" y="{base-core[3]*scale}" width="{(core[2]-core[0])*scale}" height="{(core[3]-core[1])*scale}" fill="white" stroke="#94a3b8" stroke-dasharray="4 3"/>']
        # All rectangles are DEF pin shapes with orientation N in this run.
        for block in re.findall(r'\s+- .*?;',pins,re.S):
            name=re.match(r'\s+- (\S+)',block).group(1)
            place=re.search(r'\+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \) (\S+)',block)
            assert place and place[3]=='N'
            x,y=int(place[1])/2000,int(place[2])/2000
            color={'VDD':'#e35d6a','VSS':'#397fb8'}.get(name,'#163f63')
            if name in ('VDD','VSS'):
                for a,b,c,d in re.findall(r'\+ LAYER \S+ \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)',block):
                    a,b,c,d=[int(z)/2000 for z in (a,b,c,d)]
                    svg.append(f'<rect x="{origin+(x+a)*scale}" y="{base-(y+d)*scale}" width="{(c-a)*scale}" height="{(d-b)*scale}" fill="{color}" opacity=".65"/>')
            else:
                svg.append(f'<circle cx="{origin+x*scale}" cy="{base-y*scale}" r="2.8" fill="{color}"><title>{html.escape(name)}</title></circle>')
        svg.append(f'<text x="{origin}" y="552" font-size="16">Die: {metrics["design__die__area"]/1e6:.3f} mm² · objetivo 40 %</text>')
    svg += ['<text x="40" y="595" font-size="14">Rojo: terminales de VDD · azul: terminales de VSS · puntos: 28 señales · núcleo: línea discontinua.</text>',
            '<text x="40" y="620" font-size="14">La red de alimentación no tiene violaciones de conectividad reportadas; timing y signoff siguen pendientes.</text>','</g></svg>']
    (OUT/'floorplans.svg').write_text('\n'.join(svg))
    test=ROOT/'build/gf180_mapped_game'
    mapped=json.loads((test/'results.json').read_text());assert mapped['all_passed']
    summary['mapped_game']=mapped
    for p in test.iterdir():
        if p.suffix=='.log' or p.name=='results.json':copy(p,OUT/'mapped_game'/p.name)
    for v in 'ab':
        r=ROOT/f'config/gf180/runs/stage4_100ns_u40_wait_only_{v}'
        step=next(r.glob('*-yosys-synthesis'))
        for n in ['config.json','state_out.json','yosys-synthesis.log']:copy(step/n,OUT/'mapped_game'/v/n)
    for p in (ROOT/'build/gf180_game/firmware').iterdir():
        if p.is_file():copy(p,OUT/'mapped_game/firmware'/p.name)
    summary['artifacts']=artifacts
    (OUT/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('PASS archived GF180 evidence and DEF-derived floorplan drawing')

if __name__=='__main__':main()
