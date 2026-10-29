#!/usr/bin/env python3
"""Generic synthesis checks for stage-1 blocks in the pinned local image.

Does not use the simulation memory, download images, or run GF180 physical
implementation. asic_top remains incomplete until real memory A/B is supplied.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    build = root/'build/asic_stage1_synthesis'
    build.mkdir(parents=True, exist_ok=True)
    # A failed rerun must never leave a previous successful result visible.
    (build/'results.json').unlink(missing_ok=True)
    lock = json.loads((root/'config/environment.lock.json').read_text())
    image = lock['container_image']
    docker = shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    if not Path(docker).is_file():
        raise SystemExit('Docker CLI not found')
    env = os.environ.copy()
    for key in ('GH_TOKEN', 'GITHUB_TOKEN'):
        env.pop(key, None)
    prefix = [docker, 'run', '--rm', '--pull=never', '--network=none', '--platform', 'linux/arm64',
              '--user', f'{os.getuid()}:{os.getgid()}', '--cpus', '2', '--memory', '4g',
              '--mount', f'type=bind,src={root},dst=/work', '--workdir', '/work',
              '--entrypoint', 'yosys', image]
    manifest = [p for p in (root/'config/rtl_stage1.f').read_text().splitlines()
                if p and not p.startswith('#') and p != 'rtl/asic/asic_top.v']
    inputs = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in manifest}
    results = {'scope': 'Generic synthesis of individual blocks, no PDK mapping or physical flow',
               'container_image': image, 'input_sha256': inputs, 'blocks': {}}
    for top in ('reset_ctrl', 'btn_sync', 'espino_register_file', 'pochoco_soc'):
        script = build/f'{top}.ys'
        script.write_text('read_verilog -sv ' + ' '.join(manifest) + '\n' +
                          f'hierarchy -check -top {top}\n' +
                          f'synth -top {top} -noabc\ncheck -assert\n' +
                          f'write_json build/asic_stage1_synthesis/{top}.json\n')
        result = subprocess.run([*prefix, '-Q', '-T', '-s', str(script.relative_to(root))],
                                cwd=root, env=env, capture_output=True, text=True)
        log = result.stdout + result.stderr
        (build/f'{top}.log').write_text(log)
        if result.returncode:
            raise SystemExit(f'Synthesis not completed for {top}; see {build / (top + ".log")}')
        modules = json.loads((build/f'{top}.json').read_text())['modules']
        cell_types = {}
        for name, module in modules.items():
            for cell in module.get('cells', {}).values():
                cell_type = cell['type']
                if 'latch' in cell_type.lower():
                    raise SystemExit(f'Unexpected latch: {top}/{name}/{cell_type}')
                if cell_type.startswith('SB_'):
                    raise SystemExit(f'FPGA primitive remained: {cell_type}')
                cell_types[cell_type] = cell_types.get(cell_type, 0) + 1
        if top == 'espino_register_file':
            flops = sum(count for cell_type, count in cell_types.items() if 'DFF' in cell_type)
            if flops != 544:
                raise SystemExit(f'Unexpected RF flip-flop count: {flops}, expected 544 logical bits')
        results['blocks'][top] = {'passed': True, 'cell_types_by_module_definition': cell_types,
                                  'log': f'build/asic_stage1_synthesis/{top}.log'}
        print(f'PASS synthesis block {top}')
    results['all_passed'] = True
    (build/'results.json').write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
