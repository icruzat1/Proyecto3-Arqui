"""Restore one verified local historical run without overwriting an existing run."""
import argparse, hashlib, json, os, stat, subprocess, tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = ROOT / 'build/local_archive/runs'
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    a = p.parse_args()
    assert a.run == Path(a.run).name and a.run.startswith('stage')
    record = json.loads((ARCHIVES / (a.run + '.manifest.json')).read_text())
    archive = ROOT / record['archive']
    assert digest(archive) == record['archive_sha256']
    target = ROOT / 'config/gf180/runs' / a.run
    assert not target.exists(), 'Run already exists; refusing to overwrite'
    prefix = target.relative_to(ROOT).as_posix() + '/'
    members = record['members']
    for name, info in members.items():
        assert name.startswith(prefix) and '..' not in Path(name).parts
        assert info['type'] in ('0', '5'), 'Only regular files/directories supported'
    target.mkdir()
    seen = set()
    proc = subprocess.Popen(['/opt/anaconda3/bin/zstd','-q','-d','-c',str(archive)], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=proc.stdout, mode='r|') as tf:
        for member in tf:
            assert member.name in members and member.name not in seen
            seen.add(member.name)
            info = members[member.name]; out = ROOT / member.name
            assert member.type.decode() == info['type'] and member.size == info['size']
            if member.isdir(): out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                h = hashlib.sha256()
                with tf.extractfile(member) as src, out.open('xb') as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        h.update(block); dst.write(block)
                assert h.hexdigest() == info['sha256']
            out.chmod(stat.S_IMODE(info['mode']))
    while proc.stdout.read(1024 * 1024): pass
    assert proc.wait() == 0 and seen == set(members)
    for name in sorted(members, key=lambda x: len(Path(x).parts), reverse=True):
        ns = members[name]['mtime_ns']; os.utime(ROOT / name, ns=(ns, ns))
    print('RESTORED AND VERIFIED', a.run)
if __name__ == '__main__': main()
