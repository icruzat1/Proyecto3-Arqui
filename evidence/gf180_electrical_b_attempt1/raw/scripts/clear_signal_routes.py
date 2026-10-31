#!/usr/bin/env python3
"""Remove regular non-supply dbWire routes, with preservation checks.

Run inside the pinned LibreLane container, for example:
  openroad -exit -python clear_signal_routes.py --input-odb source.odb \
    --output-dir fresh-directory --source-state state_out.json --clear-guides

The source is read-only. Only dbWire is destroyed, never dbNet/dbInst/dbSWire.
Output is a derived placement database, NOT a routed or signoff result.
Fresh global routing, detailed routing, extraction and STA must follow.
This helper does not modify a LibreLane state; the caller must invalidate old
SPEF/SDF, routing guides and carried metrics when deriving its new state.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile


SUPPLY_TYPES = {"POWER", "GROUND"}


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def require(condition, explanation):
    if not condition:
        raise RuntimeError(explanation)


def artifact(path):
    path = Path(path).resolve()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def wire_signature(wire):
    if wire is None:
        return None
    return {"length_dbu": int(wire.getLength())}


def snapshot(block):
    """Include unconnected terminals as well as every net's connected terminals."""
    nets = []
    regular = []
    special = []
    guides = []
    instances = []
    ports = []
    types = Counter()
    master_counts = Counter()
    net_types = {}
    iterm_count = 0
    for inst in block.getInsts():
        terminals = []
        for iterm in inst.getITerms():
            iterm_count += 1
            net = iterm.getNet()
            terminals.append([iterm.getMTerm().getName(), net.getName() if net else None])
        master = inst.getMaster().getName()
        master_counts[master] += 1
        instances.append([inst.getName(), master, list(inst.getLocation()),
                          str(inst.getOrient()), str(inst.getPlacementStatus()),
                          sorted(terminals)])
    for term in block.getBTerms():
        net = term.getNet()
        ports.append([term.getName(), str(term.getIoType()), str(term.getSigType()),
                      net.getName() if net else None])
    for net in block.getNets():
        name, sigtype = net.getName(), str(net.getSigType())
        net_types[name] = sigtype
        types[sigtype] += 1
        nets.append([name, sigtype, bool(net.isSpecial()),
                     sorted([[t.getInst().getName(), t.getMTerm().getName()]
                             for t in net.getITerms()]),
                     sorted(t.getName() for t in net.getBTerms())])
        wire = net.getWire()
        if wire is not None:
            regular.append([name, sigtype, wire_signature(wire)])
        for swire in net.getSWires():
            # Full special-wire geometry is additionally checked through DEF.
            special.append([name, str(swire.getWireType()),
                            sorted(str(box.getWireShapeType()) for box in swire.getWires())])
        guides.append([name, len(list(net.getGuides()))])
    connectivity = {"nets": sorted(nets), "ports": sorted(ports),
                    "instances": sorted(instances)}
    supplies = sorted(row for row in regular if row[1] in SUPPLY_TYPES)
    invariant = {
        "block": block.getName(),
        "connectivity_and_components_sha256": digest_bytes(json_bytes(connectivity)),
        "special_wire_objects_sha256": digest_bytes(json_bytes(sorted(special))),
        "supply_regular_wires_sha256": digest_bytes(json_bytes(supplies)),
        "nets": len(nets), "net_types": dict(sorted(types.items())),
        "instances": len(instances), "iterms": iterm_count, "ports": len(ports),
        "instance_master_counts": dict(sorted(master_counts.items())),
        "special_wires": len(special),
        "special_wire_shapes": sum(len(row[2]) for row in special),
        "supply_regular_wires": len(supplies),
    }
    return {
        "invariants": invariant,
        "regular_wire_count": len(regular),
        "non_supply_regular_wire_count": sum(row[1] not in SUPPLY_TYPES for row in regular),
        "regular_wires_by_type": dict(sorted(Counter(row[1] for row in regular).items())),
        "regular_wires_sha256": digest_bytes(json_bytes(sorted(regular))),
        "guide_count": sum(row[1] for row in guides),
        "supply_guide_count": sum(row[1] for row in guides
                                  if net_types[row[0]] in SUPPLY_TYPES),
        "guides_by_net_sha256": digest_bytes(json_bytes(sorted(guides))),
    }


def def_preservation(path):
    """Check every DEF byte outside NETS, including full SPECIALNETS geometry."""
    data = Path(path).read_bytes()
    match = re.search(rb"(?m)^NETS\s+\d+\s*;\r?\n.*?^END NETS\s*$", data, re.S)
    require(match is not None, f"No unique NETS section in {path}")
    require(len(re.findall(rb"(?m)^NETS\s+\d+\s*;", data)) == 1,
            "Multiple NETS sections are unsupported")
    net_section = match.group()
    # Capture each full NETS entry; preserve any POWER/GROUND regular route too.
    entries = re.findall(rb"(?ms)^\s*-\s+.*?(?=^\s*-\s+|^END NETS\s*$)", net_section)
    supplies = [entry for entry in entries
                if re.search(rb"\+\s+USE\s+(?:POWER|GROUND)\b", entry)]
    return {
        "outside_nets_sha256": digest_bytes(data[:match.start()] + data[match.end():]),
        "supply_net_entries_sha256": digest_bytes(b"".join(supplies)),
        "supply_net_entries": len(supplies),
    }


def load_design(path):
    from openroad import Tech, Design
    tech = Tech()
    design = Design(tech)
    design.readDb(str(path))
    chip = tech.getDB().getChip()
    require(chip is not None and chip.getBlock() is not None, "Input has no design block")
    return tech, design, chip.getBlock()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-odb", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-state", type=Path)
    parser.add_argument("--provenance-file", type=Path, action="append", default=[])
    parser.add_argument("--clear-guides", action="store_true",
                        help="Also clear non-supply guides; mandatory full GRT follows.")
    args = parser.parse_args()
    source = args.input_odb.resolve(strict=True)
    inputs = [source, Path(__file__).resolve(), *args.provenance_file]
    if args.source_state:
        state_path = args.source_state.resolve(strict=True)
        state = json.loads(state_path.read_text())
        require(isinstance(state.get("odb"), str), "Source state must name one odb")
        state_odb = Path(state["odb"])
        if not state_odb.is_absolute():
            state_odb = state_path.parent / state_odb
        require(state_odb.resolve() == source, "Source state's odb differs from --input-odb")
        inputs.append(state_path)
    input_records = [artifact(path) for path in inputs]
    destination = args.output_dir.resolve()
    require(not destination.exists(), "Output directory must be fresh; no overwrite allowed")
    destination.mkdir(parents=True)
    manifest_path = destination / "manifest.json"
    manifest = {
        "schema_version": 1, "status": "running",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv, "inputs": input_records,
        "operation": "destroy non-POWER/GROUND regular dbWire objects only",
        "clear_non_supply_guides": args.clear_guides,
        "limitations": ["No routing, LVS, timing, DRC or functional signoff is asserted.",
                        "Caller must regenerate global/detailed routes, RCX and STA.",
                        "Caller must drop stale state SPEF/SDF/guides and carried metrics."],
    }
    try:
        import odb
        require(hasattr(odb, "dbWire") and callable(getattr(odb.dbWire, "destroy", None)),
                "This OpenDB binding does not expose dbWire.destroy; nothing was changed")
        manifest["wire_destroy_api"] = "odb.dbWire.destroy"
        tech, design, block = load_design(source)
        nets = list(block.getNets())
        require(nets, "Input block has no nets")
        require(all(hasattr(net, "getGuides") for net in nets), "getGuides API unavailable")
        if args.clear_guides:
            require(all(callable(getattr(net, "clearGuides", None)) for net in nets),
                    "clearGuides API unavailable; nothing was changed")
        before = snapshot(block)
        manifest["before"] = before
        require(before["non_supply_regular_wire_count"] > 0,
                "Input has no non-supply regular routes; refuse an accidental no-op")
        removed = []
        with tempfile.TemporaryDirectory(prefix=".validate-", dir=destination) as tmp:
            tmp = Path(tmp)
            before_def = tmp / "before.def"
            after_def = tmp / "after.def"
            output_odb = tmp / "derived.odb"
            roundtrip_def = tmp / "derived.def"
            design.writeDef(str(before_def))
            before_geometry = def_preservation(before_def)
            for net in nets:
                sigtype = str(net.getSigType())
                if sigtype in SUPPLY_TYPES:
                    continue
                wire = net.getWire()
                if wire is not None:
                    removed.append({"net": net.getName(), "signal_type": sigtype,
                                    **wire_signature(wire)})
                    odb.dbWire.destroy(wire)
                    require(net.getWire() is None,
                            f"Wire still attached after destroy: {net.getName()}")
                if args.clear_guides:
                    net.clearGuides()
            after = snapshot(block)
            manifest["after"] = after
            require(before["invariants"] == after["invariants"],
                    "Connectivity, components, supply wires or special wires changed")
            require(after["non_supply_regular_wire_count"] == 0, "Signal routes remain")
            if args.clear_guides:
                require(after["guide_count"] == after["supply_guide_count"],
                        "Non-supply guides remain")
            else:
                require(before["guides_by_net_sha256"] == after["guides_by_net_sha256"],
                        "Guides changed unexpectedly")
            design.writeDef(str(after_def))
            after_geometry = def_preservation(after_def)
            require(before_geometry == after_geometry,
                    "DEF outside NETS or regular POWER/GROUND entries changed")
            design.writeDb(str(output_odb))
            roundtrip_tech, roundtrip_design, roundtrip_block = load_design(output_odb)
            roundtrip = snapshot(roundtrip_block)
            require(roundtrip == after, "Serialized ODB changed on re-read")
            roundtrip_design.writeDef(str(roundtrip_def))
            require(sha256(after_def) == sha256(roundtrip_def),
                    "Exported DEF is not identical to DEF from re-read output ODB")
            for record in input_records:
                require(sha256(record["path"]) == record["sha256"],
                        f"Source input changed during operation: {record['path']}")
            final_odb = destination / f"{block.getName()}.odb"
            final_def = destination / f"{block.getName()}.def"
            output_odb.rename(final_odb)
            roundtrip_def.rename(final_def)
        removed_file = destination / "removed_regular_wires.json.gz"
        with gzip.GzipFile(filename=str(removed_file), mode="wb", mtime=0) as stream:
            stream.write(json_bytes(sorted(removed, key=lambda item: item["net"])))
        manifest.update({
            "status": "verified", "removed_regular_wires": len(removed),
            "def_preservation": {"before": before_geometry, "after": after_geometry},
            "roundtrip_snapshot_sha256": digest_bytes(json_bytes(roundtrip)),
            "input_hashes_unchanged": True,
            "outputs": [artifact(final_odb), artifact(final_def), artifact(removed_file)],
        })
    except Exception as exc:
        manifest.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        raise
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": manifest["status"], "manifest": str(manifest_path),
                      "removed_regular_wires": manifest["removed_regular_wires"],
                      "preserved_special_wires": before["invariants"]["special_wires"],
                      "preserved_instances": before["invariants"]["instances"]}, indent=2))


if __name__ == "__main__":
    main()
