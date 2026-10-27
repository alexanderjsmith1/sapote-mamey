"""ingest-receipts lints each card against the contract the card was authored to.

Before this fix every ingest door (--card, --auto-detect, --receipt) linted with the §1–§48
full48 contract. A card emitted with `emit-modeb-template --contract current50_v2` got six
TITLE_MISMATCH errors (§12, §21, §22, §23, §26, §48), exit 3, and was never recorded, although
`verify-modeb --contract current50_v2` passed it.

Now ingest reads the contract marker the emitter writes into the card header, or takes
`--contract` with the same names as verify-modeb. No marker and no flag keeps full48. A card
that fails its own contract, or whose header disagrees with `--contract`, is still refused.

All fixtures are synthetic (AS-XXX, NODE_1, ctg1_*).
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mamey.mode_b_receipt import auto_detect_ingest, ingest_one_card, ingest_receipt  # noqa: E402
from mamey.modeb_current50_v2 import load_contract  # noqa: E402
from mamey.modeb_structure_gate import lint_card  # noqa: E402
from mamey.modeb_template_emitter import _header_block  # noqa: E402

from tests._modeb_card_fixtures import valid_modeb_card_stub  # noqa: E402

STRAIN, BGC, CONTIG, REGION = "AS-XXX", "BGC001", "NODE_1", "region001"
ROSTER = ["ctg1_1", "ctg1_2"]
RECORD_HEADER = f"<!-- MODE B: {BGC} | strain: {STRAIN} | session: s458 | 2026-01-01T00:00:00Z -->\n\n"


def _package(tmp_path: Path) -> Path:
    """Synthetic package: register, manifest, triage row, and the per-BGC gene roster the matrix check binds."""
    pkg = tmp_path / STRAIN / "package"
    (pkg / "judgment").mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": STRAIN}))
    reg = {"schema_version": "1.0", "strain_id": STRAIN, "total_bgcs": 1, "complete_bgcs": 0,
           "completion_pct": 0.0, "judgment_status": "PENDING", "last_sapote_session": None,
           "bgcs": {BGC: {"status": "PENDING", "mode_b_file": None, "session_id": None,
                          "timestamp": None}}}
    (pkg / f"{STRAIN}_judgment_register.json").write_text(json.dumps(reg))
    with open(pkg / f"{STRAIN}_4_triage_board.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Contig", "Region", "Product", "kcb_top"])
        w.writerow([BGC, CONTIG, REGION, "terpene", "synthetic reference"])
    with open(pkg / f"{STRAIN}_gene_by_gene_all_bgcs.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["locus_tag", "bgc_id"])
        w.writerows([[tag, BGC] for tag in ROSTER])
    with open(pkg / f"{STRAIN}_cds_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["locus_tag"])
        w.writerows([[tag] for tag in ROSTER])
    return pkg


def _section50() -> str:
    rows = "".join(
        f"| {tag} | WP_000001.1 — terpene synthase [Streptomyces examplei] | 90% id / 95% positives / qcov 100% "
        "| no bound hit | no bound hit | no bound hit | no bound hit |\n" for tag in ROSTER)
    return ("Per-gene evidence for the synthetic locus.\n\n"
            "#### Complete named-match, channel-separated table\n"
            "| Gene | NCBI nr accession + matched protein | nr id/pos/qcov "
            "| NCBI ClusteredNR accession + matched protein | ClusteredNR id/pos/qcov "
            "| local Swiss-Prot accession + matched protein | Swiss-Prot id/pos/qcov |\n"
            "|---|---|---|---|---|---|---|\n" + rows)


def v2_card(*, retitle: dict[int, str] | None = None, markers: bool = True) -> str:
    """A current50_v2 card: emitter header, then §1–§50 with the contract's exact titles."""
    contract = load_contract("current50_v2")
    head = _header_block({"strain_id": STRAIN, "node": CONTIG, "contig": CONTIG, "region": REGION,
                          "bgc_id": BGC, "products": "terpene"}, contract)
    if not markers:
        head = RECORD_HEADER + "".join(ln + "\n" for ln in head.splitlines() if not ln.startswith("<!-- MODE B"))
    parts = [head]
    for s in contract["sections"]:
        n = s["number"]
        title = (retitle or {}).get(n, s["title"])
        body = _section50() if n == 50 else f"Synthetic finding for section {n} of {BGC} ({CONTIG})."
        parts.append(f"\n## §{n} {title}\n\n{body}\n")
    return "".join(parts)


def full48_card() -> str:
    return RECORD_HEADER + valid_modeb_card_stub(BGC, CONTIG, STRAIN).split("\n", 2)[2]


def _errors(findings):
    return [f for f in findings if f.get("severity") == "ERROR"]


def _write(pkg: Path, text: str) -> Path:
    path = pkg.parent / f"{STRAIN}_{BGC}_mode_b.md"
    path.write_text(text, encoding="utf-8")
    return path


# --- the defect, stated at the gate -------------------------------------------------------

def test_v2_card_fails_full48_and_passes_its_own_contract():
    card = v2_card()
    full48 = [f["code"] for f in _errors(lint_card(card))]
    assert full48.count("TITLE_MISMATCH") == 6
    assert not [f for f in _errors(lint_card(card, contract=load_contract("current50_v2")))
                if f["code"] == "TITLE_MISMATCH"]


def test_contract_resolution():
    from mamey.mode_b_receipt import _resolve_card_contract
    assert _resolve_card_contract(v2_card())[0::2] == ("current50_v2", "card header")
    assert _resolve_card_contract(full48_card())[0::2] == ("full48", "default")
    assert _resolve_card_contract(v2_card(markers=False))[0::2] == ("full48", "default")
    assert _resolve_card_contract(v2_card(markers=False), "current50_v2")[0::2] == ("current50_v2", "--contract")
    legacy = "<!-- MODE B TEMPLATE | bgc: BGC001 | contract: modeb_corrective_full30_v1 -->\n"
    assert _resolve_card_contract(legacy)[0::2] == ("full48", "default")
    marked48 = "<!-- MODE B TEMPLATE | bgc: BGC001 | contract: modeb_corrective_full48_v1 -->\n"
    assert _resolve_card_contract(marked48)[0::2] == ("full48", "card header")
    with pytest.raises(ValueError):
        _resolve_card_contract(full48_card(), "current50_v9")


# --- --card -------------------------------------------------------------------------------

def test_card_flow_records_a_current50_v2_card(tmp_path):
    pkg = _package(tmp_path)
    out = ingest_one_card(pkg, _write(pkg, v2_card()))
    assert out["status"] == "RECORDED", _errors(out["structure_findings"])
    assert out["structure_contract"] == "current50_v2"
    assert out["structure_contract_source"] == "card header"
    assert not _errors(out["structure_findings"])


def test_card_flow_still_records_a_full48_card(tmp_path):
    pkg = _package(tmp_path)
    out = ingest_one_card(pkg, _write(pkg, full48_card()))
    assert out["status"] == "RECORDED", _errors(out["structure_findings"])
    assert (out["structure_contract"], out["structure_contract_source"]) == ("full48", "default")


def test_card_flow_refuses_a_v2_card_with_a_wrong_title(tmp_path):
    pkg = _package(tmp_path)
    out = ingest_one_card(pkg, _write(pkg, v2_card(retitle={26: "OSMAC protocol"})))
    assert out["status"] == "SKIPPED_STRUCTURE_INVALID"
    assert out["structure_contract"] == "current50_v2"
    assert [(f["code"], f["section"]) for f in _errors(out["structure_findings"])] == [("TITLE_MISMATCH", 26)]


def test_unmarked_v2_card_keeps_the_full48_default_unless_contract_is_given(tmp_path):
    pkg = _package(tmp_path)
    card = _write(pkg, v2_card(markers=False))
    out = ingest_one_card(pkg, card)
    assert out["status"] == "SKIPPED_STRUCTURE_INVALID"
    assert [f["code"] for f in _errors(out["structure_findings"])].count("TITLE_MISMATCH") == 6
    out = ingest_one_card(pkg, card, contract="current50_v2")
    assert out["status"] == "RECORDED", _errors(out["structure_findings"])


def test_contract_flag_that_contradicts_the_card_header_is_refused(tmp_path):
    pkg = _package(tmp_path)
    out = ingest_one_card(pkg, _write(pkg, v2_card()), contract="full48")
    assert out["status"] == "SKIPPED_STRUCTURE_INVALID"
    assert "CARD_CONTRACT_CONFLICT" in {f["code"] for f in _errors(out["structure_findings"])}


# --- --auto-detect and --receipt ----------------------------------------------------------

def test_auto_detect_records_a_current50_v2_card(tmp_path):
    pkg = _package(tmp_path)
    (pkg / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").write_text(v2_card(), encoding="utf-8")
    out = auto_detect_ingest(pkg)
    assert out["recorded"] == [BGC], out["skipped_structure_invalid"]
    assert out["structure_contracts"] == {BGC: "current50_v2"}


def test_auto_detect_refuses_a_v2_card_with_a_wrong_title(tmp_path):
    pkg = _package(tmp_path)
    (pkg / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").write_text(
        v2_card(retitle={12: "Bee/microbe ecological interpretation"}), encoding="utf-8")
    out = auto_detect_ingest(pkg)
    assert out["recorded"] == [] and out["skipped_structure_invalid"] == [(BGC, 1)]


def test_receipt_records_a_current50_v2_card(tmp_path):
    pkg = _package(tmp_path)
    receipt = tmp_path / "mode_b_receipt.json"
    receipt.write_text(json.dumps({"schema_version": "mode-b-receipt-1.0", "strain_id": STRAIN,
                                   "cards": [{"bgc_id": BGC, "mode_b_md": v2_card()}]}))
    out = ingest_receipt(pkg, receipt)
    assert out["recorded"] == [BGC], out["skipped_structure_invalid"]
    assert out["structure_contracts"] == {BGC: "current50_v2"}


# --- the command ----------------------------------------------------------------------------

def _cli(*argv):
    return subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "ingest-receipts", *argv],
                          capture_output=True, text=True, cwd=ROOT)


def test_cli_card_exit_codes_and_report(tmp_path):
    pkg = _package(tmp_path)
    r = _cli("--package", str(pkg), "--card", str(_write(pkg, v2_card())))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "contract:          current50_v2 (card header)" in r.stdout
    assert "structure:         0 ERROR(S)" in r.stdout and "vs §1–§50 current50_v2 contract" in r.stdout

    pkg = _package(tmp_path / "bad")
    r = _cli("--package", str(pkg), "--card", str(_write(pkg, v2_card(retitle={48: "Cross-cohort synthesis & claim ceiling"}))))
    assert r.returncode == 3, r.stdout + r.stderr
    assert "vs §1–§50 current50_v2 contract" in r.stdout


def test_cli_offers_the_same_contract_names_as_verify_modeb():
    help_text = _cli("--help").stdout
    assert re.search(r"--contract \{full48,current50_v2\}", help_text)
