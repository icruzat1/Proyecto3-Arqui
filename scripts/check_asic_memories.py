#!/usr/bin/env python3
"""Verify real ASIC memory A/B, generated program and CPU integration in RTL."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    build=root/'build/asic_stage2'
    build.mkdir(parents=True,exist_ok=True)
    (build/'results.json').unlink(missing_ok=True)
    for tool in ('iverilog','vvp'):
        if not shutil.which(tool): raise SystemExit(f'Missing {tool}')
    cases=[]

    def run(command,name,expect_failure=False):
        r=subprocess.run(list(map(str,command)),cwd=root,text=True,capture_output=True)
        log=r.stdout+r.stderr
        (build/f'{name}.log').write_text(log)
        if bool(r.returncode)!=expect_failure:
            print(log,file=sys.stderr)
            raise SystemExit(f'Unexpected exit {r.returncode}: {name}')
        return log

    run([sys.executable,'scripts/generate_asic_memory.py','--check'],'generated_check')
    log=run([sys.executable,'-m','unittest','discover','-s','sim/asic_stage2','-p','test_generate_asic_memory.py','-v'],'generator_tests')
    if '\nOK\n' not in log: raise SystemExit('Generator tests did not complete')
    print(log.strip())
    sources=[root/p for p in (root/'config/rtl_asic.f').read_text().splitlines() if p and not p.startswith('#')]
    if set(sources)!=set((root/'rtl').rglob('*.v')):
        raise SystemExit('Full ASIC source manifest does not match production RTL')
    for source in sources:
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',source.read_text(),flags=re.S)
        if re.search(r'\bSB_\w+|\binitial\b|\$readmem[hb]',text):
            raise SystemExit(f'FPGA/file-startup dependency in {source}')
    rom=root/'rtl/asic/generated/asic_program_rom.v'
    memories=[root/'rtl/asic/memory_a.v',root/'rtl/asic/memory_b.v',rom]
    # Assemble the source independently of the ROM generator's outputs.
    assemble=runpy.run_path(str(root/'baseline/proyecto2/assembler/assemble.py'))['assemble']
    words=assemble((root/'firmware/asic/game.s').read_text())
    golden=build/'golden_program.padded.hex'
    golden.write_text('\n'.join(words+['00000013']*(128-len(words)))+'\n')

    def simulate(top,srcs,name,params=(),plusargs=()):
        executable=build/f'{name}.vvp'
        run(['iverilog','-g2012','-Wall','-Wno-timescale','-s',top,*[f'-P{p}' for p in params],
             '-o',executable,root/f'sim/asic_stage2/{top}.v',*srcs],f'compile_{name}')
        log=run(['vvp',executable,*plusargs],name)
        if 'PASS ' not in log: raise SystemExit(f'No positive completion for {name}')
        print(log.strip())
        cases.append({'name':name,'passed':True,'summary':log.strip(),'log':f'build/asic_stage2/{name}.log'})

    simulate('tb_memories',memories,'memory_interfaces',plusargs=[f'+MEM_HEX={golden}'])
    simulate('tb_top_memories',sources,'top_ab_game_startup')
    custom=build/'diagnostic_rom'
    run([sys.executable,'scripts/generate_asic_memory.py','--source','sim/asic_stage2/io_diagnostic.s',
         '--output-dir',custom],'generate_io_diagnostic')
    diag_sources=[p for p in sources if p!=rom]+[custom/'asic_program_rom.v']
    for variant in (0,1):
        simulate('tb_top_io_real',diag_sources,f'top_io_{variant}',params=[f'tb_top_io_real.MemoryVariant={variant}'])
    invalid=run(['iverilog','-g2012','-s','asic_top','-Pasic_top.MemoryVariant=2',
                 '-o',build/'invalid.vvp',*sources],'invalid_variant',True)
    if 'ASIC_MEMORY_VARIANT_MUST_BE_0_OR_1' not in invalid:
        raise SystemExit('Invalid variant failed for an unexpected reason')
    tracked=sources+list((root/'sim/asic_stage2').glob('*.v'))+list((root/'sim/asic_stage2').glob('*.s'))+[
        root/'sim/asic_stage2/test_generate_asic_memory.py',Path(__file__).resolve(),
        root/'scripts/generate_asic_memory.py',root/'config/rtl_asic.f',
        root/'firmware/asic/game.s',root/'baseline/proyecto2/assembler/assemble.py']
    result={'scope':'Real ASIC memory A/B and RTL integration; production 10 MHz game startup only',
            'all_passed':True,'test_runs':cases,'generator_tests_log':'build/asic_stage2/generator_tests.log',
            'production_source_manifest_complete':True,'invalid_variant_rejected':True,
            'program_words':len(words),'program_hex_sha256':sha(root/'rtl/asic/generated/game.hex'),
            'capacities_words':{'rom_a':128,'ram_a':16,'unified_b':144},
            'full_game_verified':False,'firmware_recalibrated_to_10mhz':True,
            'post_synthesis_game_equivalence':False,'physical_flow_run':False,
            'input_sha256':{str(p.relative_to(root)):sha(p) for p in sorted(set(tracked))}}
    (build/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS memory stage: {len(cases)} simulation runs plus generator tests')


if __name__=='__main__':
    main()
