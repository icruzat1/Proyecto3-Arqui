"""Report verified final 10 MHz zero-violation implementations, with scope."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sources={'a':'evidence/gf180_final_a_traceable/results.json','b':'evidence/gf180_final_b_electrical/results.json'}
entries={v:json.loads((root/p).read_text())['runs'][v] for v,p in sources.items()}
for v,e in entries.items():
 q=e['extracted_sta']['verification']
 assert q['source_verified'] and q['complete_fresh_nine_corners'] and q['annotation_and_propagation_verified']
 assert q['setup_hold_passed'] and q['electrical_passed']
 for c in e['extracted_sta']['corners'].values():
  m=c['metrics']
  for k in ['timing__setup_vio__count','timing__hold_vio__count','design__max_cap_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count']:assert m[k]==0,(v,k)
 for k in ['routing_drc','magic_drc','lvs','antenna','disconnected_pins','xor','illegal_overlap']:assert e['checks'][k]['status']=='pass'
rows=[('Setup',0,0),('Hold (incluye recovery/removal)',0,0)]
for label,k in [('DRC de ruteo','routing_drc'),('Magic DRC','magic_drc'),('LVS','lvs')]:rows.append((label,entries['a']['checks'][k]['value'],entries['b']['checks'][k]['value']))
rows += [('Antenas (redes)',entries['a']['checks']['antenna']['metrics']['antenna__violating__nets'],entries['b']['checks']['antenna']['metrics']['antenna__violating__nets']),('Capacidad (salidas únicas)',0,0),('Transición (pines únicos)',0,0),('Fanout > 10 (conductores únicos)',0,0)]
result=dict(period_ns=100,frequency_MHz=10,initial_utilization_percent=40,a_run='stage13_final_traceable_a',b_run='stage12_electrical_route_b',rows=[dict(check=k,a=a,b=b) for k,a,b in rows],source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources.values()},verification={v:e['extracted_sta']['verification'] for v,e in entries.items()},previous_b='stage9_100ns_u40_academic_b',scope='Zero violations in all executed checks, nine timing corners; not full fabrication signoff.',limitations=['KLayout DRC omitted: no runset.','No formal EQY equivalence or IR/EM signoff claimed.','LVS uses the documented DEF/LEF extraction.','Final A and B are repaired versions of their deferred_flatten references; sweeps remain historical measurements.'])
(root/'evidence/gf180_final_comparison/violations_10mhz.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# Violaciones de las versiones finales a 10 MHz','', 'Ambas versiones usan100ns y utilización inicial40%. A: stage13_final_traceable_a. B: stage12_electrical_route_b. La B anterior académica se conserva como respaldo; esta tabla corresponde a la B corregida, no a la anterior.','', '| Control | A | B corregida |','|---|---:|---:|']
lines += [f'| {k} | {a} | {b} |' for k,a,b in rows]
lines += ['', 'Los ceros de setup, hold, capacidad, transición y fanout se verifican en las nueve esquinas. No se suman esquinas ni se mezclan unidades. Los límites Liberty y fanout10 se mantienen; todos los checkers eléctricos vuelven a estar habilitados. La B anterior tenía4salidas de capacidad,6pines de transición y12conductores con fanout excesivo: sus evidencias históricas se preservan.', '', '**Alcance:** KLayout DRC está omitido por falta de runset. No se declara equivalencia formal EQY ni cierre IR/EM; LVS usa la extracción DEF/LEF documentada. Cero violaciones en los controles ejecutados no equivale a validación completa para fabricar.', '', 'Procedencia y conteos: [JSON](../evidence/gf180_final_comparison/violations_10mhz.json). Evidencia nuevaB: [resultados](../evidence/gf180_final_b_electrical/results.json). Historia y reparación: [Cierre_Electrico_B.md](Cierre_Electrico_B.md).']
(root/'docs/Violaciones_Finales_10MHz.md').write_text('\n'.join(lines)+'\n')
print('PASS A/B final executed checks zero in nine corners')
