"""Tests for mamey/modeb_domain_phylogeny.py (P360-002) — surface _4D into the Mode-B card.

Covers: package-only mode (what the emitter uses — no tree_root), the deficit paths
(no _4D file / no row for this BGC), verdict+interpretation rendering, gate-safety (no §N marker),
and the optional tree_root enrichment (patristic distance + per-strain identity baseline).
"""
import csv
import importlib.util
from pathlib import Path

import pytest

_MOD = Path(__file__).resolve().parents[1] / "mamey" / "modeb_domain_phylogeny.py"
_spec = importlib.util.spec_from_file_location("modeb_domain_phylogeny", _MOD)
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)


def _w(path, header, rows, delim=","):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=delim)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


@pytest.fixture
def package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    S = "AS-705"
    _w(pkg / f"{S}_2_inventory.csv", ["bgc_id", "products"], [["BGC018", "T1PKS"], ["BGC048", "transAT-PKS"]])
    _w(pkg / f"{S}_4D_two_proof_rescue.csv",
       ["strain", "contig_a", "contig_b", "verdict", "interpretation", "rggmci_confidence",
        "rggmci_score", "functional_rescue_class", "ks_clade_id", "bgc_a", "bgc_b", "claim_note"],
       [[S, "NODE_58_x", "NODE_216_y", "TWO_PROOF_RESCUE", "", "HIGH_RG_GMCI_RESCUE", "0.91",
         "CORE", "KSclade_3", "BGC018", "BGC048", "note"]])
    return pkg


def test_gate_safe_no_section_marker(package):
    out = dp.domain_phylogeny(package, "BGC018")
    assert out.startswith("#### ")          # #### subsection, never a §N heading
    assert "§" not in out.split("\n")[0]     # first line carries no § marker (structure gate safe)


def test_verdict_and_interpretation_render(package):
    out = dp.domain_phylogeny(package, "BGC018")
    assert "TWO_PROOF_RESCUE" in out
    assert "`BGC048`" in out                 # the partner region
    # interpretation column blank in the row -> module fills the evidence->reading mapping
    assert "complementary two-proof candidate" in out
    assert "KSclade_3" in out


def test_absent_no_row_for_bgc(package):
    out = dp.domain_phylogeny(package, "BGC999")
    assert "No cross-region KS/AT two-proof signal" in out
    assert "BGC999" in out


def test_absent_no_4d_file(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    _w(pkg / "AS-705_2_inventory.csv", ["bgc_id"], [["BGC001"]])
    out = dp.domain_phylogeny(pkg, "BGC001")
    assert "NOT produced here" in out
    assert "not a biological negative" in out


def test_package_only_mode_cites_tree_and_defers_baseline(package):
    # emitter path: no tree_root -> section is complete from the package, baseline noted as not co-located
    out = dp.domain_phylogeny(package, "BGC018")
    assert "PKS_KS_tree_2026-08-10" in out
    assert "baseline not co-located" in out
    assert "—" in out                        # patristic distance unavailable without the tree artifact


def test_weak_pairs_collapsed(tmp_path):
    # A fragmented assembly can pair one BGC with many WEAK partners; the card must surface
    # candidate-grade pairs and collapse WEAK to a count, never render every non-signal row.
    pkg = tmp_path / "package"
    pkg.mkdir()
    S = "AS-922"
    _w(pkg / f"{S}_2_inventory.csv", ["bgc_id"], [["BGC011"]])
    rows = [[S, "NODE_1370", "NODE_235", "RGGMCI_ONLY", "", "MODERATE_RG_GMCI_CANDIDATE", "33",
             "COMPLEMENTARY", "", "BGC011", "BGC016", "n"]]
    for i, p in enumerate(("BGC031", "BGC021", "BGC026")):     # three WEAK partners
        rows.append([S, "NODE_1370", f"NODE_{300+i}", "WEAK", "", "LOW_SHARED_REFERENCE_SIGNAL",
                     "5", "AMBIGUOUS", "", "BGC011", p, "n"])
    _w(pkg / f"{S}_4D_two_proof_rescue.csv",
       ["strain", "contig_a", "contig_b", "verdict", "interpretation", "rggmci_confidence",
        "rggmci_score", "functional_rescue_class", "ks_clade_id", "bgc_a", "bgc_b", "claim_note"], rows)
    out = dp.domain_phylogeny(pkg, "BGC011")
    assert "`BGC016`" in out                      # the surfaced candidate is rendered
    assert "3 WEAK pair(s)" in out or "3 `WEAK` pair(s)" in out   # the three WEAK collapsed to a count
    assert "`BGC031`" not in out                  # WEAK partners NOT rendered as rows
    assert out.count("| **WEAK**") == 0


def test_all_weak_gives_no_candidate_line(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    S = "AS-922"
    _w(pkg / f"{S}_2_inventory.csv", ["bgc_id"], [["BGC099"]])
    _w(pkg / f"{S}_4D_two_proof_rescue.csv",
       ["strain", "contig_a", "contig_b", "verdict", "interpretation", "rggmci_confidence",
        "rggmci_score", "functional_rescue_class", "ks_clade_id", "bgc_a", "bgc_b", "claim_note"],
       [[S, "NODE_1", "NODE_2", "WEAK", "", "LOW_SHARED_REFERENCE_SIGNAL", "4", "AMBIGUOUS", "",
         "BGC099", "BGC100", "n"]])
    out = dp.domain_phylogeny(pkg, "BGC099")
    assert "No candidate-grade cross-region pair" in out
    assert "not a biological negative" in out


def test_tree_root_enrichment(package, tmp_path):
    S = "AS-705"
    root = tmp_path / "master"
    (root / S / "PKS_KS_tree_2026-08-10").mkdir(parents=True)
    _w(root / S / "PKS_KS_tree_2026-08-10" / f"{S}_KS_fragment_candidates.tsv",
       ["patristic_dist", "KS_a", "KS_b", "node_a", "node_b", "relation"],
       [["0.0423", "NODE_58_AT4", "NODE_216_AT1", "NODE_58", "NODE_216", "CROSS-REGION"]], delim="\t")
    (root / "_IDENTITY_BASELINE_2026-08-10").mkdir(parents=True)
    _w(root / "_IDENTITY_BASELINE_2026-08-10" / "_COHORT_identity_baseline.tsv",
       ["strain", "within_contig_median_pid"], [[S, "55"]], delim="\t")
    out = dp.domain_phylogeny(package, "BGC018", tree_root=root)
    assert "0.0423" in out                                  # patristic distance now present
    assert "CROSS-REGION" in out
    assert "within-contig median %id = 55%" in out          # per-strain baseline
    assert "> 75%" in out                                   # baseline(55)+20, floor 70
    assert "never pooled" in out
