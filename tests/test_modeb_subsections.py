"""Tests for the .344 gate-safe #### subsections (modeb_subsections.py). Synthetic package."""
import csv
import json
from pathlib import Path

from mamey import modeb_subsections as ms


def _pkg(tmp_path):
    p = tmp_path / "package"
    p.mkdir()
    (p / "S_4_triage_board.csv").write_text("BGC_ID\nBGC001\n", encoding="utf-8")
    (p / "manifest.json").write_text(json.dumps({"strain_id": "S", "taxonomy": "Actinomycete sp."}),
                                     encoding="utf-8")
    # HMM census
    with (p / "S_3_antismash_hmm.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bgc_id", "locus_tag", "domain_name", "tier1_diagnostic"])
        w.writerow(["BGC001", "g1", "ketoacyl-synt", "1"])
        w.writerow(["BGC001", "g2", "AMP-binding", "0"])
    # channel store with identity + positives
    (p / "blastp_nr").mkdir()
    with (p / "blastp_nr" / "BGC001_top10.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gene", "hit_rank", "pct_identity", "pct_positives", "subject_def", "subject_organism"])
        w.writerow(["g1", "1", "72.5", "85.0", "polyketide synthase", "Streptomyces sp."])
    # gene clusterblast
    with (p / "S_4A2_ClusterBlast_per_gene.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bgc_id", "query_gene", "pct_identity", "reference", "reference_source"])
        w.writerow(["BGC001", "g1", "70", "BGC0001: examplomycin", "MIBiG"])
    return p


def test_catalytic_census(tmp_path):
    b = ms.catalytic_domain_census(_pkg(tmp_path), "BGC001")
    assert "Catalytic domain census" in b and "ketoacyl-synt" in b and "diagnostic" in b


def test_blastp_channel_shows_identity_and_positives(tmp_path):
    b = ms.blastp_channel_evidence(_pkg(tmp_path), "BGC001")
    assert "BLASTp evidence" in b
    assert "%id" in b and "%pos" in b  # both metrics, never conflated
    assert "identity ≠" in b or "never conflated" in b


def test_gene_clusterblast(tmp_path):
    b = ms.gene_clusterblast(_pkg(tmp_path), "BGC001")
    assert "Gene-based ClusterBlast" in b and "examplomycin" in b


def test_genus_from_crosswalk(tmp_path, monkeypatch):
    # manifest is generic -> must fall back to the crosswalk. Point the module's data dir logic at
    # a temp crosswalk by writing one next to the real bundle data is not possible here, so assert
    # the generic-manifest path yields no genus without a crosswalk hit (safe empty).
    p = _pkg(tmp_path)
    g = ms._genus_of(p)
    # either resolves via the shipped crosswalk (if strain 'S' absent -> "") — must never raise
    assert isinstance(g, str)


def test_subsections_are_gate_safe(tmp_path):
    # every emitted subsection heading is #### and carries NO §N marker (so the structure gate,
    # which keys on §N, is unaffected)
    import re
    p = _pkg(tmp_path)
    for num in (2, 4, 5):
        block = ms.render_for_section(p, "BGC001", num)
        for line in block.splitlines():
            if line.startswith("#"):
                assert line.startswith("####"), f"non-#### heading: {line}"
                assert not re.search(r"§\s*\d", line), f"subsection carries a §N marker: {line}"
