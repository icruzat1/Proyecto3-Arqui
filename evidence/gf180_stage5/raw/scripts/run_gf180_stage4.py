#!/usr/bin/env python3
"""Reproducible initial GF180 floorplans or separate wait-only mapped netlists."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',choices=['floorplan','wait_only'],default='floorplan')
    parser.add_argument('--variant',choices=['a','b','both'],default='both')
    parser.add_argument('--tag',default='stage4_100ns_u40')
    args=parser.parse_args()
    if not args.tag.replace('_','').isalnum():
        raise SystemExit('Tag must contain only letters, numbers and underscores')
    subprocess.run([sys.executable,'scripts/generate_asic_memory.py','--check'],cwd=root,check=True)
    firmware=root/'build/gf180_game/firmware'
    if args.scope=='wait_only':
        subprocess.run([sys.executable,'scripts/generate_game_firmware.py','--profile','wait_only',
                        '--output-dir',firmware],cwd=root,check=True)
    for variant in (['a','b'] if args.variant=='both' else [args.variant]):
        label=f'{args.tag}_{args.scope}_{variant}'
        source_config=root/f'config/gf180/{variant}.json'
        config=source_config
        if args.scope=='wait_only':
            obj=json.loads(source_config.read_text())
            obj['VERILOG_FILES']=[('/work/build/gf180_game/firmware/asic_program_rom.v' if s.endswith('generated/asic_program_rom.v') else s) for s in obj['VERILOG_FILES']]
            config=source_config.parent/f'{variant}_wait_only.json'
            # Only the derived config changes; production config and ROM stay intact.
            config.write_text(json.dumps(obj,indent=2)+'\n')
        run_dir=config.parent/'runs'/label
        if run_dir.exists():
            raise SystemExit(f'Run already exists: {run_dir}; choose a fresh --tag')
        output=root/'build/gf180_stage4'/label
        output.mkdir(parents=True,exist_ok=True)
        sources=[root/s for s in (root/'config/rtl_asic.f').read_text().splitlines() if s and not s.startswith('#')]
        if args.scope=='wait_only':
            sources=[s for s in sources if s.name!='asic_program_rom.v']+[firmware/'asic_program_rom.v']
            sources+=list(firmware.iterdir())
        sources += [config,source_config,root/'config/gf180/constraints.sdc',root/'config/gf180/pin_order.cfg',
                    root/'config/rtl_asic.f',root/'config/environment.lock.json',Path(__file__).resolve(),
                    root/'scripts/run_librelane.py',root/'firmware/asic/game.s']
        hashes={p.relative_to(root).as_posix():sha(p) for p in sorted(set(sources)) if p.is_file()}
        (output/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        stop='Odb.CustomIOPlacement' if args.scope=='floorplan' else 'Yosys.Synthesis'
        command=[sys.executable,'scripts/run_librelane.py','--manual-pdk','--pdk','gf180mcuD',
                 '--scl','gf180mcu_fd_sc_mcu7t5v0','--run-tag',label,'--to',stop,
                 '--jobs','4','--condensed',config.relative_to(root).as_posix()]
        print(f'Running {label} through {stop}',flush=True)
        with (output/'flow.log').open('w') as log:
            completed=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
        unchanged=all(sha(root/name)==digest for name,digest in hashes.items())
        result={'scope':args.scope,'variant':variant,'stop_step':stop,'command':command,
                'run_dir':run_dir.relative_to(root).as_posix(),'returncode':completed.returncode,
                'input_sha256':hashes,'inputs_unchanged':unchanged,'passed':completed.returncode==0 and unchanged}
        if run_dir.exists():
            (run_dir/'input_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if not result['passed']:
            raise SystemExit(f'FAIL {label}; see {output.relative_to(root)}/flow.log')
        print(f'PASS {label}',flush=True)

if __name__=='__main__':
    main()
