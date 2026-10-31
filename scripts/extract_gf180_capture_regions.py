#!/usr/bin/env python3
"""Read-only OpenDB/netlist tracing for KLayout GUI annotations."""
import argparse, hashlib, json, re
from pathlib import Path
from openroad import Tech, Design
from audit_gf180_liberty_limits import parse_netlist

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',required=True)
a=p.parse_args();root=Path('/work');run=root/'config/gf180/runs'/a.run;out=root/a.out
assert not out.exists();out.mkdir(parents=True)
sta=next(run.glob('*-openroad-stapostpnr/state_out.json'))
state=json.loads(sta.read_text());odb=Path(state['odb']);nl=Path(state['nl'])
gds=run/'final/klayout_gds/asic_top.klayout.gds'
files=[sta,odb,nl,gds,Path(__file__).resolve(),root/'scripts/audit_gf180_liberty_limits.py']
before={str(f.relative_to(root)):sha(f) for f in files}
cells,_=parse_netlist(nl)
groups={'rf':sorted(n for n in cells if n.startswith('u_soc.u_core.u_rf.')),
        'alu':sorted(n for n in cells if n.startswith('u_soc.u_core.u_id.u_alu.')),
        'counter':sorted(n for n,c in cells.items() if re.fullmatch(r'u_soc\.u_periph\.cycles_q\[\d+\]',c['connections'].get('Q','')))}
method='Exact hierarchical RF/ALU instance names; counter FF Q signals cycles_q[0:31]; final netlist masters match routed OpenDB.'
extra={}
if not groups['alu'] or not groups['rf']:
    # This specific historical A lost its ALU boundary during flattening.
    # Reuse only the previously proved RF identities; never guess an ALU box.
    assert a.run=='stage6_100ns_u40_final_a', 'Unmapped hierarchy needs explicit provenance'
    trace_path=root/'evidence/gf180_traceability/results.json'
    trace=json.loads(trace_path.read_text())
    prior=trace['variants']['a']
    assert prior['physical_trace']['source_def']==str((run/'final/def/asic_top.def').relative_to(root))
    for n,h in trace['input_sha256'].items(): assert sha(root/n)==h, n
    groups['rf']=prior['regions']['rf_all_registers']['instances']
    assert len(groups['rf'])==544
    groups.pop('alu')
    before[str(trace_path.relative_to(root))]=sha(trace_path)
    method='Historical A RF state cells recovered by Q/source provenance and exact IDs; counter state by cycles_q. ALU boundary unavailable after flattening.'
    extra=dict(capture_groups=['overview','rf','counter'],
               colors={'rf':0x1766c5,'counter':0x00805a},
               labels={'rf':'RF: 544 registros trazados','counter':'Contador: 32 FF cycles_q'},
               annotation_note='ALU sin correspondencia verificable en este layout')
assert len(groups['counter'])==32 and len(groups['rf'])>0
tech=Tech();design=Design(tech);design.readDb(str(odb));block=tech.getDB().getChip().getBlock();units=block.getDbUnitsPerMicron()
box=lambda r:[r.xMin()/units,r.yMin()/units,r.xMax()/units,r.yMax()/units]
regions={}
for group,names in groups.items():
    selected=[]
    for name in names:
        inst=block.findInst(name);assert inst is not None
        assert inst.getMaster().getName()==cells[name]['cell']
        selected.append(dict(name=name,master=inst.getMaster().getName(),bbox_um=box(inst.getBBox())))
    regions[group]=selected
assert all(sha(root/n)==h for n,h in before.items())
result=dict(run=a.run,gds=str(gds.relative_to(root)),die_bbox_um=box(block.getDieArea()),regions=regions,
            method=method,
            scope='Counter markers cover 32 state FF, not all combinational increment logic. Markers are annotations; GDS is never modified.',input_sha256=before)
result.update(extra)
(out/'regions.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:len(v) for k,v in regions.items()})
