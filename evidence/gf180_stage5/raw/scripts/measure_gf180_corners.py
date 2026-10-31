#!/usr/bin/env python3
"""Measure each PDK corner from one ODB, without inheriting stale STA metrics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, help='Run directory relative to project')
    parser.add_argument('--step', default='12-openroad-stamidpnr-2')
    parser.add_argument('--label', default='extra-sta-allcorners')
    parser.add_argument('--corners', nargs='+', help='Optional subset for diagnostic runs')
    args = parser.parse_args()
    directory = (root/args.run).resolve()
    directory.relative_to(root)
    source = directory/args.step
    config = json.loads((source/'config.json').read_text())
    state = json.loads((source/'state_out.json').read_text())
    output = directory/args.label
    output.mkdir(exist_ok=False)
    # Discard all carried metrics: only each new process's direct measurements count.
    state['metrics'] = {}
    state_path = output/'state_in.json'
    state_path.write_text(json.dumps(state, indent=2)+'\n')
    lock = json.loads((root/'config/environment.lock.json').read_text())
    wp = lambda p: '/work/'+p.relative_to(root).as_posix()
    command = ['/Applications/Docker.app/Contents/Resources/bin/docker', 'run', '--rm',
               '--pull=never', '--network=none', '--cpus', '4', '--memory', '8g',
               '--platform', 'linux/arm64', '--user', f'{os.getuid()}:{os.getgid()}',
               '--mount', f'type=bind,source={root},target=/work', '--workdir', '/work',
               '--env', 'PDK_ROOT=/work/.pdk', lock['container_image'],
               'python3', '-m', 'librelane.steps', 'run', '--id', 'OpenROAD.STAMidPNR']
    odb = root/state['odb'].removeprefix('/work/')
    record = {'source_state':(source/'state_out.json').relative_to(root).as_posix(),
              'source_state_sha256':sha(source/'state_out.json'), 'odb_sha256':sha(odb),
              'sdc_sha256':sha(root/config['PNR_SDC_FILE'].removeprefix('/work/')),
              'script_sha256':sha(Path(__file__)), 'corners':{},
              'parasitics':'estimated from placement or global routing, not extracted',
              'all_timing_passed':False}
    selected = args.corners or config['STA_CORNERS']
    assert set(selected) <= set(config['STA_CORNERS']), 'Unknown corner'
    record['required_corners'] = config['STA_CORNERS']
    record['all_required_corners_measured'] = set(selected) == set(config['STA_CORNERS'])
    for corner in selected:
        cfg = dict(config)
        cfg['DEFAULT_CORNER'] = corner
        cfg['PNR_CORNERS'] = [corner]
        cfg_path = output/f'{corner}.json'
        cfg_path.write_text(json.dumps(cfg, indent=2)+'\n')
        target = output/corner
        invocation = command+['--config', wp(cfg_path), '--state-in', wp(state_path),
                              '--pdk-root', '/work/.pdk', '--output', wp(target)]
        with (output/f'{corner}.log').open('w') as log:
            done = subprocess.run(invocation, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        if done.returncode:
            raise SystemExit(f'Failed {corner}; inspect {output}')
        # or_metrics_out contains only newly emitted measurements.
        metrics = json.loads((target/'or_metrics_out.json').read_text())
        values = {k.removesuffix('__corner:'+corner):v for k,v in metrics.items()
                  if k.endswith('__corner:'+corner)}
        for key in ['timing__setup__ws', 'timing__hold__ws',
                    'timing__setup__tns', 'timing__hold__tns']:
            assert key in values, f'Missing fresh {key} for {corner}'
        passed = all(values[f'timing__{kind}__ws'] >= 0 and
                     values[f'timing__{kind}__tns'] == 0 for kind in ['setup','hold'])
        record['corners'][corner] = {'metrics':values, 'timing_passed':passed,
                                    'command':invocation, 'config_sha256':sha(cfg_path)}
        print(corner, 'setup', values['timing__setup__ws'], 'hold', values['timing__hold__ws'],
              'slew/cap/fanout', *[values.get(f'design__max_{x}_violation__count')
                                   for x in ['slew','cap','fanout']], flush=True)
    assert sha(odb) == record['odb_sha256'], 'ODB changed while measuring'
    record['all_timing_passed'] = all(c['timing_passed'] for c in record['corners'].values())
    (output/'results.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    main()
