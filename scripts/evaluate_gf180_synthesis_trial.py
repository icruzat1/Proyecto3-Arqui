#!/usr/bin/env python3
"""Measure named mapped modules and compare trial gates with production RTL."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import subprocess
import check_gf180_physical as common
from measure_gf180_area import liberty_cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--variant', choices=['a', 'b'], required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assert re.fullmatch(r'[A-Za-z0-9_]+', args.tag)
    run = root/'config/gf180/runs'/args.tag
    snapshot = json.loads((run/'input_sha256.json').read_text())
    assert all(common.sha(root/n) == h for n,h in snapshot.items())
    record = json.loads((root/'build/gf180_synthesis_trials'/args.tag/'result.json').read_text())
    assert record['passed'] and record['inputs_unchanged']
    step = next(run.glob('*-yosys-synthesis'))
    nl, jp, stats = step/'asic_top.nl.v', step/'asic_top.nl.v.json', step/'reports/stat.json'
    cfg = json.loads((step/'config.json').read_text())
    assert cfg['SYNTH_PARAMETERS'] == [f'MemoryVariant={"ab".index(args.variant)}']
    lib = root/'.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib'
    library = liberty_cells(lib)
    cells = json.loads(jp.read_text())['modules']['asic_top']['cells']
    direct, inclusive = defaultdict(float), defaultdict(float)
    for name, cell in cells.items():
        assert cell['type'] in library, 'Unmapped cell'
        area = library[cell['type']]['area_um2']
        path = name.rsplit('.', 1)[0] if name.startswith(('u_soc.', 'u_mem.', 'u_reset.', 'u_buttons.')) else '<top_or_synthesis_inserted>'
        direct[path] += area
        if not path.startswith('<'):
            parts = path.split('.')
            for i in range(1, len(parts)+1): inclusive['.'.join(parts[:i])] += area
    total = sum(direct.values())
    assert abs(total-json.loads(stats.read_text())['design']['area']) < .01
    alu = [name for name in cells if '.u_id.u_alu.' in name]
    assert len(alu) > 0, 'ALU provenance missing'
    sources = [root/n.strip() for n in (root/'config/rtl_asic.f').read_text().splitlines() if n.strip() and not n.startswith('#')]
    models = root/'.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog'
    libraries = [models/'primitives.v', models/'gf180mcu_fd_sc_mcu7t5v0.v']
    paths = [nl,jp,stats,lib,step/'config.json',run/'input_sha256.json',Path(__file__),root/'scripts/check_gf180_physical.py',root/'scripts/measure_gf180_area.py',*sources,*libraries]
    hashes = {p.relative_to(root).as_posix():common.sha(p) for p in paths}
    out = root/'evidence/gf180_synthesis_trials'/args.tag
    build = root/'build/gf180_synthesis_evaluation'/args.tag
    assert not out.exists() and not build.exists()
    out.mkdir(parents=True);build.mkdir(parents=True)
    raw = nl.read_text()
    checks, coverage = common.diagnostic_checks(raw)
    renamed,n = re.subn(r'(?m)^module\s+asic_top\s*\(', 'module physical_top (', raw)
    assert n == 1
    gate = build/'physical.v';gate.write_text(renamed)
    tb = out/'tb_physical.v';tb.write_text(common.testbench('ab'.index(args.variant), checks))
    result = dict(tag=args.tag, variant=args.variant, scope='Mapped synthesis, pre-PNR; not final PPA or signoff',
                  cell_count=len(cells), sequential_cells=sum(library[c['type']]['sequential'] for c in cells.values()),
                  cell_area_um2=total, direct_area_partition_um2=dict(sorted(direct.items())),
                  inclusive_module_area_um2=dict(sorted(inclusive.items())),
                  area_semantics='Direct areas partition total. Inclusive areas contain child modules and must not be summed together.',
                  alu_instances=sorted(alu), input_sha256=hashes, synthesis_input_sha256=snapshot,
                  reference='Unmodified production RTL, including when gate netlist uses candidate RTL',
                  diagnostic_bits=coverage, functional_passed=False, sdf=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    exe = build/'physical.vvp'
    commands = [['iverilog','-g2012','-DFUNCTIONAL','-s','tb_physical','-o',str(exe),str(tb),str(gate),*[str(p) for p in libraries+sources]], ['vvp',str(exe)]]
    for command,label in zip(commands,['compile','run']):
        r = subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=600)
        (out/(label+'.log')).write_text(r.stdout+r.stderr)
        assert r.returncode == 0, f'{label} failed: {out}'
        if label == 'run':
            match = re.findall(r'^PASS physical_startup.*$',r.stdout,re.M)
            assert len(match) == 1
            result['functional_summary'] = match[0]
    assert all(common.sha(root/n) == h for n,h in hashes.items())
    result.update(functional_passed=True, inputs_unchanged=True, commands=commands)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(args.tag, 'area',round(total,4), 'ALU',len(alu),result['functional_summary'],flush=True)


if __name__ == '__main__':
    main()
