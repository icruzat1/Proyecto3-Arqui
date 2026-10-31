#!/usr/bin/env python3
"""Read-only per-pin audit of routed reports against actual Liberty attributes.

Example after installation under scripts/ (or with an explicit --root):
  python3 audit_gf180_liberty_limits.py --root PROJECT --tag stage6_100ns_u40_route_eco3 \
    --variant both --output /private/tmp/eco3_ab_liberty_audit.json

No EDA tool is run and no constraint is changed. The original flow violations
remain violations. An absent Liberty limit is unknown, never treated as PASS.
Only reported violating pins are compared; this is not a new signoff run.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import fnmatch
import hashlib
import json
from pathlib import Path
import re


KINDS = {'slew': ('max slew', 'max_transition'),
         'cap': ('max capacitance', 'max_capacitance'),
         'fanout': ('max fanout', 'max_fanout')}
NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
ROW = re.compile(rf'^(\S+)\s+({NUMBER})\s+({NUMBER})\s+(?:({NUMBER})\s+)?\(VIOLATED\)\s*$')
PREFIX = 'gf180mcu_fd_sc_mcu7t5v0__'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def local(root, name):
    path = Path(name.removeprefix('/work/'))
    require(not path.is_absolute() and '..' not in path.parts, f'Invalid project path: {name}')
    path = (root / path).resolve(strict=True)
    require(path.is_relative_to(root), f'Path leaves project: {name}')
    return path


def parse_liberty(path):
    text = path.read_text()
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group().count('\n'), text, flags=re.S)
    cells, defaults = {}, {}
    depth = 0
    cell = pin = None
    cell_depth = pin_depth = None
    time_unit = capacitance_unit = None
    for number, line in enumerate(text.splitlines(), 1):
        if match := re.match(r'\s*time_unit\s*:\s*"?([^;" ]+)', line):
            time_unit = match[1]
        if match := re.match(r'\s*capacitive_load_unit\s*\(\s*([^)]*)\)', line):
            capacitance_unit = re.sub(r'\s+', '', match[1])
        if match := re.match(r'\s*cell\s*\(\s*(\w+)\s*\)\s*\{', line):
            cell, cell_depth = match[1], depth + 1
            cells[cell] = {}
        if match := re.match(r'\s*pin\s*\(\s*(\w+)\s*\)\s*\{', line):
            require(cell is not None, f'Pin outside cell: {path}:{number}')
            pin, pin_depth = match[1], depth + 1
            cells[cell][pin] = {'pin_line': number}
        if pin is not None and depth == pin_depth:
            if match := re.match(rf'\s*(max_transition|max_capacitance|max_fanout)\s*:\s*({NUMBER})\s*;', line):
                cells[cell][pin][match[1]] = {'value': match[2], 'line': number}
            if match := re.match(r'\s*direction\s*:\s*(\w+)\s*;', line):
                cells[cell][pin]['direction'] = match[1]
        if depth == 1:
            if match := re.match(rf'\s*default_(max_transition|max_capacitance|max_fanout)\s*:\s*({NUMBER})\s*;', line):
                defaults[match[1]] = {'value': match[2], 'line': number}
        braces = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
        depth += braces.count('{') - braces.count('}')
        if pin is not None and depth < pin_depth:
            pin = pin_depth = None
        if cell is not None and depth < cell_depth:
            cell = cell_depth = None
    require(depth == 0, f'Unbalanced Liberty groups: {path}')
    require(time_unit == '1ns' and capacitance_unit == '1,pf',
            f'Expected report-compatible ns/pF units, got {time_unit}/{capacitance_unit}')
    return {'path': path, 'cells': cells, 'defaults': defaults,
            'time_unit': time_unit, 'capacitance_unit': capacitance_unit}


def parse_netlist(path):
    cells, pin_nets = {}, {}
    for cell, inst, ports in re.findall(r'(?ms)^\s*(gf180mcu_fd_sc_mcu7t5v0__\w+)\s+(\S+)\s*\((.*?)\);', path.read_text()):
        inst = inst.lstrip('\\')
        require(inst not in cells, f'Duplicate instance: {inst}')
        connections = {p: n.strip().lstrip('\\') for p, n in re.findall(r'\.(\w+)\s*\(([^()]*)\)', ports)}
        cells[inst] = {'cell': cell, 'connections': connections}
        for pin, net in connections.items():
            pin_nets[inst + '/' + pin] = net
    require(cells, 'No GF180 instances parsed')
    return cells, pin_nets


def parse_report(path):
    text = path.read_text()
    counts = {kind: int(count) for kind, count in re.findall(r'^max (slew|cap|fanout) violation count (\d+)\s*$', text, re.M)}
    require(set(counts) == set(KINDS), f'Missing final violation counters: {path}')
    sections = {kind: [] for kind in KINDS}
    current = None
    labels = {title: kind for kind, (title, _) in KINDS.items()}
    for line in text.splitlines():
        if line.strip() in labels:
            current = labels[line.strip()]
        elif line.startswith('==='):
            current = None
        elif current and (match := ROW.fullmatch(line.strip())):
            sections[current].append({'pin': match[1], 'flow_limit': match[2], 'actual': match[3]})
    for kind, rows in sections.items():
        require(len(rows) == counts[kind], f'{kind}: parsed {len(rows)} != reported {counts[kind]} in {path}')
        require(len({r['pin'] for r in rows}) == len(rows), f'Duplicate {kind} pins in {path}')
    return sections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tag', default='stage6_100ns_u40_route_eco3')
    parser.add_argument('--variant', choices=['a', 'b', 'both'], default='both')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    require(re.fullmatch(r'[A-Za-z0-9_]+', args.tag), 'Invalid run tag')
    require(not args.output.exists(), 'Use a fresh output path')
    libraries, sources, runs = {}, {}, {}

    def track(path):
        key = path.relative_to(root).as_posix()
        digest = sha(path)
        require(key not in sources or sources[key] == digest, f'Source changed: {path}')
        sources[key] = digest
        return key

    for variant in ('ab' if args.variant == 'both' else args.variant):
        run = root / f'config/gf180/runs/{args.tag}_{variant}'
        steps = [p for p in run.iterdir() if re.fullmatch(r'\d+-openroad-stapostpnr(?:-\d+)?', p.name)]
        require(steps, f'No final STA in {run}')
        sta = max(steps, key=lambda p: int(p.name.split('-')[0]))
        config_path, state_path = sta / 'config.json', sta / 'state_in.json'
        cfg, state = json.loads(config_path.read_text()), json.loads(state_path.read_text())
        netlist = local(root, state['nl'])
        track(config_path); track(state_path); track(netlist)
        cells, pin_nets = parse_netlist(netlist)
        per_corner = {}
        for report in sorted(sta.glob('*/checks.rpt')):
            corner = report.parent.name
            matches = [name for pattern, paths in cfg['LIB'].items()
                       if fnmatch.fnmatchcase(corner, pattern) for name in paths]
            require(len(matches) == 1, f'Expected one Liberty for {corner}, got {matches}')
            lib_path = local(root, matches[0])
            if lib_path not in libraries:
                libraries[lib_path] = parse_liberty(lib_path)
            lib = libraries[lib_path]
            lib_name = track(lib_path)
            report_name = track(report)
            net_drivers = defaultdict(list)
            for inst, data in cells.items():
                require(data['cell'] in lib['cells'], f'Missing Liberty cell {data["cell"]}')
                for port, net in data['connections'].items():
                    if lib['cells'][data['cell']].get(port, {}).get('direction') == 'output':
                        net_drivers[net].append(inst + '/' + port)
            section = parse_report(report)
            audited = {}
            for kind, rows in section.items():
                attr = KINDS[kind][1]
                checked = []
                for row in rows:
                    record = {'pin': row['pin'], 'flow_limit': float(row['flow_limit']),
                              'actual': float(row['actual']), 'liberty_limit': None,
                              'exceeds_liberty': None, 'bound_source': None}
                    actual = Decimal(row['actual'])
                    if '/' in row['pin']:
                        inst, port = row['pin'].rsplit('/', 1)
                        require(inst in cells, f'Unknown reported instance: {row["pin"]}')
                        cell = cells[inst]['cell']
                        require(port in lib['cells'][cell], f'Missing Liberty pin {cell}/{port}')
                        pin_info = lib['cells'][cell][port]
                        bound = pin_info.get(attr) or lib['defaults'].get(attr)
                        record.update({'cell': cell.removeprefix(PREFIX), 'cell_pin': port,
                                       'net': pin_nets[row['pin']],
                                       'net_drivers': net_drivers[pin_nets[row['pin']]]})
                        if bound:
                            limit = Decimal(bound['value'])
                            record.update({'liberty_limit': float(limit),
                                           'liberty_line': bound['line'],
                                           'bound_source': 'pin' if attr in pin_info else 'library_default',
                                           'exceeds_liberty': actual > limit,
                                           'margin_to_liberty': float(limit - actual)})
                    checked.append(record)
                violations = [row for row in checked if row['exceeds_liberty'] is True]
                absent = [row for row in checked if row['liberty_limit'] is None]
                audited[kind] = {
                    'reported_flow_violations': len(checked),
                    'mapped_to_own_or_default_liberty_limit': len(checked) - len(absent),
                    'exceeds_liberty_count': len(violations),
                    'no_liberty_limit_count': len(absent),
                    'maximum_reported': max((row['actual'] for row in checked), default=None),
                    'liberty_limit_values': sorted({row['liberty_limit'] for row in checked if row['liberty_limit'] is not None}),
                    'flow_limit_values': sorted({row['flow_limit'] for row in checked}),
                    'liberty_violations': sorted(violations, key=lambda row: row['margin_to_liberty']),
                    'largest_reported_examples': sorted(checked, key=lambda row: -row['actual'])[:5],
                    'reported_value_histogram': dict(sorted(Counter(row['actual'] for row in checked).items())) if kind == 'fanout' else None,
                }
            per_corner[corner] = {'report': report_name, 'liberty': lib_name, 'checks': audited}
        require(len(per_corner) == 9, f'Expected nine reported corners, got {len(per_corner)}')
        unique_real = {kind: sorted({row['pin'] for corner in per_corner.values()
                                    for row in corner['checks'][kind]['liberty_violations']}) for kind in KINDS}
        unique_nets = {kind: sorted({row['net'] for corner in per_corner.values()
                                    for row in corner['checks'][kind]['liberty_violations']}) for kind in KINDS}
        all_bounds_known = {kind: all(c['checks'][kind]['no_liberty_limit_count'] == 0
                                     for c in per_corner.values()) for kind in KINDS}
        runs[variant] = {'netlist': netlist.relative_to(root).as_posix(), 'corners': per_corner,
                         'unique_pins_exceeding_liberty': unique_real,
                         'unique_pins_exceeding_liberty_count': {k: len(v) if all_bounds_known[k] else None
                                                                for k, v in unique_real.items()},
                         'unique_nets_exceeding_liberty': unique_nets,
                         'all_reported_pins_have_library_bound': all_bounds_known,
                         'fanout_library_assessment': 'assessed' if all_bounds_known['fanout'] else
                                                      'not_assessable_missing_pin_or_library_default_limit',
                         'maximum_reported_fanout': max((c['checks']['fanout']['maximum_reported'] or 0) for c in per_corner.values())}
        print(variant, {c: {k: [v['reported_flow_violations'], v['exceeds_liberty_count'], v['no_liberty_limit_count']]
                           for k, v in data['checks'].items()} for c, data in per_corner.items()}, flush=True)
    for name, digest in sources.items():
        require(sha(root / name) == digest, f'Source changed during audit: {name}')
    out = {'schema_version': 1, 'run_tag': args.tag, 'created_utc': datetime.now(timezone.utc).isoformat(),
           'method': 'Match every reported violating instance/pin to final netlist and actual corner Liberty pin attribute, falling back only to a declared library default.',
           'scope': 'Reported violating pins only; no rerun, no changed constraints, no signoff claim.',
           'missing_liberty_bound_means_unknown': True,
           'original_flow_violations_remain_in_force': True,
           'precision': 'Comparison uses decimal values printed in checks.rpt; sub-report-precision margins are not independently resolved.',
           'units': {'slew': 'ns', 'cap': 'pF', 'fanout': 'reported load count'},
           'script_sha256': sha(Path(__file__).resolve()), 'source_sha256': sources,
           'input_hashes_unchanged': True, 'runs': runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, separators=(',', ':'), sort_keys=True) + '\n')
    print(f'Wrote {args.output}; {args.output.stat().st_size} bytes')


if __name__ == '__main__':
    main()
