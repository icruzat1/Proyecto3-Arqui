#!/usr/bin/env python3
"""Consolidate measured sweep points, preserving failures and missing evidence."""
import hashlib,json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    progress=read(ROOT/'build/gf180_sweeps/progress.json')
    sources=[ROOT/'evidence/gf180_trace_physical_ref_a/results.json']
    sources += [ROOT/x['evidence']/'results.json' for x in progress['completed']]
    replacement=ROOT/'evidence/gf180_sweeps/stage8_t40_u40_nomargin_a/results.json'
    if replacement.exists():sources.append(replacement)
    sources=list(dict.fromkeys(sources))
    academic_path=ROOT/'evidence/gf180_final_b_academic/results.json'
    academic=read(academic_path) if academic_path.exists() else None
    rows=[];incomplete=[]
    for path in sources:
        archive=read(path)
        for v,e in archive['runs'].items():
            if not e['available']:continue
            rec=e['flow_result'];command=rec.get('command',[])
            if '--run-tag' in command:
                tag=command[command.index('--run-tag')+1]
            else:
                # A recovered Docker completion records its real exit event,
                # not an invented original host command.
                recovery=rec['recovery']
                event_path=ROOT/recovery['event_file']
                assert sha(event_path)==recovery['event_sha256']
                event=read(event_path)
                assert int(event['Actor']['Attributes']['exitCode'])==rec['returncode']
                tag=Path(e['extracted_sta']['step']).parent.name
            run=ROOT/'config/gf180/runs'/tag
            cfg=read(run/'resolved.json')
            verification=e['extracted_sta']['verification']
            if not verification['source_verified']:
                incomplete.append(dict(tag=tag,evidence=str(path.relative_to(ROOT)),reason='No complete extracted STA; excluded from numerical timing tables.'))
                continue
            assert verification['complete_fresh_nine_corners'] and verification['annotation_and_propagation_verified']
            corners={c:d['metrics'] for c,d in e['extracted_sta']['corners'].items()}
            for c,m in corners.items():
                for kind in ['setup','hold']:
                    for field in ['wns','tns','ws']:
                        value=m[f'timing__{kind}__{field}'];assert math.isfinite(value)
                        if field!='ws':assert value<=0
            sta=ROOT/e['extracted_sta']['step'];metrics=read(sta/'state_out.json')['metrics']
            timing_pass=verification['setup_hold_passed']
            physical_pass=all(e['checks'][k]['status']=='pass' for k in ['routing_drc','magic_drc','lvs','antenna','disconnected_pins','xor','illegal_overlap'])
            row=dict(tag=tag,variant=v,period_ns=cfg['CLOCK_PERIOD'],core_util_percent=cfg['FP_CORE_UTIL'],
                     hierarchy_mode=cfg['SYNTH_HIERARCHY_MODE'],extra_setup_optimization_margin_ns=cfg.get('GRT_RESIZER_SETUP_SLACK_MARGIN',0),evidence=str(path.relative_to(ROOT)),evidence_sha256=sha(path),
                     corners=corners,verification=verification,checks=e['checks'],timing_pass=timing_pass,
                     physical_pass=physical_pass,strict_pass=timing_pass and physical_pass and verification['electrical_passed'],
                     stdcell_area_um2=metrics['design__instance__area__stdcell'],die_area_um2=metrics['design__die__area'],
                     placed_utilization=metrics['design__instance__utilization'],
                     sequential_cell_count=metrics.get('design__instance__count__class:sequential_cell'),
                     max_timing_violations_per_corner=max(m['timing__setup_vio__count']+m['timing__hold_vio__count'] for m in corners.values()),
                     antenna_violations=e['checks']['antenna'].get('metrics',{}).get('antenna__violating__nets'),routing_drc=e['checks']['routing_drc'].get('value'))
            row['academic_final_acceptance']=bool(academic and academic['source_evidence']==str(path.relative_to(ROOT)) and academic['source_evidence_sha256']==sha(path) and academic['academic_acceptance_passed'])
            row['didactic_cost_usd']=row['die_area_um2']/1e6*23000
            rows.append(row)
    rows.sort(key=lambda r:(r['variant'],r['core_util_percent'],r['period_ns']))
    summary={}
    for v in 'ab':
        points=[r for r in rows if r['variant']==v and r['core_util_percent']==40]
        good=[r for r in points if r['strict_pass']]
        timing=[r for r in points if r['timing_pass']]
        summary[v]={'periods_measured_ns':sorted(r['period_ns'] for r in points),
                    'strict_fmax_observed_MHz':1000/min(r['period_ns'] for r in good) if good else None,
                    'strict_fmax_any_tested_util_MHz':max((1000/r['period_ns'] for r in rows if r['variant']==v and r['strict_pass']),default=None),
                    'timing_only_fmax_MHz':1000/min(r['period_ns'] for r in timing) if timing else None}
    sizes=[r for r in rows if r['variant']=='a' and r['period_ns']==100]
    success=[r for r in sizes if r['strict_pass']]
    result=dict(scope='Production RTL and deferred_flatten sweep; optimization margins explicitly recorded; historical A final is separate.',
                completed_batch=progress.get('finished_utc') is not None and replacement.exists() and all({40,60,100}.issubset({r['period_ns'] for r in rows if r['variant']==v and r['core_util_percent']==40}) for v in 'ab'),point_count=len(rows),rows=rows,incomplete_attempts=incomplete,
                frequency=summary,minimum_successful_A_die_um2=min(r['die_area_um2'] for r in success) if success else None,
                limitations=['KLayout DRC omitted for lack of runset; no fabrication signoff.',
                             'Antenna failures remain failures here unless explicitly justified and accepted.',
                             'Fmax is the highest observed passing point, not an absolute maximum.',
                             'Hold includes recovery/removal checks on reset; no false paths were added.'])
    out=ROOT/'evidence/gf180_sweeps';out.mkdir(exist_ok=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Barridos medidos de período y utilización','',
           'RTL de producción y síntesis `deferred_flatten`. A100/60ns conserva margen adicional de optimización20ns; A40ns y los tres puntos B usan0ns, sin cambiar criterios de aceptación. No se atribuye toda diferencia de área exclusivamente al período. Cada período nuevo vuelve a sintetizar; cada utilización tiene una implementación física nueva. Ningún punto fallido se repara para forzar su aprobación. A final anterior y candidata RTL se conservan por separado.','',
           '| Variante | Período ns | Util. inicial % | Peor setup ns | Peor hold ns | Física | Eléctrica | Cierre estricto |',
           '|---|---:|---:|---:|---:|---|---|---|']
    yn=lambda x:'PASS' if x else 'FAIL'
    for r in rows:
        q=r['verification'];lines.append(f"| {r['variant'].upper()} | {r['period_ns']} | {r['core_util_percent']} | {q['worst_setup_slack_ns']:.6f} | {q['worst_hold_slack_ns']:.6f} | {yn(r['physical_pass'])} | {yn(q['electrical_passed'])} | {yn(r['strict_pass'])} |")
    if academic:
        lines+=['', 'B100ns/40% tiene cierre académico aprobado con avisos eléctricos documentados; el FAIL eléctrico y estricto de esta tabla se conserva. No equivale a incumplimiento del objetivo temporal: B100 sí pasa setup/hold. Ver [decisión](Decision_Cierre_B.md) y [evidencia final](../evidence/gf180_final_b_academic/results.json). La aprobación no se extiende automáticamente a puntos con fallos de timing.']
    lines+=['','[Gráfico de utilización A](../evidence/gf180_sweeps/plots/utilizacion_A.png) · [SVG](../evidence/gf180_sweeps/plots/utilizacion_A.svg)','','## WNS y TNS exigidos','', 'TT corresponde a nom_tt_025C_5v00 y SS a max_ss_125C_4v50. También se comprueban las nueve esquinas: hold puede fallar en FF aunque TT y SS pasen. WNS se muestra recortado a cero cuando no hay violaciones; el margen positivo se muestra como slack en la tabla anterior.','',
            '| Corrida | Esquina | WNS setup | TNS setup | WNS hold | TNS hold |','|---|---|---:|---:|---:|---:|']
    for r in rows:
        for c in ['nom_tt_025C_5v00','max_ss_125C_4v50']:
            m=r['corners'][c];vals=[m[f'timing__{k}__{f}'] for k in ['setup','hold'] for f in ['wns','tns']]
            lines.append('| '+r['tag']+' | '+c+' | '+' | '.join(f'{v:.6f}' for v in vals)+' |')
    lines+=['','## Área y costo didáctico','',
            '| Corrida | Área stdcell µm² | Die mm² | Util. física % | FF secuenciales | Costo equivalente USD |',
            '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['tag']} | {r['stdcell_area_um2']:.0f} | {r['die_area_um2']/1e6:.6f} | {100*r['placed_utilization']:.2f} | {r['sequential_cell_count']} | {r['didactic_cost_usd']:.2f} |")
    lines+=['','Área stdcell es la métrica post-PNR sin relleno; no es el área de síntesis. El costo usa área del die × 23.000 USD/mm²; no es una cotización y excluye rendimiento de fabricación, encapsulado, pruebas, máscaras y costos fijos.','',
            'La utilización se estudia en A, alternativa de menor área; ambas memorias tienen barrido de período. La tabla detallada por las nueve esquinas, controles separados y procedencia está en evidence/gf180_sweeps/summary.json.','',
            'Estado del lote: '+('completo.' if result['completed_batch'] else 'en curso; no presentar estos datos como barrido completo.'),'']
    for v,s in summary.items():
        value=s['strict_fmax_observed_MHz']
        lines.append(f"Frecuencia {v.upper()} observada con cierre estricto a40% en este barrido: "+(f'{value:.6f} MHz.' if value is not None else 'ninguno de los puntos ensayados cumple todos los controles.'))
        timing=s['timing_only_fmax_MHz']
        lines.append(f"Frecuencia {v.upper()} observada solo por setup/hold a40%: "+(f'{timing:.6f} MHz.' if timing is not None else 'ningún punto ensayado aprobado en las nueve esquinas.'))
    for v,s in summary.items():
        if s['strict_fmax_any_tested_util_MHz'] is not None:lines.append(f"Máxima frecuencia aprobada de {v.upper()} considerando todas las utilizaciones probadas: {s['strict_fmax_any_tested_util_MHz']:.6f} MHz.")
    if success:lines.append(f"Menor die A aprobado entre los tamaños ensayados: {result['minimum_successful_A_die_um2']/1e6:.6f} mm².")
    else:lines.append('Ningún tamaño de esta receta pasa aún todos los controles; no se declara un mínimo exitoso de esta serie.')
    lines += ['', 'La A final histórica a100ns/40% sí está aprobada y se conserva fuera de esta serie deferred_flatten. B final a100ns/40% cumple timing y controles físicos ejecutados, con aceptación académica de sus avisos eléctricos. Los 10MHz comprobados de estas versiones no demuestran un máximo absoluto.']
    (ROOT/'docs/Barridos_GF180.md').write_text('\n'.join(lines)+'\n')
    print('Consolidated',len(rows),'points; batch complete:',result['completed_batch'])

if __name__=='__main__':main()
