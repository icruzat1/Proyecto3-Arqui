"""Apply four equivalent drive upgrades and spatially grouped fanout branches.

Input must be a verified unrouted copy. Keep every original diode and signal
endpoint; normalized connectivity must be identical after collapsing buffers.
No timing or electrical PASS is inferred from these structural checks.
"""
import argparse
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
import clear_signal_routes as c
from resize_gf180_drivers import groups, pins

p = argparse.ArgumentParser(description=__doc__)
for key in ['input-odb', 'source-state', 'output-dir', 'plan-json']:
    p.add_argument('--'+key, type=Path, required=True)
a = p.parse_args()
plan = json.loads(a.plan_json.read_text())
assert not a.output_dir.exists()
assert len(plan['changes']) == 4 and len(plan['fanout_nets']) == 12
for lib in plan['libraries']:
    assert c.sha256(lib['path']) == lib['sha256']
    cells = groups(Path(lib['path']).read_text(), 'cell', '  ')
    for change in plan['changes']:
        old, new = [pins(cells[change[k]]) for k in ['old_master', 'new_master']]
        assert old.keys() == new.keys() and all(old[k][:2] == new[k][:2] for k in old)
        assert new[change['pin']][2] > old[change['pin']][2]
    assert pins(cells[plan['branch_master']])['Z'][:2] == ['output', 'I']

from openroad import Tech, Design
import odb
tech = Tech()
tech.readLiberty(plan['libraries'][0]['path'])
design = Design(tech)
design.readDb(str(a.input_odb))
block = tech.getDB().getChip().getBlock()
assert c.snapshot(block)['non_supply_regular_wire_count'] == 0
source_index = a.source_state.parent.parent/'input_sha256.json'
hashes = json.loads(source_index.read_text())
assert all(c.sha256('/work/'+n) == h for n,h in hashes.items())
inputs = [a.input_odb, a.source_state, a.plan_json, source_index, Path(__file__),
          Path(c.__file__), Path(__file__).with_name('resize_gf180_drivers.py')]
records = [c.artifact(x.resolve()) for x in inputs]
before = c.snapshot(block)
original_names = {i.getName() for i in block.getInsts()}
aliases = {}
masters = {x['instance']: x['old_master'] for x in plan['changes']}

def connectivity(normalized=False):
    result = []
    for inst in block.getInsts():
        if normalized and inst.getName() not in original_names:
            continue
        master = masters.get(inst.getName(),inst.getMaster().getName()) if normalized else inst.getMaster().getName()
        connections = []
        for t in inst.getITerms():
            net = t.getNet().getName() if t.getNet() else None
            connections.append([t.getMTerm().getName(), aliases.get(net, net) if normalized else net])
        result.append([inst.getName(), master, list(inst.getLocation()), str(inst.getOrient()),
                       str(inst.getPlacementStatus()), sorted(connections)])
    return sorted(result)

original = connectivity()
ports = [(x.getName(), x.getNet().getName()) for x in block.getBTerms()]
for change in plan['changes']:
    inst = block.findInst(change['instance'])
    master = tech.getDB().findMaster(change['new_master'])
    assert inst and master and inst.getMaster().getName() == change['old_master']
    at = inst.getLocation()
    assert inst.swapMaster(master)
    inst.setLocation(*at)

def key(t):
    return t.getInst().getName()+'/'+t.getMTerm().getName()

def location(t):
    b = t.getInst().getBBox()
    return ((b.xMin()+b.xMax())//2, (b.yMin()+b.yMax())//2)

def distance(x,y):
    return abs(x[0]-y[0])+abs(x[1]-y[1])

branches = []
for item in plan['fanout_nets']:
    net = block.findNet(item['net'])
    assert net and not list(net.getBTerms())
    loads = [t for t in net.getITerms() if str(t.getIoType()) == 'INPUT']
    drivers = [t for t in net.getITerms() if str(t.getIoType()) == 'OUTPUT']
    assert len(drivers) == 1 and key(drivers[0]) == item['pin']
    assert len(loads) == item['total_reported'], (item['net'],len(loads))
    diode_names = set(item['diode_names'])
    assert diode_names == {t.getInst().getName() for t in loads if 'antenna' in t.getInst().getMaster().getName()}
    logic = [t for t in loads if t.getInst().getName() not in diode_names]
    units = {key(t): [t] for t in logic}
    for diode in [t for t in loads if t.getInst().getName() in diode_names]:
        target = min(logic,key=lambda t:(distance(location(t),location(diode)),key(t)))
        units[key(target)].append(diode)
    # Keep each diode with its closest gate; group nearby units while reserving
    # at least three load slots for any later antenna repair.
    remaining = list(units.values())
    groups_out = []
    while remaining:
        first = min(remaining,key=lambda u:(location(u[0]),key(u[0])))
        remaining.remove(first)
        group = list(first)
        while remaining:
            fitting = [u for u in remaining if len(group)+len(u) <= plan['branch_load_target']]
            if not fitting:
                break
            nxt = min(fitting,key=lambda u:(distance(location(first[0]),location(u[0])),key(u[0])))
            remaining.remove(nxt)
            group += nxt
        assert len(group) <= plan['branch_load_target']
        groups_out.append(group)
    assert 2 <= len(groups_out) <= 10
    for number,group in enumerate(groups_out):
        name = f'eco11_{item["net"]}_{number}'
        newnet = odb.dbNet.create(block,name+'_net')
        newnet.setSigType(net.getSigType())
        buf = odb.dbInst.create(block,tech.getDB().findMaster(plan['branch_master']),name)
        assert newnet and buf
        center = tuple(sum(location(t)[axis] for t in group)//len(group) for axis in [0,1])
        buf.setLocation(*center)
        buf.setPlacementStatus('PLACED')
        buf.findITerm('I').connect(net)
        buf.findITerm('Z').connect(newnet)
        for term in group:
            term.connect(newnet)
        aliases[newnet.getName()] = net.getName()
        branches.append(dict(instance=name,master=plan['branch_master'],source_net=net.getName(),
                             output_net=newnet.getName(),loads=[key(t) for t in group]))
    assert sum(str(t.getIoType())=='INPUT' for t in net.getITerms()) == len(groups_out)

assert connectivity(True) == original, 'Unexpected original logic/pin/placement change'
assert ports == [(x.getName(), x.getNet().getName()) for x in block.getBTerms()]
after = c.snapshot(block)
for invariant in ['special_wire_objects_sha256','supply_regular_wires_sha256','special_wires','special_wire_shapes']:
    assert before['invariants'][invariant] == after['invariants'][invariant]
assert after['non_supply_regular_wire_count'] == 0
assert all(c.sha256(x['path']) == x['sha256'] for x in records)
a.output_dir.mkdir(parents=True)
output_odb, output_def = [a.output_dir/('asic_top.'+ext) for ext in ['odb','def']]
design.writeDb(str(output_odb))
design.writeDef(str(output_def))
other_tech, other_design, other_block = c.load_design(output_odb)
assert c.snapshot(other_block) == after, 'ODB readback mismatch'
manifest = dict(status='verified',input_hashes_unchanged=True,inputs=records,
    resized=plan['changes'],branches=branches,diodes_preserved=True,
    normalized_connectivity_unchanged=True,before=before,after=after,
    outputs=[c.artifact(output_odb),c.artifact(output_def)],
    electrical_or_timing_pass_claimed=False)
(a.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS structurally verified ECO:',len(plan['changes']),'resized,',len(branches),'new branches')
