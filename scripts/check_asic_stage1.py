#!/usr/bin/env python3
"""Check ASIC interface/reset/RF against independent expectations and FPGA RF.

Uses simulation-only memory. This is NOT synthesis, post-netlist equivalence,
validation of memory A/B, or a test of the complete game.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ice40-model', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = root / 'baseline/proyecto2'
    build = root / 'build/asic_stage1'
    build.mkdir(parents=True, exist_ok=True)
    # A failed rerun must never leave a previous successful result visible.
    (build/'results.json').unlink(missing_ok=True)
    model = args.ice40_model.expanduser().resolve(strict=True)
    for tool in ['iverilog', 'vvp']:
        if not shutil.which(tool):
            raise SystemExit(f'Missing {tool}')
    cases = []

    def run(command, name, expected_failure=False):
        result = subprocess.run([str(c) for c in command], cwd=root, capture_output=True, text=True)
        log = result.stdout + result.stderr
        (build / f'{name}.log').write_text(log)
        if bool(result.returncode) != expected_failure:
            print(log, file=sys.stderr)
            raise SystemExit(f'Unexpected result: {name} (exit {result.returncode})')
        return log

    sources = [root / line for line in (root/'config/rtl_stage1.f').read_text().splitlines()
               if line and not line.startswith('#')]
    # This historical isolation suite intentionally substitutes the memory fixture.
    # The full stage-2 manifest is verified by check_asic_memories.py.
    if not all(p.is_file() for p in sources):
        raise SystemExit('Stage-1 source manifest references a missing file')
    for source in sources:
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', source.read_text(), flags=re.S)
        if re.search(r'\bSB_\w+|\binitial\b|\$readmem[hb]', text):
            raise SystemExit(f'FPGA/startup dependency in production source: {source}')
    # Core pipeline, peripheral and SPI must be byte-identical to the baseline.
    unchanged = [p for p in sources if p.parent.name == 'espino_core'
                 and p.name != 'espino_register_file.v']
    unchanged += [root/'rtl/pochoco_periph.v', root/'rtl/pochoco_spi_slave.v']
    for path in unchanged:
        if path.read_bytes() != (base/'pochoco_soc-main'/path.relative_to(root)).read_bytes():
            raise SystemExit(f'Unexpected core/peripheral change: {path}')

    mem_model = root/'sim/asic_stage1/asic_memory.v'
    # Guardrails: neither a missing memory nor an unapproved sim source can
    # silently produce a purported ASIC implementation.
    missing = run(['iverilog', '-g2012', '-s', 'asic_top', '-o', build/'missing.vvp', *sources],
                  'memory_required', expected_failure=True)
    if 'Unknown module type: asic_memory' not in missing:
        raise SystemExit('Unexpected failure instead of the pending-memory diagnostic')
    guard = run(['iverilog', '-g2012', '-s', 'asic_top', '-o', build/'guard.vvp', *sources, mem_model],
                'simulation_guard', expected_failure=True)
    if 'ASIC_STAGE1_MEMORY_IS_FOR_SIMULATION_ONLY' not in guard:
        raise SystemExit('Simulation memory protection did not activate')

    def padded_image(assembly, output_name):
        hex_path = build/f'{output_name}.hex'
        run([sys.executable, base/'assembler/assemble.py', assembly, hex_path], f'assemble_{output_name}')
        words = hex_path.read_text().split()
        if len(words) > 512:
            raise SystemExit('Test program exceeds fixture memory')
        padded = build/f'{output_name}.padded.hex'
        padded.write_text('\n'.join(words + ['00000013'] * (512 - len(words))) + '\n')
        return hex_path, padded

    game_hex, game = padded_image(base/'assembler/game.s', 'game')
    if game_hex.read_bytes() != (base/'assembler/game.hex').read_bytes():
        raise SystemExit('Original firmware did not reproduce')
    _, diagnostic = padded_image(root/'sim/asic_stage1/io_diagnostic.s', 'io_diagnostic')
    legacy_rf = (base/'pochoco_soc-main/rtl/espino_core/espino_register_file.v').read_text()
    legacy_file = build/'espino_register_file_legacy.v'
    legacy_file.write_text(re.sub(r'\bespino_(register_file|regbank32)\b',
                                 lambda m: m.group(0)+'_legacy', legacy_rf))

    def compile_tb(name, tb_sources, defines=()):
        executable = build/f'{name}.vvp'
        run(['iverilog', '-g2012', '-Wall', '-Wno-timescale', *[f'-D{x}' for x in defines],
             '-s', name, '-o', executable, root/f'sim/asic_stage1/{name}.v', *tb_sources],
            f'compile_{name}')
        return executable

    def simulate(executable, name, plusargs=()):
        log = run(['vvp', executable, *plusargs], name)
        if 'PASS ' not in log:
            raise SystemExit(f'No positive completion: {name}')
        print(log.strip())
        cases.append({'name': name, 'passed': True, 'summary': log.strip(),
                      'log': f'build/asic_stage1/{name}.log'})

    rf = compile_tb('tb_register_file', [root/'rtl/espino_core/espino_register_file.v', legacy_file, model],
                    ['COMPARE_ICE40'])
    simulate(rf, 'register_file')
    front = compile_tb('tb_reset_buttons', [root/'rtl/asic/reset_ctrl.v', root/'rtl/asic/btn_sync.v'])
    simulate(front, 'reset_buttons')
    top = compile_tb('tb_top_reset', [*sources, mem_model], ['ASIC_STAGE1_SIM'])
    for delay in [0, 5, 144]:
        simulate(top, f'top_reset_boot_{delay}', [f'+MEM_HEX={game}', f'+BOOT_CYCLES={delay}'])
    io = compile_tb('tb_top_io', [*sources, mem_model], ['ASIC_STAGE1_SIM'])
    simulate(io, 'top_io', [f'+MEM_HEX={diagnostic}', '+BOOT_CYCLES=5'])

    # Same ASIC wrapper and memory fixture; only the RF is replaced by the
    # original FPGA implementation. All other core files are unchanged.
    reference_text = '\n'.join(legacy_rf if p.name == 'espino_register_file.v' else p.read_text()
                               for p in [*sources, mem_model])
    module_names = re.findall(r'^\s*module\s+(\w+)', reference_text, flags=re.M)
    name_pattern = r'\b(' + '|'.join(map(re.escape, module_names)) + r')\b'
    reference = build/'reference_with_ice40_rf.v'
    reference.write_text(re.sub(name_pattern, lambda m: 'ref_'+m.group(0), reference_text))
    lockstep = compile_tb('tb_pipeline_lockstep', [*sources, mem_model, reference, model], ['ASIC_STAGE1_SIM'])
    simulate(lockstep, 'pipeline_lockstep', [f'+MEM_HEX={game}', '+BOOT_CYCLES=5'])

    tracked_inputs = sources + list((root/'sim/asic_stage1').glob('*')) + [
        Path(__file__).resolve(), root/'config/rtl_stage1.f', base/'assembler/assemble.py', base/'assembler/game.s',
        base/'pochoco_soc-main/rtl/espino_core/espino_register_file.v']
    results = {
        'scope': 'RTL stage 1 only: interface/reset/RF with simulation memory',
        'physical_flow_run': False, 'uses_production_asic_memory': False,
        'full_game_verified': False, 'post_synthesis_equivalence': False,
        'all_passed': True, 'test_runs': cases,
        'core_peripheral_files_identical_to_baseline': [str(p.relative_to(root)) for p in unchanged],
        'production_sources_have_no_fpga_primitives_or_file_initialization': True,
        'missing_asic_memory_rejected': True, 'simulation_memory_requires_explicit_define': True,
        'original_game_words': len(game_hex.read_text().split()), 'game_hex_sha256': sha(game_hex),
        'ice40_model_sha256': sha(model),
        'iverilog_version': run(['iverilog', '-V'], 'iverilog_version').splitlines()[0],
        'input_sha256': {str(p.relative_to(root)): sha(p) for p in sorted(tracked_inputs)},
    }
    (build/'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'PASS stage1: {len(cases)} test runs; results in build/asic_stage1/results.json')


if __name__ == '__main__':
    main()
