#!/usr/bin/env python3
"""Rebuild CTS from the saved repaired placement, retaining the original SDC."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['a','b','both'], default='both')
    parser.add_argument('--tag', default='stage5_100ns_u40_clockv2')
    parser.add_argument('--source-tag', default='stage5_100ns_u40_cts')
    args = parser.parse_args()
    for tag in [args.tag,args.source_tag]:
        assert tag.replace('_','').isalnum(), 'Invalid tag'
    for v in ('ab' if args.variant == 'both' else args.variant):
        label = f'{args.tag}_{v}'
        source = root/f'config/gf180/runs/{args.source_tag}_{v}'
        prior = json.loads((source/'input_sha256.json').read_text())
        assert all(sha(root/n)==h for n,h in prior.items()), 'Stale source placement'
        initial = source/'08-openroad-detailedplacement/state_out.json'
        state = json.loads(initial.read_text())
        base_config = root/f'config/gf180/{v}.json'
        cfg = json.loads(base_config.read_text())
        cfg.update(CTS_SINK_CLUSTERING_SIZE=4, CTS_MAX_CAP=0.16,
                   CTS_DISTANCE_BETWEEN_BUFFERS=100)
        config = root/f'config/gf180/{v}_clockv2.json'
        config.write_text(json.dumps(cfg,indent=2)+'\n')
        run = root/f'config/gf180/runs/{label}'
        assert not run.exists(), 'Use a fresh tag'
        output = root/'build/gf180_stage5'/label
        output.mkdir(parents=True,exist_ok=False)
        sources = [root/n for n in prior]+[initial,config,Path(__file__).resolve()]
        for value in state.values():
            if isinstance(value,str) and value.startswith('/work/'):
                sources.append(root/value.removeprefix('/work/'))
        hashes={s.relative_to(root).as_posix():sha(s) for s in sorted(set(sources))}
        (output/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        command=[sys.executable,'scripts/run_librelane.py','--manual-pdk','--pdk','gf180mcuD',
                 '--scl','gf180mcu_fd_sc_mcu7t5v0','--run-tag',label,
                 '--with-initial-state','/work/'+initial.relative_to(root).as_posix(),
                 '--from','OpenROAD.CTS','--to','OpenROAD.STAMidPNR-2',
                 '--jobs','4','--condensed',config.relative_to(root).as_posix()]
        print(f'Running {label}',flush=True)
        with (output/'flow.log').open('w') as log:
            completed=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
        unchanged=all(sha(root/n)==h for n,h in hashes.items())
        record={'variant':v,'command':command,'source_state':initial.relative_to(root).as_posix(),
                'source_state_sha256':sha(initial),'input_sha256':hashes,'inputs_unchanged':unchanged,
                'passed':completed.returncode==0 and unchanged,'returncode':completed.returncode}
        (output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        if run.exists():
            (run/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        assert record['passed'], f'Failed {label}'
        print(f'PASS flow {label}',flush=True)


if __name__=='__main__':
    main()
