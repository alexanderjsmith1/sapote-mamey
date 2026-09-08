#!/usr/bin/env python3
"""Build a package-native KS-burden TSV and hash-bound receipt.

Counts exact ``PKS_KS`` antiSMASH module rows and the separately reported
orphan/fragment KS count. KS count is capacity context: it is not module count,
chain length, pathway completeness, product identity, or activity.
"""
from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.assembly import assembly_tier, corrected_bgc_count  # noqa: E402

SCHEMA = "sapote-ks-burden-table-v1"
CLAIM_CEILING = (
    "KS counts are biosynthetic-capacity context only; KS count is not module count, "
    "chain length, pathway completeness, product identity, production, activity, or novelty."
)
FIELDS = (
    "strain", "raw_bgc_count", "interior_bgc_count", "edge_bgc_count",
    "full_contig_bgc_count", "corrected_bgc_count", "interior_pct",
    "bgc_inventory_tier", "mapped_pks_ks", "orphan_fragment_pks_ks",
    "total_pks_ks_burden", "claim_ceiling",
)


class KSBurdenHold(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _one(package: Path, pattern: str, label: str) -> Path:
    matches = sorted(package.glob(pattern))
    if len(matches) != 1:
        raise KSBurdenHold("KS_SOURCE_BINDING_HOLD", f"{label}: expected one {pattern}, found {len(matches)}")
    return matches[0]


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def package_row(package_dir: str | Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    package = Path(package_dir)
    inventory = _one(package, "*_2_inventory.csv", "inventory")
    modules = _one(package, "*_3_antismash_modules.csv", "antiSMASH modules")
    fragments = _one(package, "*_4B_pks_ks_fragment_scan.csv", "KS fragment scan")
    intake = _one(package, "*_1_intake.json", "intake")
    try:
        intake_data = json.loads(intake.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KSBurdenHold("KS_SOURCE_BINDING_HOLD", f"intake JSON unreadable: {exc}") from exc
    strain = str(intake_data.get("strain_id") or "").strip()
    if not strain:
        raise KSBurdenHold("KS_SOURCE_BINDING_HOLD", "intake strain_id is required")

    inventory_rows = _rows(inventory)
    boundaries = [str(row.get("Boundary") or "").strip().lower() for row in inventory_rows]
    interior = boundaries.count("interior")
    edge = boundaries.count("edge")
    full = boundaries.count("full-contig") + boundaries.count("full_contig")
    raw = len(inventory_rows)
    interior_pct = round(100.0 * interior / raw, 1) if raw else None

    module_rows = _rows(modules)
    ks_rows = [row for row in module_rows if str(row.get("domain") or "").strip() == "PKS_KS"]
    row_ids = [str(row.get("row_id") or "").strip() for row in ks_rows]
    if any(not value for value in row_ids) or len(row_ids) != len(set(row_ids)):
        raise KSBurdenHold("KS_MODULE_ROW_ID_HOLD", "PKS_KS rows require unique nonblank row_id values")

    orphan_count = 0
    for number, row in enumerate(_rows(fragments), 2):
        raw_count = str(row.get("n_ks") or "").strip()
        try:
            value = int(raw_count)
        except ValueError as exc:
            raise KSBurdenHold("KS_FRAGMENT_COUNT_HOLD", f"fragment row {number}: invalid n_ks") from exc
        if value < 0:
            raise KSBurdenHold("KS_FRAGMENT_COUNT_HOLD", f"fragment row {number}: negative n_ks")
        orphan_count += value

    result: dict[str, object] = {
        "strain": strain,
        "raw_bgc_count": raw,
        "interior_bgc_count": interior,
        "edge_bgc_count": edge,
        "full_contig_bgc_count": full,
        "corrected_bgc_count": corrected_bgc_count(interior, edge, full),
        "interior_pct": interior_pct if interior_pct is not None else "",
        "bgc_inventory_tier": assembly_tier(interior_pct),
        "mapped_pks_ks": len(ks_rows),
        "orphan_fragment_pks_ks": orphan_count,
        "total_pks_ks_burden": len(ks_rows) + orphan_count,
        "claim_ceiling": CLAIM_CEILING,
    }
    sources = [
        {"logical_locator": path.name, "sha256": _sha(path), "bytes": path.stat().st_size}
        for path in (intake, inventory, modules, fragments)
    ]
    return result, sources


def build(package_dirs: list[str | Path], out_path: str | Path, receipt_path: str | Path) -> dict[str, object]:
    if not package_dirs:
        raise KSBurdenHold("KS_PACKAGE_HOLD", "at least one package directory is required")
    rows: list[dict[str, object]] = []
    packages: list[dict[str, object]] = []
    seen: set[str] = set()
    for package in package_dirs:
        row, sources = package_row(package)
        strain = str(row["strain"])
        if strain in seen:
            raise KSBurdenHold("KS_DUPLICATE_STRAIN_HOLD", "each strain may appear once")
        seen.add(strain)
        rows.append(row)
        packages.append({"strain": strain, "sources": sources})
    rows.sort(key=lambda row: str(row["strain"]))
    packages.sort(key=lambda row: str(row["strain"]))

    out = Path(out_path)
    receipt = Path(receipt_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "status": "PASS",
        "row_count": len(rows),
        "output": {"logical_locator": out.name, "sha256": _sha(out), "bytes": out.stat().st_size},
        "packages": packages,
        "ks_count_contract": "mapped exact domain=PKS_KS rows + sum of fragment-scan n_ks",
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("packages", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.packages, args.out, args.receipt)
    except KSBurdenHold as exc:
        sys.stderr.write(json.dumps({"status": "HOLD", "code": exc.code, "detail": str(exc)}) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
