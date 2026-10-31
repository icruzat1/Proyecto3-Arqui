"""Read-only locations of the repaired B antenna example in before/after GDS."""
import argparse, hashlib, json
from pathlib import Path
from openroad import Tech, Design

p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',required=True);a=p.parse_args()
root=Path('/work');run=root/'config/gf180/runs'/a.run;out=root/a.out;assert not out.exists() or not any(out.iterdir());out.mkdir(parents=True,exist_ok=True)
state_path=next(run.glob('*-openroad-stapostpnr/state_out.json'));state=json.loads(state_path.read_text())
odb=Path(state['odb']);gds=run/'final/klayout_gds/asic_top.klayout.gds'
files=[state_path,odb,gds,Path(__file__).resolve()]
hashes={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
tech=Tech();design=Design(tech);design.readDb(str(odb));block=tech.getDB().getChip().getBlock();u=block.getDbUnitsPerMicron()
box=lambda r:[r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
target=block.findInst('fanout10268');diode=block.findInst('ANTENNA_1207');assert target and diode
net=target.findITerm('I').getNet();assert net.getName()=='net10289' and diode.findITerm('I').getNet().getName()==net.getName()
groups={'gate':[target],'diode':[diode]}
regions={k:[dict(name=i.getName(),master=i.getMaster().getName(),bbox_um=box(i.getBBox())) for i in v] for k,v in groups.items()}
b=box(target.getBBox());view=[b[0]-80,b[1]-30,b[2]+80,b[3]+100]
result=dict(run=a.run,gds=str(gds.relative_to(root)),die_bbox_um=box(block.getDieArea()),capture_bbox_um=view,
            regions=regions,labels={'gate':'Puerta afectada: fanout10268/I','diode':'Diodo reubicado: ANTENNA_1207'},
            colors={'gate':0xc42b23,'diode':0x00805a},capture_groups=['overview'],net='net10289',
            method='Exact gate/diode IDs and connectivity to net10289 checked in routed OpenDB.',input_sha256=hashes)
(out/'regions.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
print('Antenna example mapped',a.run)
