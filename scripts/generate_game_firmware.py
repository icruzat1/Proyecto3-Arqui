#!/usr/bin/env python3
"""Build the 10 MHz ASIC game or documented accelerated test images.

Production: 30,000,000 ticks per wait, 1,000,000 ticks per tenth.
Simulation: divide both constants by 10,000, preserving their 30:1 ratio.
Wait-only: divide only the initial wait by 10,000; retain production reaction units.
The immutable Proyecto 2 assembler remains the only instruction encoder.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import tempfile


CLOCK_HZ = 10_000_000
PROFILES = {
    "production": {"wait_ticks": 30_000_000, "tenth_ticks": 1_000_000, "acceleration_factor": 1},
    "simulation": {"wait_ticks": 3_000, "tenth_ticks": 100, "acceleration_factor": 10_000},
    "wait_only": {
        "wait_ticks": 3_000, "tenth_ticks": 1_000_000, "acceleration_factor": None,
        "wait_acceleration_factor": 10_000, "reaction_acceleration_factor": 1,
    },
}
OUTPUT_NAMES = ("game.s", "asic_program_rom.v", "game.hex", "timing.json", "manifest.json")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def constant_block(name, ticks):
    if not 0 < ticks < 2**31:
        raise ValueError("Timing constants must fit a positive signed 32-bit duration")
    upper = (ticks + 0x800) >> 12
    lower = ticks - (upper << 12)
    lines = [f"# ASIC_TIMING {name} BEGIN", f"    lui  x9, 0x{upper:x}", f"    addi x9, x9, {lower}"]
    if name == "WAIT_TICKS":
        # Keep the same number of instructions for every timing profile.
        lines.append("    addi x9, x9, 0")
    lines.append(f"# ASIC_TIMING {name} END")
    return "\n".join(lines)


def render(source, profile):
    if source.count("# TIMING_PROFILE production") != 1:
        raise ValueError("Expected exactly one production profile marker")
    result = source.replace("# TIMING_PROFILE production", f"# TIMING_PROFILE {profile}")
    for name, key in (("WAIT_TICKS", "wait_ticks"), ("TENTH_TICKS", "tenth_ticks")):
        expected = constant_block(name, PROFILES["production"][key])
        if source.count(f"# ASIC_TIMING {name} BEGIN") != 1 or source.count(f"# ASIC_TIMING {name} END") != 1 or source.count(expected) != 1:
            raise ValueError(f"Missing, duplicated or modified production timing block: {name}")
        result = result.replace(expected, constant_block(name, PROFILES[profile][key]))
    return result


def label_addresses(source):
    """Record assembly labels for testbench diagnostics; does not encode ISA."""
    labels = {}
    pc = 0
    for line in source.splitlines():
        line = line.split("#", 1)[0].split("//", 1)[0].strip()
        if not line or line.startswith("."):
            continue
        while True:
            match = re.match(r"([A-Za-z_]\w*):\s*(.*)$", line)
            if not match:
                break
            name, line = match.groups()
            if name in labels:
                raise ValueError(f"Duplicate assembly label: {name}")
            labels[name] = pc
        if line:
            pc += 4
    return labels


def generate(root, profile):
    source = root / "firmware/asic/game.s"
    source_bytes = source.read_bytes()
    rendered = render(source_bytes.decode("utf-8"), profile).encode("utf-8")
    memory_generate = runpy.run_path(str(root / "scripts/generate_asic_memory.py"))["generate"]
    with tempfile.TemporaryDirectory(prefix="asic-game-") as temporary:
        derived = Path(temporary) / "game.s"
        derived.write_bytes(rendered)
        files = memory_generate(root, derived)
    timing = {
        "schema_version": 1,
        "profile": profile,
        "clock_hz": CLOCK_HZ,
        "clock_period_ns": 100,
        **PROFILES[profile],
        "nominal_wait_seconds": 3,
        "nominal_tenth_seconds": 0.1,
        "wait_comparison": "signed((timer - start) modulo 2^32) < wait_ticks",
        "wait_assumptions": "0 < wait_ticks < 2^31; continuous polling before elapsed reaches 2^31 ticks",
        "labels": label_addresses(rendered.decode("utf-8")),
        "production_source": {"path": "firmware/asic/game.s", "sha256": sha256(source_bytes)},
        "generated_source_sha256": sha256(rendered),
    }
    timing_bytes = (json.dumps(timing, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest = json.loads(files["manifest.json"])
    # Normalize the derived source name; no temporary or workstation paths enter
    # committed evidence. The hash is the exact generated game.s, not the template.
    manifest["source"]["path"] = "game.s"
    manifest["firmware_profile"] = profile
    manifest["production_source"] = timing["production_source"]
    manifest["timing_json_sha256"] = sha256(timing_bytes)
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    files["game.s"] = rendered
    files["timing.json"] = timing_bytes
    return files


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="production")
    parser.add_argument("--output-dir", type=Path, help="Default: build/game_firmware/PROFILE")
    parser.add_argument("--check", action="store_true", help="Verify outputs without rewriting")
    args = parser.parse_args()
    output = (args.output_dir or root / "build/game_firmware" / args.profile).expanduser().resolve()
    try:
        for protected in (root / "baseline", root.parent / "Proyecto 2", root / "firmware"):
            if output.is_relative_to(protected.resolve()):
                raise ValueError("Output directory must not overwrite baseline, Proyecto 2 or firmware source")
        if args.profile != "production" and output.is_relative_to((root / "rtl").resolve()):
            raise ValueError("An accelerated simulation image must not overwrite production RTL")
        files = generate(root, args.profile)
        if args.check:
            stale = [name for name in OUTPUT_NAMES if not (output / name).is_file() or (output / name).read_bytes() != files[name]]
            if stale:
                raise ValueError("Generated files missing or stale: " + ", ".join(stale))
            action = "checked"
        else:
            output.mkdir(parents=True, exist_ok=True)
            for name in OUTPUT_NAMES:
                path = output / name
                if not path.is_file() or path.read_bytes() != files[name]:
                    path.write_bytes(files[name])
            action = "generated"
        print(f"PASS {action} {args.profile}: {json.loads(files['manifest.json'])['program_words']} words; {output}")
    except (OSError, UnicodeError, ValueError, KeyError) as error:
        raise SystemExit(f"Game firmware generation failed: {error}")


if __name__ == "__main__":
    main()
