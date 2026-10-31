#!/usr/bin/env python3
"""Derive a new state restoring only die bbox/area from its current DEF.

Install under scripts/, then use --source-state and a fresh --tag. No EDA tool
is executed and no source file is changed. Every existing state view and every
other metric is preserved exactly; nothing is copied from an older run. The
new input_sha256.json includes the source chain, current views and this script.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def geometry(def_path):
    text = def_path.read_text()
    # Remove DEF comments before requiring exactly one declaration of each.
    text = re.sub(r'(?m)^\s*#.*$', '', text)
    units = re.findall(r'(?m)^\s*UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;', text)
    dies = re.findall(r'(?m)^\s*DIEAREA\s+([^;]+);', text)
    require(len(units) == len(dies) == 1, 'Expected one UNITS and one DIEAREA declaration')
    unit = int(units[0])
    require(unit > 0, 'DEF units must be positive')
    match = re.fullmatch(r'\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*'
                         r'\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*', dies[0])
    require(match is not None, 'Only a rectangular two-point DEF DIEAREA is supported')
    dbu = [int(value) for value in match.groups()]
    x0, y0, x1, y1 = [Decimal(value) / Decimal(unit) for value in dbu]
    require(x1 > x0 and y1 > y0, 'Invalid or empty die rectangle')
    area = (x1 - x0) * (y1 - y0)
    fmt = lambda value: format(value.normalize(), 'f')
    return {
        'units_per_micron': unit, 'die_rectangle_dbu': dbu,
        'die_rectangle_microns': [fmt(value) for value in [x0, y0, x1, y1]],
        'die_area_square_microns_exact': fmt(area),
        'restored_metrics': {'design__die__bbox': ' '.join(fmt(value) for value in [x0, y0, x1, y1]),
                             'design__die__area': float(area)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source-state', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--validate-only', action='store_true', help='Read-only preview; no output is created')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    require(re.fullmatch(r'[A-Za-z0-9_]+', args.tag), 'Invalid fresh tag')

    def local(name):
        require(isinstance(name, str), f'Expected file path: {name!r}')
        path = Path(name.removeprefix('/work/'))
        require('..' not in path.parts, f'Parent traversal forbidden: {name}')
        path = (path if path.is_absolute() else root / path).resolve(strict=True)
        require(path.is_relative_to(root) and path.is_file(), f'File outside project or absent: {name}')
        return path

    def rel(path):
        return path.relative_to(root).as_posix()

    def views(obj):
        if isinstance(obj, str):
            yield local(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                yield from views(value)
        elif isinstance(obj, list):
            for value in obj:
                yield from views(value)
        else:
            require(obj is None, f'Unexpected non-path state view: {obj!r}')

    source_state = local(args.source_state)
    require(source_state.name == 'state_out.json', 'Use a completed source state_out.json')
    source_run = source_state.parent.parent
    runs = (root / 'config/gf180/runs').resolve(strict=True)
    require(source_run.parent == runs, 'Source state must belong to an immediate run directory')
    source_index = source_run / 'input_sha256.json'
    prior = read(source_index)
    require(isinstance(prior, dict) and prior, 'Source run lacks nonempty provenance')
    source_paths = {source_state, source_index}
    for name, digest in prior.items():
        path = local(name)
        require(sha(path) == digest, f'Stale source-run input: {name}')
        source_paths.add(path)
    state = read(source_state)
    require(isinstance(state, dict) and isinstance(state.get('metrics'), dict), 'Malformed state')
    require(all(state.get(name) for name in ['def', 'odb', 'nl', 'sdc']), 'Source state lacks required views')
    source_paths.update(views({name: value for name, value in state.items() if name != 'metrics'}))
    def_path = local(state['def'])
    measured = geometry(def_path)
    derived = deepcopy(state)
    derived['metrics'].update(measured['restored_metrics'])
    changed_keys = sorted(name for name in set(state['metrics']) | set(derived['metrics'])
                          if state['metrics'].get(name) != derived['metrics'].get(name))
    require(set(changed_keys) <= set(measured['restored_metrics']), 'Unexpected metric change')
    require({k: v for k, v in state.items() if k != 'metrics'} ==
            {k: v for k, v in derived.items() if k != 'metrics'}, 'State views changed')
    script = Path(__file__).resolve()
    require(args.validate_only or script.is_relative_to(root), 'Install this script under project scripts/ before writing')
    if script.is_relative_to(root):
        source_paths.add(script)
    before = {rel(path): sha(path) for path in sorted(source_paths)}
    report = {
        'status': 'preview' if args.validate_only else 'running', 'passed': False,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'command': sys.argv,
        'operation': 'Restore only die bbox and area from current rectangular DEF',
        'source_state': rel(source_state), 'source_state_sha256': sha(source_state),
        'source_def': rel(def_path), 'source_def_sha256': sha(def_path),
        'source_input_count': len(prior), 'verified_input_count': len(before),
        'script_sha256': sha(script), 'geometry': measured,
        'replaced_or_added_metric_keys': changed_keys,
        'previous_geometry_metrics': {name: state['metrics'].get(name) for name in measured['restored_metrics']},
        'other_metric_count_preserved': len(set(state['metrics']) - set(measured['restored_metrics'])),
        'state_views_unchanged': True, 'older_run_metrics_imported': False,
        'timing_or_physical_signoff_claimed': False,
    }
    if args.validate_only:
        require(all(sha(local(name)) == digest for name, digest in before.items()), 'Inputs changed during preview')
        report['input_hashes_unchanged'] = True
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    run = runs / args.tag
    require(not run.exists(), f'Use a fresh tag: {run}')
    step = run / '00-restore-geometry'
    step.mkdir(parents=True)
    result_path = run / 'result.json'
    try:
        source_snapshot = run / 'source_input_sha256.json'
        source_snapshot.write_text(json.dumps(before, indent=2, sort_keys=True) + '\n')
        require(all(sha(local(name)) == digest for name, digest in before.items()), 'Inputs changed during derivation')
        state_path = step / 'state_out.json'
        state_path.write_text(json.dumps(derived, indent=2) + '\n')
        require(read(state_path) == derived, 'Derived state did not round-trip exactly')
        report.update({'status': 'verified', 'passed': True, 'returncode': 0,
                       'inputs_unchanged': True, 'input_hashes_unchanged': True,
                       'derived_state': rel(state_path), 'derived_state_sha256': sha(state_path)})
        manifest_path = step / 'manifest.json'
        manifest_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        all_paths = source_paths | {source_snapshot, state_path, manifest_path}
        snapshot = {rel(path): sha(path) for path in sorted(all_paths)}
        require(all(sha(local(name)) == digest for name, digest in before.items()), 'Inputs changed before snapshot publication')
        (run / 'input_sha256.json').write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
        report['input_sha256_count'] = len(snapshot)
        result_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    except Exception as exc:
        report.update({'status': 'failed', 'passed': False, 'error': f'{type(exc).__name__}: {exc}'})
        result_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        raise
    print(json.dumps({name: report[name] for name in ['status', 'derived_state', 'geometry',
                                                    'other_metric_count_preserved', 'input_sha256_count']}, indent=2))


if __name__ == '__main__':
    main()
