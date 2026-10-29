#!/usr/bin/env python3
"""Run the memory interface tests on the verified generic synthesis netlists.

This is a functional post-synthesis memory test, not formal equivalence,
post-synthesis game validation, PDK-mapped simulation or timing/SDF analysis.
First run scripts/check_asic_memory_synthesis.py to produce the netlists.
"""
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


def project_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise SystemExit(f'Expected a project-relative evidence path: {relative}')
    return root / path


def renamed_netlist(source, prefix, expected_top):
    names = re.findall(r'^\s*module\s+([A-Za-z_]\w*)\s*\(', source, flags=re.M)
    if expected_top not in names or len(names) != len(set(names)):
        raise SystemExit(f'Unexpected module definitions in netlist for {expected_top}')
    # Isolate each exported hierarchy so both versions of asic_program_rom
    # can coexist. Only build copies are transformed; source netlists stay intact.
    pattern = r'\b(' + '|'.join(map(re.escape, names)) + r')\b'
    return re.sub(pattern, lambda match: prefix + match.group(0), source), names


def main():
    root = Path(__file__).resolve().parents[1]
    build = root / 'build/asic_memory_netlist'
    build.mkdir(parents=True, exist_ok=True)
    (build / 'results.json').unlink(missing_ok=True)
    for tool in ('iverilog', 'vvp'):
        if not shutil.which(tool):
            raise SystemExit(f'Missing {tool}')

    def run(command, name):
        result = subprocess.run(list(map(str, command)), cwd=root, text=True,
                                capture_output=True, timeout=180)
        log = result.stdout + result.stderr
        (build / f'{name}.log').write_text(log)
        if result.returncode:
            print(log, file=sys.stderr)
            raise SystemExit(f'Failed {name}: exit {result.returncode}')
        return log

    synthesis_path = root / 'build/asic_memory_synthesis/results.json'
    if not synthesis_path.is_file():
        raise SystemExit('Run scripts/check_asic_memory_synthesis.py first')
    synthesis = json.loads(synthesis_path.read_text())
    if synthesis.get('all_passed') is not True or not synthesis.get('input_sha256'):
        raise SystemExit('Synthesis evidence is missing or did not pass')
    for relative, expected in synthesis['input_sha256'].items():
        source = project_path(root, relative)
        if not source.is_file() or sha(source) != expected:
            raise SystemExit(f'Stale synthesis input: {relative}; rerun synthesis')

    netlists = {}
    netlist_sources = []
    for name, prefix in (('memory_a', 'syn_a_'), ('memory_b', 'syn_b_')):
        info = synthesis.get('runs', {}).get(name)
        if not info or info.get('passed') is not True:
            raise SystemExit(f'Missing passing synthesis run: {name}')
        verified_paths = {}
        for kind in ('netlist_verilog', 'netlist_json'):
            original = project_path(root, info[kind])
            if not original.is_file() or sha(original) != info[kind + '_sha256']:
                raise SystemExit(f'Stale or modified {kind}: {info[kind]}')
            verified_paths[kind] = original
        original = verified_paths['netlist_verilog']
        renamed, names = renamed_netlist(original.read_text(), prefix, name)
        destination = build / f'{name}.namespaced.v'
        destination.write_text(renamed)
        netlist_sources.append(destination)
        netlists[name] = {
            'source': info['netlist_verilog'],
            'source_sha256': sha(original),
            'json': info['netlist_json'],
            'json_sha256': sha(verified_paths['netlist_json']),
            'yosys_version': info['yosys_version'],
            'renamed_module_definitions': {module: prefix + module for module in names},
            'simulation_copy_sha256': sha(destination),
        }

    testbench = root / 'sim/asic_stage2/tb_memories.v'
    test_source = testbench.read_text()
    for name, instance, prefix in (('memory_a', 'dut_a', 'syn_a_'),
                                   ('memory_b', 'dut_b', 'syn_b_')):
        pattern = r'(?m)^(\s*)' + name + r'(?=\s+' + instance + r'\s*\()'
        test_source, count = re.subn(pattern, lambda m: m.group(1) + prefix + name, test_source)
        if count != 1:
            raise SystemExit(f'Expected one {name} instance named {instance} in the shared testbench')
    test_copy = build / 'tb_memories_netlist.v'
    test_copy.write_text(test_source)

    # The expected program is independent of the synthesized ROM structure.
    # Assemble the current production source independently of ROM outputs.
    firmware_source = root / 'firmware/asic/game.s'
    assemble = runpy.run_path(str(root / 'baseline/proyecto2/assembler/assemble.py'))['assemble']
    words = assemble(firmware_source.read_text())
    if not words or len(words) > 128 or any(not re.fullmatch(r'[0-9a-fA-F]{8}', w) for w in words):
        raise SystemExit('Invalid production program image for the 128-word ROM window')
    generated_hex = root / 'rtl/asic/generated/game.hex'
    if words != generated_hex.read_text().split():
        raise SystemExit('Generated firmware differs from the independently assembled source')
    golden = build / 'golden_program.padded.hex'
    golden.write_text('\n'.join(words + ['00000013'] * (128 - len(words))) + '\n')
    executable = build / 'memories.vvp'
    run(['iverilog', '-g2012', '-Wall', '-Wno-timescale', '-s', 'tb_memories',
         '-o', executable, test_copy, *netlist_sources], 'compile')
    log = run(['vvp', executable, f'+MEM_HEX={golden}'], 'memory_interfaces')
    summaries = [line for line in log.splitlines() if line.startswith('PASS memories ')]
    if len(summaries) != 1:
        raise SystemExit('The post-synthesis memory test did not produce its unique PASS result')
    coverage = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', summaries[0])}
    tracked = [testbench, firmware_source, root / 'baseline/proyecto2/assembler/assemble.py', generated_hex, Path(__file__).resolve()]
    result = {
        'scope': 'Functional interface tests of generic memory A/B netlists, without delays',
        'all_passed': True,
        'post_synthesis_memory_interface_test_passed': True,
        'formal_equivalence': False,
        'post_synthesis_game_equivalence': False,
        'full_game_verified': False,
        'pdk_mapped_netlist': False,
        'sdf_timing': False,
        'synthesis_results': 'build/asic_memory_synthesis/results.json',
        'synthesis_results_sha256': sha(synthesis_path),
        'synthesis_input_hashes_verified': len(synthesis['input_sha256']),
        'netlists': netlists,
        'testbench': 'sim/asic_stage2/tb_memories.v',
        'testbench_simulation_copy_sha256': sha(test_copy),
        'golden_words': len(words),
        'golden_padded_sha256': sha(golden),
        'summary': summaries[0],
        'coverage': coverage,
        'compile_log': 'build/asic_memory_netlist/compile.log',
        'simulation_log': 'build/asic_memory_netlist/memory_interfaces.log',
        'input_sha256': {str(path.relative_to(root)): sha(path) for path in tracked},
    }
    (build / 'results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(summaries[0])
    print('PASS post-synthesis memory interface tests; this does not validate the complete game')


if __name__ == '__main__':
    main()
