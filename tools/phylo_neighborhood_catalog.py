#!/usr/bin/env python3
"""Split one EPA-ng placement run into reproducible species-neighborhood subruns.

The fixed reference package and every placement are preserved. Grouping changes only
which query placements are shown together. By default, owner-recorded closest-type
species are used and the inferred nearest reference is a typed fallback.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

AS_ID = re.compile(r"AS[-_](\d+)", re.I)
BINOMIAL = re.compile(r"^([A-Z][A-Za-z-]+)[ _]([a-z][a-z-]+)")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def strain_id(value: str) -> str:
    match = AS_ID.search(value or "")
    if not match:
        raise ValueError(f"QUERY_WITHOUT_AS_ID:{value}")
    return f"AS-{int(match.group(1))}"


def species_from_reference(value: str) -> str:
    match = BINOMIAL.match((value or "").replace("_", " ").strip())
    return " ".join(match.groups()) if match else ""


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def query_names(placement: dict) -> list[str]:
    names = list(placement.get("n") or [])
    if placement.get("nm"):
        names.extend(item[0] for item in placement["nm"])
    return names


def build_groups(required: Path, neighborhoods: Path, placements: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    owner: dict[str, set[str]] = defaultdict(set)
    for row in read_tsv(required):
        if row.get("strain") and row.get("reference_species"):
            owner[strain_id(row["strain"])].add(row["reference_species"].strip())
    nearest = {}
    for row in read_tsv(neighborhoods):
        nearest[strain_id(row.get("as_query", ""))] = species_from_reference(row.get("nearest_type_strain", ""))
    groups: dict[str, list[dict]] = defaultdict(list)
    ledger = []
    seen = set()
    for placement in placements:
        names = query_names(placement)
        if len(names) != 1:
            raise ValueError(f"PLACEMENT_QUERY_MULTIPLICITY:{names}")
        name = names[0]
        strain = strain_id(name)
        if strain in seen:
            raise ValueError(f"DUPLICATE_QUERY_PLACEMENT:{strain}")
        seen.add(strain)
        owner_species = sorted(owner.get(strain, set()))
        fallback = nearest.get(strain, "")
        species_values = owner_species or ([fallback] if fallback else [])
        if not species_values:
            raise ValueError(f"QUERY_WITHOUT_NEIGHBORHOOD_AUTHORITY:{strain}")
        for species in species_values:
            groups[species].append(placement)
            ledger.append({"species_neighborhood": species, "strain": strain, "query_tip": name,
                           "grouping_authority": "owner_closest_type" if owner_species else "inferred_nearest_reference"})
    return groups, ledger


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--required-reference-table", required=True, type=Path)
    parser.add_argument("--neighborhood-table", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--species", action="append", default=[], help="Exact species neighborhood to emit; repeatable")
    parser.add_argument("--max-groups", type=int, default=0, help="Deterministic alphabetical cap; 0 emits all")
    parser.add_argument("--run-reports", action="store_true", help="Run phylo_place.py report for each filtered jplace")
    parser.add_argument("--materialize-refpkg", action="store_true", help="Copy each refpkg instead of using a relative symlink")
    args = parser.parse_args(argv)

    run = args.run_dir.resolve()
    source_jplace = run / "place/epa_result.jplace"
    neighborhoods = args.neighborhood_table or run / "report/streptomyces_neighborhoods.tsv"
    for path in (source_jplace, neighborhoods, args.required_reference_table, run / "refpkg"):
        if not path.exists():
            raise SystemExit(f"REQUIRED_INPUT_MISSING:{path}")
    if args.out.exists():
        raise SystemExit(f"OUTPUT_EXISTS:{args.out}")
    payload = json.loads(source_jplace.read_text(encoding="utf-8"))
    groups, ledger = build_groups(args.required_reference_table, neighborhoods, payload["placements"])
    selected = sorted(groups)
    if args.species:
        missing = sorted(set(args.species) - set(groups))
        if missing:
            raise SystemExit("REQUESTED_SPECIES_NOT_FOUND:" + ",".join(missing))
        selected = sorted(set(args.species))
    if args.max_groups:
        selected = selected[:args.max_groups]
    args.out.mkdir(parents=True)
    output_rows = []
    for index, species in enumerate(selected, 1):
        folder = args.out / f"{index:03d}_{slug(species)}"
        (folder / "place").mkdir(parents=True)
        target_refpkg = folder / "refpkg"
        if args.materialize_refpkg:
            shutil.copytree(run / "refpkg", target_refpkg)
        else:
            target_refpkg.symlink_to(os.path.relpath(run / "refpkg", folder), target_is_directory=True)
        subset = dict(payload)
        subset["placements"] = groups[species]
        target_jplace = folder / "place/epa_result.jplace"
        target_jplace.write_text(json.dumps(subset, separators=(",", ":")) + "\n", encoding="utf-8")
        if args.run_reports:
            env = dict(os.environ)
            command = [sys.executable, str(Path(__file__).with_name("phylo_place.py")), "report", "--refpkg", str(target_refpkg), "--jplace", str(target_jplace), "--outdir", str(folder / "report")]
            subprocess.run(command, check=True, env=env)
        strains = sorted({strain_id(query_names(item)[0]) for item in groups[species]}, key=lambda x: int(x.split("-")[1]))
        output_rows.append({"neighborhood_id": folder.name, "species_neighborhood": species, "query_count": str(len(strains)), "strains": ";".join(strains), "grouping_changes_inference": "NO"})
    with (args.out / "NEIGHBORHOOD_CATALOG.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=output_rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(output_rows)
    selected_set = set(selected)
    with (args.out / "QUERY_GROUPING_LEDGER.tsv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["species_neighborhood", "strain", "query_tip", "grouping_authority"]
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(row for row in ledger if row["species_neighborhood"] in selected_set)
    receipt = {"schema": "sapote.phylo-neighborhood-catalog.v1", "status": "PASS", "source_run": str(run),
               "source_jplace_sha256": digest(source_jplace), "group_count": len(output_rows),
               "query_grouping_rows": sum(len(groups[s]) for s in selected), "fixed_reference_inference_reused": True,
               "grouping_changes_inference": False, "refpkg_mode": "materialized" if args.materialize_refpkg else "relative_symlink"}
    (args.out / "BUILD_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(receipt, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
