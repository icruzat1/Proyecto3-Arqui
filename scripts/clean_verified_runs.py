"""Remove only inactive runs whose lossless archives and unchanged sources verify."""
import argparse, json, os, shutil, stat, subprocess, time
from pathlib import Path
from restore_archived_run import ROOT, ARCHIVES, digest
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    index = json.loads((ARCHIVES / 'progress.json').read_text())
    audit = json.loads((ROOT / 'evidence/gf180_delivery/audit.json').read_text())
    assert all(x['status'] == 'PASS' for x in audit['variants'].values())
    assert index['finished_utc'] and index['active'] is None and len(index['completed']) == 58
    out = ROOT / 'evidence/storage_cleanup'; out.mkdir(exist_ok=True)
    log = out / 'cleanup.json'
    assert not log.exists(), 'Cleanup already recorded; inspect before repeating'
    plan = {'verified_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), 'runs': [], 'kept_runs': index['keep']}
    for entry in index['completed']:
        tag = entry['run']; assert tag not in index['keep'] and tag == Path(tag).name
        run = ROOT / 'config/gf180/runs' / tag
        assert run.is_dir() and not run.is_symlink()
        rec = json.loads((ARCHIVES / (tag + '.manifest.json')).read_text())
        assert rec['full_member_hashes_verified'] and digest(ROOT / rec['archive']) == rec['archive_sha256']
        members = rec['members']
        actual = set()
        for base, dirs, files in os.walk(run, followlinks=False):
            for name in dirs + files:
                p = Path(base) / name; rel = p.relative_to(ROOT).as_posix(); actual.add(rel)
                assert rel in members and not p.is_symlink()
                r = members[rel]; s = p.stat()
                assert s.st_mtime_ns == r['mtime_ns'] and stat.S_IMODE(s.st_mode) == stat.S_IMODE(r['mode'])
                if p.is_file(): assert s.st_size == r['size'] and digest(p) == r['sha256']
                else: assert p.is_dir() and r['type'] == '5'
        assert actual == set(members)
        plan['runs'].append({k:v for k,v in rec.items() if k != 'members'})
        print('UNCHANGED AND ARCHIVED', tag, flush=True)
    plan['project_allocated_bytes_before'] = int(subprocess.check_output(['du','-sk',str(ROOT)]).split()[0]) * 1024
    plan['free_bytes_before'] = shutil.disk_usage(ROOT).free
    (out / 'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    if not args.apply:
        print('PLAN VERIFIED; no deletion'); return
    plan['deleted'] = []
    log.write_text(json.dumps(plan,indent=2)+'\n')
    for entry in plan['runs']:
        run = ROOT / 'config/gf180/runs' / entry['run']
        shutil.rmtree(run)
        plan['deleted'].append(entry['run'])
        log.write_text(json.dumps(plan,indent=2)+'\n')
    plan['project_allocated_bytes_after'] = int(subprocess.check_output(['du','-sk',str(ROOT)]).split()[0]) * 1024
    plan['free_bytes_after'] = shutil.disk_usage(ROOT).free
    plan['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    log.write_text(json.dumps(plan,indent=2)+'\n')
    print('CLEANUP COMPLETE', len(plan['deleted']), 'runs; project GB', plan['project_allocated_bytes_after']/1e9)
if __name__ == '__main__': main()
