#!/usr/bin/env python3
"""Derive a fresh, verified unrouted state without changing its source run.

Install this wrapper under the project's scripts/ directory before running:
  .venv/bin/python scripts/prepare_gf180_reroute.py \
    --source-run config/gf180/runs/stage6_100ns_u40_route_a \
    --source-step 08-openroad-detailedrouting \
    --tag stage6_100ns_u40_unrouted_v3_a

The output is a placement database that MUST undergo fresh GRT/DRT/RCX/STA.
No previous timing/routing/signoff metrics or timing views are carried forward.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def require(ok,message):
    if not ok:
        raise RuntimeError(message)


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',required=True)
    parser.add_argument('--source-step',required=True)
    parser.add_argument('--tag',required=True)
    args=parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9_]+',args.tag),'Invalid fresh tag')
    require(re.fullmatch(r'[A-Za-z0-9_-]+',args.source_step),'Invalid source step')
    source=(root/args.source_run).resolve(strict=True)
    require(source.parent==(root/'config/gf180/runs').resolve(),
            'Source run must be an immediate child of config/gf180/runs')
    relative=lambda p:p.relative_to(root).as_posix()
    wp=lambda p:'/work/'+relative(p)
    def host(path):
        require(isinstance(path,str) and path.startswith('/work/'),
                f'Expected /work view path: {path!r}')
        target=(root/path.removeprefix('/work/')).resolve(strict=True)
        target.relative_to(root)
        require(target.is_file(),f'View is not a file: {target}')
        return target
    def views(obj):
        if isinstance(obj,str) and obj.startswith('/work/'):
            yield host(obj)
        elif isinstance(obj,dict):
            for value in obj.values():
                yield from views(value)
        elif isinstance(obj,list):
            for value in obj:
                yield from views(value)
    source_index=source/'input_sha256.json'
    prior=json.loads(source_index.read_text())
    require(isinstance(prior,dict) and prior,'Missing nonempty baseline input hashes')
    prior_files=[]
    for name,digest in prior.items():
        path=(root/name).resolve(strict=True)
        path.relative_to(root)
        require(sha(path)==digest,f'Stale source-run input: {name}')
        prior_files.append(path)
    initial=source/args.source_step/'state_out.json'
    old_state=json.loads(initial.read_text())
    input_odb=host(old_state['odb'])
    for key in ('nl','pnl','sdc'):
        require(key in old_state and isinstance(old_state[key],str),
                f'Source state must contain its matching logical {key} view')
        host(old_state[key])
    helper=root/'scripts/clear_signal_routes.py'
    lock_path=root/'config/environment.lock.json'
    lock=json.loads(lock_path.read_text())
    require('@sha256:' in lock['container_image'],'Container image must be digest-pinned')
    paths=set(prior_files+[source_index,initial,helper,Path(__file__).resolve(),lock_path])
    paths.update(views({k:v for k,v in old_state.items() if k!='metrics'}))
    before_hashes={relative(p):sha(p) for p in sorted(paths)}
    run=source.parent/args.tag
    require(not run.exists(),f'Use a fresh tag; destination exists: {run}')
    run.mkdir()
    output=run/'00-clear-signal-routes'  # Helper requires this not to exist yet.
    snapshot=run/'source_input_sha256.json'
    snapshot.write_text(json.dumps(before_hashes,indent=2)+'\n')
    docker=Path('/Applications/Docker.app/Contents/Resources/bin/docker')
    docker_path=str(docker) if docker.is_file() else shutil.which('docker')
    require(docker_path is not None,'Docker executable unavailable')
    command=[docker_path,'run','--rm','--pull=never','--network=none',
             '--cpus','4','--memory','8g','--platform','linux/arm64',
             '--user',f'{os.getuid()}:{os.getgid()}',
             '--mount',f'type=bind,source={root},target=/work','--workdir','/work',
             '--env','PDK_ROOT=/work/.pdk',lock['container_image'],
             'openroad','-exit','-python',wp(helper),
             '--input-odb',wp(input_odb),'--source-state',wp(initial),
             '--output-dir',wp(output),'--clear-guides',
             '--provenance-file',wp(snapshot),
             '--provenance-file',wp(source_index),
             '--provenance-file',wp(Path(__file__).resolve()),
             '--provenance-file',wp(lock_path)]
    record={'status':'running','passed':False,
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'source_run':relative(source),'source_step':args.source_step,
            'source_state':relative(initial),'source_state_sha256':sha(initial),
            'source_run_input_hashes_verified_count':len(prior),
            'command':command,'run_dir':relative(run),
            'operation':'Derived placement database; fresh routing/extraction/STA required',
            'logical_views_preserved':['json_h','vh','nl','pnl','sdc'],
            'routing_or_timing_signoff_claimed':False}
    result_path=run/'result.json'
    result_path.write_text(json.dumps(record,indent=2)+'\n')
    try:
        env=os.environ.copy()
        for key in ('GITHUB_TOKEN','GH_TOKEN'):
            env.pop(key,None)
        print(f'Preparing verified unrouted state: {args.tag}',flush=True)
        with (run/'prepare.log').open('w') as log:
            done=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        record['returncode']=done.returncode
        require(done.returncode==0,f'Clear-routes helper failed; see {run}/prepare.log')
        manifest_path=output/'manifest.json'
        manifest=json.loads(manifest_path.read_text())
        require(manifest.get('status')=='verified','Helper manifest is not verified')
        require(manifest.get('input_hashes_unchanged') is True,'Helper input verification missing')
        require(manifest.get('clear_non_supply_guides') is True,'Guides were not cleared')
        before,after=manifest['before'],manifest['after']
        require(before['invariants']==after['invariants'],'Preservation invariants differ')
        require(after['non_supply_regular_wire_count']==0,'Signal routes remain')
        require(after['guide_count']==after['supply_guide_count'],'Non-supply guides remain')
        require(manifest['def_preservation']['before']==manifest['def_preservation']['after'],
                'DEF preservation failed')
        outputs=[]
        for artifact in manifest['outputs']:
            path=host(artifact['path'])
            path.relative_to(output)
            require(path.stat().st_size==artifact['bytes'] and sha(path)==artifact['sha256'],
                    f'Output differs from verified manifest: {path}')
            outputs.append(path)
        for artifact in manifest['inputs']:
            require(sha(host(artifact['path']))==artifact['sha256'],
                    f'Input differs from helper manifest: {artifact["path"]}')
        odbs=[p for p in outputs if p.suffix=='.odb']
        defs=[p for p in outputs if p.suffix=='.def']
        require(len(odbs)==len(defs)==1,'Expected exactly one derived ODB and DEF')
        require(all(sha(root/name)==digest for name,digest in before_hashes.items()),
                'Source run, tools or provenance changed during preparation')
        keep={'json_h','vh','nl','pnl','sdc'}
        state={k:v for k,v in old_state.items() if k in keep and v is not None}
        state.update({'odb':wp(odbs[0]),'def':wp(defs[0]),'metrics':{}})
        state_path=output/'state_out.json'
        state_path.write_text(json.dumps(state,indent=2)+'\n')
        # The historical SDF/SPEF files remain only as provenance hashes. They
        # are absent from the consumable state, as are all carried metrics.
        final_paths=paths|{snapshot,manifest_path,state_path}|set(outputs)
        final_paths.update(views({k:v for k,v in state.items() if k!='metrics'}))
        hashes={relative(p):sha(p) for p in sorted(final_paths)}
        (run/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        record.update({'status':'verified','passed':True,'inputs_unchanged':True,
                       'manifest':relative(manifest_path),'manifest_sha256':sha(manifest_path),
                       'derived_state':relative(state_path),'derived_state_sha256':sha(state_path),
                       'removed_regular_wires':manifest['removed_regular_wires'],
                       'invalidated_state_keys':sorted(set(old_state)-keep-{'odb','def','metrics'}),
                       'invalidated_metric_count':len(old_state.get('metrics',{})),
                       'input_sha256_count':len(hashes),
                       'preserved_instances':after['invariants']['instances'],
                       'preserved_special_wires':after['invariants']['special_wires']})
    except Exception as exc:
        record.update({'status':'failed','passed':False,'error':f'{type(exc).__name__}: {exc}'})
        result_path.write_text(json.dumps(record,indent=2)+'\n')
        raise
    result_path.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','derived_state','removed_regular_wires',
                                          'preserved_instances','preserved_special_wires')},indent=2))


if __name__=='__main__':
    main()
