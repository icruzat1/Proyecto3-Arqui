#!/usr/bin/env python3
"""Resize nine GF180 drivers and relocate one existing diode; input unrouted.
Requires clear_signal_routes.py beside this script. No legalization/routing.
Caller must regenerate logical views, placement, routing, extraction and STA.
"""
import argparse, json, re, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
import clear_signal_routes as c


def groups(text, kind, indent):
    hits = list(re.finditer(r'(?m)^' + indent + kind + r'\s*\(\s*(\w+)\s*\)\s*\{', text))
    return {m[1]: text[m.end():hits[i+1].start() if i+1 < len(hits) else len(text)] for i, m in enumerate(hits)}


def pins(text):
    result = {}
    for name, body in groups(text, 'pin', '    ').items():
        direction = re.search(r'\bdirection\s*:\s*(\w+)\s*;', body)
        function = re.search(r'\bfunction\s*:\s*"([^"]*)"', body)
        cap = re.search(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)\s*;', body)
        c.require(direction is not None, f'Missing Liberty direction: {name}')
        result[name] = [direction[1], re.sub(r'\s+', '', function[1]) if function else None, float(cap[1]) if cap else None]
    return result


def signature(block, normalize=None, placements=None, raw=False):
    normalize = normalize or {}
    placements = placements or {}
    instances = [[i.getName(), normalize.get(i.getName(), i.getMaster().getName()), *placements.get(i.getName(), pose(i)), sorted([t.getMTerm().getName(),
                  t.getNet().getName() if t.getNet() else None] for t in i.getITerms())] for i in block.getInsts()]
    nets = [[n.getName(), str(n.getSigType()), bool(n.isSpecial()), sorted(t.getName() for t in n.getBTerms())] for n in block.getNets()]
    ports = [[t.getName(), str(t.getIoType()), str(t.getSigType()), t.getNet().getName() if t.getNet() else None] for t in block.getBTerms()]
    data = [sorted(instances), sorted(nets), sorted(ports)]
    return data if raw else c.digest_bytes(c.json_bytes(data))


def pose(inst):
    return [list(inst.getLocation()), str(inst.getOrient()), str(inst.getPlacementStatus())]


def bbox(obj):
    b = obj.getBBox()
    return [b.xMin(), b.yMin(), b.xMax(), b.yMax()]


def check_diode(block, move, moved=False):
    diode, ref, right, target = [block.findInst(move[k]) for k in ['instance', 'reference_instance', 'right_neighbor', 'target_instance']]
    c.require(all(x is not None for x in [diode, ref, right, target]), 'Missing diode/neighbors/target')
    box = move['new_bbox_dbu']; rb = bbox(ref)
    c.require(diode.getMaster().getName() == ref.getMaster().getName() == move['master'], 'Diode master mismatch')
    c.require(block.getDbUnitsPerMicron() == 2000 and bbox(target) == move['target_bbox_dbu'], 'Coordinate reference changed')
    c.require(rb[2] == box[0] and bbox(right)[0] == box[2] and rb[1::2] == bbox(right)[1::2] == box[1::2], 'Expected exact gap/row changed')
    c.require(diode.getMaster().getWidth() == box[2]-box[0] and diode.getMaster().getHeight() == box[3]-box[1], 'Diode does not fit gap')
    c.require(diode.findITerm('I').getNet().getName() == move['net'], 'Diode net changed')
    for name in move['other_net_diodes_to_preserve']:
        item = block.findInst(name)
        c.require(item is not None and item.findITerm('I').getNet().getName() == move['net'], 'Companion diode missing/disconnected')
    rows = [r for r in block.getRows() if bbox(r)[0] <= rb[0] and bbox(r)[2] >= box[2] and bbox(r)[1::2] == box[1::2] and str(r.getOrient()) == str(ref.getOrient())]
    c.require(rows and any((box[0]-bbox(r)[0]) % r.getSite().getWidth() == 0 for r in rows), 'Destination not aligned on reference row')
    for inst in block.getInsts():
        other = bbox(inst)
        c.require(inst.getName() == move['instance'] or not (max(box[0],other[0]) < min(box[2],other[2]) and max(box[1],other[1]) < min(box[3],other[3])), f'Destination overlap: {inst.getName()}')
    c.require(pose(diode) == ([move['new_location_dbu'], str(ref.getOrient()), 'LOCKED'] if moved else [move['old_location_dbu'], *pose(diode)[1:]]), 'Unexpected diode placement')
    c.require(not moved or bbox(diode) == box, 'Moved diode bbox differs from exact gap')
    return diode, ref


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['input-odb', 'source-state', 'output-dir', 'plan-json']:
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    src, state_path, plan_path = [p.resolve(strict=True) for p in [a.input_odb, a.source_state, a.plan_json]]
    out = a.output_dir.resolve()
    c.require(not out.exists(), 'Output directory must be fresh')
    state, plan = json.loads(state_path.read_text()), json.loads(plan_path.read_text())
    c.require(Path(state['odb']).resolve() == src, 'Source state does not reference the input ODB')
    root = state_path.parents[5]
    c.require(state_path.parent.parent.parent == root/'config/gf180/runs', 'Unexpected source-state location')
    changes = plan['changes']
    move = plan['diode_move']
    c.require(move['instance'] == 'ANTENNA_1207' and move['new_location_dbu'] == [2363200,1105440] and move['new_bbox_dbu'] == [2363200,1105440,2365440,1113280] and move['placement_status'] == 'LOCKED', 'Unapproved diode relocation')
    expected = {'fanout8781', 'fanout6971', 'fanout14583', 'fanout14102', 'fanout6968', '_30746_', '_30765_', '_27038_', '_30912_'}
    c.require(len(changes) == 9 and {x['instance'] for x in changes} == expected, 'Plan must contain precisely the approved nine instances')
    for x in changes:
        c.require(x['old_master'].startswith('gf180mcu_fd_sc_mcu7t5v0__') and x['old_master'].endswith('_1') and
                  x['new_master'] == x['old_master'][:-1] + '2', 'Only same-function-family _1 to _2 substitutions allowed')
    source_index = state_path.parent.parent/'input_sha256.json'
    source_hashes = json.loads(source_index.read_text())
    c.require(isinstance(source_hashes, dict) and source_hashes, 'Missing source-run provenance')
    required = {root/n: h for n, h in source_hashes.items()}
    required.update({Path(n): h for n, h in plan['source_checks'].items()})
    required.update({Path(x['path']): x['sha256'] for x in plan['libraries']})
    c.require(plan['source_checks'] and required, 'Missing source hashes')
    for path, digest in required.items():
        c.require(c.sha256(path) == digest, f'Stale source: {path}')
    inputs = set(required) | {src, state_path, source_index, plan_path, Path(__file__).resolve(), Path(c.__file__).resolve()}
    records = [c.artifact(p) for p in sorted(inputs)]
    corners = {rc+'_'+pvt for rc in ['nom', 'min', 'max'] for pvt in ['tt_025C_5v00', 'ss_125C_4v50', 'ff_n40C_5v50']}
    c.require(len(plan['libraries']) == 9 and {x['corner'] for x in plan['libraries']} == corners, 'Expected all nine corners')
    cache, liberty_checks = {}, {}
    for lib in plan['libraries']:
        if lib['path'] not in cache:
            cache[lib['path']] = groups(Path(lib['path']).read_text(), 'cell', '  ')
        cells, checked = cache[lib['path']], []
        for x in changes:
            c.require(x['old_master'] in cells and x['new_master'] in cells, 'Missing exact Liberty master')
            old, new = pins(cells[x['old_master']]), pins(cells[x['new_master']])
            c.require(old and old.keys() == new.keys() and all(old[p][:2] == new[p][:2] for p in old), 'Liberty pin/function mismatch')
            p = x['pin']
            c.require(old[p][0] == 'output' and old[p][1] is not None and old[p][2] is not None and new[p][2] > old[p][2], 'Output function/capacity check failed')
            checked.append({'instance': x['instance'], 'function': old[p][1], 'old_cap_pf': old[p][2], 'new_cap_pf': new[p][2]})
        liberty_checks[lib['corner']] = checked
    # swapMaster invokes STA equivalence callbacks: load the matching Liberty
    # before the ODB, even though this operation does not analyze timing.
    from openroad import Tech, Design
    tech = Tech()
    tech.readLiberty(plan['libraries'][0]['path'])
    design = Design(tech)
    design.readDb(str(src))
    block = tech.getDB().getChip().getBlock()
    before, logical_before = c.snapshot(block), signature(block)
    before_details = signature(block, raw=True)
    c.require(before['non_supply_regular_wire_count'] == 0, 'Clear all regular signal/clock wires first')
    diode, reference = check_diode(block, move)
    old_pose = pose(diode)
    targets = []
    master_pins = lambda m: sorted((p.getName(), str(p.getIoType()), str(p.getSigType())) for p in m.getMTerms())
    for x in changes:
        inst, master = block.findInst(x['instance']), tech.getDB().findMaster(x['new_master'])
        c.require(inst is not None and master is not None, 'Exact instance/master unavailable')
        c.require(inst.getMaster().getName() == x['old_master'], 'Instance differs from approved old master')
        c.require(master_pins(inst.getMaster()) == master_pins(master), 'Physical master pin mismatch')
        c.require(callable(getattr(inst, 'swapMaster', None)), 'OpenDB swapMaster unavailable')
        targets.append((inst, master))
    out.mkdir(parents=True)
    manifest = {'status': 'running', 'inputs': records, 'plan': changes, 'liberty_checks': liberty_checks,
                'before': before, 'diode_move': move, 'diode_before_pose': old_pose,
                'legalization_and_fresh_routing_required': True, 'antenna_recheck_required': True, 'signoff_claimed': False}
    try:
        with tempfile.TemporaryDirectory(prefix='.verify-', dir=out) as tmp:
            tmp = Path(tmp)
            original, changed, odb, reread_def = [tmp/n for n in ['before.def', 'after.def', 'resized.odb', 'reread.def']]
            design.writeDef(str(original))
            for inst, master in targets:
                location = inst.getLocation()
                c.require(inst.swapMaster(master), f'swapMaster failed: {inst.getName()}')
                # Reflected instances otherwise shift by the master width delta.
                inst.setLocation(*location)
            diode.setOrient(reference.getOrient()); diode.setLocation(*move['new_location_dbu']); diode.setPlacementStatus('LOCKED')
            check_diode(block, move, moved=True)
            c.require(all(block.findInst(x['instance']).getMaster().getName() == x['new_master'] for x in changes), 'Wrong resulting master')
            normalized_details = signature(block, {x['instance']: x['old_master'] for x in changes}, {move['instance']: old_pose}, raw=True)
            if normalized_details != before_details:
                diff = [[a,b] for old,new in zip(before_details, normalized_details) for a,b in zip(old,new) if a != b]
                print(json.dumps({'unexpected_changes': diff[:12]}), flush=True)
            c.require(normalized_details == before_details, 'Connectivity/positions/other instances changed')
            after = c.snapshot(block)
            c.require(after['non_supply_regular_wire_count'] == 0, 'Unexpected regular signal wires')
            design.writeDef(str(changed))
            normalized = changed.read_text()
            for x in changes:
                normalized, count = re.subn(r'(?m)^(\s*-\s+' + re.escape(x['instance']) + r'\s+)' + re.escape(x['new_master']) + r'(?=\s)', lambda m: m[1]+x['old_master'], normalized)
                c.require(count == 1, 'Expected one DEF master replacement per instance')
            pattern = r'(?ms)^[ \t]*-[ \t]+' + re.escape(move['instance']) + r'[ \t]+.*?;'
            original_records, changed_records = re.findall(pattern, original.read_text()), re.findall(pattern, normalized)
            c.require(len(original_records) == len(changed_records) == 1, 'Expected unique diode DEF record')
            normalized = re.sub(pattern, lambda m: original_records[0], normalized)
            c.require(normalized == original.read_text(), 'DEF changed beyond nine masters and one diode placement')
            design.writeDb(str(odb))
            other_tech, other, other_block = c.load_design(odb)
            c.require(c.snapshot(other_block) == after and signature(other_block) == signature(block), 'ODB readback changed')
            check_diode(other_block, move, moved=True)
            other.writeDef(str(reread_def))
            c.require(c.sha256(changed) == c.sha256(reread_def), 'ODB/DEF readback incongruent')
            for record in records:
                c.require(c.sha256(record['path']) == record['sha256'], 'Input changed during resizing')
            c.require(all(c.sha256(p) == digest for p, digest in required.items()), 'Expected source hash changed')
            final_odb, final_def = out/(block.getName()+'.odb'), out/(block.getName()+'.def')
            odb.rename(final_odb); reread_def.rename(final_def)
        manifest.update(status='verified', input_hashes_unchanged=True, after=after,
                        normalized_connectivity_sha256=logical_before, def_only_expected_master_and_diode_changes=True,
                        outputs=[c.artifact(final_odb), c.artifact(final_def)])
    except Exception as exc:
        manifest.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        raise
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': manifest['status'], 'resized_instances': len(changes), 'relocated_diode': move['instance'], 'manifest': str(out/'manifest.json')}))


if __name__ == '__main__':
    main()
