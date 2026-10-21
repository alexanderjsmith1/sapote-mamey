"""Class-routed second proof: KS clade for polyketide pairs; marker conflict and intact-relative position otherwise.

Public fixtures only (two published draft genomes). No network, no external tools.
"""
import csv
import zipfile
from pathlib import Path

import pytest

from mamey import nonks_second_proof as N
from mamey import split_evidence_layers as L

FIX = Path(__file__).resolve().parent / "fixtures"
VWPH = FIX / "rggmci_public_VWPH00000000.1_subset.zip"
MTQP = FIX / "rggmci_public_MTQP00000000.1_groups_subset.zip"


def _pair(zip_path, a, b):
    with zipfile.ZipFile(zip_path) as zf:
        return L.score_pair(L.RegionCache(zf), a, b)


@pytest.mark.parametrize("zip_path,a,b,verdict,gap", [
    (VWPH, "VWPH01000001.1.region003.gbk", "VWPH01000008.1.region001.gbk", "CONSISTENT", -1),
    (VWPH, "VWPH01000004.1.region003.gbk", "VWPH01000010.1.region003.gbk", "CONFLICT", 2799),
    (VWPH, "VWPH01000001.1.region003.gbk", "VWPH01000004.1.region003.gbk", "APART_WEAK", 1867),
    (MTQP, "MTQP01000026.1.region001.gbk", "MTQP01000043.1.region001.gbk", "CONSISTENT", -12),
    (MTQP, "MTQP01000038.1.region001.gbk", "MTQP01000043.1.region001.gbk", "CONSISTENT", 7),
])
def test_layers_on_public_drafts(zip_path, a, b, verdict, gap):
    """Values match the benchmark scorecard script this module was ported from (all 16 fixture pairs checked)."""
    row = _pair(zip_path, a, b)
    assert row["layers_verdict"] == verdict and row["locus_gap_genes"] == gap
    assert (row["duplicated_markers"] != "") == (verdict == "CONFLICT")


def test_layers_are_order_independent():
    a, b = "VWPH01000001.1.region003.gbk", "VWPH01000008.1.region001.gbk"
    ab, ba = _pair(VWPH, a, b), _pair(VWPH, b, a)
    assert ab["layers_verdict"] == ba["layers_verdict"] and ab["locus_gap_genes"] == ba["locus_gap_genes"]


def test_cut_marker_is_not_a_second_copy():
    """A marker on a gene that runs off the record end may be the other half of the same gene."""
    cut = 'CDS             <1..300\n                     /locus_tag="a1"\n                     /sec_met_domain="YcaO (E-value: 1e-30)"\n'
    whole = 'CDS             1..300\n                     /locus_tag="b1"\n                     /sec_met_domain="YcaO (E-value: 1e-30)"\n'
    head = "LOCUS       x\nFEATURES             Location/Qualifiers\n     "
    ia, ib, ic = (L.region_inventory(head + t) for t in (cut, whole, whole))
    assert L.duplicated_markers(ia, ib) == []
    assert L.duplicated_markers(ib, ic) == ["YcaO"]


def test_completes_core_needs_both_pieces():
    def inv(*names):
        return {"names": L.Counter(names), "whole": L.Counter(names), "terminal": 0, "starter": 0}
    assert L.completes_core(inv("Condensation", "PCP"), inv("AMP-binding"), ["NRPS"], ["NRPS"]) == ["NRPS"]
    assert L.completes_core(inv("Condensation", "AMP-binding", "PCP"), inv("AMP-binding"), ["NRPS"], ["NRPS"]) == []


def test_default_policy_is_class_routed():
    from mamey.cli import build_parser
    assert N.DEFAULT_POLICY == N.CLASS_ROUTED_POLICY == "class_routed_v1"
    assert N.KS_POLICY in N.POLICIES and N.POSITION_POLICY in N.POLICIES
    parsed = build_parser().parse_args(["two-proof-rescue", "--package", "p"])
    assert parsed.policy == N.DEFAULT_POLICY and parsed.input_zip is None


def _manifest(products_a, products_b, domains_a, domains_b, ks_a=0):
    return {"strain_id": "PUB-1", "bgcs": [
        {"bgc_id": "BGC001", "contig": "VWPH01000001.1", "region_number": 3, "antismash_region": "region003",
         "start": 1, "end": 40000, "products": products_a, "ks_domain_count": ks_a,
         "source_gbk": "VWPH01000001.1.region003.gbk"},
        {"bgc_id": "BGC002", "contig": "VWPH01000008.1", "region_number": 1, "antismash_region": "region001",
         "start": 1, "end": 30000, "products": products_b, "ks_domain_count": 0,
         "source_gbk": "VWPH01000008.1.region001.gbk"}],
        "source_scans": {"domain_architecture": {"per_bgc": {"BGC001": {"domain_counts": domains_a},
                                                             "BGC002": {"domain_counts": domains_b}}}}}


def _row():
    return {"contig_a": "VWPH01000001.1", "contig_b": "VWPH01000008.1", "bgc_a": "BGC001", "bgc_b": "BGC002",
            "verdict": "RGGMCI_ONLY", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
            "functional_rescue_class": "COMPLEMENTARY", "rggmci_score": "20", "ks_clade_id": ""}


def test_archive_scorecard_routes_a_non_ks_pair():
    """Non-KS core observed, no KS: routed to core completion; position is recorded but is not the second proof."""
    m = _manifest(["NRPS"], ["NRPS"], {"NRPS_A": 2}, {"NRPS_A": 1})
    cards = N.archive_scorecards([_row()], m, VWPH)
    assert len(cards) == 1 and cards[0]["layers_verdict"] == "CONSISTENT" and cards[0]["completes_core"] == ""
    out = N.apply_policy([_row()], m, cards)[0]
    assert out["rule_policy"] == "class_routed_v1"
    assert out["second_proof_channel"] == "CORE_COMPLETION" and out["position_verdict"] == "CONSISTENT"
    # position CONSISTENT alone is homology, not biosynthetic logic: no promotion
    assert out["verdict"] == "RGGMCI_ONLY" and out["independent_proof_state"] == "NOT_READ_OR_UNRESOLVED"
    assert "SUPPORTING_ONLY" in out["kcb_role"]


@pytest.mark.parametrize("core,pos,verdict,state", [
    ("NRPS", "CONSISTENT", "TWO_PROOF_RESCUE", "PRESENT"),
    ("NRPS", "NOT_READ", "TWO_PROOF_RESCUE", "PRESENT"),
    ("NRPS", "APART_WEAK", "TWO_PROOF_RESCUE", "PRESENT"),
    ("NRPS", "CONFLICT", "POSITION_VETO", "CONTRADICTED"),
    ("NRPS", "APART_CLOSE", "POSITION_VETO", "CONTRADICTED"),
    ("", "CONSISTENT", "RGGMCI_ONLY", "NOT_READ_OR_UNRESOLVED"),
])
def test_core_completion_is_the_non_ks_second_proof(core, pos, verdict, state):
    from mamey.companion_evidence import identity_text
    m = _manifest(["NRPS"], ["NRPS"], {"NRPS_A": 2}, {"NRPS_A": 1})
    card = {"strain": "PUB-1", "identity_a": identity_text("PUB-1", m["bgcs"][0]),
            "identity_b": identity_text("PUB-1", m["bgcs"][1]), "layers_verdict": pos, "relative": "pub-relative",
            "completes_core": core}
    out = N.apply_policy([_row()], m, [card])[0]
    assert out["verdict"] == verdict and out["independent_proof_state"] == state and out["core_completion"] == core


def test_core_completion_needs_high_and_complementary_logic():
    from mamey.companion_evidence import identity_text
    m = _manifest(["NRPS"], ["NRPS"], {"NRPS_A": 2}, {"NRPS_A": 1})
    card = {"strain": "PUB-1", "identity_a": identity_text("PUB-1", m["bgcs"][0]),
            "identity_b": identity_text("PUB-1", m["bgcs"][1]), "layers_verdict": "CONSISTENT", "relative": "r",
            "completes_core": "NRPS"}
    moderate = {**_row(), "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE"}
    no_logic = {**_row(), "functional_rescue_class": "ACCESSORY_ONLY", "verdict": "WEAK"}
    for row in (moderate, no_logic):
        assert N.apply_policy([row], m, [card])[0]["verdict"] != "TWO_PROOF_RESCUE"


def test_ks_pair_keeps_the_ks_clade_route():
    m = _manifest(["T1PKS"], ["NRPS"], {"PKS_KS": 1}, {"NRPS_A": 1}, ks_a=1)
    out = N.apply_policy([_row()], m, N.archive_scorecards([_row()], m, VWPH))[0]
    assert out["second_proof_channel"] == "NONE" and out["verdict"] == "RGGMCI_ONLY"


def test_no_archive_means_not_read_never_a_promotion():
    m = _manifest(["NRPS"], ["NRPS"], {"NRPS_A": 2}, {"NRPS_A": 1})
    out = N.apply_policy([_row()], m)[0]
    assert out["verdict"] == "RGGMCI_ONLY" and out["position_verdict"] == "NOT_READ"
    assert out["independent_proof_state"] == "NOT_READ_OR_UNRESOLVED"


def test_missing_region_record_is_skipped_not_scored():
    m = _manifest(["NRPS"], ["NRPS"], {"NRPS_A": 2}, {"NRPS_A": 1})
    m["bgcs"][1]["source_gbk"] = "absent.region001.gbk"
    assert N.archive_scorecards([_row()], m, VWPH) == []


def test_written_rows_name_the_policy(tmp_path):
    from mamey.rescue_two_proof import write_4d_csv
    m = _manifest(["NRPS"], ["NRPS"], {"NRPS_A": 2}, {"NRPS_A": 1})
    rows = N.apply_policy([_row()], m, N.archive_scorecards([_row()], m, VWPH))
    path = write_4d_csv(rows, tmp_path / "PUB-1_4D_two_proof_rescue.csv", "PUB-1")
    written = list(csv.DictReader(open(path)))[0]
    assert written["two_proof_logic_version"] == "class_routed_v1"
    assert written["second_proof_channel"] == "CORE_COMPLETION"
    assert "core completion not shown" in written["interpretation"] and "core_completion" in written
