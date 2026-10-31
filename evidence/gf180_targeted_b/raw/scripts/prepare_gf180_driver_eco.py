#!/usr/bin/env python3
"""Apply the explicit driver/diode plan, legalize, and freeze a fresh ECO state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from derive_gf180_geometry import geometry


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_]+', args.tag)
    source = (root/args.source_run).resolve(); source.relative_to(root)
    config = (root/args.config).resolve(); config.relative_to(root)
    plan = (root/args.plan).resolve(); plan.relative_to(root)
    prior = json.loads((source/'input_sha256.json').read_text())
    assert prior and all(sha(root/n) == h for n, h in prior.items())
    initial = source/'00-clear-signal-routes/state_out.json'
    state = json.loads(initial.read_text())
    origin = json.loads((source/'result.json').read_text())['source_run']
    base = root/origin/'resolved.json'
    lock_path = root/'config/environment.lock.json'
    lock = json.loads(lock_path.read_text())
    helper = root/'scripts/resize_gf180_drivers.py'
    paths = {root/n for n in prior} | {initial, config, plan, base, helper,
             Path(__file__).resolve(), root/'scripts/derive_gf180_geometry.py', lock_path}
    paths.update([source/'input_sha256.json', source/'result.json'])
    before = {p.relative_to(root).as_posix(): sha(p) for p in paths}
    run = root/'config/gf180/runs'/args.tag
    assert not run.exists(), 'Use a fresh tag'
    run.mkdir()
    output = run/'00-targeted-resize'
    wp = lambda p: '/work/'+p.relative_to(root).as_posix()
    docker = ['/Applications/Docker.app/Contents/Resources/bin/docker', 'run', '--rm',
              '--pull=never', '--network=none', '--cpus', '4', '--memory', '8g',
              '--platform', 'linux/arm64', '--user', f'{os.getuid()}:{os.getgid()}',
              '--mount', f'type=bind,source={root},target=/work', '--workdir', '/work',
              '--env', 'PDK_ROOT=/work/.pdk', lock['container_image']]
    record = {'status': 'running', 'passed': False, 'source_state': str(initial.relative_to(root)),
              'commands': [], 'physical_signoff_claimed': False}
    def save():
        (run/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    def execute(command, name):
        record['commands'].append(command); save()
        with (run/(name+'.log')).open('w') as log:
            done = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        assert done.returncode == 0, f'{name} failed: inspect {run/name}.log'
    save()
    try:
        execute(docker+['openroad', '-exit', '-python', wp(helper),
                '--input-odb', state['odb'], '--source-state', wp(initial),
                '--output-dir', wp(output), '--plan-json', wp(plan)], 'resize')
        manifest = json.loads((output/'manifest.json').read_text())
        assert manifest['status'] == 'verified' and manifest['input_hashes_unchanged']
        for item in manifest['outputs']:
            path = root/item['path'].removeprefix('/work/')
            assert sha(path) == item['sha256']
        # The old logical views have weaker masters: regenerate them from ODB.
        staged = {k: v for k, v in state.items() if k in ['sdc', 'json_h', 'vh']}
        staged.update(odb=wp(output/'asic_top.odb'), def_=None)
        staged.pop('def_')
        staged['def'] = wp(output/'asic_top.def')
        staged['metrics'] = geometry(output/'asic_top.def')['restored_metrics']
        state_path = output/'state_out.json'
        state_path.write_text(json.dumps(staged, indent=2)+'\n')
        cfg = json.loads(base.read_text())
        def resolve(value):
            if isinstance(value, str) and value.startswith('dir::'):
                return wp((config.parent/value.removeprefix('dir::')).resolve())
            if isinstance(value, list): return [resolve(v) for v in value]
            return value
        cfg.update({k: resolve(v) for k, v in json.loads(config.read_text()).items()})
        cfg['meta'] = {'version': 2, 'step': 'OpenROAD.DetailedPlacement'}
        cfg_path = run/'detailed_placement_config.json'
        cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
        step = run/'01-openroad-detailedplacement'
        execute(docker+['python3', '-m', 'librelane.steps', 'run', '--id',
                'OpenROAD.DetailedPlacement', '--config', wp(cfg_path), '--state-in',
                wp(state_path), '--pdk-root', '/work/.pdk', '--output', wp(step)], 'legalize')
        final = json.loads((step/'state_out.json').read_text())
        assert all(final.get(k) for k in ['odb', 'def', 'nl', 'pnl', 'sdc'])
        assert all(sha(root/n) == h for n, h in before.items()), 'Source changed'
        paths.update([output/'manifest.json', state_path, cfg_path, step/'state_out.json',
                      step/'config.json', step/'or_metrics_out.json'])
        paths.update(root/item['path'].removeprefix('/work/') for item in manifest['outputs'])
        paths.update(root/final[k].removeprefix('/work/') for k in ['odb', 'def', 'nl', 'pnl', 'sdc'])
        hashes = {p.relative_to(root).as_posix(): sha(p) for p in sorted(paths)}
        (run/'input_sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
        record.update(status='verified', passed=True, inputs_unchanged=True,
                      final_state=str((step/'state_out.json').relative_to(root)), input_sha256=hashes)
        save(); print('PASS targeted ECO preparation', args.tag, flush=True)
    except Exception as exc:
        record.update(status='failed', error=str(exc)); save(); raise


if __name__ == '__main__':
    main()
