#!/usr/bin/env python3
"""Read final DEF/config/STA evidence; do not modify or run implementation."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 results={}
 for v,tag,archive in [('a','stage13_final_traceable_a','evidence/gf180_final_a_traceable/results.json'),('b','stage12_electrical_route_b','evidence/gf180_final_b_electrical/results.json')]:
  src=ROOT/archive;e=read(src)['runs'][v];assert e['extracted_sta']['verification']['setup_hold_passed']
  run=ROOT/'config/gf180/runs'/tag;cfgpath=run/'resolved.json';cfg=read(cfgpath);deffile=run/'final/def/asic_top.def';text=deffile.read_text()
  units=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',text)[1]);die=[int(n)/units for n in re.search(r'DIEAREA\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)',text).groups()]
  block=text.split('PINS ',1)[1].split('END PINS',1)[0];pins=[]
  for name,body in re.findall(r'^\s*-\s+(\S+)\s+(.*?);',block,re.M|re.S):
   use=re.search(r'\+ USE (\w+)',body)[1];xy=re.search(r'\+ (?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)',body);x,y=[int(n)/units for n in xy.groups()]
   edge=min({'oeste':abs(x-die[0]),'este':abs(x-die[2]),'sur':abs(y-die[1]),'norte':abs(y-die[3])},key=lambda k:{'oeste':abs(x-die[0]),'este':abs(x-die[2]),'sur':abs(y-die[1]),'norte':abs(y-die[3])}[k]) if use=='SIGNAL' else None
   pins.append(dict(name=name,use=use,position_um=[x,y],edge=edge,layers=sorted(set(re.findall(r'\+ LAYER (\w+)',body)))))
  assert len(pins)==30 and sum(p['use']=='SIGNAL' for p in pins)==28
  mpath=ROOT/e['extracted_sta']['step']/'state_out.json';metrics=read(mpath)['metrics']
  results[v]=dict(measured_run=tag,final_acceptance_run=tag,hierarchy_mode=cfg['SYNTH_HIERARCHY_MODE'],period_ns=cfg['CLOCK_PERIOD'],initial_utilization_percent=cfg['FP_CORE_UTIL'],die_bbox_um=die,die_area_um2=metrics['design__die__area'],stdcell_area_um2=metrics['design__instance__area__stdcell'],placed_utilization=metrics['design__instance__utilization'],sequential_cells=metrics['design__instance__count__class:sequential_cell'],didactic_cost_usd=metrics['design__die__area']/1e6*23000,pins=pins,pdn={k:cfg[k] for k in ['PDN_RAIL_LAYER','PDN_RAIL_WIDTH','PDN_HORIZONTAL_LAYER','PDN_VERTICAL_LAYER','PDN_HWIDTH','PDN_VWIDTH','PDN_HPITCH','PDN_VPITCH','PDN_HSPACING','PDN_VSPACING','PDN_CORE_RING']},verification=e['extracted_sta']['verification'],sources={str(p.relative_to(ROOT)):sha(p) for p in [src,deffile,cfgpath,mpath]})
 out=ROOT/'evidence/gf180_final_comparison';out.mkdir(exist_ok=True);(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 lines=['# Macros finales: comparación, terminales y alimentación','', 'A usa stage13_final_traceable_a y B stage12_electrical_route_b. Ambas parten de la receta deferred_flatten y conservan identificación de todos los bloques funcionales. A añade un retardo local al reset; B conserva su reparación eléctrica. Los resultados físicos incluyen esas correcciones y no se atribuyen exclusivamente a la arquitectura de memoria. Las áreas de síntesis comparables están en Ensayo_RTL_Trazabilidad.md y las capturas y particiones verificadas en Capturas_Layout.md.','', '| Magnitud | A | B |','|---|---:|---:|']
 for label,key,scale,suffix in [('Área stdcell post-PNR, µm²','stdcell_area_um2',1,''),('Área del die, mm²','die_area_um2',1e-6,''),('Celdas secuenciales','sequential_cells',1,''),('Utilización física, %','placed_utilization',100,''),('Costo didáctico, USD','didactic_cost_usd',1,'')]:lines.append('| '+label+' | '+' | '.join(f"{results[v][key]*scale:.6f}" for v in 'ab')+' |')
 lines+=['','Ambos usan 100 ns y utilización inicial 40 %. La utilización física final cambia al insertar buffers, reparar redes y construir el reloj. No confundirla con el objetivo de floorplan. Costo = área del die en mm² × 23.000 USD/mm²: no es una cotización e ignora máscaras, rendimiento, encapsulado, pruebas y costos fijos. Los barridos de las implementaciones anteriores están completos en Barridos_GF180.md; no se trasladan automáticamente sus resultados a estos finales corregidos. Esta corrección se valida a10MHz, sin declarar un máximo absoluto.','','## Terminales verificados en los DEF finales','', 'Cada macro tiene 28 terminales de señal y VDD/VSS. Son pines de macro; no se diseñó un anillo de pads de encapsulado. La agrupación facilita integración y lectura, sin afirmar que sea la única ubicación óptima.','']
 for v,r in results.items():
  lines.append('**'+v.upper()+'**')
  for edge in ['norte','oeste','este','sur']:lines.append('- '+edge+': '+', '.join(p['name'] for p in r['pins'] if p['edge']==edge)+'.')
  lines.append('')
 lines+=['## Alimentación y límites','', 'Ambos usan rieles Metal1 de 0,6 µm y una malla Metal4 vertical / Metal5 horizontal de 1,6 µm de ancho. Los pasos de la malla son 153,6 µm vertical y 153,18 µm horizontal; separación configurada 1,7 µm. No se habilita anillo de núcleo. VDD/VSS aparecen como terminales especiales de alimentación en Metal4/Metal5. Se mantienen parámetros de la configuración GF180 utilizada para conectar filas y distribuir alimentación sin inventar una geometría ajena al PDK.','', 'Los controles de conectividad y los DRC disponibles aprobados respaldan la implementación académica. No demuestran caída IR o electromigración aprobadas: no hay un contrato completo de fuentes de alimentación/corriente para declarar signoff de potencia. KLayout DRC está omitido por ausencia de runset. La nueva B presenta cero excesos de capacidad, transición y fanout en las nueve esquinas; el cierre académico anterior se conserva como historial.','', 'Datos, coordenadas y huellas de DEF/config/STA: [evidence/gf180_final_comparison/results.json](../evidence/gf180_final_comparison/results.json).']
 (ROOT/'docs/Comparacion_Final_AB.md').write_text('\n'.join(lines)+'\n')
 print('PASS: two final DEFs, 30 terminals each, metrics and source hashes consolidated.')
if __name__=='__main__':main()
