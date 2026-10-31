"""Lossless archive of inactive physical runs, with full member hash verification.
This command never deletes original files. Cleanup is a separate reviewed step.
"""
import hashlib,json,os,subprocess,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/local_archive/runs'
OUT.mkdir(parents=True,exist_ok=True)
KEEP={'stage13_final_traceable_a','stage12_electrical_route_b','stage7_trace_ref_a','stage7_trace_ref_b','stage13_trace_wait_only_a','stage10_trace_wait_only_b'}
ZSTD='/opt/anaconda3/bin/zstd'
progress=OUT/'progress.json'
assert not progress.exists(),'Do not duplicate the archive process'
runs=sorted(p for p in (ROOT/'config/gf180/runs').iterdir() if p.is_dir() and p.name not in KEEP)
status=dict(started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),scope='Lossless archival only; originals retained',keep=sorted(KEEP),completed=[],total_runs=len(runs))
def save():progress.write_text(json.dumps(status,indent=2)+'\n')
def digest_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
class HashReader:
 def __init__(self,f):self.f=f;self.h=hashlib.sha256()
 def read(self,n=-1):
  b=self.f.read(n);self.h.update(b);return b
save()
for run in runs:
 status['active']=run.name;save()
 target=OUT/(run.name+'.tar.zst');assert not target.exists()
 members={}
 proc=subprocess.Popen([ZSTD,'-q','-1','-T4','-o',str(target)],stdin=subprocess.PIPE)
 with tarfile.open(fileobj=proc.stdin,mode='w|',format=tarfile.PAX_FORMAT) as tf:
  for base,dirs,files in os.walk(run,followlinks=False):
   for name in sorted(dirs+files):
    p=Path(base)/name;rel=p.relative_to(ROOT).as_posix();info=tf.gettarinfo(str(p),arcname=rel)
    record=dict(size=info.size,mode=info.mode,type=info.type.decode(),mtime_ns=p.lstat().st_mtime_ns)
    if info.isfile():
     with p.open('rb') as f:
      r=HashReader(f);tf.addfile(info,r);record['sha256']=r.h.hexdigest()
    else:
     tf.addfile(info)
     if info.issym() or info.islnk():record['linkname']=info.linkname
    members[rel]=record
 proc.stdin.close();assert proc.wait()==0
 verifier=subprocess.Popen([ZSTD,'-q','-d','-c',str(target)],stdout=subprocess.PIPE)
 seen=set()
 with tarfile.open(fileobj=verifier.stdout,mode='r|') as tf:
  for info in tf:
   assert info.name in members and info.name not in seen
   seen.add(info.name);rec=members[info.name];assert info.size==rec['size']
   if info.isfile():
    h=hashlib.sha256()
    f=tf.extractfile(info)
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    assert h.hexdigest()==rec['sha256'],info.name
   elif info.issym() or info.islnk():assert info.linkname==rec['linkname']
 # Drain trailing archive padding to avoid pipe truncation.
 while verifier.stdout.read(1024*1024):pass
 verifier.stdout.close();assert verifier.wait()==0 and seen==set(members)
 assert all((ROOT/n).lstat().st_mtime_ns==v['mtime_ns'] for n,v in members.items()),'Source changed during archive'
 record=dict(run=run.name,archive=str(target.relative_to(ROOT)),archive_sha256=digest_file(target),archive_bytes=target.stat().st_size,
             uncompressed_regular_bytes=sum(v['size'] for v in members.values()),full_member_hashes_verified=True,originals_deleted=False,members=members)
 (OUT/(run.name+'.manifest.json')).write_text(json.dumps(record,indent=2)+'\n')
 status['completed'].append({k:v for k,v in record.items() if k!='members'});save()
 print('VERIFIED',run.name,round(record['uncompressed_regular_bytes']/1e9,3),'GB ->',round(record['archive_bytes']/1e6,1),'MB',flush=True)
status['active']=None;status['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
print('ALL ARCHIVES VERIFIED; NO ORIGINALS DELETED',flush=True)
