#!/usr/bin/env python3
"""Emit a line-addressable census of registry-backed and inline scan markers.

The report is deliberately static: it distinguishes biological-detection
markers from parser grammar so an accession or antiSMASH-file-name regex is
not mistaken for an unwired marker definition.
"""
from __future__ import annotations

import argparse
import ast
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "mamey" / "source_scans.py"
REGISTRY = ROOT / "registry_inventory_v1.9.4.json"
REGISTRY_BACKED = {
    "DOMAIN_CLASS_PATTERNS", "CHITINASE_PATTERNS", "REGULATOR_PATTERNS",
    "TRANSPORTER_PATTERNS", "RESISTANCE_PATTERNS", "CCTT_PATTERNS",
    "FLBR_PATTERNS", "CASSETTE_PATTERNS", "UMED_PATTERNS", "TFBS_MOTIFS",
}
INLINE_SOURCE = {
    "PRIMARY_METABOLISM_PATTERNS", "VETO_CONTEXT_PATTERNS", "MOBILE_ELEMENT_PATTERNS",
    "_KS_ACTIVE_SITE", "_AT_ACTIVE_SITE", "QS_PRODUCT_LABELS", "QS_CDS_PATTERNS",
    "GLYCOSYLATED_COMPOUND_KEYWORDS", "_AMINOGLYCOSIDE_ANCHOR", "_DOIS_GENE",
    "_POLYENE_ANCHOR", "_ENEDIYNE_SPECIFIC", "_ENEDIYNE_GENERIC", "_PREV001_SIGNAL",
    "_KCB_CLASS_COMPAT",
}


def _name(node: ast.stmt) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _string_count(node: ast.AST | None) -> int:
    return sum(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in ast.walk(node)) if node else 0


def _preview(node: ast.AST | None) -> str:
    if node is None:
        return ""
    rendered = ast.unparse(node).replace("\n", " ")
    return rendered[:300]


def _row(**kwargs: Any) -> dict[str, Any]:
    return {
        "module": kwargs["module"], "line": kwargs["line"], "scan": kwargs["scan"],
        "marker_id": kwargs["marker_id"], "marker_kind": kwargs["marker_kind"],
        "literal_count": kwargs["literal_count"], "registry_status": kwargs["registry_status"],
        "registry_library": kwargs.get("registry_library", ""),
        "phase1_execution": kwargs["phase1_execution"], "definition_preview": kwargs["definition_preview"],
    }


def source_rows() -> list[dict[str, Any]]:
    parsed = ast.parse(SOURCE.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for node in parsed.body:
        name = _name(node)
        value = getattr(node, "value", None)
        if name in REGISTRY_BACKED and isinstance(value, ast.Dict):
            library = "mamey_" + {
                "DOMAIN_CLASS_PATTERNS": "domain_class", "CHITINASE_PATTERNS": "chitin_glycan",
                "REGULATOR_PATTERNS": "regulator", "TRANSPORTER_PATTERNS": "transporter",
                "RESISTANCE_PATTERNS": "resistance", "CCTT_PATTERNS": "cctt", "FLBR_PATTERNS": "flbr",
                "CASSETTE_PATTERNS": "cassette", "UMED_PATTERNS": "umed", "TFBS_MOTIFS": "tfbs",
            }[name]
            for key, item in zip(value.keys, value.values):
                marker = key.value if isinstance(key, ast.Constant) else ast.unparse(key)
                rows.append(_row(module="mamey/source_scans.py", line=key.lineno, scan=name,
                    marker_id=marker, marker_kind="regex_or_motif", literal_count=_string_count(item),
                    registry_status="BOTH", registry_library=library,
                    phase1_execution="registry overlay; literal fallback; exact parity asserted",
                    definition_preview=_preview(item)))
        elif name in INLINE_SOURCE:
            rows.append(_row(module="mamey/source_scans.py", line=node.lineno, scan=name,
                marker_id=name, marker_kind="inline_marker_or_guard", literal_count=_string_count(value),
                registry_status="INLINE_ONLY", phase1_execution="hardcoded source_scans execution",
                definition_preview=_preview(value)))
    return rows


def extra_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative, names, scan in (
        ("mamey/scoring.py", {"AB_KEYWORDS", "AF_KEYWORDS", "NOVELTY_KEYWORDS"}, "scoring keyword map"),
        ("mamey/antismash_evidence.py", {"_KCB_PKSNRPS_RE", "_KCB_RIPP_RE", "_SEC_MET_RE"}, "antiSMASH evidence classification"),
    ):
        parsed = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in parsed.body:
            name = _name(node)
            if name not in names:
                continue
            value = getattr(node, "value", None)
            rows.append(_row(module=relative, line=node.lineno, scan=scan, marker_id=name,
                marker_kind="inline_keyword_or_regex", literal_count=_string_count(value),
                registry_status="INLINE_ONLY", phase1_execution="hardcoded module execution",
                definition_preview=_preview(value)))
    # These are intentionally documented exclusions, not biological markers.
    rows.append(_row(module="mamey/rggmci.py", line=407, scan="ClusterBlast parser", marker_id="ACCESSION_RE",
        marker_kind="parser_grammar_not_detection_marker", literal_count=1, registry_status="NOT_MARKER",
        phase1_execution="parses accession syntax only", definition_preview="compiled accession grammar"))
    return rows


def registry_only_rows() -> list[dict[str, Any]]:
    inventory = json.loads(REGISTRY.read_text(encoding="utf-8"))
    mamey_libraries = {"mamey_" + suffix for suffix in (
        "domain_class", "chitin_glycan", "regulator", "transporter", "resistance", "cctt", "flbr", "cassette", "umed", "tfbs"
    )}
    rows = []
    for entry in inventory:
        types = {target.get("type") for target in entry.get("targets", [])}
        if entry.get("library") in mamey_libraries and types & {"regex", "motif"}:
            continue
        rows.append(_row(module="registry_inventory_v1.9.4.json", line="", scan=entry.get("library", ""),
            marker_id=entry.get("id", ""), marker_kind="registry_entry", literal_count=sum(
                isinstance(target.get("value"), str) for target in entry.get("targets", [])
            ), registry_status="IN_REGISTRY_ONLY", registry_library=entry.get("library", ""),
            phase1_execution="inactive Phase-2/manual or Sapote-owned registry entry",
            definition_preview=json.dumps(entry.get("targets", []), sort_keys=True)[:300]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    rows = source_rows() + extra_rows() + registry_only_rows()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, delimiter="\t", fieldnames=list(_row(module="", line="", scan="", marker_id="", marker_kind="", literal_count=0, registry_status="", phase1_execution="", definition_preview="")))
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
