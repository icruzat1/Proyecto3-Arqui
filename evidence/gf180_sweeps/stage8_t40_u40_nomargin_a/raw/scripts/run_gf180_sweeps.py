#!/usr/bin/env python3
"""Bounded sweep: one flow per point, immutable inputs, no automatic ECO retries."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, data):
    p.write_text(json.dumps(data, indent=2)+'\n')

def local(s, cfg):
    p = ROOT/s[6:] if s.startswith('/work/') else cfg.parent/s[5:]
    p = p.resolve(); p.relative_to(ROOT)
    return p

def synthesis(v, t, config):
    if t == 100:
        source = ROOT/f'config/gf180/runs/stage7_trace_ref_{v}'
        prior = json.loads((source/'input_sha256.json').read_text())
        assert all(sha(ROOT/n) == h for n,h in prior.items())
        return source
    tag = f'stage8_synth_t{t}_{v}'
    source = ROOT/'config/gf180/runs'/tag
    output = ROOT/'build/gf180_sweeps'/tag
    assert not source.exists() and not output.exists(), 'Use a new sweep ID'
    output.mkdir(parents=True)
    cfg = json.loads(config.read_text())
    files = [local(n,config) for n in cfg['VERILOG_FILES']]
    files += [config, local(cfg['PNR_SDC_FILE'],config), local(cfg['IO_PIN_ORDER_CFG'],config),
              Path(__file__).resolve(), ROOT/'scripts/run_librelane.py', ROOT/'config/environment.lock.json']
    hashes = {p.relative_to(ROOT).as_posix():sha(p) for p in files}
    command = [sys.executable,'scripts/run_librelane.py','--manual-pdk','--pdk','gf180mcuD',
               '--scl','gf180mcu_fd_sc_mcu7t5v0','--run-tag',tag,'--to','OpenROAD.STAPrePNR',
               '--jobs','4','--condensed',str(config.relative_to(ROOT))]
    start=time.time()
    with (output/'flow.log').open('w') as f:
        r=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    unchanged=all(sha(ROOT/n)==h for n,h in hashes.items())
    write(output/'result.json',dict(command=command,returncode=r.returncode,inputs_unchanged=unchanged,
                                   input_sha256=hashes,elapsed_seconds=time.time()-start))
    if source.exists(): write(source/'input_sha256.json',hashes)
    assert r.returncode==0 and unchanged, f'Synthesis failed: {tag}'
    return source

def main():
    output=ROOT/'build/gf180_sweeps';output.mkdir(exist_ok=True)
    status=output/'progress.json'
    assert not status.exists(), 'This is a one-shot batch; never replay completed points'
    # A utilization study; both memory variants receive the period study.
    points=[('a',60,40),('a',40,40),('a',100,50),('a',100,30),
            ('b',100,40),('b',60,40),('b',40,40)]
    record={'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'points':points,'completed':[], 'retry_policy':'none','old_60GB_limit_revoked':True}
    write(status,record)
    for v,t,u in points:
        # Preserve usable host capacity, independent of the revoked project ceiling.
        free=shutil.disk_usage(ROOT).free
        assert free>20_000_000_000, 'Insufficient host free space: pause for user'
        used=int(subprocess.check_output(['du','-sk',str(ROOT)],text=True).split()[0])*1024
        tag=f'stage8_t{t}_u{u}_{v}'
        record['active']=dict(tag=tag,project_bytes=used,host_free_bytes=free)
        write(status,record);print('START',tag,f'{used/1e9:.2f} GB',flush=True)
        config=ROOT/f'config/gf180/{v}_sweep_t{t}_u{u}.json'
        source=synthesis(v,t,config)
        sta=next(source.glob('*-openroad-staprepnr'))
        command=[sys.executable,'scripts/resume_gf180.py','--source-run',str(source.relative_to(ROOT)),
                 '--source-step',sta.name,'--config',str(config.relative_to(ROOT)),
                 '--tag',tag,'--from','OpenROAD.Floorplan','--to','Misc.ReportManufacturability']
        start=time.time()
        with (output/(tag+'.log')).open('w') as f:
            r=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        result_path=ROOT/'build/gf180_stage5'/tag/'result.json'
        assert result_path.exists(), 'Runner infrastructure failure; stop batch'
        result=json.loads(result_path.read_text())
        assert result['inputs_unchanged'], 'Inputs changed during sweep'
        run=ROOT/'config/gf180/runs'/tag
        assert (run/'resolved.json').exists(), 'Flow did not initialize; stop batch'
        archive=ROOT/'evidence/gf180_sweeps'/tag
        archive_command=[sys.executable,'scripts/summarize_gf180_sweep.py',
                         '--tag',tag[:-2],'--variant',v,'--period',str(t),'--output',str(archive)]
        with (output/(tag+'_archive.log')).open('w') as f:
            a=subprocess.run(archive_command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        assert a.returncode==0, 'Evidence archive failed; stop batch'
        record['completed'].append(dict(tag=tag,returncode=result['returncode'],
                                        elapsed_seconds=time.time()-start,evidence=str(archive.relative_to(ROOT))))
        write(status,record);print('DONE',tag,'returncode',result['returncode'],flush=True)
    record['active']=None;record['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    write(status,record);print('COMPLETE bounded sweep',flush=True)

if __name__=='__main__':main()
