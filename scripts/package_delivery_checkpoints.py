#!/usr/bin/env python3
"""Package existing routed checkpoints; never execute physical implementation."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['final'],default='final');args=parser.parse_args()
 out=ROOT/'evidence/gf180_final_replay/final'
 out.mkdir(parents=True,exist_ok=True)
 replay_base='build/final_replay/final'
 sources={'a':'config/gf180/runs/stage13_final_traceable_a/01-openroad-detailedrouting/state_out.json','b':'config/gf180/runs/stage12_electrical_route_b/01-openroad-detailedrouting/state_out.json'}
 configs={'a':'config/gf180/a_final_traceable.json','b':'config/gf180/b_electrical_eco.json'}
 for v,name in sources.items():
  state=json.loads((ROOT/name).read_text());files={}
  def rewrite(obj):
   if isinstance(obj,str) and obj.startswith('/work/'):
    source=ROOT/obj[6:];assert source.is_file()
    if obj not in files:files[obj]={'source':source,'member':f'views/{len(files):02d}_{source.name}','sha256':sha(source)}
    return '/work/'+replay_base+'/'+v+'/'+files[obj]['member']
   if isinstance(obj,dict):return {k:rewrite(x) for k,x in obj.items()}
   if isinstance(obj,list):return [rewrite(x) for x in obj]
   return obj
  converted={k:(value if k=='metrics' else rewrite(value)) for k,value in state.items()}
  manifest={'variant':v,'source_state':name,'source_state_sha256':sha(ROOT/name),'config':configs[v],'config_sha256':sha(ROOT/configs[v]),'from_step':'Odb.RemoveRoutingObstructions','scope':'Existing routed checkpoint; replays extraction/STA/export/checks, not synthesis or routing from RTL.','files':{x['member']:{'source':str(x['source'].relative_to(ROOT)),'sha256':x['sha256']} for x in files.values()}}
  target=out/f'{v}_checkpoint.zip';assert not target.exists()
  with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   z.writestr('state.json',json.dumps(converted,indent=2)+'\n');z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
   for item in files.values():z.write(item['source'],item['member'])
  with zipfile.ZipFile(target) as z:
   assert z.testzip() is None
   for item in files.values():assert hashlib.sha256(z.read(item['member'])).hexdigest()==item['sha256']
  manifest['archive_sha256']=sha(target);manifest['archive_bytes']=target.stat().st_size
  (out/f'{v}_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  print(v,'checkpoint verified',round(target.stat().st_size/1e6,2),'MB',flush=True)
if __name__=='__main__':main()
