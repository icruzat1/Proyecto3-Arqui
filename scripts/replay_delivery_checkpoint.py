#!/usr/bin/env python3
"""Restore a verified final checkpoint; optionally repeat its remaining checks."""
import argparse,hashlib,json,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['a','b'],required=True);p.add_argument('--tag');p.add_argument('--prepare-only',action='store_true');p.add_argument('--profile',choices=['final'],default='final');a=p.parse_args()
 tag=a.tag or 'replay_final_'+a.variant
 assert tag.replace('_','').isalnum()
 directory=ROOT/'build/final_replay/final'/a.variant
 archive=ROOT/'evidence/gf180_final_replay/final'/f'{a.variant}_checkpoint.zip'
 outer=json.loads(archive.with_name(f'{a.variant}_manifest.json').read_text());assert digest(archive.read_bytes())==outer['archive_sha256']
 with zipfile.ZipFile(archive) as z:
  manifest=json.loads(z.read('manifest.json'));assert manifest['variant']==a.variant
  assert digest((ROOT/manifest['config']).read_bytes())==manifest['config_sha256']
  allowed={'state.json','manifest.json',*manifest['files']};assert set(z.namelist())==allowed
  for name in allowed:
   path=Path(name);assert not path.is_absolute() and '..' not in path.parts
   data=z.read(name)
   if name in manifest['files']:assert digest(data)==manifest['files'][name]['sha256']
   target=directory/name
   if target.exists():assert target.read_bytes()==data,'Existing checkpoint changed; stop'
   else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 print('PASS restored checkpoint',a.variant,flush=True)
 if a.prepare_only:return
 assert not (ROOT/'config/gf180/runs'/tag).exists(),'Use a fresh --tag'
 state='/work/'+(directory/'state.json').relative_to(ROOT).as_posix()
 command=[sys.executable,'scripts/run_librelane.py','--manual-pdk','--pdk','gf180mcuD','--scl','gf180mcu_fd_sc_mcu7t5v0','--run-tag',tag,'--with-initial-state',state,'--from',manifest['from_step'],'--to','Misc.ReportManufacturability','--jobs','4','--condensed',manifest['config']]
 result=subprocess.run(command,cwd=ROOT)
 record={'command':command,'returncode':result.returncode,'archive_sha256':outer['archive_sha256'],'scope':manifest['scope']}
 (directory/(tag+'_result.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(result.returncode)
if __name__=='__main__':main()
