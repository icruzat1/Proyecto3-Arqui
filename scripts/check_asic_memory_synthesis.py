#!/usr/bin/env python3
"""Synthesize memory A/B and each complete top using the pinned local image.

Checks generic logic and actual FF-backed storage, not GF180 area, frequency,
physical implementation, or functional equivalence of the generated netlists.
"""
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def enabled_attribute(value):
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str) and re.fullmatch(r"[01]+", value):
        return int(value, 2) != 0
    return bool(value)


def is_flip_flop(cell_type):
    return cell_type.startswith("$_") and "DFF" in cell_type.upper()


def inspect_hierarchy(modules, top):
    """Expand each instance, including repeated instances of the same module."""
    leaf_types = Counter()
    module_instances = Counter()
    flip_flop_bits = 0

    def visit(module_name, path, ancestors):
        nonlocal flip_flop_bits
        if module_name in ancestors:
            raise ValueError(f"Recursive hierarchy at {path}: {module_name}")
        module = modules[module_name]
        module_instances[module_name] += 1
        attributes = module.get("attributes", {})
        if any(enabled_attribute(attributes.get(key, 0)) for key in ("blackbox", "whitebox")):
            raise ValueError(f"Unresolved box at {path}: {module_name}")
        if module.get("memories"):
            raise ValueError(f"Unmapped memory objects in {path}")
        for name, cell in module.get("cells", {}).items():
            cell_type = cell["type"]
            child = f"{path}/{name}"
            if cell_type in modules:
                visit(cell_type, child, ancestors | {module_name})
                continue
            if "LATCH" in cell_type.upper() or cell_type.startswith("$_SR_"):
                raise ValueError(f"Unexpected latch at {child}: {cell_type}")
            if cell_type.startswith("SB_"):
                raise ValueError(f"FPGA primitive at {child}: {cell_type}")
            if cell_type.lower().startswith(("$mem", "$_mem")):
                raise ValueError(f"Unmapped memory cell at {child}: {cell_type}")
            if not cell_type.startswith("$_"):
                raise ValueError(f"Unresolved or non-generic cell at {child}: {cell_type}")
            leaf_types[cell_type] += 1
            if is_flip_flop(cell_type):
                q_bits = cell.get("connections", {}).get("Q", [])
                if not q_bits or any(not isinstance(bit, int) for bit in q_bits):
                    raise ValueError(f"Invalid flip-flop Q at {child}")
                flip_flop_bits += len(q_bits)

    if top not in modules:
        raise ValueError(f"Missing synthesized top module {top}")
    visit(top, top, set())
    return {
        "leaf_cell_types_by_instance": dict(sorted(leaf_types.items())),
        "total_leaf_cells": sum(leaf_types.values()),
        "generic_flip_flop_bits": flip_flop_bits,
        "module_instance_counts": dict(sorted(module_instances.items())),
        "counting_method": "Recursive expansion from top; repeated module instances counted separately",
    }


def verify_storage(modules, module_name, array_name, word_count):
    """Prove named array bits are distinct live Q outputs, not constants/ROM."""
    if module_name not in modules:
        raise ValueError(f"Memory module {module_name} disappeared from the netlist")
    module = modules[module_name]
    nets = module.get("netnames", {})
    drivers = defaultdict(list)
    for cell_name, cell in module.get("cells", {}).items():
        for port_name, direction in cell.get("port_directions", {}).items():
            if direction != "output":
                continue
            for bit in cell["connections"].get(port_name, []):
                if isinstance(bit, int):
                    drivers[bit].append((cell_name, cell["type"], port_name))
    all_bits = set()
    ff_types = Counter()
    words = []
    for word in range(word_count):
        name = f"{array_name}[{word}]"
        # Yosys JSON names normally omit the Verilog escaped-name prefix.
        if name not in nets and "\\" + name in nets:
            name = "\\" + name
        if name not in nets:
            raise ValueError(f"Missing storage net {module_name}/{array_name}[{word}]; inspect netlist naming before changing this check")
        bits = nets[name]["bits"]
        if len(bits) != 32 or any(not isinstance(bit, int) for bit in bits):
            raise ValueError(f"Storage word contains constants or has wrong width: {module_name}/{name}")
        if len(set(bits)) != 32 or all_bits.intersection(bits):
            raise ValueError(f"Storage bits merged or aliased: {module_name}/{name}")
        for bit in bits:
            sources = drivers[bit]
            if len(sources) != 1:
                raise ValueError(f"Storage bit {module_name}/{name}/{bit} has {len(sources)} cell drivers")
            _, cell_type, port = sources[0]
            if port != "Q" or not is_flip_flop(cell_type):
                raise ValueError(f"Storage bit {module_name}/{name}/{bit} is not directly driven by FF Q: {sources}")
            ff_types[cell_type] += 1
        all_bits.update(bits)
        words.append(name)
    expected_bits = 32 * word_count
    if len(all_bits) != expected_bits:
        raise ValueError(f"Incorrect independent storage count in {module_name}: {len(all_bits)} != {expected_bits}")
    return {
        "module": module_name,
        "array": array_name,
        "words_verified": word_count,
        "bits_per_word": 32,
        "independent_storage_bits_verified": expected_bits,
        "each_bit_has_one_flip_flop_q_driver": True,
        "no_constant_or_aliased_storage_bits": True,
        "storage_flip_flop_types": dict(sorted(ff_types.items())),
        "word_netnames": words,
    }


def main():
    root = Path(__file__).resolve().parents[1]
    build = root / "build/asic_memory_synthesis"
    build.mkdir(parents=True, exist_ok=True)
    (build / "results.json").unlink(missing_ok=True)
    lock_path = root / "config/environment.lock.json"
    image = json.loads(lock_path.read_text())["container_image"]
    source_manifest = root / "config/rtl_asic.f"
    sources = [line.strip() for line in source_manifest.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    if len(sources) != len(set(sources)):
        raise SystemExit("Duplicate production source in config/rtl_asic.f")
    # Paths must be project-relative tokens suitable for Yosys command files.
    for name in sources:
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", name) or ".." in Path(name).parts:
            raise SystemExit(f"Unsafe or unsupported manifest path: {name}")
        if not (root / name).is_file():
            raise SystemExit(f"Missing production source: {name}")
        if not name.startswith("rtl/"):
            raise SystemExit(f"Only production RTL is accepted: {name}")
    if set(sources) != {p.relative_to(root).as_posix() for p in (root / "rtl").rglob("*.v")}:
        raise SystemExit("Production manifest does not match rtl/*.v recursively")
    check = subprocess.run([sys.executable, str(root / "scripts/generate_asic_memory.py"), "--check"],
                           cwd=root, capture_output=True, text=True)
    (build / "generator_check.log").write_text(check.stdout + check.stderr)
    if check.returncode:
        raise SystemExit("Generated program is stale or invalid; see build/asic_memory_synthesis/generator_check.log")
    docker = shutil.which("docker") or "/Applications/Docker.app/Contents/Resources/bin/docker"
    if not Path(docker).is_file():
        raise SystemExit("Docker CLI not found")
    env = os.environ.copy()
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        env.pop(name, None)
    prefix = [docker, "run", "--rm", "--pull=never", "--network=none", "--platform", "linux/arm64",
              "--user", f"{os.getuid()}:{os.getgid()}", "--cpus", "2", "--memory", "4g",
              "--mount", f"type=bind,src={root},dst=/work", "--workdir", "/work",
              "--entrypoint", "yosys", image]
    inputs = sources + ["config/rtl_asic.f", "config/environment.lock.json",
                        "scripts/generate_asic_memory.py", "scripts/check_asic_memory_synthesis.py",
                        "rtl/asic/generated/manifest.json", "rtl/asic/generated/game.hex",
                        "baseline/proyecto2/assembler/assemble.py", "firmware/asic/game.s"]
    results = {
        "scope": "Generic synthesis and FF-storage verification of memory A/B and both complete macro variants",
        "container_image": image,
        "input_sha256": {name: sha(root / name) for name in sorted(inputs)},
        "abc_run": False,
        "pdk_mapping_run": False,
        "physical_flow_run": False,
        "post_synthesis_functional_equivalence_verified": False,
        "runs": {},
    }
    runs = [("memory_a", "memory_a", None, "ram_ff", 16),
            ("memory_b", "memory_b", None, "mem_ff", 144),
            ("asic_top_a", "asic_top", 0, "ram_ff", 16),
            ("asic_top_b", "asic_top", 1, "mem_ff", 144)]
    for label, top, variant, array, word_count in runs:
        memory_type = "memory_a" if array == "ram_ff" else "memory_b"
        other_memory = "memory_b" if memory_type == "memory_a" else "memory_a"
        script = build / f"{label}.ys"
        netlist_json = build / f"{label}.json"
        netlist_verilog = build / f"{label}.v"
        # Remove previous outputs so a partially failed run cannot look fresh.
        for path in (netlist_json, netlist_verilog):
            path.unlink(missing_ok=True)
        commands = ["read_verilog -sv " + " ".join(sources)]
        if variant is not None:
            commands.append(f"chparam -set MemoryVariant {variant} asic_top")
        commands += [f"hierarchy -check -top {top}", f"synth -top {top} -noabc", "check -assert",
                     f"write_json build/asic_memory_synthesis/{label}.json",
                     f"write_verilog -noattr build/asic_memory_synthesis/{label}.v"]
        script.write_text("\n".join(commands) + "\n")
        command = prefix + ["-Q", "-T", "-s", script.relative_to(root).as_posix()]
        completed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
        log = completed.stdout + completed.stderr
        (build / f"{label}.log").write_text(log)
        if completed.returncode:
            raise SystemExit(f"Synthesis failed for {label}; see build/asic_memory_synthesis/{label}.log")
        netlist = json.loads(netlist_json.read_text())
        modules = netlist["modules"]
        try:
            hierarchy = inspect_hierarchy(modules, top)
            module_counts = hierarchy["module_instance_counts"]
            if module_counts.get(memory_type) != 1 or other_memory in modules:
                raise ValueError(f"{label} must contain exactly one {memory_type} and no {other_memory}")
            storage = verify_storage(modules, memory_type, array, word_count)
        except ValueError as error:
            raise SystemExit(f"Netlist validation failed for {label}: {error}")
        warnings = [{"line": number, "message": line} for number, line in enumerate(log.splitlines(), 1)
                    if line.startswith("Warning:")]
        results["runs"][label] = {
            "passed": True,
            "top": top,
            "memory_variant": "A" if memory_type == "memory_a" else "B",
            "yosys_version": netlist["creator"],
            "no_latches_unmapped_memories_fpga_primitives_or_blackboxes": True,
            "selected_architecture_only": True,
            "hierarchy": hierarchy,
            "storage": storage,
            "warnings": warnings,
            "log": f"build/asic_memory_synthesis/{label}.log",
            "script": f"build/asic_memory_synthesis/{label}.ys",
            "netlist_json": f"build/asic_memory_synthesis/{label}.json",
            "netlist_json_sha256": sha(netlist_json),
            "netlist_verilog": f"build/asic_memory_synthesis/{label}.v",
            "netlist_verilog_sha256": sha(netlist_verilog),
        }
        print(f"PASS synthesis {label}: {storage['independent_storage_bits_verified']} independent storage bits, "
              f"{hierarchy['generic_flip_flop_bits']} total generic FF bits", flush=True)
    results["all_passed"] = True
    (build / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print("PASS memory synthesis: four runs; no GF180 area or timing claimed")


if __name__ == "__main__":
    main()
