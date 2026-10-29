#!/usr/bin/env python3
"""Verifica la copia FPGA sin escribir en el Proyecto 2 original."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    return result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ice40-model", type=Path, required=True)
    args = parser.parse_args()
    model = args.ice40_model.expanduser().resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    base = root / "baseline/proyecto2"
    build = root / "build/baseline"
    build.mkdir(parents=True, exist_ok=True)
    for tool in ["iverilog", "vvp"]:
        if not shutil.which(tool):
            raise SystemExit(f"Falta {tool} en PATH")
    hexfile = build / "game.regenerated.hex"
    run([sys.executable, str(base / "assembler/assemble.py"), str(base / "assembler/game.s"), str(hexfile)], root)
    generated = hexfile.read_bytes()
    for relative in ["assembler/game.hex", "pochoco_soc-main/sw/game.hex"]:
        if generated != (base / relative).read_bytes():
            raise SystemExit(f"El programa regenerado difiere de {relative}")
    soc = base / "pochoco_soc-main"
    rtl = sorted((soc / "rtl").rglob("*.v"))
    executable = build / "startup.vvp"
    run(["iverilog", "-g2012", "-s", "tb_proyecto2_startup", "-o", str(executable), str(model), str(root / "sim/tb_proyecto2_startup.v"), *map(str, rtl)], soc)
    log = run(["vvp", str(executable)], soc)
    if "PASS:" not in log:
        raise SystemExit("La simulacion no produjo su confirmacion de exito")
    (build / "startup.log").write_text(log)
    result = {"assembler_words": len(generated.split()), "hex_sha256": hashlib.sha256(generated).hexdigest(), "startup_cycles": 2000, "startup_passed": True, "ice40_model_sha256": hashlib.sha256(model.read_bytes()).hexdigest()}
    (build / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: programa reproducible y arranque FPGA verificado")


if __name__ == "__main__":
    main()
