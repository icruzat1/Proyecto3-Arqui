#!/usr/bin/env python3
"""Verify a complete accelerated game in both RTL and synthesized A/B macros.

The production 10 MHz firmware is kept separate. Only its two timing constants
are divided by 10,000 for these tests, identically for RTL and netlists. The
generic flattened netlists have no PDK mapping and no SDF timing annotation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-only", action="store_true", help="Run the semantic RTL tests only; do not claim netlist verification")
    args = parser.parse_args()
    build = root / "build/asic_full_game"
    build.mkdir(parents=True, exist_ok=True)
    (build / "results.json").unlink(missing_ok=True)
    for name in ("iverilog", "vvp"):
        if not shutil.which(name):
            raise SystemExit(f"Missing {name}")

    def relative(path):
        return path.relative_to(root).as_posix()

    def run(command, label, timeout=300):
        result = subprocess.run(list(map(str, command)), cwd=root, text=True,
                                capture_output=True, timeout=timeout)
        log = result.stdout + result.stderr
        (build / f"{label}.log").write_text(log)
        if result.returncode:
            print(log, file=sys.stderr)
            raise SystemExit(f"Failed {label}: exit {result.returncode}")
        return log

    production_rom = root / "rtl/asic/generated/asic_program_rom.v"
    production_rom_hash = sha(production_rom)
    original_sources = [line.strip() for line in (root / "config/rtl_asic.f").read_text().splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
    for source in original_sources:
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", source) or ".." in Path(source).parts:
            raise SystemExit(f"Unsupported source manifest path: {source}")
    if original_sources.count("rtl/asic/generated/asic_program_rom.v") != 1:
        raise SystemExit("Expected exactly one production ROM in the source manifest")
    inputs = original_sources + ["config/rtl_asic.f", "config/environment.lock.json", "firmware/asic/game.s",
                                "scripts/generate_game_firmware.py", "scripts/generate_asic_memory.py",
                                "scripts/check_asic_memory_synthesis.py", "scripts/check_full_game.py",
                                "sim/asic_stage3/tb_full_game.v", "baseline/proyecto2/assembler/assemble.py"]
    input_hashes = {name: sha(root / name) for name in sorted(set(inputs))}
    image_dir = build / "firmware"
    run([sys.executable, root / "scripts/generate_game_firmware.py", "--profile", "simulation",
         "--output-dir", image_dir], "generate_firmware")
    timing = json.loads((image_dir / "timing.json").read_text())
    if (timing.get("profile"), timing.get("clock_hz"), timing.get("wait_ticks"), timing.get("tenth_ticks"), timing.get("acceleration_factor")) != ("simulation", 10_000_000, 3000, 100, 10_000):
        raise SystemExit("Unexpected accelerated firmware profile; review scoreboard and coverage")
    if timing["wait_ticks"] != 30 * timing["tenth_ticks"]:
        raise SystemExit("The accelerated image does not preserve the 3s / 0.1s ratio")
    sources = [relative(image_dir / "asic_program_rom.v") if name == "rtl/asic/generated/asic_program_rom.v" else name
               for name in original_sources]
    tb = root / "sim/asic_stage3/tb_full_game.v"
    results = {
        "scope": "Complete game semantic checks and cycle-by-cycle logical terminal comparison of RTL and generic whole-macro netlists",
        "all_passed": False,
        "full_game_verified": False,
        "post_synthesis_game_equivalence": False,
        "comparison_kind": "Dynamic simulation of identical stimuli; not formal equivalence",
        "pdk_mapped_netlist": False,
        "sdf_timing": False,
        "physical_flow_run": False,
        "clock_period_ns": 100,
        "production_game_at_real_time_simulated": False,
        "acceleration": timing,
        "firmware_hashes": {relative(path): sha(path) for path in sorted(image_dir.iterdir()) if path.is_file()},
        "input_sha256": input_hashes,
        "production_rom_preserved_sha256": production_rom_hash,
        "stimulus_notes": "Both models receive the same reset/buttons on the same falling clock edges. SPI inputs are held idle. Every external output is compared after each rising clock edge, including boot and reset.",
        "semantic_reference": "Independent arithmetic from actual peripheral timer samples, plus explicit expected 10 rounds, wrong retry without count/sum change, held-button release, saturation and truncated average. Netlist internals are never used by the checker.",
        "runs": {},
    }

    def simulation(variant, netlist=None):
        label = ("equivalence_" if netlist else "rtl_") + ("a" if variant == 0 else "b")
        executable = build / f"{label}.vvp"
        trace = build / f"{label}.trace.csv"
        command = ["iverilog", "-g2012", "-Wall", "-Wno-timescale", "-s", "tb_full_game",
                   f"-Ptb_full_game.MemoryVariant={variant}", "-o", executable]
        if netlist:
            command += ["-DWITH_NETLIST", netlist]
        command += [tb] + [root / source for source in sources]
        run(command, f"compile_{label}")
        log = run(["vvp", executable, f"+WAIT_TICKS={timing['wait_ticks']}",
                   f"+TENTH_TICKS={timing['tenth_ticks']}", f"+TRACE={trace}"], label, timeout=600)
        summaries = [line for line in log.splitlines() if line.startswith("PASS full_game ")]
        if len(summaries) != 1:
            raise SystemExit(f"Missing unique passing summary for {label}")
        coverage = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", summaries[0])}
        expected = {"variant": variant, "correct": 10, "wrong": 2, "attempts": 12,
                    "capped": 1, "average": 16, "sum": 162, "held_checks": 4800, "resets": 3}
        for key, value in expected.items():
            if coverage.get(key) != value:
                raise SystemExit(f"Unexpected semantic coverage {label}/{key}: {coverage.get(key)} != {value}")
        info = {"passed": True, "coverage": coverage, "summary": summaries[0],
                "simulation_log": relative(build / f"{label}.log"),
                "compile_log": relative(build / f"compile_{label}.log"),
                "external_trace": relative(trace), "external_trace_sha256": sha(trace),
                "netlist_compared": bool(netlist)}
        results["runs"][label] = info
        print(summaries[0], flush=True)
        return info

    for variant in (0, 1):
        simulation(variant)
    results["full_game_verified"] = True
    if not args.rtl_only:
        lock = json.loads((root / "config/environment.lock.json").read_text())
        image = lock["container_image"]
        if "@sha256:" not in image:
            raise SystemExit("The synthesis image must be pinned by digest")
        docker = shutil.which("docker") or "/Applications/Docker.app/Contents/Resources/bin/docker"
        if not Path(docker).is_file():
            raise SystemExit("Docker CLI not found")
        inspect = runpy.run_path(str(root / "scripts/check_asic_memory_synthesis.py"))["inspect_hierarchy"]
        prefix = [docker, "run", "--rm", "--pull=never", "--network=none", "--platform", "linux/arm64",
                  "--user", f"{os.getuid()}:{os.getgid()}", "--cpus", "2", "--memory", "4g",
                  "--mount", f"type=bind,src={root},dst=/work", "--workdir", "/work",
                  "--entrypoint", "yosys", image]
        results["container_image"] = image
        results["abc_run"] = False
        for variant, suffix in ((0, "a"), (1, "b")):
            label = f"synthesis_{suffix}"
            script = build / f"{label}.ys"
            netlist = build / f"{label}.v"
            netjson = build / f"{label}.json"
            for path in (netlist, netjson):
                path.unlink(missing_ok=True)
            commands = ["read_verilog -sv " + " ".join(sources),
                        f"chparam -set MemoryVariant {variant} asic_top", "hierarchy -check -top asic_top",
                        "flatten -noscopeinfo", "synth -top asic_top -noabc", "check -assert", "rename asic_top netlist_top",
                        f"write_json {relative(netjson)}", f"write_verilog -noattr {relative(netlist)}"]
            script.write_text("\n".join(commands) + "\n")
            run(prefix + ["-Q", "-T", "-s", relative(script)], label, timeout=600)
            synthesized = json.loads(netjson.read_text())
            hierarchy = inspect(synthesized["modules"], "netlist_top")
            if set(synthesized["modules"]) != {"netlist_top"}:
                raise SystemExit("Unexpected surviving modules after complete top flattening")
            syn_info = {"passed": True, "memory_variant": variant, "yosys_version": synthesized["creator"],
                        "hierarchy": hierarchy, "netlist_verilog": relative(netlist),
                        "netlist_verilog_sha256": sha(netlist), "netlist_json": relative(netjson),
                        "netlist_json_sha256": sha(netjson), "script": relative(script),
                        "log": relative(build / f"{label}.log")}
            results["runs"][label] = syn_info
            print(f"PASS whole-game synthesis {suffix}: {hierarchy['generic_flip_flop_bits']} generic FF bits", flush=True)
            paired = simulation(variant, netlist)
            reference = results["runs"][f"rtl_{suffix}"]
            if paired["coverage"] != reference["coverage"] or paired["external_trace_sha256"] != reference["external_trace_sha256"]:
                raise SystemExit(f"Standalone RTL and paired RTL/netlist runs diverged for {suffix}")
            paired["identical_standalone_rtl_trace"] = True
            if sha(netlist) != syn_info["netlist_verilog_sha256"] or sha(netjson) != syn_info["netlist_json_sha256"]:
                raise SystemExit("Netlist files changed during simulation")
        results["post_synthesis_game_equivalence"] = True
    if sha(production_rom) != production_rom_hash:
        raise SystemExit("The production ROM changed during accelerated game tests")
    if any(sha(root / name) != digest for name, digest in input_hashes.items()):
        raise SystemExit("An input file changed during this run; rerun against a stable revision")
    results["all_passed"] = True
    (build / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print("PASS complete A/B game " + ("RTL semantic checks only" if args.rtl_only else "RTL and generic post-synthesis cycle comparison; no PDK mapping or SDF"))


if __name__ == "__main__":
    main()
