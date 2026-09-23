"""Generate claim-safe metabolomics and activity decision trees."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from typing import Any
from .csv_safety import SafeDictWriter
from .deep_bgc_report import DeepBGCReportError, IDENTITY_KEYS
from .exact_identity import exact_locus_display, ExactLocusIdentityError

class ActivityDecisionTreeError(ValueError):
    pass

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _identity(row: dict[str, Any]) -> tuple[dict[str, str], str]:
    values = {k: str(row.get(k, "")).strip() for k in IDENTITY_KEYS}
    try:
        display = exact_locus_display(*(values[k] for k in IDENTITY_KEYS))
    except ExactLocusIdentityError as exc:
        raise ActivityDecisionTreeError(str(exc)) from exc
    return values, display

def build_activity_decision_trees(leads_tsv: Path, receipt_root: Path, output_dir: Path) -> dict[str, Any]:
    with leads_tsv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise ActivityDecisionTreeError("lead table is empty")
    admitted: list[tuple[dict[str, str], str]] = []
    seen: set[str] = set()
    for row in rows:
        identity, display = _identity(row)
        if display in seen:
            raise ActivityDecisionTreeError(f"duplicate exact locus: {display}")
        seen.add(display)
        claim = str(row.get("claim_ceiling", "")).strip()
        if not claim:
            raise ActivityDecisionTreeError(f"missing claim ceiling for {display}")
        # Test the raw string, not the Path: Path("") normalises to Path("."),
        # which is truthy and would clear every guard below.  Mirrors the
        # reference implementation in mamey/thesis_handoff.py::_safe.
        raw_locator = str(row.get("report_receipt", "")).strip()
        locator = Path(raw_locator)
        if not raw_locator or locator.is_absolute() or ".." in locator.parts:
            raise ActivityDecisionTreeError("report_receipt must be a safe relative locator")
        root = receipt_root.resolve()
        receipt_path = (root / locator).resolve()
        if receipt_path != root and root not in receipt_path.parents:
            raise ActivityDecisionTreeError("report_receipt escapes configured root")
        if not receipt_path.is_file():
            raise ActivityDecisionTreeError(f"report_receipt is not a file: {raw_locator}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("identity") != identity:
            raise ActivityDecisionTreeError("report receipt exact identity mismatch")
        admitted.append((row, display))
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ActivityDecisionTreeError(
            f"output directory already exists: {output_dir}; choose a new delivery directory"
        ) from exc
    md = ["# Metabolomics and Activity Decision Trees", "", "These are bounded decision gates, not product or activity claims.", ""]
    decision_rows: list[dict[str, str]] = []
    for row, display in admitted:
        md += [f"## {display}", "", f"Hypothesis: {row.get('hypothesis','unresolved')}", "",
               "1. Expression gate: confirm transcript, protein, or culture-condition evidence for the target genes.",
               "2. Genetic linkage gate: compare a targeted perturbation or orthogonal genotype to an appropriate control.",
               "3. Feature gate: require a reproducible LC-MS or MS/MS feature with blank subtraction and replicate support.",
               "4. Activity gate: test fraction or purified material with counterscreens, dose response, and matrix controls.",
               "5. Claim gate: advance only the narrowest statement jointly supported by genetic, chemical, and activity evidence.", "",
               f"Current claim ceiling: {row['claim_ceiling']}", ""]
        decision_rows.append({"exact_locus": display, "next_gate": "expression", "status": "EVIDENCE_REQUIRED", "claim_ceiling": row["claim_ceiling"]})
    markdown = output_dir / "ACTIVITY_DECISION_TREES.md"
    markdown.write_text("\n".join(md), encoding="utf-8")
    table = output_dir / "ACTIVITY_DECISION_TREES.tsv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = SafeDictWriter(handle, delimiter="\t", fieldnames=list(decision_rows[0]))
        writer.writeheader(); writer.writerows(decision_rows)
    receipt = {"schema":"sapote.activity_decision_tree.receipt.v1", "lead_count":len(rows),
               "input":{"name":leads_tsv.name,"sha256":_sha(leads_tsv)},
               "outputs":{p.name:{"sha256":_sha(p),"bytes":p.stat().st_size} for p in (markdown, table)}}
    receipt_path = output_dir / "ACTIVITY_DECISION_TREE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return receipt
