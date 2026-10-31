import os,hashlib,json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root);tag='stage10_trace_wait_only_b';cfg=root/'config/gf180/b_final_wait_only.json';out=root/'build/gf180_final_game_synthesis';out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads(cfg.read_text());sources=[root/x[6:] if x.startswith('/work/') else (cfg.parent/x[5:]).resolve() for x in c['VERILOG_FILES']]
sources += [cfg,root/'config/environment.lock.json',root/'scripts/check_gf180_mapped_game_trial.py',root/'config/gf180/constraints.sdc']
sources += list((root/'build/gf180_game/firmware').iterdir())
hashes={str(p.relative_to(root)):sha(p) for p in sources if p.is_file()}
image=json.loads((root/'config/environment.lock.json').read_text())['container_image'];D='/Applications/Docker.app/Contents/Resources/bin/docker'
cmd=[D,'run','--rm','--pull=never','--network=none','--cpus','1','--memory','3g','--platform','linux/arm64','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={root},target=/work','--workdir','/work','--env','PDK_ROOT=/work/.pdk',image,'python3','-m','librelane','--manual-pdk','--pdk','gf180mcuD','--scl','gf180mcu_fd_sc_mcu7t5v0','--run-tag',tag,'--to','Yosys.Synthesis','--jobs','1','--condensed',str(cfg.relative_to(root))]
assert not (root/'config/gf180/runs'/tag).exists()
with (out/'flow.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
unchanged=all(sha(root/n)==h for n,h in hashes.items());record=dict(returncode=r.returncode,inputs_unchanged=unchanged,input_sha256=hashes,command=cmd,scope='Final B synthesis recipe with wait-only test firmware; not production geometry')
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');assert r.returncode==0 and unchanged
(root/'config/gf180/runs'/tag/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
subprocess.run([sys.executable,'-B','scripts/check_gf180_mapped_game_trial.py'],check=True)
print('PASS final B synthesis recipe game verification',flush=True)
