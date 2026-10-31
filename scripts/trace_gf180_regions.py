#!/usr/bin/env python3
"""Trace mapped area bounds and physical IDs using existing files; no EDA run."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--physical-a-tag', default='stage6_100ns_u40_final_a')
    parser.add_argument('--physical-b-tag', default='stage6_100ns_u40_route_eco3_b')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    require(not output.exists(), 'Output already exists')
    sys.path.insert(0, str(root/'scripts'))
    from audit_gf180_liberty_limits import parse_netlist, parse_liberty, sha
    from measure_gf180_area import liberty_cells
    libpath = root/'.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib'
    library = liberty_cells(libpath)
    pins = parse_liberty(libpath)['cells']
    inputs = {libpath: sha(libpath)}
    for name in ['audit_gf180_liberty_limits.py', 'measure_gf180_area.py']:
        path = root/'scripts'/name; inputs[path] = sha(path)
    result = {'method': 'Mapped synthesis cells: storage-Q provenance, private feedback mux topology, exclusive counter D cone',
              'scope': 'Area lower bounds and actual renamed IDs; not full module partition or signoff',
              'script_sha256':sha(Path(__file__)), 'variants': {}}
    for variant in 'ab':
        base = root/f'config/gf180/runs/stage4_100ns_u40_floorplan_{variant}/06-yosys-synthesis'
        nl, jp, stats = base/'asic_top.nl.v', base/'asic_top.nl.v.json', base/'reports/stat.json'
        for p in [nl, jp, stats]: inputs[p] = sha(p)
        cells, _ = parse_netlist(nl)
        module = json.loads(jp.read_text())['modules']['asic_top']
        total = json.loads(stats.read_text())['design']['area']
        require(len(cells) == len(module['cells']), 'Renamed and JSON cell counts differ')
        area = lambda ids: sum(library[cells[n]['cell']]['area_um2'] for n in sorted(ids))
        require(abs(area(cells)-total) < .01, 'Area differs from synthesis report')
        drivers, consumers = defaultdict(set), defaultdict(set)
        for name, cell in cells.items():
            for pin, net in cell['connections'].items():
                direction = pins[cell['cell']][pin]['direction']
                (drivers if direction == 'output' else consumers)[net].add(name)
        def driver(net):
            require(len(drivers[net]) == 1, f'Expected unique driver of {net}')
            return next(iter(drivers[net]))
        array = 'ram_ff' if variant == 'a' else 'mem_ff'
        memory = {n for n,c in cells.items() if re.fullmatch(r'u_mem\..*\.'+array+r'\[\d+\]\[\d+\]', c['connections'].get('Q',''))}
        require(len(memory) == (512 if variant == 'a' else 4608), 'Unexpected memory bit count')
        muxes = set()
        for n in memory:
            q,d = (cells[n]['connections'][pin] for pin in ['Q','D'])
            mux = driver(d); c = cells[mux]
            require(c['cell'].endswith('__mux2_2') and q in [c['connections']['I0'],c['connections']['I1']], 'Storage feedback mux not recognized')
            require(consumers[d] == {n}, 'Feedback mux has another consumer')
            muxes.add(mux)
        require(len(muxes) == len(memory), 'Shared memory mux unexpectedly found')
        # JSON and Verilog generated instance names differ. Use the Q signal
        # to recover the original FF source attribute, never a guessed rename.
        jq = {c['connections']['Q'][0]: c for c in module['cells'].values() if 'Q' in c['connections']}
        rf = set()
        for n,c in cells.items():
            q = c['connections'].get('Q'); net = module['netnames'].get(q)
            if net and len(net['bits']) == 1 and 'espino_register_file.v' in jq[net['bits'][0]].get('attributes',{}).get('src',''):
                rf.add(n)
        require(len(rf) == 544, 'Expected 480 RF storage plus 64 registered output bits')
        counter = {n for n,c in cells.items() if re.fullmatch(r'u_soc\.u_periph\.cycles_q\[\d+\]',c['connections'].get('Q',''))}
        require(len(counter) == 32, 'Unexpected counter width')
        counter_gates = set(); queue = [cells[n]['connections']['D'] for n in counter]
        while queue:
            net = queue.pop()
            if net.startswith("1'"): continue
            name = driver(net)
            if name in counter or name in counter_gates: continue
            cell = cells[name]
            require(not library[cell['cell']]['sequential'], 'Counter cone includes foreign FF')
            counter_gates.add(name)
            queue.extend(net for pin,net in cell['connections'].items() if pins[cell['cell']][pin]['direction'] == 'input')
        require(len(counter_gates) == 66, 'Counter cone topology differs from prior audit')
        for n in counter_gates:
            for pin,net in cells[n]['connections'].items():
                if pins[cells[n]['cell']][pin]['direction'] == 'output':
                    require(consumers[net] <= counter | counter_gates, 'Counter combinational logic is shared')
        regions = {'memory_storage': memory, 'memory_private_feedback_muxes': muxes,
                   'rf_all_registers': rf, 'counter_registers_and_increment': counter | counter_gates}
        all_ids = set()
        for ids in regions.values():
            require(not all_ids & ids, 'Area regions overlap'); all_ids |= ids
        minimum = area(memory | muxes)
        result['variants'][variant] = {
            'synthesis_cell_area_um2': total,
            'regions': {k: {'count':len(ids),'area_um2':area(ids),'instances':sorted(ids)} for k,ids in regions.items()},
            'memory_area_lower_bound_um2': minimum,
            'memory_area_lower_bound_fraction': minimum/total,
            'memory_strict_majority_proven': minimum > total/2,
            'dominance_interpretation': 'memory_b dominates every disjoint competing block; lower bound already exceeds half the complete top' if minimum > total/2 else 'No dominant module proven by this lower bound',
            'alu_named_boundary_net_count': sum('u_id.u_alu.' in n for n in module['netnames']),
            'alu_source_net_count': sum('espino_alu.v' in n.get('attributes',{}).get('src','') for n in module['netnames'].values()),
            'alu_attribution_complete': False,
            'whole_module_area_attribution_complete': False,
            'limits': ['RF area excludes read/write combinational logic.', 'Memory lower bound excludes read muxes, decode and loader/ROM logic.', 'Counter excludes distribution and MMIO mux.', 'No absent ALU boundary is reconstructed by guessing.', 'Instance IDs refer to synthesis; physical survival is checked separately.']}
    # These are origins of preserved physical instances, not layout screenshots.
    for variant, tag in [('a', args.physical_a_tag), ('b', args.physical_b_tag)]:
        require(bool(re.fullmatch(r'[A-Za-z0-9_]+', tag)), 'Invalid physical tag')
        path = root/f'config/gf180/runs/{tag}/final/def/asic_top.def'
        text = path.read_text(); inputs[path] = sha(path)
        units = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', text)[1])
        section = re.search(r'^COMPONENTS\s+(\d+)\s*;(.*?)^END COMPONENTS', text, re.M|re.S)
        records = re.findall(r'^\s*-\s+(.*?)\s*;', section[2], re.M|re.S)
        require(len(records) == int(section[1]), 'DEF component count mismatch')
        positions = {}
        for record in records:
            name, master = record.split()[:2]
            xy = re.search(r'\+\s+(?:PLACED|FIXED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', record)
            if xy:
                positions[name] = dict(master=master, x_um=int(xy[1])/units, y_um=int(xy[2])/units, orientation=xy[3])
        original, _ = parse_netlist(root/f'config/gf180/runs/stage4_100ns_u40_floorplan_{variant}/06-yosys-synthesis/asic_top.nl.v')
        mapped = {}
        for region in ['rf_all_registers', 'counter_registers_and_increment']:
            ids = result['variants'][variant]['regions'][region]['instances']
            require(all(n in positions for n in ids), 'A selected instance is absent from routed DEF')
            require(all(re.sub(r'_\d+$','',original[n]['cell']) == re.sub(r'_\d+$','',positions[n]['master']) for n in ids), 'Physical master changed function family')
            mapped[region] = [dict(instance=n, **positions[n]) for n in ids]
        result['variants'][variant]['physical_trace'] = dict(source_def=str(path.relative_to(root)), all_selected_ids_present=True,
            master_function_family_preserved=True, regions=mapped,
            scope='Selected synthesis instance origins retained in this routed DEF; no ALU mapping and no annotated GUI screenshot claimed')
    require(all(sha(p) == digest for p,digest in inputs.items()), 'Source changed during inspection')
    result['input_sha256'] = {str(p.relative_to(root)):digest for p,digest in inputs.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    for v,r in result['variants'].items():
        print(v, 'memory lower bound', round(r['memory_area_lower_bound_fraction']*100,4), '%', 'RF FF',r['regions']['rf_all_registers']['count'], 'counter',r['regions']['counter_registers_and_increment']['count'])


if __name__ == '__main__':
    main()
