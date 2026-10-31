#!/usr/bin/env python3
"""Reproducible KLayout GUI captures; no physical design mutations."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--antenna',action='store_true');p.add_argument('--render-only',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1];assert a.run.replace('_','').isalnum()
folder=('antenna_' if a.antenna else '')+a.run;out=root/'evidence/layout_captures'/folder
image=json.loads((root/'config/environment.lock.json').read_text())['container_image']
base=['/Applications/Docker.app/Contents/Resources/bin/docker','run','--rm','--pull=never','--network=none',
      '--cpus','1','--memory','2g','--user',f'{os.getuid()}:{os.getgid()}',
      '--mount',f'type=bind,source={root},target=/work','--workdir','/work',
      '--env','QT_QPA_PLATFORM=offscreen','--env','XDG_CACHE_HOME=/tmp',image]
commands=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
extractor='scripts/extract_gf180_antenna_capture.py' if a.antenna else 'scripts/extract_gf180_capture_regions.py'
if not a.render_only:
    commands.append(base+['openroad','-exit','-python',extractor,'--run',a.run,'--out',str(out.relative_to(root))])
commands.append(base+['klayout','-z','-nc','-r','scripts/klayout_capture_regions.py','-rd','capture_dir='+str(out.relative_to(root))])
log=root/'build'/('capture_'+folder+'.log')
with log.open('w') as f:
    for cmd in commands:
        r=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT);assert r.returncode==0,f'See {log}'
regions=json.loads((out/'regions.json').read_text())
assert all(sha(root/n)==h for n,h in regions['input_sha256'].items()),'Source changed'
inputs=[root/extractor,root/'scripts/klayout_capture_regions.py',Path(__file__).resolve(),root/'config/environment.lock.json',out/'regions.json']
manifest=dict(commands=commands,source_hashes_verified=True,input_sha256={str(p.relative_to(root)):sha(p) for p in inputs},
              images={p.name:sha(p) for p in sorted(out.glob('*.png'))},scope='Actual KLayout GUI viewport exports with overlays; no GDS modifications.')
(out/'capture_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS capture',folder)
