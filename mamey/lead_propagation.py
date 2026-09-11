"""lead_propagation.py — package-level lead-propagation audit (v9.7.405).

Revived from the pre-Sapote-Mamey `mamey_lead_propagation.py` (June 2026, engine 1.6.1), which
declared `required_destinations` per lead and failed when a lead was missing from any downstream
surface. That audit was never carried into the packaged engine; this module restores the idea
against the CURRENT package layout.

Rule: **a lead the triage board names must appear, by its exact `BGC_ID`, in every downstream
package surface that claims to list leads.** A lead that is on the board but absent from the
compiled report, the gene-by-gene top-leads table, the manifest, or the reader entry page is a
propagation defect — the reader would never meet it — and it is reported per lead, per surface.

Deterministic, read-only, no scientific content: it checks string presence of locked BGC ids,
never scores, never re-ranks. Claim-safety unaffected (class-level hypotheses, judgment deferred).
Prints nothing; the operator front door is `tools/lead_propagation_gate.py`.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

__all__ = ["LEAD_TIERS", "DEFAULT_DESTINATIONS", "LeadPropagation", "audit_package", "find_triage_board"]

# Tiers the engine's own ladder treats as leads (scoring.py: Exceptional/High/Medium/Low/Inventory).
LEAD_TIERS: tuple[str, ...] = ("Exceptional", "High")

# Package surfaces that CLAIM to present leads. Each is a glob relative to the package directory;
# `required` surfaces must exist for a PASS, `optional` ones are checked only when present
# (they are enrichment files that a valid package may legitimately lack).
DEFAULT_DESTINATIONS: dict[str, dict] = {
    "compiled_report": {"glob": "*_compiled_report.md", "required": False},
    "gene_by_gene_top_leads": {"glob": "*_gene_by_gene_top_leads.csv", "required": False},
    "manifest": {"glob": "manifest.json", "required": True},
    "manifest_short": {"glob": "manifest_short.json", "required": False},
    "open_me_first": {"glob": "OPEN_ME_FIRST.html", "required": False},
    "inventory": {"glob": "*_2_inventory.csv", "required": True},
    "workbook": {"glob": "*_5_workbook.xlsx", "required": False},
}


@dataclass
class LeadPropagation:
    bgc_id: str
    lead_tier: str
    rank: str
    present_destinations: list[str] = field(default_factory=list)
    missing_destinations: list[str] = field(default_factory=list)

    @property
    def gate_status(self) -> str:
        return "PASS" if not self.missing_destinations else "FAIL"

    def to_dict(self) -> dict:
        return asdict(self) | {"gate_status": self.gate_status}


def find_triage_board(package_dir: Path) -> Path | None:
    hits = sorted(package_dir.glob("*_4_triage_board.csv"))
    return hits[0] if hits else None


def _surface_text(path: Path) -> str:
    """Return searchable text for a surface. XLSX is read via openpyxl when available; a
    workbook that cannot be read is treated as an empty surface (reported, never crashed on)."""
    if path.suffix.lower() == ".xlsx":
        try:
            import openpyxl  # optional
        except Exception:
            return ""
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:
            return ""
        parts: list[str] = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                parts.extend(str(v) for v in row if v is not None)
        return "\n".join(parts)
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _leads_from_board(board: Path, tiers: tuple[str, ...]) -> list[tuple[str, str, str]]:
    with board.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        tier = (r.get("Lead_tier_auto") or "").strip()
        bid = (r.get("BGC_ID") or "").strip()
        if bid and tier in tiers:
            out.append((bid, tier, (r.get("Rank") or "").strip()))
    return out


_FRAGMENT_BOUNDARIES = {"edge", "full-contig", "full_contig", "contig-edge", "contig_edge"}


def _fragments_from_inventory(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return exact-identity fragment rows and typed identity holds.

    Inventory boundary state is authoritative. A fragment is never dropped for
    having a low tier, while an incomplete identity is never guessed.
    """
    strain = path.name.split("_2_inventory.csv")[0]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    fragments: list[dict[str, str]] = []
    holds: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, 2):
        boundary = (row.get("Boundary") or row.get("edge_status") or "").strip()
        if boundary.lower() not in _FRAGMENT_BOUNDARIES:
            continue
        bgc = (row.get("BGC_ID") or row.get("bgc_id") or "").strip()
        node = (row.get("Node_ID") or row.get("Contig") or row.get("node_id") or row.get("contig") or "").strip()
        region = (row.get("antiSMASH_Region") or row.get("Region") or row.get("region") or "").strip()
        if not all((strain, node, region, bgc)):
            holds.append({"kind": "FRAGMENT_EXACT_IDENTITY_INCOMPLETE", "inventory_row": str(row_number)})
            continue
        fragments.append({
            "full_identity": f"{strain} / {node} / {region} / {bgc}",
            "bgc_id": bgc,
            "boundary": boundary,
        })
    return fragments, holds


def audit_package(package_dir: str | Path, *, tiers: tuple[str, ...] = LEAD_TIERS,
                  destinations: dict[str, dict] | None = None) -> dict:
    """Audit one sealed package. Returns a JSON-serialisable receipt:

    status: PASS | FAIL | NO_BOARD | NO_LEADS
    leads:  one record per board lead with present/missing destinations
    surfaces: which destination files were found (and which required ones were not)
    """
    pkg = Path(package_dir)
    dests = destinations or DEFAULT_DESTINATIONS
    board = find_triage_board(pkg)
    receipt: dict = {"schema": "lead_propagation_receipt_v1", "package": pkg.name,
                     "lead_tiers": list(tiers), "surfaces": {}, "leads": [],
                     "missing_required_surfaces": []}
    if board is None:
        receipt["status"] = "NO_BOARD"
        return receipt
    receipt["triage_board"] = board.name

    texts: dict[str, str] = {}
    for name, spec in dests.items():
        hits = sorted(pkg.glob(spec["glob"]))
        if hits:
            receipt["surfaces"][name] = hits[0].name
            texts[name] = _surface_text(hits[0])
        else:
            receipt["surfaces"][name] = None
            if spec.get("required"):
                receipt["missing_required_surfaces"].append(name)

    inventory_name = receipt["surfaces"].get("inventory")
    fragments: list[dict[str, str]] = []
    fragment_holds: list[dict[str, str]] = []
    if inventory_name:
        fragments, fragment_holds = _fragments_from_inventory(pkg / inventory_name)
    receipt["fragment_identity_holds"] = fragment_holds
    receipt["fragments"] = []
    for fragment in fragments:
        missing = [name for name in ("manifest", "inventory") if name in texts and fragment["bgc_id"] not in texts[name]]
        receipt["fragments"].append({
            "full_identity": fragment["full_identity"],
            "boundary": fragment["boundary"],
            "required_destinations": ["manifest", "inventory"],
            "missing_destinations": missing,
            "gate_status": "PASS" if not missing else "FAIL",
        })
    receipt["fragment_count"] = len(fragments)
    receipt["fragment_failed_count"] = sum(row["gate_status"] == "FAIL" for row in receipt["fragments"])

    leads = _leads_from_board(board, tiers)
    if not leads:
        receipt["status"] = (
            "NO_LEADS"
            if not receipt["missing_required_surfaces"] and not fragment_holds and not receipt["fragment_failed_count"]
            else "FAIL"
        )
        return receipt

    for bid, tier, rank in leads:
        rec = LeadPropagation(bgc_id=bid, lead_tier=tier, rank=rank)
        for name, txt in texts.items():
            (rec.present_destinations if bid in txt else rec.missing_destinations).append(name)
        receipt["leads"].append(rec.to_dict())

    failed = [l for l in receipt["leads"] if l["gate_status"] == "FAIL"]
    receipt["lead_count"] = len(receipt["leads"])
    receipt["failed_count"] = len(failed)
    receipt["status"] = "PASS" if not failed and not receipt["missing_required_surfaces"] and not fragment_holds and not receipt["fragment_failed_count"] else "FAIL"
    return receipt


def write_receipt(package_dir: str | Path, receipt: dict, name: str = "lead_propagation.json") -> Path:
    out = Path(package_dir) / name
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return out
