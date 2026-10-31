#!/usr/bin/env python3
"""Archive routing/checker evidence and verify fresh nine-corner extracted STA.

Exit status describes archival, not signoff. Missing, skipped and failed checks
remain explicit. Full STA logs/max/min reports retain hashes; metrics events,
checks, summary and physical-check failure reports are preserved compactly.
"""
import argparse
import fnmatch
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil


EXPECTED = [f'{rc}_{pvt}' for rc in ['nom', 'min', 'max']
            for pvt in ['tt_025C_5v00', 'ss_125C_4v50', 'ff_n40C_5v50']]
REQUIRED = [f'timing__{kind}__{field}' for kind in ['setup', 'hold']
            for field in ['ws', 'tns']] + [
    f'design__max_{kind}_violation__count' for kind in ['slew', 'cap', 'fanout']]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def metric_events(path):
    values, events = {}, []
    if path.is_file():
        with path.open(errors='replace') as stream:
            for line in stream:
                match = re.match(r'^%OL_METRIC_([IF])\s+(\S+)\s+(\S+)\s*$', line.strip())
                if match:
                    kind, name, value = match.groups()
                    values[name] = int(value) if kind == 'I' else float(value)
                    events.append(line.strip())
    return values, events


def fresh_corner(values, corner):
    suffix = '__corner:'+corner
    return {k.removesuffix(suffix):v for k,v in values.items() if k.endswith(suffix)}


def classify(corners, source_verified, configured):
    complete = (set(corners) == set(EXPECTED) == set(configured) and
                all(all(finite(info['metrics'].get(k)) for k in REQUIRED)
                    for info in corners.values()))
    clean_annotation = (complete and all(info.get('filtered_unannotated') == 0
                                         and info.get('clocks_propagated') is True
                                         for info in corners.values()))
    result = {'expected_corners': EXPECTED, 'measured_corners': sorted(corners),
              'complete_fresh_nine_corners': complete, 'source_verified': source_verified,
              'annotation_and_propagation_verified': clean_annotation,
              'setup_hold_passed': None, 'electrical_passed': None}
    for kind in ['setup', 'hold']:
        key = f'timing__{kind}__ws'
        candidates = {c:i['metrics'][key] for c,i in corners.items() if finite(i['metrics'].get(key))}
        if candidates:
            worst = min(candidates, key=candidates.get)
            result[f'worst_{kind}_corner'] = worst
            result[f'worst_{kind}_slack_ns'] = candidates[worst]
    for kind in ['slew', 'cap', 'fanout']:
        key = f'design__max_{kind}_violation__count'
        available = [i['metrics'][key] for i in corners.values() if finite(i['metrics'].get(key))]
        result[f'max_{kind}_violations_per_corner'] = max(available) if available else None
    if complete and source_verified and clean_annotation:
        result['setup_hold_passed'] = all(i['metrics'][f'timing__{k}__ws'] >= 0 and
            i['metrics'][f'timing__{k}__tns'] == 0 for i in corners.values() for k in ['setup', 'hold'])
        result['electrical_passed'] = all(i['metrics'][f'design__max_{k}_violation__count'] == 0
            for i in corners.values() for k in ['slew', 'cap', 'fanout'])
    return result


def verify_provenance(root, snapshot, record):
    """Require completed runner confirmation, without requiring flow success."""
    def project_path(name):
        if not isinstance(name, str):
            return None
        path = Path(name.removeprefix('/work/'))
        if path.is_absolute() or '..' in path.parts:
            return None
        path = (root/path).resolve()
        return path if path.is_relative_to(root) else None

    valid_snapshot = isinstance(snapshot, dict) and bool(snapshot)
    changed = []
    for name, digest in snapshot.items() if isinstance(snapshot, dict) else []:
        path = project_path(name)
        if (path is None or not path.is_file() or
            not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest) or
            sha(path) != digest):
            changed.append(name)
    finished = (isinstance(record.get('passed'), bool) and
                isinstance(record.get('returncode'), int) and
                not isinstance(record.get('returncode'), bool))
    matched_snapshot = valid_snapshot and record.get('input_sha256') == snapshot
    runner_unchanged = record.get('inputs_unchanged') is True
    source_path = project_path(record.get('source_state'))
    matched_source = bool(source_path and source_path.is_file() and
                          sha(source_path) == record.get('source_state_sha256'))
    return {
        'verified': bool(valid_snapshot and not changed and finished and
                         matched_snapshot and runner_unchanged and matched_source),
        'changed_or_missing_inputs': changed,
        'input_count': len(snapshot) if isinstance(snapshot, dict) else 0,
        'runner_completed': finished,
        'runner_snapshot_matches': bool(matched_snapshot),
        'runner_inputs_unchanged': runner_unchanged,
        'source_state_hash_matches': matched_source,
        'flow_success_required_for_provenance': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tag', required=True)
    parser.add_argument('--period', type=float, required=True)
    parser.add_argument('--variant', choices=['a', 'b', 'both'], default='both')
    parser.add_argument('--output', type=Path, help='Fresh archive directory')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not re.fullmatch(r'[A-Za-z0-9_]+', args.tag):
        raise ValueError('Invalid run tag')
    out = (args.output or root/'evidence/gf180_stage6').resolve()
    out.mkdir(parents=True, exist_ok=False)
    artifacts, omitted, runs = {}, {}, {}

    def rel(path):
        return path.relative_to(root).as_posix()

    def local(name):
        path = (root/name.removeprefix('/work/')).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError(f'Path outside project: {name}')
        return path

    def reference(path):
        return {'path': rel(path), 'sha256': sha(path), 'bytes': path.stat().st_size}

    def preserve(path):
        if not path.is_file() or rel(path) in artifacts:
            return
        record = reference(path)
        compressed = path.stat().st_size > 256*1024
        destination = out/'raw'/rel(path)
        if compressed:
            destination = Path(str(destination)+'.gz')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if compressed:
            with path.open('rb') as src, destination.open('wb') as dst:
                with gzip.GzipFile(filename='', mode='wb', fileobj=dst, mtime=0) as zipped:
                    shutil.copyfileobj(src, zipped)
        else:
            shutil.copyfile(path, destination)
        if sha(path) != record['sha256']:
            raise ValueError(f'File changed during archival: {path}')
        record.update(archive=destination.relative_to(out).as_posix(), gzip=compressed,
                      archive_sha256=sha(destination))
        artifacts[rel(path)] = record

    def archive_tree(directory):
        for path in sorted(directory.rglob('*')):
            if not path.is_file():
                continue
            if path.name in ['max.rpt', 'min.rpt', 'sta.log'] or (
                'stamidpnr' in path.parent.name and path.suffix == '.log'):
                omitted[rel(path)] = dict(reference(path), reason='Full STA output; compact metrics and checks retained')
            elif path.name in ['COMMANDS', 'config.json', 'state_in.json', 'state_out.json',
                               'or_metrics_out.json', 'filter_unannotated_metrics.json', 'runtime.txt'] or (
                path.suffix in ['.log', '.rpt', '.txt', '.xml', '.lyrdb', '.drc'] or
                ('reports' in path.parts and path.suffix == '.json')):
                preserve(path)

    variants = 'ab' if args.variant == 'both' else args.variant
    for variant in variants:
        run = root/f'config/gf180/runs/{args.tag}_{variant}'
        entry = {'available': run.is_dir(), 'checks': {}, 'stages': {}, 'omissions': [],
                 'physical_signoff_claimed': False, 'formal_equivalence_claimed': False}
        runs[variant] = entry
        if not run.is_dir():
            continue
        cfg = read(run/'resolved.json')
        preserve(run/'resolved.json')
        for path in run.iterdir():
            if path.is_file() and path.suffix in ['.json', '.log']:
                preserve(path)
        # The routing runner shares the stage5 bookkeeping directory.
        choices = [root/f'build/gf180_stage5/{args.tag}_{variant}',
                   root/f'build/gf180_stage6/{args.tag}_{variant}']
        build = next((p for p in choices if (p/'result.json').is_file()),
                     next((p for p in choices if p.is_dir()), choices[0]))
        record = read(build/'result.json') if (build/'result.json').is_file() else {}
        if build.is_dir():
            archive_tree(build)
            preserve(build/'result.json')
            preserve(build/'input_sha256.json')
        entry['flow_result'] = record
        snapshot_path = run/'input_sha256.json'
        snapshot = read(snapshot_path) if snapshot_path.is_file() else record.get('input_sha256', {})
        entry['provenance'] = verify_provenance(root, snapshot, record)
        source_verified = entry['provenance']['verified']
        for name in snapshot:
            p = Path(name)
            if p.parts[0] == 'scripts' or (p.parts[0] == 'config' and 'runs' not in p.parts):
                preserve(root/name)
        entry['configuration'] = {k:v for k,v in cfg.items() if k.startswith(('RUN_', 'ERROR_ON_')) or k in [
            'STA_CORNERS', 'TIMING_VIOLATION_CORNERS', 'SETUP_VIOLATION_CORNERS',
            'HOLD_VIOLATION_CORNERS', 'MAX_SLEW_VIOLATION_CORNERS', 'MAX_CAP_VIOLATION_CORNERS',
            'KLAYOUT_DRC_RUNSET', 'MAGIC_DRC_USE_GDS', 'MAGIC_EXT_USE_GDS',
            'MAGIC_EXT_ABSTRACT', 'RSZ_DONT_TOUCH_LIST', 'EQY_FORCE_ACCEPT_PDK', 'VSRC_LOC_FILES']}
        if not cfg.get('KLAYOUT_DRC_RUNSET'):
            entry['omissions'].append('KLayout DRC has no configured runset; skipped is not PASS')
        if not cfg.get('RUN_EQY') or (str(cfg.get('PDK', '')).startswith('gf180') and not cfg.get('EQY_FORCE_ACCEPT_PDK')):
            entry['omissions'].append('Formal EQY equivalence disabled or unsupported for GF180')
        if not cfg.get('MAGIC_EXT_USE_GDS'):
            entry['omissions'].append('LVS extraction uses DEF/LEF; not complete transistor-level GDS extraction')
        if not cfg.get('VSRC_LOC_FILES'):
            entry['omissions'].append('IR-drop analysis has no explicit supply-source locations; report is not power-integrity signoff')
        steps = sorted((p for p in run.iterdir() if p.is_dir() and re.match(r'^\d+-', p.name)),
                       key=lambda p: int(p.name.split('-', 1)[0]))
        for step in steps:
            archive_tree(step)
            direct = read(step/'or_metrics_out.json') if (step/'or_metrics_out.json').is_file() else {}
            for log in step.glob('*.log'):
                values, _ = metric_events(log)
                direct.update(values)
            entry['stages'][step.name] = {'completed': (step/'state_out.json').is_file(),
                'fresh_direct_metrics': direct, 'state': rel(step/'state_out.json'),
                'checker_reached': '-checker-' in step.name}

        def latest(suffix):
            found = [p for p in steps if re.search(re.escape(suffix) + r'(?:-\d+)?$', p.name)]
            return found[-1] if found else None

        def check(label, suffix, metric, report_patterns=(), state_with_report=False):
            step = latest(suffix)
            result = {'status': 'not_run', 'metric': metric}
            if step:
                item = entry['stages'][step.name]
                reports = sorted({p for pattern in report_patterns for p in step.glob(pattern) if p.is_file()})
                value = item['fresh_direct_metrics'].get(metric)
                method = 'direct_metric'
                if value is None and state_with_report and item['completed'] and reports:
                    value = read(step/'state_out.json').get('metrics', {}).get(metric)
                    method = 'known_producer_state_with_own_report'
                valid = item['completed'] and finite(value) and (not report_patterns or bool(reports))
                result = {'status': ('pass' if value == 0 else 'fail') if valid else 'unverified',
                          'metric': metric, 'value': value, 'source': rel(step),
                          'method': method, 'reports': [rel(p) for p in reports]}
            entry['checks'][label] = result

        check('routing_drc', '-openroad-detailedrouting', 'route__drc_errors')
        # A continuation may start directly from a completed DRT state. Accept
        # its routing DRC only when the runner fingerprints that exact producer.
        inherited_route = None
        if not latest('-openroad-detailedrouting') and source_verified:
            initial = local(record['source_state'])
            producer = initial.parent
            producer_cfg = producer/'config.json'
            producer_metrics = producer/'or_metrics_out.json'
            if (producer_cfg.is_file() and producer_metrics.is_file() and
                read(producer_cfg).get('meta', {}).get('step') == 'OpenROAD.DetailedRouting'):
                value = read(producer_metrics).get('route__drc_errors')
                if finite(value):
                    inherited_route = producer
                    for artifact in [initial, producer_cfg, producer_metrics]: preserve(artifact)
                    entry['checks']['routing_drc'] = {
                        'status': 'pass' if value == 0 else 'fail', 'value': value,
                        'metric': 'route__drc_errors', 'source': rel(producer),
                        'method': 'completed_DRT_source_state_verified_by_runner',
                        'reexecuted_in_this_run': False}
        check('disconnected_pins', '-odb-reportdisconnectedpins', 'design__critical_disconnected_pin__count')
        # The last antenna step must follow detailed routing, not only global routing.
        ant = [p for p in steps if re.search(r'-openroad-checkantennas(?:-\d+)?$', p.name)]
        if ant:
            item = entry['stages'][ant[-1].name]
            values = item['fresh_direct_metrics']
            route = latest('-openroad-detailedrouting')
            good = bool(route and int(ant[-1].name.split('-')[0]) > int(route.name.split('-')[0]))
            if inherited_route and not route:
                # Before this fresh antenna check only the obstruction-removal
                # step may run; it does not reroute or resize the source layout.
                preceding = [p for p in steps if int(p.name.split('-')[0]) < int(ant[-1].name.split('-')[0])]
                good = all(read(p/'config.json').get('meta', {}).get('step') ==
                           'Odb.RemoveRoutingObstructions' for p in preceding)
            valid = good and item['completed'] and all(finite(values.get(k)) for k in ['antenna__violating__nets', 'antenna__violating__pins'])
            entry['checks']['antenna'] = {'status': ('pass' if values['antenna__violating__nets'] == values['antenna__violating__pins'] == 0 else 'fail') if valid else 'unverified',
                                         'source': rel(ant[-1]), 'metrics': values}
        else:
            entry['checks']['antenna'] = {'status': 'not_run'}
        check('magic_drc', '-magic-drc', 'magic__drc_error__count', ['reports/drc.magic.rpt'], True)
        check('illegal_overlap', '-magic-spiceextraction', 'magic__illegal_overlap__count', ['feedback.txt'], True)
        check('lvs', '-netgen-lvs', 'design__lvs_error__count', ['reports/lvs.netgen.json'], True)
        check('xor', '-klayout-xor', 'design__xor_difference__count', ['xor.xml'])
        check('klayout_drc', '-klayout-drc', 'klayout__drc_error__count', ['reports/drc.klayout.json'], True)
        if not cfg.get('KLAYOUT_DRC_RUNSET'):
            entry['checks']['klayout_drc']['status'] = 'skipped_no_runset'
        sta = latest('-openroad-stapostpnr')
        corners, spefs, sta_verified = {}, {}, False
        if sta and (sta/'state_in.json').is_file():
            state = read(sta/'state_in.json')
            sta_config = read(sta/'config.json')
            actual_sdc = sta_config.get('SIGNOFF_SDC_FILE') or sta_config.get('PNR_SDC_FILE')
            sdc_matches = bool(actual_sdc and sha(local(actual_sdc)) == sha(root/'config/gf180/constraints.sdc')
                               and sta_config.get('CLOCK_PERIOD') == args.period == cfg.get('CLOCK_PERIOD'))
            entry['signoff_sdc_matches_production_requested_period'] = sdc_matches
            spef_map = state.get('spef', {})
            rcx = latest('-openroad-rcx')
            complete_spefs = bool(rcx and (rcx/'state_out.json').is_file() and isinstance(spef_map, dict))
            for corner in EXPECTED:
                matches = [v for pattern,v in spef_map.items() if fnmatch.fnmatchcase(corner, pattern)]
                if len(matches) != 1:
                    complete_spefs = False
                    continue
                p = local(matches[0])
                spefs[corner] = reference(p)
                complete_spefs = complete_spefs and bool(rcx and p.is_relative_to(rcx) and p.stat().st_size)
            for corner in EXPECTED:
                directory = sta/corner
                log = directory/'sta.log'
                if not log.is_file():
                    continue
                values, events = metric_events(log)
                filter_path = directory/'filter_unannotated_metrics.json'
                if filter_path.is_file():
                    values.update(read(filter_path))
                metrics = fresh_corner(values, corner)
                unpropagated = directory/'unpropagated.rpt'
                corners[corner] = {'metrics': metrics, 'fresh_source': reference(log),
                    'filtered_unannotated': metrics.get('timing__unannotated_net_filtered__count'),
                    'clocks_propagated': unpropagated.is_file() and not unpropagated.read_text().strip()}
                projection = out/'fresh_metrics'/variant/f'{corner}.txt'
                projection.parent.mkdir(parents=True, exist_ok=True)
                projection.write_text('\n'.join(events)+'\n')
                corners[corner]['metrics_projection'] = projection.relative_to(out).as_posix()
                corners[corner]['metrics_projection_sha256'] = sha(projection)
            sta_verified = (source_verified and complete_spefs and sdc_matches and (sta/'state_out.json').is_file() and
                            local(state['nl']).is_relative_to(run) and local(state['odb']).is_relative_to(run))
        entry['extracted_sta'] = {'step': rel(sta) if sta else None, 'spefs': spefs, 'corners': corners,
                                 'verification': classify(corners, sta_verified, cfg.get('STA_CORNERS', []))}
        for name in ['setup_hold', 'electrical']:
            passed = entry['extracted_sta']['verification'][name+'_passed']
            entry['checks'][name] = {'status': 'unverified' if passed is None else ('pass' if passed else 'fail')}
        entry['available_checks_all_passed'] = all(c['status'] == 'pass' for name,c in entry['checks'].items() if name != 'klayout_drc')
        final = run/'final'
        entry['final_views'] = [reference(p) for p in sorted(final.rglob('*')) if p.is_file() and
            p.suffix in ['.gds', '.def', '.lef', '.v', '.spef', '.sdc']] if final.is_dir() else []
        report = latest('-misc-reportmanufacturability')
        entry['manufacturability_report_reached'] = bool(report and (report/'manufacturability.rpt').is_file())

    summary = {'generator': 'summarize_gf180_sweep.py', 'requested_period_ns': args.period, 'run_tag': args.tag, 'variants': list(variants),
        'physical_signoff_claimed': False, 'formal_equivalence_claimed': False,
        'fresh_metric_policy': 'Final STA is read only from per-corner %OL_METRIC events and extraction annotation metrics, never carried state metrics',
        'runs': runs, 'artifacts': artifacts, 'omitted_large_sta': omitted}
    (out/'results.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    size = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    print(f'PASS archive created at {out}; {size/1024/1024:.2f} MiB. This is not a signoff PASS.')
    for variant, entry in runs.items():
        print(variant, {k:v['status'] for k,v in entry.get('checks', {}).items()})


if __name__ == '__main__':
    main()
