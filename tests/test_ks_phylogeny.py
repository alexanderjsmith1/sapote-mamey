"""Engine tests for mamey/ks_phylogeny.py (C06 / P358-003 engine placement).

Covers the two gates (strain-internal, iterative-module caveat), deterministic extraction of an
aSDomain /translation, and the A.3 routing (DOMAIN_ONLY_HINT -> adjudication queue; a two-proof
rescue is never queued).
"""
from pathlib import Path

import pytest

from mamey import ks_phylogeny as ksp

# Minimal antiSMASH-style region GBK with two PKS_KS aSDomains carrying /translation.
_GBK = """LOCUS       NODE_58_length_1000_cov_9    1000 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     aSDomain        100..300
                     /aSDomain="PKS_KS"
                     /locus_tag="ctg1_1"
                     /domain_id="nrpspksdomains_ctg1_1_PKS_KS.1"
                     /label="ctg1_1_PKS_KS.1"
                     /evalue="1.0e-90"
                     /translation="MKSAAAAAKS"
     aSDomain        400..600
                     /aSDomain="PKS_AT"
                     /locus_tag="ctg1_1"
                     /domain_id="nrpspksdomains_ctg1_1_PKS_AT.1"
                     /label="ctg1_1_PKS_AT.1"
                     /evalue="1.0e-70"
                     /translation="MATATATATAT"
     aSDomain        700..900
                     /aSDomain="PKS_KS"
                     /locus_tag="ctg1_2"
                     /domain_id="nrpspksdomains_ctg1_2_PKS_KS.1"
                     /label="ctg1_2_PKS_KS.1"
                     /evalue="1.0e-88"
                     /translation="MKSBBBBBKS"
//
"""


def _write_region(tmp_path: Path, fname: str, text: str = _GBK) -> Path:
    d = tmp_path / "regions"
    d.mkdir(exist_ok=True)
    (d / fname).write_text(text, encoding="utf-8")
    return d


def test_extracts_ks_with_translation(tmp_path):
    d = _write_region(tmp_path, "AS-705_NODE_58_region001.gbk")
    res = ksp.extract_module_core_domains(d)
    assert res["strain"] == "AS-705"
    assert res["class_counts"]["PKS_KS"] == 2
    assert res["class_counts"]["PKS_AT"] == 1
    ks = [x for x in res["domains"] if x["domain_class"] == "PKS_KS"]
    assert ks[0]["translation"] == "MKSAAAAAKS"  # /translation read directly, whitespace stripped


def test_strain_internal_gate_rejects_mixed(tmp_path):
    d = _write_region(tmp_path, "AS-705_NODE_58_region001.gbk")
    (d / "AS-696_NODE_9_region001.gbk").write_text(_GBK, encoding="utf-8")
    with pytest.raises(ValueError, match="STRAIN-INTERNAL ONLY"):
        ksp.extract_module_core_domains(d)


def test_strain_internal_gate_rejects_unparseable_filename(tmp_path):
    # v9.7.374 guard-gap fix: a file whose name does not match the <STRAIN>_NODE_x_regionNNN.gbk
    # convention used to be silently DROPPED from the uniqueness check (the `if s` filter) while its
    # domains were still merged -- so one normally-named strain-A file plus one unparseably-named
    # file (potentially a contaminating strain B) fused into a fictitious "strain-internal" pathway.
    # The gate must now fail closed on any unrecognized filename before uniqueness is even checked.
    d = _write_region(tmp_path, "AS-705_NODE_58_region001.gbk")
    (d / "contaminant_contig_region001.gbk").write_text(_GBK, encoding="utf-8")
    with pytest.raises(ValueError, match="could not determine a strain id"):
        ksp.extract_module_core_domains(d)


def test_iterative_module_caveat_present(tmp_path):
    d = _write_region(tmp_path, "AS-705_NODE_58_region001.gbk")
    res = ksp.extract_module_core_domains(d)
    assert any("ITERATIVE-MODULE GUARD" in c for c in res["claim_safety"])


def test_fasta_header_round_trips(tmp_path):
    d = _write_region(tmp_path, "AS-705_NODE_58_region001.gbk")
    fa = ksp.domain_fastas(ksp.extract_module_core_domains(d))
    assert fa["PKS_KS"].startswith(">AS-705__NODE_58__region001__ctg1_1__")
    assert "MKSAAAAAKS" in fa["PKS_KS"]


def test_route_only_domain_only_hints():
    verdicts = [
        {"bgc_a": "BGC018", "bgc_b": "BGC048", "verdict": "CORROBORATED_SPLIT",
         "is_rescue": True, "supporting_clades": "C_cisAT", "domain_classes": "PKS_KS",
         "n_module_core_domains": 4, "rggmci_homology": "PRESENT"},
        {"bgc_a": "BGC002", "bgc_b": "BGC022", "verdict": "DOMAIN_ONLY_HINT",
         "is_rescue": False, "supporting_clades": "C_cisAT", "domain_classes": "PKS_KS",
         "n_module_core_domains": 2, "rggmci_homology": "ABSENT"},
    ]
    q = ksp.route_domain_only_hints(verdicts)
    assert len(q) == 1
    assert q[0]["bgc_a"] == "BGC002" and q[0]["bgc_b"] == "BGC022"
    assert q[0]["disposition"] == "PENDING_ADJUDICATION"
    # the two-proof rescue is never queued
    assert all(not (r["bgc_a"] == "BGC018") for r in q)


def test_write_adjudication_queue(tmp_path):
    verdicts = [{"bgc_a": "BGC002", "bgc_b": "BGC022", "verdict": "DOMAIN_ONLY_HINT",
                 "is_rescue": False, "supporting_clades": "C_cisAT", "domain_classes": "PKS_KS",
                 "n_module_core_domains": 2, "rggmci_homology": "ABSENT"}]
    out = tmp_path / "queue.tsv"
    summary = ksp.write_adjudication_queue(ksp.route_domain_only_hints(verdicts), out)
    assert summary["queued"] == 1
    text = out.read_text(encoding="utf-8")
    assert "PENDING_ADJUDICATION" in text and "BGC002" in text
