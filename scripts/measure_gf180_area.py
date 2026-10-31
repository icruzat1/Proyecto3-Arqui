#!/usr/bin/env python3
"""Measure mapped synthesis area with auditable, non-overlapping regions.

This reads existing Yosys JSON/stat and the matching Liberty. It runs no tools
and does not infer physical die area or assign untraceable logic to an ALU.
"""
import argparse
from collections import Counter, defaultdict
import fnmatch
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def liberty_cells(path):
    # Restrict to the standard-cell syntax in the pinned GF180 Liberty.
    text = path.read_text()
    headers = list(re.finditer(r'\bcell\s*\(\s*"?([^\s)";]+)"?\s*\)\s*\{', text))
    require(bool(headers), 'No Liberty cells found')
    result = {}
    for i, header in enumerate(headers):
        body = text[header.end():headers[i+1].start() if i+1 < len(headers) else len(text)]
        areas = re.findall(r'\barea\s*:\s*([0-9.eE+-]+)\s*;', body)
        require(len(areas) == 1, f'Expected one area for {header.group(1)}')
        name = header.group(1)
        require(name not in result, f'Duplicate Liberty cell {name}')
        result[name] = {'area_um2': float(areas[0]),
                        'sequential': bool(re.search(r'\b(?:ff|ff_bank|latch|latch_bank)\s*\(', body))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', required=True, type=Path, help='New JSON file; existing files are rejected')
    parser.add_argument('--source-tag', default='stage4_100ns_u40_floorplan')
    parser.add_argument('--variant', choices=['a', 'b', 'both'], default='both')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    require(not output.exists(), 'Output exists; choose a fresh file')
    require(bool(re.fullmatch(r'[A-Za-z0-9_]+', args.source_tag)), 'Unsafe source tag')
    report = {'scope': 'Mapped synthesis area, not placement/routing/die area',
              'schema_version': 1, 'script_sha256': sha(Path(__file__)), 'variants': {},
              'limits': [
                  'RF region includes only the 480 stored x1..x15 bits; output FF and read/write logic are excluded.',
                  'Memory regions include only 512/4608 storage FF, excluding ROM, read multiplexers, loader and output FF.',
                  'Counter includes 32 FF and its exclusive D-input combinational cone; reset/clock distribution and MMIO read mux are excluded.',
                  'Unattributed remainder is deliberately not labeled ALU or any complete module.',
                  'Module-dominant area and annotated final layout still require additional provenance.']}
    for variant in ('ab' if args.variant == 'both' else args.variant):
        run = root/f'config/gf180/runs/{args.source_tag}_{variant}'
        candidates = list(run.glob('*-yosys-synthesis'))
        require(len(candidates) == 1, f'Expected one synthesis step in {run}')
        step = candidates[0]
        cfg_path = step/'config.json'; net_path = step/'asic_top.nl.v.json'; stat_path = step/'reports/stat.json'
        cfg = json.loads(cfg_path.read_text())
        require(cfg['SYNTH_PARAMETERS'] == [f'MemoryVariant={0 if variant == "a" else 1}'], 'Variant mismatch')
        corner = cfg['DEFAULT_CORNER']
        lib_names = [path for pattern, paths in cfg['LIB'].items() if fnmatch.fnmatchcase(corner, pattern) for path in paths]
        require(len(lib_names) == 1, 'This audit requires one unambiguous mapped standard-cell Liberty')
        require(lib_names[0].startswith('/work/'), 'Expected project-local container Liberty path')
        lib_path = (root/lib_names[0].removeprefix('/work/')).resolve(strict=True)
        lib_path.relative_to(root)
        library = liberty_cells(lib_path)
        netlist = json.loads(net_path.read_text())
        require('asic_top' in netlist['modules'], 'Missing top')
        for name, definition in netlist['modules'].items():
            if name != 'asic_top':
                require(name in library and not definition.get('cells') and
                        int(str(definition.get('attributes', {}).get('blackbox', '0')), 2) != 0,
                        f'Non-library hierarchy or unresolved module: {name}')
        module = netlist['modules']['asic_top']; cells = module['cells']; nets = module['netnames']
        require(all(c['type'] in library for c in cells.values()), 'Unmapped or unknown library cell')
        drivers, consumers = defaultdict(set), defaultdict(set)
        for name, cell in cells.items():
            for port, direction in cell['port_directions'].items():
                require(direction in ('input', 'output'), 'Unexpected inout cell port')
                for bit in cell['connections'][port]:
                    (drivers if direction == 'output' else consumers)[bit].add(name)
        def area(names):
            return sum(library[cells[n]['type']]['area_um2'] for n in sorted(names))
        def storage(pattern, expected_indices):
            selected = {}
            for name, net in nets.items():
                match = re.fullmatch(pattern, name)
                if not match:
                    continue
                key = tuple(map(int, match.groups()))
                require(len(net['bits']) == 1 and isinstance(net['bits'][0], int), f'Non-single-bit storage {name}')
                require(key not in selected, f'Duplicate storage name {name}')
                selected[key] = (name, net['bits'][0])
            require(set(selected) == expected_indices, 'Missing or unexpected storage indices')
            bits = {bit for _,bit in selected.values()}
            require(len(bits) == len(expected_indices), 'Aliased storage bits')
            ff = set()
            for name, bit in selected.values():
                require(len(drivers[bit]) == 1, f'Storage {name} does not have one driver')
                driver = next(iter(drivers[bit])); cell = cells[driver]
                require(library[cell['type']]['sequential'] and cell['connections'].get('Q') == [bit], f'Storage {name} is not a direct single-bit FF.Q')
                ff.add(driver)
            require(len(ff) == len(bits), 'Storage bits unexpectedly share an FF instance')
            return ff, selected
        rf, rf_nets = storage(r'u_soc\.u_core\.u_rf\.regs_q\[(\d+)\]\[(\d+)\]', {(w,b) for w in range(1,16) for b in range(32)})
        array = 'ram_ff' if variant == 'a' else 'mem_ff'; words = 16 if variant == 'a' else 144
        memory, memory_nets = storage(r'u_mem\..*\.' + array + r'\[(\d+)\]\[(\d+)\]', {(w,b) for w in range(words) for b in range(32)})
        counter_ff, counter_nets = storage(r'u_soc\.u_periph\.cycles_q\[(\d+)\]', {(b,) for b in range(32)})
        comb, foreign, primary = set(), set(), set()
        queue = [b for n in counter_ff for b in cells[n]['connections']['D']]
        while queue:
            bit = queue.pop()
            if not isinstance(bit, int):
                continue
            if not drivers[bit]:
                primary.add(bit)
            require(len(drivers[bit]) <= 1, 'Multiple drivers in counter D cone')
            for name in drivers[bit]:
                if name in counter_ff:
                    continue
                if library[cells[name]['type']]['sequential']:
                    foreign.add(name); continue
                if name in comb:
                    continue
                comb.add(name)
                for port,direction in cells[name]['port_directions'].items():
                    if direction == 'input':
                        queue.extend(cells[name]['connections'][port])
        all_counter = counter_ff | comb
        shared = {}
        output_bits = {b for p in module['ports'].values() if p['direction'] == 'output' for b in p['bits']}
        for name in comb:
            outs = [b for port,direction in cells[name]['port_directions'].items() if direction == 'output' for b in cells[name]['connections'][port]]
            outside = set().union(*(consumers[b] for b in outs)) - all_counter
            if outside or output_bits.intersection(outs):
                shared[name] = sorted(outside) + (['<top output>'] if output_bits.intersection(outs) else [])
        require(not foreign and not primary and not shared, 'Counter cone changed or shared: review boundary before attributing area')
        require(len(comb) == 66, 'Expected audited 32 FF + 66 gate counter; topology changed, review attribution')
        regions = {'rf_storage':rf, 'memory_storage':memory, 'counter_storage_and_increment':all_counter}
        pairwise = {f'{a}:{b}': sorted(regions[a] & regions[b]) for i,a in enumerate(regions) for b in list(regions)[i+1:]}
        require(all(not overlap for overlap in pairwise.values()), 'Attribution regions overlap')
        assigned = set().union(*regions.values()); remainder = set(cells) - assigned
        total = area(cells); stats = json.loads(stat_path.read_text())['design']
        require(abs(total-stats['area']) < 0.01, 'Liberty sum disagrees with Yosys stat area')
        require(stats['num_cells'] == len(cells), 'Yosys cell count disagrees with netlist')
        counts = Counter(c['type'] for c in cells.values())
        top5 = [{'cell_type':name,'count':count,'unit_area_um2':library[name]['area_um2'],'total_area_um2':count*library[name]['area_um2']} for name,count in sorted(counts.items(),key=lambda item:(-item[1],item[0]))[:5]]
        report['variants'][variant] = {
            'source_step':step.relative_to(root).as_posix(),'default_corner':corner,
            'input_sha256':{p.relative_to(root).as_posix():sha(p) for p in (cfg_path,net_path,stat_path,lib_path)},
            'yosys_creator':netlist['creator'],'total_cell_count':len(cells),'total_cell_area_um2':total,
            'total_sequential_cells':sum(library[c['type']]['sequential'] for c in cells.values()),
            'top5_by_instance_count':top5,'cells_with_src_attribute':sum('src' in c.get('attributes',{}) for c in cells.values()),
            'regions':{name:{'cell_count':len(names),'area_um2':area(names),'fraction_of_total_cell_area':area(names)/total,'cell_instances':sorted(names)} for name,names in regions.items()},
            'storage_counts':{'rf_bits':len(rf),'memory_words':words,'memory_bits':len(memory),'counter_bits':len(counter_ff),'counter_comb_cells':len(comb)},
            'counter_ff_area_um2':area(counter_ff),'counter_comb_area_um2':area(comb),
            'region_intersections':pairwise,'assigned_unique_cells':len(assigned),'assigned_unique_area_um2':area(assigned),
            'unattributed_cell_count':len(remainder),'unattributed_area_um2':area(remainder),
            'unattributed_fraction':area(remainder)/total,'area_partition_sum_um2':area(assigned)+area(remainder),
            'alu_area_um2':None,'whole_module_area_attribution_complete':False,
            'counter_foreign_sequential_boundaries':sorted(foreign),'counter_primary_input_boundaries':sorted(primary),'counter_shared_combinational_cells':shared}
        require(abs(area(assigned)+area(remainder)-total)<0.01, 'Area partition does not sum to total')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:
        json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(f'PASS mapped synthesis area audit: {output}; no die area or complete ALU attribution claimed')


if __name__ == '__main__':
    main()
