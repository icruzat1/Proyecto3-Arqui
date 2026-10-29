#!/usr/bin/env python3
"""Ejecuta LibreLane ARM64 con el proyecto montado en /work."""
import json
import os
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
if not sys.argv[1:]:
    raise SystemExit("Uso: python3 scripts/run_librelane.py [opciones LibreLane] ruta/relativa/config.yaml")
lock = json.loads((root / "config/environment.lock.json").read_text())
env = os.environ.copy()
toolbin = Path("/Applications/Docker.app/Contents/Resources/bin")
if toolbin.is_dir():
    env["PATH"] = str(toolbin) + os.pathsep + env.get("PATH", "")
for key in ["GITHUB_TOKEN", "GH_TOKEN"]:
    env.pop(key, None)
docker = shutil.which("docker", path=env.get("PATH"))
if not docker:
    raise SystemExit("No se encuentra Docker. Abre Docker Desktop y comprueba su instalación.")
command = [docker, "run", "--rm", "--platform", "linux/arm64", "--user", f"{os.getuid()}:{os.getgid()}",
           "--mount", f"type=bind,source={root},target=/work", "--workdir", "/work",
           "--env", "PDK_ROOT=/work/.pdk", lock["container_image"],
           "python3", "-m", "librelane", *sys.argv[1:]]
os.execve(docker, command, env)
