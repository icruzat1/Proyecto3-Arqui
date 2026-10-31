#!/usr/bin/env python3
"""Archive compact placement/CTS evidence using only directly emitted STA metrics.

All corner checks/metrics are preserved. Full max/min reports are gzip-compressed
for the worst setup/hold corner per run; other reports retain paths and SHA256.
An optional final tag selects a candidate, never implies physical signoff.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def fresh_corners(metrics):
    result = {}
    for key, value in metrics.items():
        if '__corner:' in key:
            name, corner = key.rsplit('__corner:', 1)
            result.setdefault(corner, {})[name] = value
    return result


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def aggregate(corners, expected, verified):
    required = ['timing__setup__ws', 'timing__hold__ws',
                'timing__setup__tns', 'timing__hold__tns',
                'design__max_slew_violation__count', 'design__max_cap_violation__count',
                'design__max_fanout_violation__count']
    complete = (set(corners) == set(expected) and bool(expected) and
                all(all(finite(m.get(k)) for k in required) for m in corners.values()))
    result = {'complete': complete, 'source_verified': verified,
              'measured_corners': sorted(corners), 'expected_corners': list(expected),
              'postcts_setup_hold_passed': None, 'electrical_constraints_passed': None}
    for kind in ['setup', 'hold']:
        key = f'timing__{kind}__ws'
        available = {c:m[key] for c,m in corners.items() if finite(m.get(key))}
        if available:
            worst = min(available, key=available.get)
            result[f'worst_{kind}_corner'] = worst
            result[f'worst_{kind}_slack_ns'] = available[worst]
    for kind in ['slew', 'cap', 'fanout']:
        key = f'design__max_{kind}_violation__count'
        values = [m[key] for m in corners.values() if finite(m.get(key))]
        if values:
            result[f'max_{kind}_violations_per_corner'] = max(values)
    if complete and verified:
        result['postcts_setup_hold_passed'] = all(
            m[f'timing__{kind}__ws'] >= 0 and m[f'timing__{kind}__tns'] == 0
            for m in corners.values() for kind in ['setup', 'hold'])
        result['electrical_constraints_passed'] = all(
            m[f'design__max_{kind}_violation__count'] == 0
            for m in corners.values() for kind in ['slew', 'cap', 'fanout'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--base-tag', default='stage5_100ns_u40_cts')
    parser.add_argument('--include-tag', action='append', help='Additional run tag; default includes clockv2')
    parser.add_argument('--final-tag', default='stage5_100ns_u40_clockv2')
    parser.add_argument('--output', type=Path, help='Fresh directory; default evidence/gf180_stage5')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    tags = list(dict.fromkeys([args.base_tag] + (args.include_tag or ['stage5_100ns_u40_clockv2']) + [args.final_tag]))
    if not all(re.fullmatch(r'[A-Za-z0-9_]+', tag) for tag in tags):
        raise ValueError('Run tags must contain only letters, digits and underscores')
    out = (args.output or root/'evidence/gf180_stage5').resolve()
    if out.exists():
        raise ValueError(f'Archive directory already exists; choose a fresh --output: {out}')
    out.mkdir(parents=True)
    artifacts, omitted, warnings, runs, simulations = {}, {}, [], {}, {}

    def rel(path):
        return path.relative_to(root).as_posix()

    def local(name):
        path = root/name.removeprefix('/work/')
        path = path.resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError(f'Path leaves project: {name}')
        return path

    def preserve(path, target=None, compress=False):
        if not path.is_file():
            return None
        name = rel(path)
        if name in artifacts:
            return artifacts[name]['archive']
        target = target or Path('raw')/name
        if compress:
            target = Path(str(target)+'.gz')
        destination = out/target
        destination.parent.mkdir(parents=True, exist_ok=True)
        before = sha(path)
        if compress:
            with path.open('rb') as source, destination.open('wb') as sink:
                with gzip.GzipFile(filename='', mode='wb', fileobj=sink, mtime=0, compresslevel=9) as zipped:
                    shutil.copyfileobj(source, zipped)
        else:
            shutil.copyfile(path, destination)
        if sha(path) != before:
            raise ValueError(f'Artifact changed during archival: {name}')
        artifacts[name] = {'archive': target.as_posix(), 'source_sha256': before,
                           'archive_sha256': sha(destination), 'bytes': destination.stat().st_size,
                           'source_bytes': path.stat().st_size, 'gzip': compress}
        return target.as_posix()

    def omit(path, reason):
        if path.is_file() and rel(path) not in artifacts:
            omitted[rel(path)] = {'sha256': sha(path), 'bytes': path.stat().st_size, 'reason': reason}

    def small_files(directory):
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            if path.name in ['max.rpt', 'min.rpt']:
                continue
            if path.suffix in ['.json', '.rpt'] or path.name in ['COMMANDS', 'runtime.txt']:
                if path.name.endswith('.process_stats.json'):
                    continue
                preserve(path, compress=path.stat().st_size > 256*1024)
            elif path.suffix == '.log':
                if path.stat().st_size <= 256*1024:
                    preserve(path)
                else:
                    omit(path, 'Large tool log duplicates reports; wrapper flow log is archived')

    for path in [root/'config/environment.lock.json', root/'config/gf180/constraints.sdc',
                 root/'scripts/run_gf180_stage5.py', root/'scripts/run_gf180_clock_repair.py',
                 root/'scripts/measure_gf180_corners.py', root/'scripts/check_gf180_physical.py',
                 root/'scripts/summarize_gf180_stage5.py']:
        preserve(path)

    for tag in tags:
        runs[tag] = {}
        for variant in 'ab':
            run = root/f'config/gf180/runs/{tag}_{variant}'
            entry = {'available': run.is_dir(), 'stages': {}, 'allcorners': None}
            runs[tag][variant] = entry
            if not run.is_dir():
                warnings.append(f'Missing run: {tag}_{variant}')
                continue
            resolved_path = run/'resolved.json'
            cfg = read(resolved_path) if resolved_path.is_file() else {}
            expected = cfg.get('STA_CORNERS', [])
            preserve(resolved_path)
            entry['configuration'] = {k:cfg.get(k) for k in [
                'PDK', 'STD_CELL_LIBRARY', 'CLOCK_PERIOD', 'FP_CORE_UTIL', 'PL_TARGET_DENSITY',
                'CTS_SINK_CLUSTERING_SIZE', 'CTS_MAX_CAP', 'CTS_DISTANCE_BETWEEN_BUFFERS',
                'MAX_FANOUT_CONSTRAINT', 'MAX_TRANSITION_CONSTRAINT', 'MAX_CAPACITANCE_CONSTRAINT',
                'RSZ_DONT_TOUCH_RX', 'RSZ_DONT_TOUCH_LIST']}
            entry['resolved_config'] = rel(resolved_path)
            build = root/f'build/gf180_stage5/{tag}_{variant}'
            record_path = build/'result.json'
            record = read(record_path) if record_path.is_file() else {}
            entry['flow_passed'] = record.get('passed')
            if build.is_dir():
                for path in sorted(build.iterdir()):
                    if path.suffix in ['.json', '.log']:
                        preserve(path, compress=path.stat().st_size > 256*1024)
            snapshot_path = run/'input_sha256.json'
            snapshot = read(snapshot_path) if snapshot_path.is_file() else {}
            preserve(snapshot_path)
            for name in snapshot:
                parts = Path(name).parts
                if parts[0] == 'scripts' or (parts[0] == 'config' and 'runs' not in parts):
                    preserve(root/name)
            mismatch = [n for n,h in snapshot.items() if not (root/n).is_file() or sha(root/n) != h]
            verified = bool(snapshot) and not mismatch and record.get('passed') is True
            if record.get('input_sha256') is not None:
                verified = verified and record['input_sha256'] == snapshot
            entry['provenance'] = {'verified': verified, 'input_count': len(snapshot),
                                   'changed_or_missing_inputs': mismatch,
                                   'snapshot': rel(snapshot_path) if snapshot else None}
            if not verified:
                warnings.append(f'Run incomplete or provenance unverified: {tag}_{variant}')
            # Only completed steps are enumerated. Raw state files are retained
            # for provenance, but their carried STA metrics are never summarized.
            steps = [p for p in run.iterdir() if p.is_dir() and
                     (re.match(r'^\d+-', p.name) or p.name == 'extra-sta-postplacement') and
                     (p/'state_out.json').is_file()]
            for step in sorted(steps):
                small_files(step)
                metric_path = step/'or_metrics_out.json'
                direct = read(metric_path) if metric_path.is_file() else {}
                item = {'state': rel(step/'state_out.json'),
                        'fresh_metrics_file': rel(metric_path) if metric_path.is_file() else None,
                        'fresh_metrics': direct, 'fresh_timing_corners': fresh_corners(direct)}
                entry['stages'][step.name] = item
                if step.name.endswith('-openroad-resizertimingpostcts'):
                    entry['physical_metrics'] = {k:v for k,v in direct.items() if k.startswith('design__')}
                    state = read(step/'state_out.json')
                    entry['physical_views'] = {k:{'path':v, 'sha256':sha(local(v))}
                        for k,v in state.items() if k in ['nl', 'odb', 'def', 'sdc'] and isinstance(v,str)}
                for name in ['max.rpt', 'min.rpt']:
                    omit(step/name, 'Intermediate STA report; direct metrics/checks retained')
            all_dir = run/'extra-sta-allcorners'
            result_path = all_dir/'results.json'
            if not result_path.is_file():
                entry['allcorners'] = {'available': False, 'aggregate': aggregate({}, expected, False)}
                warnings.append(f'No completed all-corner measurement: {tag}_{variant}')
                continue
            measured = read(result_path)
            preserve(result_path)
            small_files(all_dir)
            source_state = local(measured['source_state'])
            source = read(source_state)
            source_config = read(source_state.parent/'config.json')
            source_ok = (sha(source_state) == measured.get('source_state_sha256') and
                         sha(local(source['odb'])) == measured.get('odb_sha256') and
                         sha(local(source_config['PNR_SDC_FILE'])) == measured.get('sdc_sha256') and
                         read(all_dir/'state_in.json').get('metrics') == {} and
                         source_state.parent.parent == run and
                         source_state.parent.name.endswith('-openroad-stamidpnr-2') and
                         source.get('odb') == entry.get('physical_views', {}).get('odb', {}).get('path'))
            corners, corner_info = {}, {}
            for corner in expected:
                directory = all_dir/corner
                metric_path = directory/'or_metrics_out.json'
                if not metric_path.is_file() or not (directory/'state_out.json').is_file():
                    continue
                small_files(directory)
                metrics = fresh_corners(read(metric_path)).get(corner, {})
                info = measured.get('corners', {}).get(corner, {})
                config_path = all_dir/f'{corner}.json'
                same = (metrics == info.get('metrics') and
                        config_path.is_file() and sha(config_path) == info.get('config_sha256'))
                source_ok = source_ok and same
                corners[corner] = metrics
                corner_info[corner] = {'fresh_metrics': metrics, 'record_matches': same,
                                       'raw_metrics': rel(metric_path), 'checks': rel(directory/'checks.rpt')}
            combined = aggregate(corners, expected, verified and source_ok)
            entry['allcorners'] = {'available': True, 'source_verified': source_ok,
                                  'results': rel(result_path), 'corners': corner_info,
                                  'aggregate': combined}
            if not source_ok:
                warnings.append(f'All-corner provenance mismatch: {tag}_{variant}')
            # Preserve full paths for the limiting setup and hold cases only.
            for kind, filename in [('setup', 'max.rpt'), ('hold', 'min.rpt')]:
                corner = combined.get(f'worst_{kind}_corner')
                if corner:
                    selected = all_dir/corner/filename
                    preserve(selected, compress=True)
                    entry['allcorners'][f'worst_{kind}_report'] = rel(selected)
            for corner in corners:
                for filename in ['max.rpt', 'min.rpt']:
                    omit(all_dir/corner/filename, 'Non-limiting report; fresh metrics and checks archived')

    for tag in tags:
        directory = root/'build/gf180_physical'/tag
        result_path = directory/'results.json'
        if not result_path.is_file():
            simulations[tag] = {'available': False}
            continue
        result = read(result_path)
        preserve(result_path)
        info = {'available': True, 'results': rel(result_path), 'recorded_all_passed': result.get('all_passed'), 'runs': {}}
        for variant, item in result.get('runs', {}).items():
            netlist = local(item['netlist'])
            changes = [n for n,h in item.get('input_sha256', {}).items()
                       if not (root/n).is_file() or sha(root/n) != h]
            info['runs'][variant] = {'recorded_passed': item.get('passed'), 'coverage': item.get('coverage'),
                'netlist_sha256_matches': sha(netlist) == item.get('netlist_sha256'),
                'changed_inputs_since_test': changes, 'scope': result.get('scope')}
        for path in sorted(directory.rglob('*')):
            if path.is_file() and (path.suffix == '.log' or path.name == 'tb_physical.v'):
                preserve(path, compress=path.stat().st_size > 256*1024)
        simulations[tag] = info

    comparisons = {}
    for variant in 'ab':
        before, after = runs[args.base_tag][variant], runs[args.final_tag][variant]
        first = (before.get('allcorners') or {}).get('aggregate', {})
        last = (after.get('allcorners') or {}).get('aggregate', {})
        delta = {k:last[k]-first[k] for k in ['worst_setup_slack_ns', 'worst_hold_slack_ns',
                    'max_slew_violations_per_corner', 'max_cap_violations_per_corner',
                    'max_fanout_violations_per_corner'] if finite(first.get(k)) and finite(last.get(k))}
        comparisons[variant] = {'before_tag': args.base_tag, 'after_tag': args.final_tag,
                               'before': first, 'after': last, 'delta': delta}
        p, q = before.get('physical_metrics', {}), after.get('physical_metrics', {})
        comparisons[variant]['physical_delta'] = {k:q[k]-p[k] for k in [
            'design__instance__count', 'design__instance__area', 'design__instance__utilization']
            if finite(p.get(k)) and finite(q.get(k))}
    final = [(runs[args.final_tag][v].get('allcorners') or {}).get('aggregate', {}) for v in 'ab']
    def all_known(key):
        values = [x.get(key) for x in final]
        return all(values) if all(isinstance(v, bool) for v in values) else None
    total = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    summary = {'generator': 'summarize_gf180_stage5.py',
        'scope': 'Placement, CTS and repair; estimated parasitics before routing',
        'base_tag': args.base_tag, 'included_tags': tags, 'selected_final_tag': args.final_tag,
        'physical_signoff': False, 'routed_timing_signoff': False,
        'selected_postcts_setup_hold_passed': all_known('postcts_setup_hold_passed'),
        'selected_electrical_constraints_passed': all_known('electrical_constraints_passed'),
        'metric_policy': 'Only or_metrics_out.json emissions count as fresh STA; state_out metrics may be inherited',
        'report_policy': 'All checks/metrics; full gzip max/min for worst setup/hold corner per run; remaining hashes retained',
        'runs': runs, 'before_after': comparisons, 'simulations': simulations,
        'warnings': warnings, 'artifacts': artifacts, 'omitted_artifacts': omitted,
        'archived_payload_bytes': total}
    encoded = json.dumps(summary, indent=2, sort_keys=True)+'\n'
    if total+len(encoded.encode()) > 15*1024*1024:
        warnings.append('Archive exceeds preferred 15 MiB; full limiting reports retained')
        encoded = json.dumps(summary, indent=2, sort_keys=True)+'\n'
    (out/'results.json').write_text(encoded)
    actual = total+len(encoded.encode())
    print(f'PASS archived {len(artifacts)} artifacts to {out}; total {actual/1024/1024:.2f} MiB')
    print('Selected candidate setup/hold:', summary['selected_postcts_setup_hold_passed'],
          'electrical:', summary['selected_electrical_constraints_passed'], '; physical signoff: False')
    for warning in warnings:
        print('NOTE:', warning)


if __name__ == '__main__':
    main()
