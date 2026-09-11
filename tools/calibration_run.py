#!/usr/bin/env python3
"""Run the portable Sapote-Mamey detector calibration panel.

Synthetic controls execute current detector owners. Reference-library and
external-target rows remain provenance-bound controls; external inputs are
explicitly gated rather than silently treated as tested.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

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
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.models import BGCRecord, CDSFeature
from mamey.rggmci import compute_rggmci
from mamey.source_scans import (
    CASSETTE_PATTERNS,
    CCTT_PATTERNS,
    CHITINASE_PATTERNS,
    RESISTANCE_PATTERNS,
    TFBS_MOTIFS,
    UMED_PATTERNS,
    motif_to_regex,
    scan_blda_tta,
)

DEFAULT_PANEL = ROOT / "mamey" / "data" / "calibration_panel.json"
DEFAULT_BASELINE = ROOT / "mamey" / "data" / "calibration_baseline.json"
REFERENCE_LIBRARY = ROOT / "mamey" / "data" / "reference_bgc_library.json"
SCANS = ("cctt", "cgad", "resistance", "tfbs", "umed", "blda_tta", "cassettes", "rggmci")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pattern_call(text: str, patterns: dict[str, list[str]], expected: str) -> bool:
    return expected in {
        family for family, regexes in patterns.items()
        if any(re.search(regex, text, re.IGNORECASE) for regex in regexes)
    }


def _rggmci_positive() -> bool:
    bgcs = [
        BGCRecord("CAL-BGC-RGA", "synthetic_rg_a", 1, 1, 10000, 10000, products=["lanthipeptide"]),
        BGCRecord("CAL-BGC-RGB", "synthetic_rg_b", 1, 1, 10000, 10000, products=["lanthipeptide"]),
    ]
    records = []
    for bgc_id, contig, start, end in (
        ("CAL-BGC-RGA", "synthetic_rg_a", 100, 500),
        ("CAL-BGC-RGB", "synthetic_rg_b", 450, 900),
    ):
        records.append({
            "bgc_id": bgc_id, "contig": contig, "region_number": 1,
            "region_key": f"{contig}.region001", "ref": "BGC0000001",
            "source": "synthetic", "reference_type": "lanthipeptide", "rank": 1,
            "nprot": 8, "cumulative_score": 100.0, "mean_identity": 80.0,
            "interval_start": start, "interval_end": end, "source_file": "synthetic",
            "subjects": ("syn_001", "syn_002", "syn_003"), "db_kind": "knownclusterblast",
        })
    return compute_rggmci(bgcs, {"reference_records": records, "reference_record_count": 2}).get("pairs_total", 0) > 0


def evaluate_case(case: dict[str, Any]) -> bool:
    scan, text, expected = case["scan"], case["input"], case["expected_call"]
    if scan == "cctt":
        return _pattern_call(text, CCTT_PATTERNS, expected) if expected != "NO_CALL" else not any(_pattern_call(text, CCTT_PATTERNS, key) for key in CCTT_PATTERNS)
    if scan == "cgad":
        return _pattern_call(text, CHITINASE_PATTERNS, expected) if expected != "NO_CALL" else not any(_pattern_call(text, CHITINASE_PATTERNS, key) for key in CHITINASE_PATTERNS)
    if scan == "resistance":
        return _pattern_call(text, RESISTANCE_PATTERNS, expected) if expected != "NO_CALL" else not any(_pattern_call(text, RESISTANCE_PATTERNS, key) for key in RESISTANCE_PATTERNS)
    if scan == "umed":
        return _pattern_call(text, UMED_PATTERNS, expected) if expected != "NO_CALL" else not any(_pattern_call(text, UMED_PATTERNS, key) for key in UMED_PATTERNS)
    if scan == "cassettes":
        return _pattern_call(text, CASSETTE_PATTERNS, expected) if expected != "NO_CALL" else not any(_pattern_call(text, CASSETTE_PATTERNS, key) for key in CASSETTE_PATTERNS)
    if scan == "tfbs":
        calls = {name for name, motifs in TFBS_MOTIFS.items() if any(re.search(motif_to_regex(m), text.upper()) for m in motifs)}
        return expected in calls if expected != "NO_CALL" else not calls
    if scan == "blda_tta":
        bgc = BGCRecord("CAL-BGC-BLDA", "synthetic_blda", 1, 1, max(9, len(text)), max(9, len(text)))
        cds = CDSFeature("synthetic_blda", 1, max(9, len(text)), 1, "CAL_CDS_001", "synthetic", nucleotide_seq=text)
        row = scan_blda_tta([cds], [bgc], organism="Streptomyces sp.")["per_bgc"][bgc.bgc_id]
        positive = row["tta_codons"] > 0
        return positive if expected == "TTA_PRESENT" else not positive
    if scan == "rggmci":
        positive = _rggmci_positive() if text == "shared_reference_pair" else False
        return positive if expected == "PAIR_PRESENT" else not positive
    raise ValueError(f"unknown calibration scan: {scan}")


def _display(identity: dict[str, str]) -> str:
    required = ("strain", "full_node_or_contig", "region", "bgc_alias")
    if any(not identity.get(key) for key in required):
        raise ValueError("calibration identity is incomplete")
    return " / ".join(identity[key] for key in required)


def _portable_locator(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"external:{path.name}"


def run(panel_path: Path, baseline_path: Path, live_input_root: Path | None = None) -> dict[str, Any]:
    panel = json.loads(panel_path.read_text())
    baseline = json.loads(baseline_path.read_text())
    panel_hash = _sha256(panel_path)
    if baseline.get("panel_sha256") != panel_hash:
        raise ValueError("calibration baseline is not bound to this panel hash")
    expected_hash = panel["sources"]["reference_bgc_library.json"]["sha256"]
    if _sha256(REFERENCE_LIBRARY) != expected_hash:
        raise ValueError("reference_bgc_library.json hash differs from calibration panel binding")

    current_calls: dict[str, bool] = {}
    rows = []
    per_scan: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    flips = []
    for case in panel["synthetic_cases"]:
        matched_expectation = evaluate_case(case)
        observed_positive = bool(case["expected_positive"]) if matched_expectation else not bool(case["expected_positive"])
        current_calls[case["case_id"]] = observed_positive
        expected_positive = bool(case["expected_positive"])
        bucket = "tp" if observed_positive and expected_positive else "fp" if observed_positive else "fn" if expected_positive else "tn"
        per_scan[case["scan"]][bucket] += 1
        identity_display = _display(case["identity"])
        rows.append({"case_id": case["case_id"], "scan": case["scan"], "identity": case["identity"], "identity_display": identity_display, "expected_positive": expected_positive, "observed_positive": observed_positive})
        old = baseline["calls"].get(case["case_id"])
        if old is not None and bool(old) != observed_positive:
            flips.append({"case_id": case["case_id"], "scan": case["scan"], "identity": case["identity"], "identity_display": identity_display, "baseline_positive": bool(old), "current_positive": observed_positive})

    metrics = {}
    recall_drops = []
    precision_drops = []
    for scan in SCANS:
        counts = per_scan[scan]
        recall = counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else None
        precision = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else None
        metrics[scan] = {**counts, "recall": recall, "precision": precision}
        prior = baseline["per_scan"][scan]["recall"]
        if recall is not None and recall < prior:
            recall_drops.append({"scan": scan, "baseline_recall": prior, "current_recall": recall})
        prior_precision = baseline["per_scan"][scan]["precision"]
        if precision is not None and precision < prior_precision:
            precision_drops.append({"scan": scan, "baseline_precision": prior_precision,
                                    "current_precision": precision})

    live = {"status": "LIVE_INPUTS_NOT_REQUESTED", "targets_total": len(panel["live_targets"]), "verified": 0, "missing": []}
    if live_input_root is not None:
        root = live_input_root.resolve()
        for target in panel["live_targets"]:
            candidate = (root / target["region_member"]).resolve()
            if candidate != root and root not in candidate.parents:
                raise ValueError(f"live target escapes input root: {target['target_id']}")
            if not candidate.is_file() or _sha256(candidate) != target["region_member_sha256"]:
                live["missing"].append({"target_id": target["target_id"], "identity_display": _display(target), "region_member": target["region_member"]})
            else:
                live["verified"] += 1
        live["status"] = "LIVE_INPUTS_HASH_VERIFIED" if not live["missing"] else "LIVE_INPUTS_ABSENT_SKIP"

    status = "FAIL_CALL_FLIP" if flips else "PASS"
    return {
        "schema_version": "mamey_calibration_drift_v1", "status": status,
        "panel_path": _portable_locator(panel_path), "panel_sha256": panel_hash,
        "baseline_path": _portable_locator(baseline_path), "baseline_sha256": _sha256(baseline_path),
        "synthetic_cases": len(rows), "reference_controls": len(panel["reference_controls"]),
        "external_targets": len(panel["live_targets"]), "per_scan": metrics,
        "flipped_calls": flips, "recall_drops": recall_drops,
        "precision_drops": precision_drops, "case_results": rows,
        "executed_denominator": {"synthetic_executed": len(rows),
                                 "reference_controls_unexercisable": len(panel["reference_controls"]),
                                 "live_targets_unexecuted": len(panel["live_targets"])},
        "live_panel": live,
        "claim_safety": "Calibration measures deterministic detector behavior. It does not validate BGC identity, activity, expression, or physical contig linkage.",
    }


REFERENCE_FIELDS = [
    "control_number", "mibig_accession", "compound", "reference_class",
    "expected_class_triggers", "class_trigger_observed", "class_trigger_result",
    "expected_standing_rule", "standing_rule_observed", "standing_rule_result",
    "expected_rggmci_linkage", "rggmci_observed", "rggmci_result",
    "overall_status", "miss_classification", "evidence_reason",
]


def reference_control_rows() -> list[dict[str, str]]:
    """Account for every reference-library control without inventing an input binding.

    The library carries expected metadata, not runnable antiSMASH region inputs. A
    detector hit, standing-rule call, or physical split linkage therefore cannot be
    observed for an individual reference record in the shipped tree.
    """
    library = json.loads(REFERENCE_LIBRARY.read_text(encoding="utf-8"))
    rows = []
    for index, reference in enumerate(library.get("entries", []), start=1):
        expected = ";".join(reference.get("expected_marker_set") or []) or "NONE_DECLARED"
        rows.append({
            "control_number": str(index),
            "mibig_accession": str(reference.get("mibig_accession") or "MISSING"),
            "compound": str(reference.get("compound") or "MISSING"),
            "reference_class": str(reference.get("class") or "MISSING"),
            "expected_class_triggers": expected,
            "class_trigger_observed": "NOT_OBSERVED",
            "class_trigger_result": "NOT_EXERCISABLE",
            "expected_standing_rule": "NONE_DECLARED_IN_REFERENCE_RECORD",
            "standing_rule_observed": "NOT_OBSERVED",
            "standing_rule_result": "NOT_EXERCISABLE",
            "expected_rggmci_linkage": "NOT_APPLICABLE_NO_SPLIT_FIXTURE",
            "rggmci_observed": "NOT_OBSERVED",
            "rggmci_result": "NOT_EXERCISABLE",
            "overall_status": "NOT_EXERCISABLE",
            "miss_classification": "FIXTURE_DEFECT_MISSING_RUNNABLE_BINDING",
            "evidence_reason": "reference metadata has no hash-bound antiSMASH region fixture; similarity metadata is not a detector observation",
        })
    return rows


def write_reference_control_tsv(path: Path) -> Path:
    rows = reference_control_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=REFERENCE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_synthetic_tsv(path: Path, result: dict[str, Any]) -> Path:
    fields = ["case_id", "scan", "identity", "expected_positive", "observed_positive", "result"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in result["case_results"]:
            writer.writerow({
                "case_id": row["case_id"], "scan": row["scan"],
                "identity": row["identity_display"],
                "expected_positive": str(row["expected_positive"]).lower(),
                "observed_positive": str(row["observed_positive"]).lower(),
                "result": "HIT" if row["expected_positive"] == row["observed_positive"] else "MISS",
            })
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--live-input-root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--reference-tsv", type=Path)
    parser.add_argument("--synthetic-tsv", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.panel, args.baseline, args.live_input_root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        emit(json.dumps({"schema_version": "mamey_calibration_drift_v1", "status": "ERROR", "error": str(exc)}, indent=2))
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload)
    else:
        sys.stdout.write(payload)
    if args.reference_tsv:
        write_reference_control_tsv(args.reference_tsv)
    if args.synthetic_tsv:
        write_synthetic_tsv(args.synthetic_tsv, result)
    return 1 if result["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
