#!/usr/bin/env python3
"""Compare logical outputs of RTL and GF180 mapped wait-only game netlists.

The second correct result follows EE, so its change to 00 is observable at the
terminals. Internal MMIO nets are optimized away by mapping and are not claimed
as compared. No SDF or power-aware simulation is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',default='stage4_100ns_u40')
    args=parser.parse_args()
    build=root/'build/gf180_mapped_game'
    build.mkdir(parents=True,exist_ok=True)
    (build/'results.json').unlink(missing_ok=True)
    firmware=root/'build/gf180_game/firmware'
    verify=runpy.run_path(str(root/'scripts/check_game_timing.py'))['verify_profile']
    verify(firmware,'wait_only',3000,1000000)
    tb=root/'sim/asic_stage3/tb_game_wait_only.v'
    # Keep the existing semantic scoreboard, stimulus and terminal comparison.
    # Remove only the generic-netlist internal diagnostics that mapping purges.
    code=tb.read_text()
    pattern=r'`ifdef WITH_NETLIST\n    // Flattened net names.*?`endif\n'
    code,count=re.subn(pattern,'',code,flags=re.S)
    assert count==1, 'Expected exactly one generic-only diagnostic block'
    copy=build/'tb_game_wait_only_mapped.v'
    copy.write_text(code)
    models=root/'.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog'
    libs=[models/'primitives.v',models/'gf180mcu_fd_sc_mcu7t5v0.v']
    sources=[root/n for n in (root/'config/rtl_asic.f').read_text().splitlines() if n and not n.startswith('#')]
    sources=[p for p in sources if p.name!='asic_program_rom.v']+[firmware/'asic_program_rom.v']
    hashes={p.relative_to(root).as_posix():sha(p) for p in sources+libs+[tb,Path(__file__).resolve()]}
    results={'all_passed':False,'pdk_mapped_netlist':True,'sdf_timing':False,'power_aware':False,
             'scope':'Wait-only game terminal equivalence; two correct rounds and one incorrect single-button retry',
             'internal_mmio_nets_compared':False,'second_correct_result_visible_after_error':True,
             'clock_period_ns':100,'wait_ticks':3000,'tenth_ticks':1000000,
             'input_sha256':hashes,'testbench_copy_sha256':sha(copy),'runs':{}}
    def run(cmd,label):
        r=subprocess.run(list(map(str,cmd)),cwd=root,capture_output=True,text=True,timeout=900)
        (build/(label+'.log')).write_text(r.stdout+r.stderr)
        if r.returncode: raise SystemExit(f'Failed {label}: {r.stdout}{r.stderr}')
        return r.stdout+r.stderr
    for i,v in enumerate('ab'):
        directory=root/f'config/gf180/runs/{args.tag}_wait_only_{v}'
        snapshot=json.loads((directory/'input_sha256.json').read_text())
        assert all(sha(root/n)==h for n,h in snapshot.items()), 'Stale synthesis input'
        step=next(directory.glob('*-yosys-synthesis'))
        cfg=json.loads((step/'config.json').read_text())
        assert cfg['PDK']=='gf180mcuD' and cfg['STD_CELL_LIBRARY']=='gf180mcu_fd_sc_mcu7t5v0'
        assert cfg['CLOCK_PERIOD']==100 and cfg['SYNTH_PARAMETERS']==[f'MemoryVariant={i}']
        assert '/work/build/gf180_game/firmware/asic_program_rom.v' in cfg['VERILOG_FILES']
        nl=step/'asic_top.nl.v'
        data=json.loads((step/'asic_top.nl.v.json').read_text())['modules']['asic_top']
        assert all(c['type'].startswith('gf180mcu_fd_sc_mcu7t5v0__') for c in data['cells'].values())
        renamed,n=re.subn(r'(?m)^module asic_top\(', 'module netlist_top(',nl.read_text())
        assert n==1
        netcopy=build/f'mapped_{v}.v';netcopy.write_text(renamed)
        executable=build/f'mapped_{v}.vvp';trace=build/f'mapped_{v}.trace.csv'
        run(['iverilog','-g2012','-DFUNCTIONAL','-DWITH_NETLIST','-s','tb_game_wait_only',
             f'-Ptb_game_wait_only.MemoryVariant={i}','-o',executable,copy,netcopy,*libs,*sources],f'compile_{v}')
        log=run(['vvp',executable,f'+TRACE={trace}'],f'mapped_{v}')
        summary=[s for s in log.splitlines() if s.startswith('PASS game_wait_only ')]
        assert len(summary)==1
        coverage={k:int(x) for k,x in re.findall(r'(\w+)=(\d+)',summary[0])}
        expected={'correct':2,'wrong':1,'attempts':3,'held_checks':600,'first_round_cycles':302,'second_round_cycles':302,'wrong_round_cycles':269}
        assert all(coverage[k]==x for k,x in expected.items())
        results['runs'][v]={'passed':True,'coverage':coverage,'netlist':str(nl.relative_to(root)),
                            'netlist_sha256':sha(nl),'trace_sha256':sha(trace),'synthesis_input_sha256':snapshot}
        print(summary[0],flush=True)
    assert all(sha(root/n)==h for n,h in hashes.items()), 'Inputs changed during test'
    results['all_passed']=True
    (build/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS GF180 mapped A/B functional terminals, without SDF')

if __name__=='__main__':main()
