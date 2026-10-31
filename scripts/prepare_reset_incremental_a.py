"""Prepare the single authorized final A iteration from its traceable routed state."""
import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
wp=lambda p:'/work/'+p.relative_to(root).as_posix()
source=root/'config/gf180/runs/stage7_trace_physical_ref_a'
prior=json.loads((source/'input_sha256.json').read_text())
assert all(sha(root/n)==h for n,h in prior.items()),'Source changed'
state_path=source/'34-openroad-detailedrouting/state_out.json'
old=json.loads(state_path.read_text())
run=root/'config/gf180/runs/stage13_reset_prepared_v2_a'
assert not run.exists(),'Do not repeat preparation'
run.mkdir()
state={k:v for k,v in old.items() if k in ['odb','def','sdc','json_h','vh']}
state['metrics']={k:v for k,v in old['metrics'].items() if k in ['design__die__bbox','design__die__area']}
initial=run/'initial_state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
cfg=json.loads((source/'resolved.json').read_text())
cfg['INSERT_ECO_BUFFERS']=[]
cfg['meta']={'version':2,'step':'Custom.ResetIncrementalA'}
config=run/'incremental_config.json';config.write_text(json.dumps(cfg,indent=2)+'\n')
files={root/n for n in prior}|{state_path,initial,config,source/'input_sha256.json',source/'resolved.json',
    Path(__file__).resolve(),root/'scripts/reset_incremental_a.py',root/'scripts/run_reset_incremental_step.py'}
files|={root/v.removeprefix('/work/') for k,v in state.items() if isinstance(v,str) and v.startswith('/work/')}
before={p.relative_to(root).as_posix():sha(p) for p in files}
out=run/'01-reset-incremental'
image=json.loads((root/'config/environment.lock.json').read_text())['container_image']
cmd=['/Applications/Docker.app/Contents/Resources/bin/docker','run','--rm','--pull=never','--network=none',
 '--cpus','4','--memory','8g','--platform','linux/arm64','--user',f'{os.getuid()}:{os.getgid()}',
 '--mount',f'type=bind,source={root},target=/work','--workdir','/work','--env','PDK_ROOT=/work/.pdk',image,
 'python3','scripts/run_reset_incremental_step.py','run','--id','Custom.ResetIncrementalA',
 '--config',wp(config),'--state-in',wp(initial),'--pdk-root','/work/.pdk','--output',wp(out)]
with (run/'prepare.log').open('w') as log:
    result=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,'See '+str(run/'prepare.log')
assert all(sha(root/n)==h for n,h in before.items())
final=out/'state_out.json';s=json.loads(final.read_text())
files|={final,out/'config.json'}
files|={root/v.removeprefix('/work/') for v in s.values() if isinstance(v,str) and v.startswith('/work/')}
hashes={p.relative_to(root).as_posix():sha(p) for p in files}
(run/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
(run/'result.json').write_text(json.dumps(dict(command=cmd,returncode=result.returncode,passed=True,
 inputs_unchanged=True,input_sha256=hashes,source_state=str(state_path.relative_to(root)),
 scope='Two reset nets changed; final DRT/RCX/STA/DRC/LVS required'),indent=2)+'\n')
print('PASS traceable A reset ECO prepared')
