"""Export current A/B layouts with verified identifiers for all functional blocks."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--variant',choices=['a','b'],required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1]
tag={'a':'stage13_final_traceable_a','b':'stage12_electrical_route_b'}[a.variant]
synth='stage7_trace_ref_'+a.variant
out=root/'evidence/layout_captures'/(tag+'_blocks')
image=json.loads((root/'config/environment.lock.json').read_text())['container_image']
base=['/Applications/Docker.app/Contents/Resources/bin/docker','run','--rm','--pull=never','--network=none',
 '--cpus','1','--memory','2g','--user',f'{os.getuid()}:{os.getgid()}',
 '--mount',f'type=bind,source={root},target=/work','--workdir','/work',
 '--env','QT_QPA_PLATFORM=offscreen','--env','XDG_CACHE_HOME=/tmp',image]
commands=[
 base+['openroad','-exit','-python','scripts/extract_final_blocks.py','--run',tag,'--synthesis',synth,'--out',str(out.relative_to(root))],
 base+['klayout','-z','-nc','-r','scripts/render_final_blocks.py','-rd','capture_dir='+str(out.relative_to(root))]]
log=root/'build'/('capture_final_blocks_'+a.variant+'.log')
with log.open('w') as f:
 for cmd in commands:
  r=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT);assert r.returncode==0,f'See {log}'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
regions=json.loads((out/'regions.json').read_text());assert all(sha(root/n)==h for n,h in regions['input_sha256'].items())
inputs=[root/'scripts/extract_final_blocks.py',root/'scripts/render_final_blocks.py',Path(__file__).resolve(),root/'config/environment.lock.json',out/'regions.json',out/'all_instances.json']
manifest=dict(commands=commands,source_hashes_verified=True,input_sha256={str(p.relative_to(root)):sha(p) for p in inputs},
 images={p.name:sha(p) for p in sorted(out.glob('*.png'))},scope='Actual KLayout GUI viewport exports. All named functional blocks verified in final ODB/netlist. Overlapping parent/child groups are not additive.')
(out/'capture_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS all functional block captures',a.variant,len(manifest['images']),flush=True)
