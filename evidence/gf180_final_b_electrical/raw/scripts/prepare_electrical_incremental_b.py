"""Prepare a fresh incremental state from the completed stage11 B route."""
import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wp(p):return '/work/'+p.relative_to(root).as_posix()
source=root/'config/gf180/runs/stage11_electrical_route_b'
prior=json.loads((source/'input_sha256.json').read_text())
assert all(sha(root/n)==h for n,h in prior.items())
state_path=source/'06-openroad-detailedrouting/state_out.json'
old=json.loads(state_path.read_text())
run=root/'config/gf180/runs/stage12_incremental_prepared_v2_b'
assert not run.exists()
run.mkdir()
state={k:v for k,v in old.items() if k in ['odb','def','sdc','json_h','vh']}
state['metrics']={k:v for k,v in old['metrics'].items() if k in ['design__die__bbox','design__die__area']}
initial=run/'initial_state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
cfg=json.loads((source/'resolved.json').read_text())
cfg['INSERT_ECO_BUFFERS']=[]
cfg['meta']={'version':2,'step':'Custom.ElectricalIncremental'}
config=run/'incremental_config.json';config.write_text(json.dumps(cfg,indent=2)+'\n')
files={root/n for n in prior}|{state_path,initial,config,source/'input_sha256.json',source/'resolved.json',
    Path(__file__).resolve(),root/'scripts/electrical_incremental_b.py',root/'scripts/run_electrical_incremental_step.py'}
files|={root/v.removeprefix('/work/') for k,v in state.items() if isinstance(v,str) and v.startswith('/work/')}
before={p.relative_to(root).as_posix():sha(p) for p in files}
out=run/'01-electrical-incremental'
image=json.loads((root/'config/environment.lock.json').read_text())['container_image']
cmd=['/Applications/Docker.app/Contents/Resources/bin/docker','run','--rm','--pull=never','--network=none',
     '--cpus','4','--memory','8g','--platform','linux/arm64','--user',f'{os.getuid()}:{os.getgid()}',
     '--mount',f'type=bind,source={root},target=/work','--workdir','/work','--env','PDK_ROOT=/work/.pdk',image,
     'python3','scripts/run_electrical_incremental_step.py','run','--id','Custom.ElectricalIncremental',
     '--config',wp(config),'--state-in',wp(initial),'--pdk-root','/work/.pdk','--output',wp(out)]
with (run/'prepare.log').open('w') as log:
    done=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT)
assert done.returncode==0, 'See '+str(run/'prepare.log')
assert all(sha(root/n)==h for n,h in before.items())
final=out/'state_out.json';s=json.loads(final.read_text())
files|={final,out/'config.json'}
files|={root/v.removeprefix('/work/') for v in s.values() if isinstance(v,str) and v.startswith('/work/')}
hashes={p.relative_to(root).as_posix():sha(p) for p in files}
(run/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
(run/'result.json').write_text(json.dumps(dict(command=cmd,returncode=done.returncode,passed=True,
    inputs_unchanged=True,input_sha256=hashes,source_state=str(state_path.relative_to(root)),
    source_state_sha256=sha(state_path),scope='Three-net incremental ECO; fresh DRT/RCX/STA required'),indent=2)+'\n')
print('PASS incremental ECO state prepared')
