#!/usr/bin/env python3
"""Compare production RTL and post-CTS GF180 logic in a short startup test.

Two boot epochs, interrupted boot, reset, retained fetch/timer nets, buttons
and four SPI frames. Bounded simulation, not formal equivalence, a complete
30-million-cycle game round, ordinary RAM interface validation, or SDF timing.
Uses the unpowered .nl.v and FUNCTIONAL models, without changing source views.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root, name):
    if name.startswith('/work/'):
        name = name.removeprefix('/work/')
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts,
            f'Expected project-relative or /work path: {name}')
    result = (root/path).resolve(strict=True)
    require(result.is_relative_to(root), f'Path leaves project: {name}')
    return result


def diagnostic_checks(netlist):
    """Require preserved observables; report partial instruction bits explicitly."""
    declarations = set(re.findall(r'^\s*wire\s+(\S+)\s*;', netlist, re.M))
    checks, coverage = [], {}
    signals = [('core_rst_ni', 1), ('rst_sync_ni', 1), ('mem_boot_done', 1),
               ('instr_addr', 32), ('u_soc.u_periph.cycles_q', 32),
               ('u_soc.u_spi.price_q', 8), ('u_soc.u_spi.new_price_q', 1)]
    for name, width in signals + [('instr_rdata', 32)]:
        bits = []
        for bit in range(width):
            ref = name if width == 1 else f'{name}[{bit}]'
            token = ref if ref in declarations else '\\'+ref
            if token not in declarations:
                continue
            bits.append(bit)
            condition = "reference.core_rst_ni === 1'b1" if name == 'instr_rdata' else '1'
            checks.append(f'''    if (({condition}) && reference.{ref} !== gate.{token} )
      $fatal(1, "Diagnostic mismatch {ref} at sample %0d", samples);''')
        if name == 'instr_rdata':
            require(len(bits) >= 16, 'Too few retained instruction-data bits')
        else:
            require(len(bits) == width, f'Required diagnostic net optimized away: {name}')
        coverage[name] = bits
    return '\n'.join(checks), coverage


def testbench(variant, checks):
    return r'''`timescale 1ns/1ps
module tb_physical;
  reg clk=0, rst_n=1, enabled=0;
  reg [3:0] btn=0;
  reg sclk=0, mosi=0, cs_n=1;
  wire [3:0] r_led,g_led;
  wire [6:0] r_s1,r_s2,g_s1,g_s2;
  wire r_miso,g_miso;
  always #50 clk=~clk;
  asic_top #(.MemoryVariant(VARIANT)) reference (
    .clk_i(clk),.rst_ni(rst_n),.btn_i(btn),.leds_o(r_led),.seg1_o(r_s1),.seg2_o(r_s2),
    .spi_sclk_i(sclk),.spi_mosi_i(mosi),.spi_cs_n_i(cs_n),.spi_miso_o(r_miso));
  physical_top gate (
    .clk_i(clk),.rst_ni(rst_n),.btn_i(btn),.leds_o(g_led),.seg1_o(g_s1),.seg2_o(g_s2),
    .spi_sclk_i(sclk),.spi_mosi_i(mosi),.spi_cs_n_i(cs_n),.spi_miso_o(g_miso));
  integer samples=0,active_cycles=0,fetch_changes=0,spi_frames=0,epochs=0;
  integer reset_checks=0,button_changes=0,n,e;
  reg [31:0] last_pc=0;
  task compare_all;
    begin
      samples=samples+1;
      if ((^{r_led,r_s1,r_s2,r_miso,g_led,g_s1,g_s2,g_miso}) === 1'bx)
        $fatal(1,"Unknown external output at sample %0d",samples);
      if ({r_led,r_s1,r_s2,r_miso} !== {g_led,g_s1,g_s2,g_miso})
        $fatal(1,"External output mismatch at sample %0d",samples);
CHECKS
    end
  endtask
  always @(posedge clk) begin
    #1;
    if(enabled) begin
      compare_all;
      if(reference.core_rst_ni === 1'b1) begin
        active_cycles=active_cycles+1;
        if(reference.instr_addr !== last_pc) fetch_changes=fetch_changes+1;
        last_pc=reference.instr_addr;
      end
    end
  end
  task assert_reset;
    begin
      #17; rst_n=0; #1;
      compare_all;
      if(reference.core_rst_ni !== 0 || gate.core_rst_ni !== 0 ||
         reference.u_soc.u_periph.cycles_q !== 0)
        $fatal(1,"Asynchronous reset did not clear reset/counter");
      reset_checks=reset_checks+1;
    end
  endtask
  task spi_byte(input [7:0] value);
    integer bit_index;
    begin
      @(negedge clk); cs_n=0;
      repeat(10) @(negedge clk);
      for(bit_index=7;bit_index>=0;bit_index=bit_index-1) begin
        mosi=value[bit_index];
        repeat(10) @(negedge clk); sclk=1;
        repeat(10) @(negedge clk); sclk=0;
      end
      repeat(10) @(negedge clk); cs_n=1;
      repeat(10) @(negedge clk);
      if(reference.u_soc.u_spi.price_q !== value ||
         reference.u_soc.u_spi.new_price_q !== 1)
        $fatal(1,"SPI reference receive failed");
      spi_frames=spi_frames+1;
    end
  endtask
  initial begin
    #7; rst_n=0; #1; enabled=1;
    repeat(6) @(negedge clk); rst_n=1;
    // Interrupt B's actual loader; A has already booted at this point.
    repeat(70) @(negedge clk);
    if(VARIANT == 1 && reference.mem_boot_done !== 0)
      $fatal(1,"B left its initial loading interval too early");
    assert_reset;
    for(e=0;e<2;e=e+1) begin
      repeat(6) @(negedge clk); rst_n=1;
      repeat(220) @(negedge clk);
      if(reference.core_rst_ni !== 1 || reference.mem_boot_done !== 1)
        $fatal(1,"Boot did not complete");
      spi_byte(8'h3c); spi_byte(8'ha5);
      for(n=0;n<10000;n=n+1) begin
        @(negedge clk);
        if(n%113 == 0) begin btn=(n/113+e)%16; button_changes=button_changes+1; end
      end
      if(r_led !== 4'hf || reference.u_soc.u_periph.cycles_q < 10000)
        $fatal(1,"Production startup or timer did not progress");
      epochs=epochs+1;
      if(e==0) assert_reset;
    end
    @(negedge clk);
    if(active_cycles < 20000 || fetch_changes < 1000 || spi_frames != 4 || reset_checks != 2)
      $fatal(1,"Insufficient startup coverage");
    $display("PASS physical_startup variant=%0d epochs=%0d samples=%0d active_cycles=%0d fetch_changes=%0d spi_frames=%0d reset_checks=%0d button_changes=%0d",
             VARIANT,epochs,samples,active_cycles,fetch_changes,spi_frames,reset_checks,button_changes);
    $finish;
  end
  initial begin #3000000; $fatal(1,"Physical startup timeout"); end
endmodule
'''.replace('VARIANT', str(variant)).replace('CHECKS', checks)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='stage5_100ns_u40_cts')
    parser.add_argument('--variant', choices=['a', 'b', 'both'], default='both')
    parser.add_argument('--state-step', default='12-openroad-stamidpnr-2')
    args = parser.parse_args()
    require(bool(re.fullmatch(r'[A-Za-z0-9_]+', args.tag)), 'Invalid run tag')
    require(shutil.which('iverilog') and shutil.which('vvp'), 'Icarus Verilog required')
    output = root/'build/gf180_physical'/args.tag
    output.mkdir(parents=True, exist_ok=True)
    result_path = output/'results.json'
    result_path.unlink(missing_ok=True)
    sources = [local(root, n.strip()) for n in (root/'config/rtl_asic.f').read_text().splitlines()
               if n.strip() and not n.lstrip().startswith('#')]
    models = root/'.pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog'
    libraries = [models/'primitives.v', models/'gf180mcu_fd_sc_mcu7t5v0.v']
    model_modules = set(re.findall(r'\bmodule\s+(\w+)\s*\(', libraries[1].read_text()))
    variants = ['a', 'b'] if args.variant == 'both' else [args.variant]
    results = {'all_passed': False, 'scope': 'Bounded production startup/reset/SPI and retained-net comparison',
               'formal_equivalence': False, 'full_game_verified': False, 'sdf_timing': False,
               'power_aware': False, 'production_firmware_unchanged': True,
               'ordinary_ram_interfaces_tested': False, 'runs': {}}

    for variant in variants:
        index = 'ab'.index(variant)
        run_dir = root/f'config/gf180/runs/{args.tag}_{variant}'
        snapshot_path = run_dir/'input_sha256.json'
        snapshot = json.loads(snapshot_path.read_text())
        require(bool(snapshot), 'Missing source provenance')
        for name, digest in snapshot.items():
            require(sha(local(root, name)) == digest, f'Stale physical input: {name}')
        record_path = root/f'build/gf180_stage5/{args.tag}_{variant}/result.json'
        record = json.loads(record_path.read_text())
        require(record.get('passed') is True and record.get('input_sha256') == snapshot,
                'Physical flow did not finish with unchanged inputs')
        resolved_path = run_dir/'resolved.json'
        cfg = json.loads(resolved_path.read_text())
        require(cfg['PDK'] == 'gf180mcuD' and cfg['STD_CELL_LIBRARY'] == 'gf180mcu_fd_sc_mcu7t5v0',
                'Wrong technology')
        require(cfg['SYNTH_PARAMETERS'] == [f'MemoryVariant={index}'] and cfg['CLOCK_PERIOD'] == 100,
                'Wrong memory variant or clock')
        require(set(local(root, n) for n in cfg['VERILOG_FILES']) == set(sources),
                'Physical run did not use the production RTL manifest')
        state_path = run_dir/args.state_step/'state_out.json'
        state = json.loads(state_path.read_text())
        netlist = local(root, state['nl'])
        require(netlist.parent.parent == run_dir and netlist.parent.name.endswith('-openroad-resizertimingpostcts'),
                'Expected post-CTS timing-repaired netlist')
        raw = netlist.read_text()
        require(not re.search(r'\.(?:VDD|VSS|VNW|VPW)\s*\(', raw),
                'Use unpowered .nl.v, not the powered netlist')
        types = set(re.findall(r'^\s*(gf180mcu_fd_sc_mcu7t5v0__\w+)\s', raw, re.M))
        require(bool(types) and types <= model_modules,
                f'Cell models missing; none silently removed: {sorted(types-model_modules)}')
        renamed, count = re.subn(r'(?m)^module\s+asic_top\s*\(', 'module physical_top (', raw)
        require(count == 1, 'Expected one flattened asic_top')
        checks, diagnostics = diagnostic_checks(raw)
        build = output/variant
        build.mkdir(exist_ok=True)
        copy, tb, executable = build/'physical.v', build/'tb_physical.v', build/'physical.vvp'
        copy.write_text(renamed)
        tb.write_text(testbench(index, checks))
        tracked = list(sources) + libraries + [netlist, state_path, snapshot_path, record_path,
                    resolved_path, root/'config/rtl_asic.f', Path(__file__).resolve(), copy, tb]
        hashes = {p.relative_to(root).as_posix(): sha(p) for p in tracked}

        def run(command, label):
            completed = subprocess.run(list(map(str, command)), cwd=root, text=True,
                                       capture_output=True, timeout=600)
            log = completed.stdout+completed.stderr
            (build/f'{label}.log').write_text(log)
            require(completed.returncode == 0, f'{label} failed; inspect {build}/{label}.log')
            return log

        version = run(['iverilog', '-V'], 'iverilog_version').splitlines()[0]
        run(['iverilog', '-g2012', '-DFUNCTIONAL', '-s', 'tb_physical', '-o', executable,
             tb, copy, *libraries, *sources], 'compile')
        log = run(['vvp', executable], 'simulation')
        lines = [line for line in log.splitlines() if line.startswith('PASS physical_startup ')]
        require(len(lines) == 1, 'Missing unique PASS summary')
        coverage = {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)', lines[0])}
        require(coverage['variant'] == index and coverage['epochs'] == 2 and coverage['spi_frames'] == 4,
                'Unexpected simulation coverage')
        require(all(sha(local(root, n)) == h for n,h in hashes.items()), 'Test inputs changed')
        require(all(sha(local(root, n)) == h for n,h in snapshot.items()), 'Physical provenance changed')
        results['runs'][variant] = {'passed': True, 'summary': lines[0], 'coverage': coverage,
            'diagnostic_bits_compared': diagnostics, 'physical_cells_removed': [],
            'cell_types': sorted(types), 'iverilog_version': version,
            'state': state_path.relative_to(root).as_posix(), 'netlist': netlist.relative_to(root).as_posix(),
            'netlist_sha256': sha(netlist), 'input_sha256': hashes,
            'simulation_log': (build/'simulation.log').relative_to(root).as_posix()}
        print(lines[0], flush=True)
    results['all_passed'] = True
    result_path.write_text(json.dumps(results, indent=2, sort_keys=True)+'\n')
    print('PASS bounded post-CTS production startup; no full game, formal proof or SDF claim')


if __name__ == '__main__':
    main()
