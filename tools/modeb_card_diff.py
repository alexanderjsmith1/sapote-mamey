#!/usr/bin/env python3
"""Report current-package facts that would change a stored Mode B card.

This is a read-only diff. It does not regenerate, edit, admit, or approve a card.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.modeb_structure_gate import lint_card  # noqa: E402

SCHEMA = "sapote-modeb-card-diff-v1"
META = re.compile(r"<!--\s*MODE B TEMPLATE\s*\|(?P<body>.*?)-->", re.I | re.S)
REGION = re.compile(r"\bregion\d+\b", re.I)
KCB_STATE = re.compile(r"\bKCB(?:_evidence)?_state\s*[=:]\s*([A-Z_]+)", re.I)


class CardDiffHold(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _one(package: Path, pattern: str) -> Path:
    paths = sorted(package.glob(pattern))
    if len(paths) != 1:
        raise CardDiffHold("CARD_DIFF_SOURCE_HOLD", f"expected one {pattern}, found {len(paths)}")
    return paths[0]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _card_identity(text: str) -> dict[str, str]:
    match = META.search(text)
    fields: dict[str, str] = {}
    if match:
        for part in match.group("body").split("|"):
            if ":" in part:
                key, value = part.split(":", 1)
                fields[key.strip().lower()] = value.strip()
    region_match = REGION.search(text)
    return {
        "strain": fields.get("strain", ""),
        "node": fields.get("node", ""),
        "region": region_match.group(0).lower() if region_match else "",
        "bgc_alias": fields.get("bgc", ""),
    }


def compare(package_dir: str | Path, card_path: str | Path) -> dict[str, object]:
    package, card = Path(package_dir), Path(card_path)
    if not card.is_file():
        raise CardDiffHold("CARD_DIFF_SOURCE_HOLD", "stored card is absent")
    text = card.read_text(encoding="utf-8", errors="replace")
    card_id = _card_identity(text)
    if not all(card_id.values()):
        raise CardDiffHold("CARD_EXACT_IDENTITY_HOLD", "stored card lacks strain, node, region, or BGC alias")

    inventory_path = _one(package, "*_2_inventory.csv")
    triage_path = _one(package, "*_4_triage_board.csv")
    inventory = _read_csv(inventory_path)
    matches = [row for row in inventory if (row.get("BGC_ID") or "").strip() == card_id["bgc_alias"]]
    if len(matches) != 1:
        raise CardDiffHold("CARD_PACKAGE_JOIN_HOLD", "BGC alias must join exactly one inventory row")
    row = matches[0]
    package_strain = inventory_path.name.split("_2_inventory.csv")[0]
    current = {
        "strain": package_strain,
        "node": (row.get("Node_ID") or row.get("Contig") or "").strip(),
        "region": (row.get("antiSMASH_Region") or row.get("Region") or "").strip().lower(),
        "bgc_alias": (row.get("BGC_ID") or "").strip(),
    }
    if not all(current.values()):
        raise CardDiffHold("PACKAGE_EXACT_IDENTITY_HOLD", "current inventory row lacks a complete exact identity")

    changed: list[dict[str, object]] = []
    if card_id != current:
        changed.append({"section": 1, "kind": "EXACT_IDENTITY_CHANGED", "stored": card_id, "current": current})

    context = {
        "boundary": row.get("Boundary", ""),
        "length_kb": row.get("Length_kb", ""),
        "bgc_id": current["bgc_alias"],
        "node_id": current["node"],
        "region": current["region"],
    }
    findings = lint_card(text, bgc_context=context, check_depth=False)
    for finding in findings:
        changed.append({
            "section": finding.get("section"),
            "kind": "STRUCTURE_GATE_" + str(finding.get("code") or "FINDING"),
            "severity": finding.get("severity"),
        })

    triage_rows = [r for r in _read_csv(triage_path) if (r.get("BGC_ID") or "").strip() == current["bgc_alias"]]
    current_kcb = str(row.get("KCB_evidence_state") or row.get("KCB_state") or "UNKNOWN_KCB").strip()
    stored_match = KCB_STATE.search(text)
    stored_kcb = stored_match.group(1).upper() if stored_match else "NOT_RECORDED"
    if stored_kcb != current_kcb.upper():
        changed.append({"section": 28, "kind": "KCB_EVIDENCE_STATE_CHANGED", "stored": stored_kcb, "current": current_kcb})
    if triage_rows:
        for field, section in (("Protocluster_count", 10), ("Chemical_hybrid", 10), ("Overmerge_state", 10)):
            value = str(triage_rows[0].get(field) or "").strip()
            if value and value not in text:
                changed.append({"section": section, "kind": f"CURRENT_{field.upper()}_NOT_RECORDED", "current": value})

    full_identity = " / ".join((current["strain"], current["node"], current["region"], current["bgc_alias"]))
    sections = sorted({item["section"] for item in changed if isinstance(item.get("section"), int)})
    return {
        "schema": SCHEMA,
        "status": "STALE_DIFFERENCES_FOUND" if changed else "NO_CURRENT_DIFFERENCE_FOUND",
        "full_identity": full_identity,
        "changed_sections": sections,
        "differences": changed,
        "sources": [
            {"logical_locator": inventory_path.name, "sha256": _sha(inventory_path)},
            {"logical_locator": triage_path.name, "sha256": _sha(triage_path)},
            {"logical_locator": card.name, "sha256": _sha(card)},
        ],
        "claim_ceiling": "Mechanical stale-card comparison only; no regeneration, interpretation, evidence admission, or publication approval.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package")
    parser.add_argument("card")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        result = compare(args.package, args.card)
    except CardDiffHold as exc:
        sys.stderr.write(json.dumps({"status": "HOLD", "code": exc.code, "detail": str(exc)}) + "\n")
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
