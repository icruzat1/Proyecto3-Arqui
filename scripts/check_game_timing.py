#!/usr/bin/env python3
"""Verify generated game wait instructions and directed Espino ALU boundaries.

This is arithmetic/firmware evidence, not full CPU or post-layout verification.
Full-game RTL/netlist simulation is a separate check.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def fields(word):
    return {"opcode": word & 127, "rd": (word >> 7) & 31,
            "funct3": (word >> 12) & 7, "rs1": (word >> 15) & 31,
            "rs2": (word >> 20) & 31, "funct7": word >> 25,
            "imm_i": signed(word >> 20, 12)}


def expect(word, **expected):
    actual = fields(word)
    require(all(actual[key] == value for key, value in expected.items()),
            f"Unexpected firmware instruction {word:08x}: expected {expected}, got {actual}")


def load_constant(words, start, count):
    expect(words[start], opcode=0x37, rd=9)
    value = words[start] & 0xfffff000
    for word in words[start + 1:start + count]:
        expect(word, opcode=0x13, funct3=0, rd=9, rs1=9)
        value = (value + fields(word)["imm_i"]) & 0xffffffff
    return value


def verify_profile(directory, profile, wait_ticks, tenth_ticks):
    timing = json.loads((directory / "timing.json").read_text())
    words = [int(line, 16) for line in (directory / "game.hex").read_text().splitlines()]
    require(len(words) == 95, "Expected the corrected 95-word game")
    require(timing["profile"] == profile and timing["clock_hz"] == 10000000 and
            timing["clock_period_ns"] == 100 and timing["wait_ticks"] == wait_ticks and
            timing["tenth_ticks"] == tenth_ticks, "Unexpected timing profile metadata")
    labels = timing["labels"]
    require(labels["wait3"] == 68, "Wait instruction positions changed; review this directed test")
    # Verify exact machine instructions, independently of assembly comments.
    # lw start, constant load, copy start, increment seed, lw current, elapsed
    # subtraction, signed elapsed-duration branch back to the wait loop.
    expect(words[12], opcode=3, funct3=2, rd=7, rs1=2, imm_i=12)
    require(load_constant(words, 13, 3) == wait_ticks, "Wrong encoded wait duration")
    expect(words[15], opcode=0x13, funct3=0, rd=9, rs1=9, imm_i=0)
    expect(words[16], opcode=0x13, funct3=0, rd=8, rs1=7, imm_i=0)
    expect(words[17], opcode=0x13, funct3=0, rd=11, rs1=11, imm_i=1)
    expect(words[18], opcode=3, funct3=2, rd=7, rs1=2, imm_i=12)
    expect(words[19], opcode=0x33, funct3=0, funct7=0x20, rd=7, rs1=7, rs2=8)
    branch = words[20]
    expect(branch, opcode=0x63, funct3=4, rs1=7, rs2=9)
    displacement = signed(((branch >> 31) << 12) | (((branch >> 7) & 1) << 11) |
                          (((branch >> 25) & 63) << 5) | (((branch >> 8) & 15) << 1), 13)
    require(80 + displacement == labels["wait3"], "Wait branch target is wrong")
    divisor_index = labels["div_l"] // 4 - 3
    require(load_constant(words, divisor_index, 2) == tenth_ticks,
            "Wrong encoded reaction-time divisor")
    expect(words[divisor_index + 2], opcode=0x13, funct3=0, rd=15, rs1=0, imm_i=0)
    return words, {13, 14, divisor_index, divisor_index + 1}


def main():
    root = Path(__file__).resolve().parents[1]
    build = root / "build/asic_game_timing"
    build.mkdir(parents=True, exist_ok=True)
    (build / "results.json").unlink(missing_ok=True)
    profiles = {}
    generated = []
    for profile, wait_ticks, tenth_ticks in (("production", 30000000, 1000000),
                                             ("simulation", 3000, 100)):
        directory = build / profile
        command = [sys.executable, str(root / "scripts/generate_game_firmware.py"),
                   "--profile", profile, "--output-dir", str(directory)]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        (build / f"generate_{profile}.log").write_text(result.stdout + result.stderr)
        require(result.returncode == 0, f"Firmware generation failed: {profile}")
        words, allowed = verify_profile(directory, profile, wait_ticks, tenth_ticks)
        profiles[profile] = {"wait_ticks": wait_ticks, "tenth_ticks": tenth_ticks,
                             "word_count": len(words), "wait_machine_code_verified": True,
                             "reaction_divisor_machine_code_verified": True,
                             "file_sha256": {p.name: sha(p) for p in sorted(directory.iterdir()) if p.is_file()}}
        generated.append((words, allowed))
    require(generated[0][1] == generated[1][1], "Profile code positions differ")
    changed = {index for index, (a, b) in enumerate(zip(generated[0][0], generated[1][0])) if a != b}
    require(changed <= generated[0][1], "Profiles differ outside the timing constants")
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    require(iverilog and vvp, "Icarus Verilog and vvp are required")
    source = root / "sim/asic_stage3/tb_timer_compare.v"
    alu = root / "rtl/espino_core/espino_alu.v"
    binary = build / "timer_compare.vvp"
    commands = (("compile", [iverilog, "-g2012", "-s", "tb_timer_compare", "-o", str(binary), str(source), str(alu)]),
                ("timer_compare", [vvp, str(binary)]))
    for name, command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        log = result.stdout + result.stderr
        (build / f"{name}.log").write_text(log)
        require(result.returncode == 0, f"{name} failed; inspect its log")
        if name == "timer_compare":
            require("PASS timer_compare checks=20 old_algorithm_failures=2 corrected_algorithm_failures=0" in log,
                    "Directed ALU test did not report its expected coverage")
    inputs = ["scripts/check_game_timing.py", "scripts/generate_game_firmware.py",
              "scripts/generate_asic_memory.py", "firmware/asic/game.s",
              "baseline/proyecto2/assembler/assemble.py", "sim/asic_stage3/tb_timer_compare.v",
              "rtl/espino_core/espino_alu.v"]
    results = {
        "scope": "Decoded firmware constants/wait instructions and directed arithmetic using the production Espino ALU",
        "profiles": profiles,
        "only_timing_constants_differ_between_profiles": True,
        "changed_word_indices": sorted(changed),
        "directed_alu_cases": 20,
        "old_algorithm_failures_demonstrated": 2,
        "corrected_algorithm_failures": 0,
        "tested_counter_origins": ["0x00000010", "0x7fffffe0", "0xffffffe0"],
        "input_sha256": {name: sha(root / name) for name in inputs},
        "log_sha256": {p.name: sha(p) for p in sorted(build.glob("*.log"))},
        "limits": ["This check is not a full CPU or post-synthesis netlist execution.",
                   "Elapsed signed comparison assumes duration below 2^31 and continuous polling before elapsed reaches 2^31.",
                   "Reaction-time division retains original signed behavior; reactions of 2^31 cycles or more are not verified."]
    }
    (build / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print("PASS firmware timing: production 30000000/1000000, simulation 3000/100; 95 words; 20 ALU boundary cases")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Game timing verification failed: {error}")
