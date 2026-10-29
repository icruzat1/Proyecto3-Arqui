#!/usr/bin/env python3
"""Section 3.7: RTL/netlist cycles with only the 3-second wait shortened.

The 1,000,000-cycle tenth and 10 MHz clock are unchanged. A short reaction is
zero tenths. MMIO requests/stores are compared to observe the exact completion
cycle even when writing 00 leaves an already-zero display unchanged.
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


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-only", action="store_true")
    args=parser.parse_args()
    build=root/"build/asic_game_wait_only"
    build.mkdir(parents=True,exist_ok=True)
    (build/"results.json").unlink(missing_ok=True)
    require(shutil.which("iverilog") and shutil.which("vvp"),"Icarus Verilog and vvp are required")

    def relative(path):
        return path.relative_to(root).as_posix()

    def run(command,label,timeout=300):
        result=subprocess.run(list(map(str,command)),cwd=root,capture_output=True,text=True,timeout=timeout)
        log=result.stdout+result.stderr
        (build/f"{label}.log").write_text(log)
        require(result.returncode==0,f"{label} failed; inspect its log")
        return log

    sources=[line.strip() for line in (root/"config/rtl_asic.f").read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    require(len(sources)==len(set(sources)),"Duplicate production RTL source")
    require(all(re.fullmatch(r"[A-Za-z0-9_./-]+",name) and ".." not in Path(name).parts for name in sources),
            "Unsupported source path")
    require(sources.count("rtl/asic/generated/asic_program_rom.v")==1,"Expected exactly one production ROM")
    inputs=sources+["config/rtl_asic.f","config/environment.lock.json","firmware/asic/game.s",
                    "scripts/generate_game_firmware.py","scripts/generate_asic_memory.py",
                    "scripts/check_game_timing.py","scripts/check_asic_memory_synthesis.py",
                    "scripts/check_game_wait_only.py","sim/asic_stage3/tb_game_wait_only.v",
                    "baseline/proyecto2/assembler/assemble.py"]
    input_hashes={name:sha(root/name) for name in sorted(set(inputs))}
    firmware=build/"firmware"
    run([sys.executable,root/"scripts/generate_game_firmware.py","--profile","wait_only","--output-dir",firmware],
        "generate_firmware")
    timing=json.loads((firmware/"timing.json").read_text())
    require((timing["profile"],timing["wait_ticks"],timing["tenth_ticks"],timing["clock_hz"],timing["clock_period_ns"])
            ==("wait_only",3000,1000000,10000000,100),"Unexpected wait-only timing profile")
    # Reuse the independent instruction decoder, not assembly comments, to
    # establish that the divisor is truly one million in the executed image.
    check=runpy.run_path(str(root/"scripts/check_game_timing.py"))["verify_profile"]
    check(firmware,"wait_only",3000,1000000)
    sources=[relative(firmware/"asic_program_rom.v") if name=="rtl/asic/generated/asic_program_rom.v" else name
             for name in sources]
    results={
        "scope":"Correct round, incorrect single-button retry and second correct round; only the three-second wait shortened",
        "all_passed":False,"post_synthesis_game_equivalence":False,
        "comparison_kind":"Dynamic simulation of identical stimuli; not formal equivalence",
        "clock_period_ns":100,"wait_ticks":3000,"tenth_ticks":1000000,
        "reaction_divisor_unchanged_from_production":True,
        "encoded_wait_and_reaction_constants_verified":True,
        "production_game_at_real_time_simulated":False,
        "pdk_mapped_netlist":False,"sdf_timing":False,"physical_flow_run":False,
        "profile":timing,"input_sha256":input_hashes,
        "firmware_sha256":{p.name:sha(p) for p in sorted(firmware.iterdir()) if p.is_file()},
        "stimulus_notes":"Same reset/buttons on falling edges; idle SPI; all logical outputs compared after every rising edge, including boot/reset.",
        "diagnostic_notes":"Flattened core reset and MMIO request/write/address/byte enables/payload are also compared before every active edge. This observes the exact 00 result-write cycle even if display outputs do not change.",
        "runs":{}}

    def simulate(variant,netlist=None):
        suffix="a" if variant==0 else "b"
        label=("equivalence_" if netlist else "rtl_")+suffix
        executable=build/f"{label}.vvp"
        trace=build/f"{label}.trace.csv"
        command=["iverilog","-g2012","-Wall","-Wno-timescale","-s","tb_game_wait_only",
                 f"-Ptb_game_wait_only.MemoryVariant={variant}","-o",executable]
        if netlist:
            command += ["-DWITH_NETLIST",netlist]
        command += [root/"sim/asic_stage3/tb_game_wait_only.v"]+[root/name for name in sources]
        run(command,f"compile_{label}")
        log=run(["vvp",executable,f"+TRACE={trace}"],label,timeout=600)
        summaries=[line for line in log.splitlines() if line.startswith("PASS game_wait_only ")]
        require(len(summaries)==1,f"Missing unique PASS summary: {label}")
        coverage={key:int(value) for key,value in re.findall(r"(\w+)=(\d+)",summaries[0])}
        for key,value in {"variant":variant,"correct":2,"wrong":1,"attempts":3,"held_checks":600,"ram_accesses":0}.items():
            require(coverage.get(key)==value,f"Wrong coverage {label}/{key}")
        require(coverage["compared"]==coverage["cycles"]-1 and coverage["requests"]>100 and coverage["stores"]>=10,
                "Insufficient cycle/MMIO comparison coverage")
        info={"passed":True,"summary":summaries[0],"coverage":coverage,
              "netlist_compared":bool(netlist),"trace":relative(trace),"trace_sha256":sha(trace),
              "simulation_log":relative(build/f"{label}.log"),"compile_log":relative(build/f"compile_{label}.log")}
        results["runs"][label]=info
        print(summaries[0],flush=True)
        return info

    for variant in (0,1):
        simulate(variant)
    if not args.rtl_only:
        image=json.loads((root/"config/environment.lock.json").read_text())["container_image"]
        require("@sha256:" in image,"Synthesis image must be pinned by digest")
        docker=shutil.which("docker") or "/Applications/Docker.app/Contents/Resources/bin/docker"
        require(Path(docker).is_file(),"Docker CLI not found")
        inspect=runpy.run_path(str(root/"scripts/check_asic_memory_synthesis.py"))["inspect_hierarchy"]
        prefix=[docker,"run","--rm","--pull=never","--network=none","--platform","linux/arm64",
                "--user",f"{os.getuid()}:{os.getgid()}","--cpus","2","--memory","4g",
                "--mount",f"type=bind,src={root},dst=/work","--workdir","/work","--entrypoint","yosys",image]
        results["container_image"]=image
        results["abc_run"]=False
        required_nets={"core_rst_ni":1,"u_soc.per_req":1,"u_soc.data_we":1,
                       "u_soc.data_addr":32,"u_soc.data_be":4,"u_soc.data_wdata":32}
        for variant,suffix in ((0,"a"),(1,"b")):
            label=f"synthesis_{suffix}"
            script=build/f"{label}.ys"
            netlist=build/f"{label}.v"
            netjson=build/f"{label}.json"
            for path in (netlist,netjson):
                path.unlink(missing_ok=True)
            commands=["read_verilog -sv "+" ".join(sources),f"chparam -set MemoryVariant {variant} asic_top",
                      "hierarchy -check -top asic_top","flatten -noscopeinfo","synth -top asic_top -noabc",
                      "check -assert","rename asic_top netlist_top",f"write_json {relative(netjson)}",
                      f"write_verilog -noattr {relative(netlist)}"]
            script.write_text("\n".join(commands)+"\n")
            run(prefix+["-Q","-T","-s",relative(script)],label,timeout=600)
            data=json.loads(netjson.read_text())
            require(set(data["modules"])=={"netlist_top"},"Unexpected modules after flattening")
            hierarchy=inspect(data["modules"],"netlist_top")
            nets=data["modules"]["netlist_top"]["netnames"]
            for name,width in required_nets.items():
                require(name in nets and len(nets[name]["bits"])==width,
                        f"Required diagnostic net missing or changed: {name}")
            info={"passed":True,"variant":variant,"yosys_version":data["creator"],"hierarchy":hierarchy,
                  "diagnostic_nets_verified":required_nets,"netlist":relative(netlist),
                  "netlist_sha256":sha(netlist),"netlist_json":relative(netjson),"netlist_json_sha256":sha(netjson),
                  "script":relative(script),"script_sha256":sha(script),"log":relative(build/f"{label}.log")}
            results["runs"][label]=info
            print(f"PASS wait-only synthesis {suffix}: {hierarchy['generic_flip_flop_bits']} generic FF bits",flush=True)
            paired=simulate(variant,netlist)
            reference=results["runs"][f"rtl_{suffix}"]
            require(paired["coverage"]==reference["coverage"] and paired["trace_sha256"]==reference["trace_sha256"],
                    f"Standalone and paired runs differ: {suffix}")
            paired["identical_standalone_rtl_trace"]=True
            require(sha(netlist)==info["netlist_sha256"] and sha(netjson)==info["netlist_json_sha256"],
                    "Netlist changed during simulation")
        results["post_synthesis_game_equivalence"]=True
    require(all(sha(root/name)==digest for name,digest in input_hashes.items()),"An input changed during verification")
    results["all_passed"]=True
    results["log_sha256"]={p.name:sha(p) for p in sorted(build.glob("*.log"))}
    (build/"results.json").write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print("PASS wait-only A/B game "+("RTL checks only" if args.rtl_only else "RTL/netlist exact MMIO cycles and logical terminals; no PDK mapping or SDF"))


if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:
        raise SystemExit(f"Wait-only game check failed: {error}")
