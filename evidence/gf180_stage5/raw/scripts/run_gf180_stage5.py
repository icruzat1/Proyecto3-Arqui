#!/usr/bin/env python3
"""Continue immutable GF180 floorplans through placement, CTS and timing repair."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['a', 'b', 'both'], default='both')
    parser.add_argument('--source-tag', default='stage4_100ns_u40_floorplan')
    parser.add_argument('--tag', default='stage5_100ns_u40_cts')
    args = parser.parse_args()
    for label in (args.tag, args.source_tag):
        if not label.replace('_', '').isalnum():
            raise SystemExit('Tags must contain only letters, numbers and underscores')
    lock = json.loads((root/'config/environment.lock.json').read_text())
    for variant in (['a', 'b'] if args.variant == 'both' else [args.variant]):
        label = f'{args.tag}_{variant}'
        source = root/f'config/gf180/runs/{args.source_tag}_{variant}'
        initial = source/'26-odb-customioplacement/state_out.json'
        historical = json.loads((source/'input_sha256.json').read_text())
        for name, digest in historical.items():
            if sha(root/name) != digest:
                raise SystemExit(f'Source floorplan input changed: {name}')
        run_dir = root/f'config/gf180/runs/{label}'
        if run_dir.exists():
            raise SystemExit(f'Run already exists: {run_dir}; choose a fresh --tag')
        output = root/'build/gf180_stage5'/label
        output.mkdir(parents=True, exist_ok=False)
        state = json.loads(initial.read_text())
        sources = [root/name for name in historical] + [initial, Path(__file__).resolve()]
        # Include every material view actually consumed by the resumed flow.
        def views(obj):
            if isinstance(obj, str) and obj.startswith('/work/'):
                yield root/obj.removeprefix('/work/')
            elif isinstance(obj, dict):
                for value in obj.values():
                    yield from views(value)
        sources += list(views({k:v for k,v in state.items() if k != 'metrics'}))
        hashes = {s.relative_to(root).as_posix():sha(s) for s in sorted(set(sources))}
        (output/'input_sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
        command = [sys.executable, 'scripts/run_librelane.py', '--manual-pdk', '--pdk',
                   'gf180mcuD', '--scl', 'gf180mcu_fd_sc_mcu7t5v0', '--run-tag', label,
                   '--with-initial-state', '/work/'+initial.relative_to(root).as_posix(),
                   '--from', 'Odb.ApplyDEFTemplate', '--to', 'OpenROAD.STAMidPNR-2',
                   '--jobs', '4', '--condensed', f'config/gf180/{variant}.json']
        print(f'Running {label}: placement, clock tree, setup/hold repair', flush=True)
        with (output/'flow.log').open('w') as log:
            result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(f'Failed {label}; see {output}/flow.log')
        # Classic has no fresh STA between placement repair and CTS. Measure
        # that saved ODB separately, never mistake carried metrics for new STA.
        pre = next(run_dir.glob('*-openroad-stamidpnr'))
        placed = next(run_dir.glob('*-openroad-detailedplacement'))
        docker = '/Applications/Docker.app/Contents/Resources/bin/docker'
        container = [docker, 'run', '--rm', '--pull=never', '--network=none',
                     '--cpus', '4', '--memory', '8g', '--platform', 'linux/arm64',
                     '--user', f'{os.getuid()}:{os.getgid()}', '--mount',
                     f'type=bind,source={root},target=/work', '--workdir', '/work',
                     '--env', 'PDK_ROOT=/work/.pdk', lock['container_image']]
        wp = lambda path: '/work/'+path.relative_to(root).as_posix()
        sta = run_dir/'extra-sta-postplacement'
        sta_command = container+['python3', '-m', 'librelane.steps', 'run', '--id',
                      'OpenROAD.STAMidPNR', '--config', wp(pre/'config.json'),
                      '--state-in', wp(placed/'state_out.json'), '--pdk-root',
                      '/work/.pdk', '--output', wp(sta)]
        with (output/'sta_postplacement.log').open('w') as log:
            measured = subprocess.run(sta_command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        unchanged = all(sha(root/name) == digest for name,digest in hashes.items())
        record = {'variant':variant, 'source_state':initial.relative_to(root).as_posix(),
                  'source_state_sha256':sha(initial), 'command':command,
                  'sta_command':sta_command, 'run_dir':run_dir.relative_to(root).as_posix(),
                  'flow_returncode':result.returncode, 'sta_returncode':measured.returncode,
                  'inputs_unchanged':unchanged, 'input_sha256':hashes,
                  'passed':result.returncode == 0 and measured.returncode == 0 and unchanged}
        (output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
        (run_dir/'input_sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
        if not record['passed']:
            raise SystemExit(f'Failed verification: {label}')
        print(f'PASS flow {label}; inspect timing separately from flow success', flush=True)


if __name__ == '__main__':
    main()
