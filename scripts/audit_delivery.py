import json,hashlib,gzip,zipfile,re,datetime
from pathlib import Path
P=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def check(p,h):
 assert sha(p)==h,str(p)
res={'reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only audit of existing final physical and functional evidence; no physical rerun','variants':{}}
for v,folder in [('a','gf180_final_a_traceable'),('b','gf180_final_b_electrical')]:
 base=P/'evidence'/folder;d=json.loads((base/'results.json').read_text());r=d['runs'][v]
 for a in d['artifacts'].values():
  q=base/a['archive'];check(q,a['archive_sha256'])
  if a['gzip']:assert hashlib.sha256(gzip.decompress(q.read_bytes())).hexdigest()==a['sha256']
  else:check(q,a['sha256'])
 assert r['available_checks_all_passed'] and r['manufacturability_report_reached']
 for view in r['final_views']:check(P/view['path'],view['sha256'])
 sta=r['extracted_sta'];assert len(sta['corners'])==9
 for name,c in sta['corners'].items():
  check(P/c['fresh_source']['path'],c['fresh_source']['sha256'])
  raw={}
  with (P/c['fresh_source']['path']).open() as f:
   for l in f:
    if l.startswith('%OL_METRIC'):
     s=l.split();raw[s[1].split('__corner:')[0]]=s[2]
  for k in ['timing__setup_vio__count','timing__hold_vio__count','design__max_cap_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count','timing__setup__wns','timing__hold__wns','timing__setup__tns','timing__hold__tns']:
   assert c['metrics'][k]==0 and float(raw[k])==0,(v,name,k)
  assert c['clocks_propagated'] and c['filtered_unannotated']==0
 for k in ['routing_drc','magic_drc','lvs','antenna','disconnected_pins','xor','illegal_overlap']:assert r['checks'][k]['status']=='pass'
 run='stage13_final_traceable_a' if v=='a' else 'stage12_electrical_route_b'
 src=P/('build/final_traceable_functional_a_v2/results.json' if v=='a' else 'build/gf180_routed/final_b_electrical/results.json')
 f=json.loads(src.read_text());fr=f['runs'][v];assert fr['passed'] and fr['input_hashes_unchanged']
 check(P/f'config/gf180/runs/{run}/final/nl/asic_top.nl.v',fr['netlist_sha256'])
 for path,h in fr['input_sha256'].items():check(P/path,h)
 check(P/fr['simulation_log'],fr['simulation_log_sha256'])
 prefix=P/'evidence/gf180_final_replay/final'
 m=json.loads((prefix/f'{v}_manifest.json').read_text());z=prefix/f'{v}_checkpoint.zip';check(z,m['archive_sha256'])
 with zipfile.ZipFile(z) as a:
  assert a.testzip() is None
  for n,info in m['files'].items():assert hashlib.sha256(a.read(n)).hexdigest()==info['sha256'],n
 res['variants'][v]={'run':run,'status':'PASS','archived_artifacts_verified':len(d['artifacts']),'final_views_verified':len(r['final_views']),'fresh_raw_corners_verified':9,'functional_samples':fr['coverage']['samples'],'functional_scope':f['scope'],'netlist_sha256':fr['netlist_sha256'],'checkpoint_crc_and_sha_verified':True,'setup_slack_ns':sta['verification']['worst_setup_slack_ns'],'hold_slack_ns':sta['verification']['worst_hold_slack_ns'],'omissions':r['omissions']}
s=json.loads((P/'evidence/gf180_sweeps/summary.json').read_text());res['sweeps_complete']=s.get('completed_batch');res['sweeps_count']=s.get('point_count');assert res['sweeps_complete'] and res['sweeps_count']==8

for v,tag in [('a','stage13_final_traceable_a'),('b','stage12_electrical_route_b')]:
 base=P/'evidence/layout_captures'/(tag+'_blocks')
 cap=json.loads((base/'capture_manifest.json').read_text())
 for n,h in cap['input_sha256'].items():check(P/n,h)
 for n,h in cap['images'].items():check(base/n,h)
 r=json.loads((base/'regions.json').read_text())
 for n,h in r['input_sha256'].items():check(P/n,h)
 assert len(r['regions']['alu'])==589 and len(r['regions']['rf'])==1804
 assert r['synthesis']['counter_ff']==32 and r['synthesis']['counter_cells']==110
 assert len(json.loads((base/'all_instances.json').read_text()))==r['final_instance_count']
 res['variants'][v]['all_functional_block_groups']=len(r['regions'])
 res['variants'][v]['captures_verified']=len(cap['images'])
 res['variants'][v]['alu_cells_identified']=589
 game=P/('build/gf180_final_a_game/results.json' if v=='a' else 'evidence/gf180_final_b_academic/game_wait_only/results.json')
 g=json.loads(game.read_text());assert g['all_passed'] and g['runs'][v]['passed']
 for name,h in g['input_sha256'].items():check(P/name,h)
 check(P/g['runs'][v]['netlist'],g['runs'][v]['netlist_sha256'])
 res['variants'][v]['mapped_game_coverage']=g['runs'][v]['coverage']
 res['variants'][v]['game_scope']=g['scope']
res['remaining_outside_implementation']=['Informe PDF aplazado por el usuario','Preparación oral del equipo','Publicación mediante VS Code personal pendiente']
res['local_cleanup_record']='evidence/storage_cleanup/cleanup.json'
out=P/'evidence/gf180_delivery/audit.json';out.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
