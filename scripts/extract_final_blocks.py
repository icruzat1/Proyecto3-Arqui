"""Identify all functional blocks in the actual final ODB; no design changes."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
from openroad import Tech,Design
from audit_gf180_liberty_limits import parse_netlist,parse_liberty
from measure_gf180_area import liberty_cells
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--synthesis',required=True);p.add_argument('--out',required=True)
a=p.parse_args();root=Path('/work');run=root/'config/gf180/runs'/a.run;out=root/a.out
assert not out.exists();out.mkdir(parents=True)
sta=next(run.glob('*-openroad-stapostpnr/state_out.json'));state=json.loads(sta.read_text())
nl=Path(state['nl']);odb=Path(state['odb']);gds=run/'final/klayout_gds/asic_top.klayout.gds'
sn=root/'config/gf180/runs'/a.synthesis/'06-yosys-synthesis/asic_top.nl.v'
lib=root/'.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib'
files=[sta,nl,odb,gds,sn,lib,Path(__file__),root/'scripts/audit_gf180_liberty_limits.py',root/'scripts/measure_gf180_area.py']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(f.relative_to(root)):sha(f) for f in files}
cells,_=parse_netlist(nl);syn,_=parse_netlist(sn);library=liberty_cells(lib);pins=parse_liberty(lib)['cells']
prefixes={'rf':'u_soc.u_core.u_rf.','alu':'u_soc.u_core.u_id.u_alu.','memory':'u_mem.',
 'instruction_rom':'u_mem.gen_a.u_memory.u_instr_rom.','data_rom':'u_mem.gen_a.u_memory.u_data_rom.',
 'decode':'u_soc.u_core.u_id.u_decoder.','fetch':'u_soc.u_core.u_if.','load_store':'u_soc.u_core.u_lsu.',
 'control':'u_soc.u_core.u_ctrl.','peripherals':'u_soc.u_periph.','spi':'u_soc.u_spi.',
 'reset':'u_reset.','buttons':'u_buttons.'}
groups={k:sorted(n for n in cells if n.startswith(v)) for k,v in prefixes.items()}
if a.run.endswith('_b'):
 for k in ['instruction_rom','data_rom']:groups.pop(k)
 for k in ['instruction_rom','data_rom']:prefixes.pop(k)
drivers={};consumers=defaultdict(set)
for n,c in syn.items():
 for pin,net in c['connections'].items():
  if pins[c['cell']].get(pin,{}).get('direction')=='output':
   assert net not in drivers;drivers[net]=n
  elif pins[c['cell']].get(pin,{}).get('direction')=='input':consumers[net].add(n)
counter={n for n,c in syn.items() if re.fullmatch(r'u_soc\.u_periph\.cycles_q\[\d+\]',c['connections'].get('Q',''))}
assert len(counter)==32
cone=set(counter);queue=[syn[n]['connections']['D'] for n in counter]
while queue:
 net=queue.pop()
 if net.startswith("1'"):continue
 n=drivers[net]
 if n in cone:continue
 c=syn[n];assert not library[c['cell']]['sequential'],n
 cone.add(n);queue.extend(v for pin,v in c['connections'].items() if pins[c['cell']][pin]['direction']=='input')
for n in cone-counter:
 for pin,net in syn[n]['connections'].items():
  if pins[syn[n]['cell']][pin]['direction']=='output':assert consumers[net]<=cone
assert all(n in cells for n in cone)
groups['counter']=sorted(cone)
assert len(groups['alu'])==589 and len(groups['rf'])==1804
assert all(groups.values()),'A required block is unidentifiable'
tech=Tech();design=Design(tech);design.readDb(str(odb));block=tech.getDB().getChip().getBlock();units=block.getDbUnitsPerMicron()
box=lambda b:[b.xMin()/units,b.yMin()/units,b.xMax()/units,b.yMax()/units]
regions={}
for g,names in groups.items():
 selected=[]
 for n in names:
  inst=block.findInst(n);assert inst is not None and inst.getMaster().getName()==cells[n]['cell'],n
  selected.append(dict(name=n,master=inst.getMaster().getName(),bbox_um=box(inst.getBBox())))
 regions[g]=selected
direct=defaultdict(float);inc=defaultdict(float)
for n,c in syn.items():
 path=n.split('.')[:-1]
 direct['.'.join(path) or '<synthesis_support>']+=library[c['cell']]['area_um2']
 for i in range(1,len(path)+1):inc['.'.join(path[:i])]+=library[c['cell']]['area_um2']
total=sum(direct.values());counter_area=sum(library[syn[n]['cell']]['area_um2'] for n in cone)
all_inst={}
for n,c in cells.items():
 inst=block.findInst(n);assert inst is not None and inst.getMaster().getName()==c['cell']
 all_inst[n]=dict(master=c['cell'],module='.'.join(n.split('.')[:-1]) or '<physical_support>',origin_um=[x/units for x in inst.getLocation()])
assert all(sha(root/n)==h for n,h in before.items())
labels={'rf':'RF','alu':'ALU','counter':'Contador: FF y logica de incremento','memory':'Memoria A: ROM y RAM',
 'instruction_rom':'ROM de instrucciones','data_rom':'ROM lectura de datos','decode':'Decodificador','fetch':'Fetch',
 'load_store':'Unidad load/store','control':'Control del procesador','peripherals':'Perifericos MMIO',
 'spi':'SPI','reset':'Reset','buttons':'Sincronizacion de botones'}
if a.run.endswith('_b'):labels['memory']='Memoria B: FF y carga'
r=dict(run=a.run,synthesis_run=a.synthesis,gds=str(gds.relative_to(root)),die_bbox_um=box(block.getDieArea()),
 regions=regions,capture_groups=['overview',*groups],labels=labels,
 colors={k:v for k,v in zip(groups,[0x1766c5,0xd64e0a,0x79459d,0x966a00,0x558900,0x267079,0x8c414f,0x536e97,0x772252,0x93672d,0x194c77,0x663d99,0x6d6720,0x00805a])},
 overview_groups=['rf','alu','counter'],input_sha256=before,
 method='Exact hierarchical final cell names and master identities in OpenDB; counter is exclusive D feedback cone rooted in 32 cycles_q FF, derived from the matching synthesis.',
 scope='Block groups may overlap (memory/ROM and peripherals/counter); do not sum their areas. Physical support cells classified separately; original GDS/ODB unchanged.',
 synthesis=dict(total_area_um2=total,direct_partition_um2=dict(direct),inclusive_module_area_um2=dict(inc),
  top_five=Counter(c['cell'] for c in syn.values()).most_common(5),counter_cells=len(cone),counter_ff=32,
  counter_area_um2=counter_area,counter_fraction=counter_area/total,cell_count=len(syn)),
 final_instance_count=len(all_inst))
(out/'regions.json').write_text(json.dumps(r,indent=2)+'\n')
(out/'all_instances.json').write_text(json.dumps(all_inst,indent=2)+'\n')
print(json.dumps({'groups':{k:len(v) for k,v in groups.items()},'synthesis_area':total,'counter_area':counter_area,'counter_fraction':counter_area/total}))
