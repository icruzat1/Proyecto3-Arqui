#!/usr/bin/env python3
"""Run an isolated synthesis/pre-PNR trial with storage and provenance guards."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assert re.fullmatch(r'[A-Za-z0-9_]+', args.tag)
    config = (root/args.config).resolve(); config.relative_to(root)
    cfg = json.loads(config.read_text())
    assert cfg['CLOCK_PERIOD'] == 100 and cfg['FP_CORE_UTIL'] == 40
    assert cfg['SYNTH_HIERARCHY_MODE'] == 'deferred_flatten'
    def local(s):
        p = (root/s[6:] if s.startswith('/work/') else config.parent/s[5:] if s.startswith('dir::') else root/s).resolve()
        p.relative_to(root)
        return p
    paths = {local(s) for s in cfg['VERILOG_FILES']}
    paths.update([local(cfg['PNR_SDC_FILE']), local(cfg['SIGNOFF_SDC_FILE']),
                  config, Path(__file__).resolve(), root/'scripts/run_librelane.py',
                  root/'config/environment.lock.json', root/'config/rtl_asic.f'])
    # Production is checked even when this trial replaces one source.
    paths.update(root/s.strip() for s in (root/'config/rtl_asic.f').read_text().splitlines() if s.strip() and not s.startswith('#'))
    before = {p.relative_to(root).as_posix(): sha(p) for p in sorted(paths)}
    kib = int(subprocess.check_output(['du', '-sk', str(root)], text=True).split()[0])
    assert kib*1024 + 1_000_000_000 < 60_000_000_000, 'Storage ceiling: pause before trial'
    output = root/'build/gf180_synthesis_trials'/args.tag
    run = config.parent/'runs'/args.tag
    assert not output.exists() and not run.exists(), 'Choose a fresh tag'
    output.mkdir(parents=True)
    command = [sys.executable, 'scripts/run_librelane.py', '--manual-pdk', '--pdk', 'gf180mcuD',
               '--scl', 'gf180mcu_fd_sc_mcu7t5v0', '--run-tag', args.tag,
               '--to', 'OpenROAD.STAPrePNR', '--jobs', '4', '--condensed', str(config.relative_to(root))]
    record = dict(scope='synthesis and pre-PNR STA only; not routed timing', command=command,
                  storage_before_bytes=kib*1024, storage_limit_bytes=60_000_000_000,
                  reserved_growth_bytes=1_000_000_000, input_sha256=before, passed=False)
    (output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Running', args.tag, flush=True)
    with (output/'flow.log').open('w') as log:
        done = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    unchanged = all(sha(root/n) == h for n,h in before.items())
    after_kib = int(subprocess.check_output(['du', '-sk', str(root)], text=True).split()[0])
    record.update(returncode=done.returncode, inputs_unchanged=unchanged,
                  storage_after_bytes=after_kib*1024, passed=done.returncode == 0 and unchanged)
    (output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    if run.exists():
        (run/'input_sha256.json').write_text(json.dumps(before, indent=2)+'\n')
    assert record['passed'], f'Trial failed; see {output}/flow.log'
    print('PASS', args.tag, 'pre-PNR only', flush=True)


if __name__ == '__main__':
    main()
