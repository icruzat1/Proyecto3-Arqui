#!/usr/bin/env python3
"""Bounded functional comparison of routed GF180 netlists and production RTL.

Reuses the unchanged startup/reset/button/SPI stimuli and retained-net checks in
check_gf180_physical.py. Uses FUNCTIONAL PDK models and the unpowered .nl.v.
A completed DRT/FillInsertion netlist may be tested even if a later timing or
physical checker failed. The flow's failure remains explicitly recorded.
This is not SDF timing simulation, formal equivalence, or physical signoff.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import types


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def local(root, name):
    require(isinstance(name, str), f'Expected a view path, received {name!r}')
    if name.startswith('/work/'):
        name = name.removeprefix('/work/')
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts,
            f'Expected project-relative or /work path: {name}')
    result = (root / path).resolve(strict=True)
    require(result.is_relative_to(root), f'Path leaves project: {name}')
    return result


def key(root, path):
    path = path.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def read_json(path):
    return json.loads(path.read_text())


def step_number(path):
    match = re.match(r'^(\d+)-', path.name)
    require(match is not None, f'Expected numbered completed step: {path}')
    return int(match.group(1))


def shared_checker(root):
    path = root / 'scripts/check_gf180_physical.py'
    # exec avoids writing __pycache__ into the project during read-only preflight.
    module = types.ModuleType('_gf180_existing_physical_checks')
    module.__file__ = str(path)
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    return module, path


def select_state(root, run_dir, state_step):
    if state_step != 'auto':
        require(bool(re.fullmatch(r'\d+-[A-Za-z0-9_-]+', state_step)),
                'state-step must be a numbered run step or auto')
        selected = run_dir / state_step / 'state_out.json'
        require(selected.is_file(), f'Selected step is not completed: {selected}')
    else:
        candidates = [p for p in run_dir.glob('*/state_out.json')
                      if re.fullmatch(r'\d+-[A-Za-z0-9_-]+', p.parent.name)]
        require(candidates, f'No completed states in {run_dir}')
        selected = max(candidates, key=lambda p: step_number(p.parent))
    state = read_json(selected)
    netlist = local(root, state.get('nl'))
    producer = netlist.parent
    require(producer.parent == run_dir and netlist.name == 'asic_top.nl.v',
            'Selected unpowered netlist must be produced within this run')
    producer_state = producer / 'state_out.json'
    producer_config = producer / 'config.json'
    require(producer_state.is_file() and producer_config.is_file(),
            'Netlist producer is missing its completed state/config')
    producer_cfg = read_json(producer_config)
    require(producer_cfg.get('meta', {}).get('step') in
            {'OpenROAD.DetailedRouting', 'OpenROAD.FillInsertion'},
            'Expected a completed DetailedRouting or FillInsertion netlist')
    require(step_number(producer) <= step_number(selected.parent),
            'Selected state predates its netlist producer')
    require(local(root, read_json(producer_state).get('nl')) == netlist,
            'Producer state does not point to this netlist')
    routed_steps = []
    for directory in run_dir.iterdir():
        if not directory.is_dir() or not re.fullmatch(r'\d+-[A-Za-z0-9_-]+', directory.name):
            continue
        if step_number(directory) > step_number(producer):
            continue
        cfg_path, state_path = directory / 'config.json', directory / 'state_out.json'
        if cfg_path.is_file() and state_path.is_file():
            if read_json(cfg_path).get('meta', {}).get('step') == 'OpenROAD.DetailedRouting':
                routed_steps.append(directory)
    require(routed_steps, 'No completed DetailedRouting step before the selected netlist')
    routing = max(routed_steps, key=step_number)
    routing_state_path = routing / 'state_out.json'
    routing_state = read_json(routing_state_path)
    require(local(root, routing_state.get('nl')).parent == routing,
            'DetailedRouting state lacks its own output netlist')
    tracked = [selected, producer_state, producer_config, routing_state_path,
               routing / 'config.json', netlist]
    for view in ['odb', 'def', 'sdc']:
        tracked.append(local(root, state.get(view)))
    final = run_dir / 'final/nl/asic_top.nl.v'
    if final.is_file():
        require(sha(final) == sha(netlist),
                'Final exported netlist differs from the selected completed state')
        tracked.append(final)
    return {
        'state': selected, 'netlist': netlist, 'producer': producer,
        'routing': routing, 'tracked': tracked,
        'final_export_matches': True if final.is_file() else None,
    }


def prepare(root, tag, variant, state_step, common, common_path):
    index = 'ab'.index(variant)
    run_dir = root / f'config/gf180/runs/{tag}_{variant}'
    snapshot_path = run_dir / 'input_sha256.json'
    snapshot = read_json(snapshot_path)
    require(isinstance(snapshot, dict) and snapshot, 'Missing source provenance')
    for name, digest in snapshot.items():
        require(sha(local(root, name)) == digest, f'Stale routed-run input: {name}')
    record_path = root / f'build/gf180_stage5/{tag}_{variant}/result.json'
    record = read_json(record_path)
    require(record.get('input_sha256') == snapshot and record.get('inputs_unchanged') is True,
            'Runner did not confirm the same unchanged source inputs')
    require(isinstance(record.get('passed'), bool) and
            isinstance(record.get('returncode'), int), 'Runner has not completed')
    # Do not require passed=True: functional success must not erase a flow failure.
    source_state = local(root, record.get('source_state'))
    require(sha(source_state) == record.get('source_state_sha256'),
            'Runner source-state fingerprint changed')
    resolved_path = run_dir / 'resolved.json'
    cfg = read_json(resolved_path)
    require(cfg['PDK'] == 'gf180mcuD' and
            cfg['STD_CELL_LIBRARY'] == 'gf180mcu_fd_sc_mcu7t5v0', 'Wrong technology')
    require(cfg['SYNTH_PARAMETERS'] == [f'MemoryVariant={index}'] and
            cfg['CLOCK_PERIOD'] == 100, 'Wrong memory variant or clock')
    source_manifest = root / 'config/rtl_asic.f'
    sources = [local(root, line.strip()) for line in source_manifest.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith('#')]
    require(set(local(root, name) for name in cfg['VERILOG_FILES']) == set(sources),
            'Routed run did not use the production RTL manifest')
    models = root / '.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog'
    libraries = [models / 'primitives.v', models / 'gf180mcu_fd_sc_mcu7t5v0.v']
    module_names = set(re.findall(r'\bmodule\s+(\w+)\s*\(', libraries[1].read_text()))
    selected = select_state(root, run_dir, state_step)
    raw = selected['netlist'].read_text()
    require(not re.search(r'\.(?:VDD|VSS|VNW|VPW)\s*\(', raw),
            'Use the unpowered .nl.v, not .pnl.v')
    require(not re.search(r'\$sdf_annotate\b', raw), 'Unexpected timing annotation')
    cell_counts = Counter(re.findall(r'^\s*(gf180mcu_fd_sc_mcu7t5v0__\w+)\s', raw, re.M))
    require(cell_counts and set(cell_counts) <= module_names,
            f'Missing PDK models; no cells removed: {sorted(set(cell_counts)-module_names)}')
    renamed, count = re.subn(r'(?m)^module\s+asic_top\s*\(', 'module physical_top (', raw)
    require(count == 1, 'Expected one flattened asic_top')
    checks, diagnostics = common.diagnostic_checks(raw)
    tb = common.testbench(index, checks)
    tracked = selected['tracked'] + sources + libraries + [snapshot_path, record_path,
              resolved_path, source_state, source_manifest, common_path, Path(__file__).resolve()]
    tracked_paths = {key(root, path): path for path in tracked}
    hashes = {name: sha(path) for name, path in tracked_paths.items()}
    physical_pattern = r'gf180mcu_fd_sc_mcu7t5v0__(?:antenna|endcap|filltie|fill_\d+|fillcap_\d+)'
    report = {
        'variant': variant, 'passed': False,
        'state': key(root, selected['state']), 'netlist': key(root, selected['netlist']),
        'netlist_sha256': sha(selected['netlist']),
        'netlist_producer': key(root, selected['producer']),
        'completed_detailed_routing_step': key(root, selected['routing']),
        'final_export_matches_selected_netlist': selected['final_export_matches'],
        'physical_flow_reported_passed': record['passed'],
        'physical_flow_returncode': record['returncode'],
        'flow_success_required_for_functional_test': False,
        'source_provenance_validated': True,
        'diagnostic_bits_compared': diagnostics, 'physical_cells_removed': [],
        'cell_type_counts': dict(sorted(cell_counts.items())),
        'physical_cells_kept_with_pdk_models': {name: count for name, count in sorted(cell_counts.items())
                                               if re.fullmatch(physical_pattern, name)},
        'stimulus_implementation': key(root, common_path),
        'stimulus_implementation_sha256': sha(common_path),
        'input_sha256': hashes,
    }
    return {'report': report, 'index': index, 'raw': renamed, 'tb': tb,
            'sources': sources, 'libraries': libraries, 'tracked': tracked_paths,
            'snapshot': snapshot}


def verify_unchanged(root, prepared):
    for name, path in prepared['tracked'].items():
        require(sha(path) == prepared['report']['input_sha256'][name],
                f'Test input changed: {name}')
    for name, digest in prepared['snapshot'].items():
        require(sha(local(root, name)) == digest, f'Routed provenance changed: {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tag', default='stage6_100ns_u40_route')
    parser.add_argument('--variant', choices=['a', 'b', 'both'], default='both')
    parser.add_argument('--state-step', default='auto')
    parser.add_argument('--output', type=Path, help='Fresh output directory; default build/gf180_routed/TAG')
    parser.add_argument('--validate-only', action='store_true', help='Read-only provenance/model preflight; no simulation')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    require(bool(re.fullmatch(r'[A-Za-z0-9_]+', args.tag)), 'Invalid run tag')
    common, common_path = shared_checker(root)
    variants = list('ab') if args.variant == 'both' else [args.variant]
    prepared = {variant: prepare(root, args.tag, variant, args.state_step, common, common_path)
                for variant in variants}
    if args.validate_only:
        for data in prepared.values():
            verify_unchanged(root, data)
        print(json.dumps({'preflight_passed': True, 'simulation_run': False,
                          'functional_equivalence_claimed': False,
                          'runs': {v: data['report'] for v, data in prepared.items()}}, indent=2, sort_keys=True))
        return
    require(shutil.which('iverilog') and shutil.which('vvp'), 'Icarus Verilog required')
    output = (args.output or root / 'build/gf180_routed' / args.tag).resolve()
    require(not output.exists(), f'Output must be a fresh directory: {output}')
    output.mkdir(parents=True)
    result_path = output / 'results.json'
    results = {
        'schema_version': 1, 'all_passed': False, 'status': 'running',
        'scope': 'Bounded production startup/reset/buttons/SPI and retained-net comparison after routing',
        'formal_equivalence': False, 'full_game_verified': False, 'sdf_timing': False,
        'timing_signoff': False, 'physical_signoff': False, 'power_aware': False,
        'production_firmware_unchanged': True, 'ordinary_ram_interfaces_tested': False,
        'flow_success_may_be_false_despite_functional_pass': True,
        'command': sys.argv, 'runs': {},
    }

    def save():
        result_path.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')

    save()
    try:
        for variant, data in prepared.items():
            report = data['report']
            results['runs'][variant] = report
            build = output / variant
            build.mkdir()
            netlist, tb, executable = build / 'physical.v', build / 'tb_physical.v', build / 'physical.vvp'
            netlist.write_text(data['raw'])
            tb.write_text(data['tb'])
            generated = {key(root, path): sha(path) for path in [netlist, tb]}

            def run(command, label):
                completed = subprocess.run(list(map(str, command)), cwd=root, text=True,
                                           capture_output=True, timeout=600)
                log = completed.stdout + completed.stderr
                log_path = build / f'{label}.log'
                log_path.write_text(log)
                require(completed.returncode == 0, f'{label} failed; inspect {log_path}')
                return log

            version = run(['iverilog', '-V'], 'iverilog_version').splitlines()[0]
            run(['iverilog', '-g2012', '-DFUNCTIONAL', '-s', 'tb_physical', '-o', executable,
                 tb, netlist, *data['libraries'], *data['sources']], 'compile')
            log = run(['vvp', executable], 'simulation')
            lines = [line for line in log.splitlines() if line.startswith('PASS physical_startup ')]
            require(len(lines) == 1, 'Missing unique PASS summary')
            coverage = {name: int(value) for name, value in re.findall(r'(\w+)=(\d+)', lines[0])}
            require(coverage.get('variant') == data['index'] and coverage.get('epochs') == 2
                    and coverage.get('spi_frames') == 4 and coverage.get('reset_checks') == 2
                    and coverage.get('samples', 0) >= 21000 and coverage.get('active_cycles', 0) >= 20000
                    and coverage.get('fetch_changes', 0) >= 1000,
                    'Unexpected bounded simulation coverage')
            verify_unchanged(root, data)
            require(generated == {key(root, path): sha(path) for path in [netlist, tb]},
                    'Generated simulation inputs changed')
            report.update({'passed': True, 'summary': lines[0], 'coverage': coverage,
                           'iverilog_version': version, 'generated_input_sha256': generated,
                           'simulation_log': key(root, build / 'simulation.log'),
                           'simulation_log_sha256': sha(build / 'simulation.log'),
                           'compile_log_sha256': sha(build / 'compile.log'),
                           'input_hashes_unchanged': True})
            save()
            print(f'PASS routed functional {variant}: {lines[0]}', flush=True)
        for data in prepared.values():
            verify_unchanged(root, data)
        results.update({'all_passed': True, 'status': 'completed'})
        save()
    except Exception as exc:
        results.update({'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
        save()
        raise
    print('PASS bounded routed functional test; timing/physical signoff and formal equivalence remain unasserted')


if __name__ == '__main__':
    main()
