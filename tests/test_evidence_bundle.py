"""Tests for tools/evidence_bundle.py (P360-001 / Idea D) — deterministic reader-side bundle.

Exercises the deficit semantics: PRESENT (file + row), ABSENT_NO_ROWS (file, no matching row),
ABSENT_NO_FILE (channel not produced). Never confuses absence with negation.
"""
import csv
import importlib.util
from pathlib import Path

import pytest

_MOD = Path(__file__).resolve().parents[1] / "tools" / "evidence_bundle.py"
_spec = importlib.util.spec_from_file_location("evidence_bundle", _MOD)
eb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eb)


def _write(path: Path, header: list[str], rows: list[list]):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


@pytest.fixture
def package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    S = "AS-705"
    # inventory: two BGCs
    _write(pkg / f"{S}_2_inventory.csv", ["bgc_id", "products", "contig", "edge_status"],
           [["BGC018", "T1PKS", "NODE_58", "loose"], ["BGC048", "transAT-PKS", "NODE_216", "complete"]])
    # convergence: only BGC018 has a row
    _write(pkg / f"{S}_3_mibig_convergence.csv", ["bgc_id", "compound", "pct_identity"],
           [["BGC018", "nystatin", "77"]])
    # per-gene clusterblast: BGC048 has two gene hits
    _write(pkg / f"{S}_4A2_ClusterBlast_per_gene.csv", ["bgc_id", "query_gene", "subject_gene", "pct_identity"],
           [["BGC048", "ctg1_1", "refA", "88"], ["BGC048", "ctg1_2", "refB", "80"]])
    # RG-GMCI: one pair linking BGC018 + BGC048
    _write(pkg / f"{S}_4A_RGGMCI_ranked_pairs.csv", ["bgc_a", "bgc_b", "rggmci_confidence", "rggmci_score"],
           [["BGC018", "BGC048", "HIGH_RG_GMCI_RESCUE", "0.91"]])
    # _4D two-proof: BGC018+BGC048 CORROBORATED
    _write(pkg / f"{S}_4D_two_proof_rescue.csv",
           ["strain", "contig_a", "contig_b", "verdict", "bgc_a", "bgc_b"],
           [[S, "NODE_58", "NODE_216", "TWO_PROOF_RESCUE", "BGC018", "BGC048"]])
    # NOTE: _3_mibig_profile.csv is deliberately NOT written -> ABSENT_NO_FILE
    return pkg


def test_bundle_assembles_channels(package):
    b = eb.build_evidence_bundle(package)
    assert b["strain"] == "AS-705"
    assert b["bgc_count"] == 2
    assert set(b["bgcs"]) == {"BGC018", "BGC048"}


def test_present_vs_absent_no_rows(package):
    b = eb.build_evidence_bundle(package)
    ch18 = b["bgcs"]["BGC018"]["channels"]
    ch48 = b["bgcs"]["BGC048"]["channels"]
    assert ch18["mibig_convergence"]["deficit"] == "PRESENT"      # BGC018 has a convergence row
    assert ch48["mibig_convergence"]["deficit"] == "ABSENT_NO_ROWS"  # file exists, no BGC048 row
    assert ch48["per_gene_clusterblast"]["deficit"] == "PRESENT"
    assert ch18["per_gene_clusterblast"]["deficit"] == "ABSENT_NO_ROWS"


def test_absent_no_file(package):
    b = eb.build_evidence_bundle(package)
    # _3_mibig_profile.csv was never written
    for bid in ("BGC018", "BGC048"):
        assert b["bgcs"][bid]["channels"]["mibig_novelty_profile"]["deficit"] == "ABSENT_NO_FILE"


def test_two_proof_channel_carried(package):
    b = eb.build_evidence_bundle(package)
    for bid in ("BGC018", "BGC048"):
        tp = b["bgcs"][bid]["channels"]["two_proof_rescue"]
        assert tp["deficit"] == "PRESENT"
        assert tp["verdicts"] == ["TWO_PROOF_RESCUE"]


def test_rggmci_pairs_touch_both(package):
    b = eb.build_evidence_bundle(package)
    assert b["bgcs"]["BGC018"]["channels"]["rggmci_pairs"]["n_pairs"] == 1
    assert b["bgcs"]["BGC048"]["channels"]["rggmci_pairs"]["n_pairs"] == 1


def test_claim_safety_and_write(package, tmp_path):
    b = eb.build_evidence_bundle(package)
    assert any("ABSENT_NO_FILE" in c for c in b["claim_safety"])
    out = eb.write_evidence_bundle(b, tmp_path / "out")
    assert out["bgc_count"] == 2
    md = (tmp_path / "out" / "AS-705_evidence_bundle.md").read_text()
    assert "Evidence Summary — BGC018" in md and "Two-proof rescue" in md


def test_not_a_package_raises(tmp_path):
    with pytest.raises(ValueError, match="not a sealed Mamey package"):
        eb.build_evidence_bundle(tmp_path)


# ── BB16 evidence-join extensions (folded 2026-08-11) ────────────────────────────────────────
def _mk_pkg(tmp_path, conv_family="nystatin", graded_family=None, manifest=None, empty_col=False):
    pkg = tmp_path / "package"; pkg.mkdir()
    S = "AS-424"
    _write(pkg / f"{S}_2_inventory.csv", ["bgc_id", "products"], [["BGC001", "T1PKS"]])
    conv_rows = [["BGC001", conv_family, "" if empty_col else "60"]]
    _write(pkg / f"{S}_3_mibig_convergence.csv", ["bgc_id", "compound", "pct_identity"], conv_rows)
    if graded_family is not None:
        _write(pkg / f"{S}_nr_vs_MIBiG_per_bgc.csv", ["bgc_id", "compound", "graded_pct"],
               [["BGC001", graded_family, "60.5"]])
    if manifest is not None:
        (pkg / "manifest.json").write_text(manifest, encoding="utf-8")
    return pkg


def test_channels_agree_disagree(tmp_path):
    pkg = _mk_pkg(tmp_path, conv_family="aureonuclemycin", graded_family="chelocardin")
    b = eb.build_evidence_bundle(pkg)
    assert b["bgcs"]["BGC001"]["channels_agree"] == "DISAGREE"


def test_channels_agree_agree(tmp_path):
    pkg = _mk_pkg(tmp_path, conv_family="zorbamycin", graded_family="zorbamycin")
    b = eb.build_evidence_bundle(pkg)
    assert b["bgcs"]["BGC001"]["channels_agree"] == "AGREE"


def test_channels_one_channel_only(tmp_path):
    pkg = _mk_pkg(tmp_path, conv_family="nystatin", graded_family=None)  # no graded file
    b = eb.build_evidence_bundle(pkg)
    assert b["bgcs"]["BGC001"]["channels_agree"] == "ONE_CHANNEL_ONLY"


def test_unmeasured_fields_row_level(tmp_path):
    pkg = _mk_pkg(tmp_path, empty_col=True)   # pct_identity blank but the row+file exist
    b = eb.build_evidence_bundle(pkg)
    um = b["bgcs"]["BGC001"]["unmeasured_fields"]
    assert any("mibig_convergence.pct_identity" == f for f in um)


def test_antismash_strictness_from_manifest(tmp_path):
    pkg = _mk_pkg(tmp_path, manifest='{"antismash_strictness": "RELAXED"}')
    assert eb.build_evidence_bundle(pkg)["antismash_strictness"] == "RELAXED"


def test_antismash_strictness_unknown(tmp_path):
    pkg = _mk_pkg(tmp_path, manifest=None)
    assert eb.build_evidence_bundle(pkg)["antismash_strictness"] == "UNKNOWN"
