#!/usr/bin/env python3
"""Resume an immutable physical state with an explicit new config and fresh tag."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',required=True)
    parser.add_argument('--source-step',required=True)
    parser.add_argument('--config',required=True)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--from',dest='start',required=True)
    parser.add_argument('--to',dest='stop',required=True)
    args=parser.parse_args()
    assert args.tag.replace('_','').isalnum(), 'Invalid tag'
    source=(root/args.source_run).resolve(); source.relative_to(root)
    config=(root/args.config).resolve(); config.relative_to(root)
    prior=json.loads((source/'input_sha256.json').read_text())
    assert all(sha(root/n)==h for n,h in prior.items()), 'Stale source run'
    initial=source/args.source_step/'state_out.json'
    run=config.parent/'runs'/args.tag
    assert not run.exists(), 'Use a fresh tag'
    output=root/'build/gf180_stage5'/args.tag
    output.mkdir(parents=True,exist_ok=False)
    paths=[root/n for n in prior]+[initial,config,Path(__file__).resolve()]
    def views(obj):
        if isinstance(obj,str) and obj.startswith('/work/'):
            yield root/obj.removeprefix('/work/')
        elif isinstance(obj,dict):
            for value in obj.values(): yield from views(value)
    state=json.loads(initial.read_text())
    paths+=list(views({k:v for k,v in state.items() if k!='metrics'}))
    hashes={f.relative_to(root).as_posix():sha(f) for f in sorted(set(paths))}
    (output/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    command=[sys.executable,'scripts/run_librelane.py','--manual-pdk','--pdk','gf180mcuD',
             '--scl','gf180mcu_fd_sc_mcu7t5v0','--run-tag',args.tag,
             '--with-initial-state','/work/'+initial.relative_to(root).as_posix(),
             '--from',args.start,'--to',args.stop,'--jobs','4','--condensed',args.config]
    print('Running',args.tag,flush=True)
    with (output/'flow.log').open('w') as log:
        done=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
    unchanged=all(sha(root/n)==h for n,h in hashes.items())
    record={'command':command,'source_state':initial.relative_to(root).as_posix(),
            'source_state_sha256':sha(initial),'input_sha256':hashes,
            'inputs_unchanged':unchanged,'returncode':done.returncode,
            'passed':done.returncode==0 and unchanged}
    (output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    if run.exists(): (run/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    assert record['passed'],f'Failed {args.tag}; see {output}/flow.log'
    print('PASS flow',args.tag,flush=True)


if __name__=='__main__':main()
