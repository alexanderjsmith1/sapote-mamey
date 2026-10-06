"""tools/strain_slides.py and the gap-rescue map: a split cluster is assembled across contigs from the evidence already held.

The owner, 2026-10-02, on a halogenated, glycosylated core whose halogenase and sugar genes sat on another contig: "we
really don't have the data integrated", then "it is the per-gene clusterblast and rggmci should be surfacing this", and
of a contig pulled in by one set-aside transporter: "This does not belong with this slide or this bgc."
The locks below hold the rules those messages produced, on synthetic data (no cohort data ships in tests):
- per-gene KnownClusterBlast is read from the antiSMASH ZIP, with each region's ranked cluster list;
- a partner region surfaces when RG-GMCI links it and either the intact-relative position is CONSISTENT, or both
  regions hit different genes of a cluster in both regions' top three and position does not contradict; whatever the
  two-proof check (built on KS clades) says. Position that contradicts (APART_CLOSE, CONFLICT) sets it aside. On the
  In a lineage benchmark, the KCB rule alone admitted 2 of 17 false HIGH links; position rejected the readable one;
- the strip draws a partner contig only when it holds a SUPPORTED find (the map's rule, locked in
  test_447_gap_rescue_supported_partner_contigs.py);
- reference genes are grouped by step, from the reference's product line or else the found gene's Pfam names.
"""
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import strain_slides as ss  # noqa: E402

CORE, PART, FAR = "NODE_1_length_9000_cov_5.1", "NODE_2_length_8000_cov_5.2", "NODE_3_length_7000_cov_5.3"


def _kcb(name, hits):
    """A KnownClusterBlast text file: hits = [(accession, cluster name, [(query, subject, identity)])], in rank order."""
    out = ["ClusterBlast scores for x", "", "Significant hits: "]
    out += [f"{i}. {a}.1\t{n}" for i, (a, n, _) in enumerate(hits, 1)] + ["", "", "Details:", ""]
    for i, (a, n, rows) in enumerate(hits, 1):
        out += [">>", f"{i}. {a}.1", f"Source: {n}", "Type: other", "", "Table of Blast hits (query gene, subject gene, "
                "%identity, blast score, %coverage, e-value):"]
        out += [f"{q}\t{s}\t{p}\t100\t95.0\t1e-50" for q, s, p in rows] + ["", ""]
    return name, "\n".join(out)


def _zip(tmp, files, prefix="x (Loose)/"):
    z = tmp / "x.zip"
    with zipfile.ZipFile(z, "w") as fh:
        for name, text in files:
            fh.writestr(f"{prefix}knownclusterblast/{name}", text)
    return z


def _D(tmp, rgg_conf="HIGH_RG_GMCI_RESCUE", partner_rank=1):
    hits_core = [("BGC0000010", "examplomycin", [("c_1", "P1", 60), ("c_2", "P2", 61), ("c_3", "P3", 58)]),
                 ("BGC0000020", "otheromycin", [("c_1", "Q1", 50), ("c_2", "Q2", 52)])]
    shared = ("BGC0000010", "examplomycin", [("p_1", "P7", 70), ("p_2", "P8", 66), ("p_3", "P9", 64)])
    filler = [(f"BGC00009{k}0", f"filler{k}", [("p_1", f"F{k}", 40)]) for k in range(3)]
    hits_part = filler[:partner_rank - 1] + [shared] + filler[partner_rank - 1:]
    z = _zip(tmp, [_kcb(f"{CORE}_c1.txt", hits_core), _kcb(f"{PART}_c1.txt", hits_part)])
    D = {"src": {}, "kcb": ss.kcb_genes(str(z)), "mibig_names": {}, "gfeat": defaultdict(list), "pfam": {},
         "inv": {"BGC001": {"Contig": CORE, "antiSMASH_Region": "region001", "Products": "indole"},
                 "BGC002": {"Contig": PART, "antiSMASH_Region": "region001", "Products": "halogenated"}},
         "genes": {"BGC001": [{"locus_tag": f"c_{k}"} for k in (1, 2, 3)],
                   "BGC002": [{"locus_tag": f"p_{k}"} for k in (1, 2, 3)]},
         "rgg": [{"bgc_a": "BGC002", "bgc_b": "BGC001", "rggmci_confidence": rgg_conf, "rggmci_score": "26"}],
         "twoproof": {("BGC001", "BGC002"): {"verdict": "RGGMCI_ONLY"}}, "scorecard": {}}
    return D


def test_per_gene_kcb_and_region_ranks_are_read_from_the_zip(tmp_path):
    D = _D(tmp_path)
    assert D["kcb"]["c_2"][0][:2] == ("BGC0000010", "examplomycin") and D["kcb"]["c_2"][0][3] == 61.0
    assert ss.kcb_top(D, "BGC001") == ["BGC0000010", "BGC0000020"]


def test_kcb_files_at_the_zip_top_level_are_read_too(tmp_path):
    """Most result ZIPs keep knownclusterblast/ at the top level; only some nest it in a result folder."""
    z = _zip(tmp_path, [_kcb(f"{CORE}_c1.txt", [("BGC0000010", "examplomycin", [("c_1", "P1", 60)])])], prefix="")
    assert ss.kcb_genes(str(z))["c_1"][0][0] == "BGC0000010"


def _text(D):
    return "".join(t for p in ss.split_paras(D, "BGC001") for t, _, _ in p)


def test_rggmci_plus_complementary_kcb_surfaces_the_partner_whatever_two_proof_says(tmp_path):
    D = _D(tmp_path)
    (x,), aside = ss.split_partners(D, "BGC001")
    assert x["other"] == "BGC002" and "RGGMCI_ONLY" in x["why"] and not aside
    c = x["conc"][0]
    assert c["acc"] == "BGC0000010" and (c["a"], c["b"], c["both"], c["union"]) == (3, 3, 0, 6)
    assert "different genes of examplomycin (3 here, 3 there)" in _text(D) and "not checked against a public relative" in _text(D)


def test_position_consistent_plus_kcb_is_two_layers(tmp_path):
    D = _D(tmp_path)
    D["scorecard"][frozenset(("BGC001", "BGC002"))] = {"layers_verdict": "CONSISTENT", "relative_source": "Examplo sp. X",
                                                       "relative_assembly": "complete", "locus_gap_genes": "3"}
    assert "In Examplo sp. X, a complete genome, the two loci sit together (3 genes apart)." in _text(D)


def test_a_position_that_contradicts_sets_the_partner_aside(tmp_path):
    """Benchmark: a false HIGH link passed the KCB rule; its loci were 1,118 genes apart in a complete relative."""
    D = _D(tmp_path)
    D["scorecard"][frozenset(("BGC001", "BGC002"))] = {"layers_verdict": "APART_CLOSE", "relative_source": "Examplo sp. X",
                                                       "relative_assembly": "complete", "locus_gap_genes": "1118"}
    shown, aside = ss.split_partners(D, "BGC001")
    assert not shown and aside[0]["other"] == "BGC002" and "separate clusters" in _text(D)


def test_position_alone_surfaces_a_partner_without_kcb(tmp_path):
    D = _D(tmp_path, partner_rank=4)  # the shared cluster is outside the partner's top three: no KCB signal
    D["scorecard"][frozenset(("BGC001", "BGC002"))] = {"layers_verdict": "CONSISTENT", "relative_source": "Examplo sp. X",
                                                       "relative_assembly": "draft", "locus_gap_genes": "0"}
    (x,), _ = ss.split_partners(D, "BGC001")
    assert x["other"] == "BGC002" and not x["conc"] and "does not show them hitting different genes" in _text(D)


def test_a_shared_cluster_outside_either_top_three_does_not_count(tmp_path):
    assert ss.split_partners(_D(tmp_path, partner_rank=4), "BGC001") == ([], [])


def test_no_rggmci_link_means_no_split_signal(tmp_path):
    assert ss.split_partners(_D(tmp_path, rgg_conf="LOW_SHARED_REFERENCE_SIGNAL"), "BGC001") == ([], [])


def test_steps_come_from_the_reference_product_then_the_found_genes_pfam():
    D = {"gfeat": {"g1": [{"domain": "PF00001", "i_evalue": "1e-50"}]}, "pfam": {"PF00001": "Trp_halogenase"}}
    assert ss.step_of({"reference_product": "putative O-glycosyltransferase"}) == "glycosylation"
    assert ss.step_of({"reference_product": "D-glucose O-methyltransferase"}) == "methylation"
    assert ss.step_of({"reference_product": "AbcH", "best_locus": "g1", "reference_gene_kind": "biosynthetic"}, D) \
        == "halogenation"
    assert ss.step_of({"reference_product": "unknown"}) == "unannotated in the reference"


def test_no_assembled_block_when_every_find_is_on_the_core_contig():
    """A gap rescue whose finds all sit in the core region assembles nothing across contigs; the block is left out so
    the region's own biosynthetic-logic lines stay."""
    D = {"kcb": {}, "mibig_names": {}, "gfeat": {}, "pfam": {}, "src": {}}
    st = {"table": [{"name": "abcA", "status": "PRESENT_IN_CORE", "best_locus": "c_1", "best_identity_pct": "80",
                     "best_contig": CORE, "reference_product": "synthase", "reference_gene_kind": "biosynthetic"},
                    {"name": "abcB", "status": "MISSING_NOT_FOUND", "best_locus": "", "best_identity_pct": ""}]}
    assert ss.pathway_paras(D, {"reference": "BGC0000010"}, st) == []


def test_the_banner_counts_links_without_a_settled_verdict(tmp_path):
    """With a verdict table, a region keeps its review-draft banner while any shown link is unresolved or unruled."""
    D = _D(tmp_path)
    D["verdicts"] = {}
    assert ss.unsettled_links(D, "BGC001") == (1, 1)
    D["verdicts"] = {"BGC001": [{"partner region": "S / C2 / region001 / BGC002", "verdict": "UNRESOLVED"}]}
    assert ss.unsettled_links(D, "BGC001") == (1, 1)
    D["verdicts"]["BGC001"][0]["verdict"] = "REJECT"
    assert ss.unsettled_links(D, "BGC001") == (0, 1)
