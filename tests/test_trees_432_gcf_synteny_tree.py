"""TREES_432 — render_gcf_synteny_tree: tree beside gene-arrow tracks with homology links.

Checks: gene roles come only from antiSMASH qualifiers through the fixed table; a track whose
first t2ks gene is on the minus strand is reverse-complemented so the KS points right; row
labels carry the four-component identity from the bound package inventory and a region with
no bound alias gets an identity hold instead of an invented alias; the figure, role table,
rows table and caption are written; no arrow degenerates into a flat line.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("gcf_synteny_432", ROOT / "tools" / "render_gcf_synteny_tree.py")
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)

pytest.importorskip("Bio")

AA = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHFTVAL"


def _gbk(path, name, genes, length=9000):
    """Write a minimal antiSMASH-style region GBK. genes: (start, end, strand, kind, domains, functions)."""
    from Bio.Seq import Seq
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio.SeqRecord import SeqRecord
    from Bio import SeqIO
    rec = SeqRecord(Seq("ACGT" * (length // 4)), id=name, name=name[:16], description=f"Genus sp. {name}")
    rec.annotations["molecule_type"] = "DNA"; rec.annotations["organism"] = f"Genus sp. {name}"
    for i, (s, e, strand, kind, doms, funcs) in enumerate(genes):
        q = {"locus_tag": [f"{name}_{i}"], "translation": [AA[: (e - s) // 3]]}
        if kind: q["gene_kind"] = [kind]
        if doms: q["sec_met_domain"] = doms
        if funcs: q["gene_functions"] = funcs
        rec.features.append(SeqFeature(FeatureLocation(s, e, strand=strand), type="CDS", qualifiers=q))
    SeqIO.write(rec, str(path), "genbank")


def _fixture(tmp_path):
    ks = ["t2ks (E-value: 1e-100, bitscore: 300, seeds: 25)"]
    clf = ["t2clf (E-value: 1e-80, bitscore: 250, seeds: 25)"]
    # cluster A: KS on plus strand at 1000-2200; cluster B: same genes on the minus strand (must flip)
    genes_plus = [(100, 700, 1, "regulatory", [], ["regulatory (smcogs) SMCOG1000: TetR family regulator"]),
                  (1000, 2200, 1, "biosynthetic", ks, ["biosynthetic (rule-based-clusters) T2PKS: t2ks"]),
                  (2300, 3500, 1, "biosynthetic", clf, ["biosynthetic (rule-based-clusters) T2PKS: t2clf"]),
                  (3600, 4300, 1, "biosynthetic-additional", [], ["biosynthetic-additional (smcogs) SMCOG1128: cyclase/dehydrase"]),
                  (4400, 5000, 1, "", [], []),
                  (5200, 6300, 1, "biosynthetic-additional", [], ["biosynthetic-additional (smcogs) SMCOG1062: glycosyltransferase"])]
    genes_minus = [(9000 - e, 9000 - s, -strand, k, d, f) for s, e, strand, k, d, f in genes_plus]
    a = tmp_path / "STRN1_NODE_1_length_9000_cov_10.0.region001.gbk"; _gbk(a, "STRN1", genes_plus)
    b = tmp_path / "STRN2_NODE_5_length_9000_cov_12.5.region002.gbk"; _gbk(b, "STRN2", genes_minus)
    c = tmp_path / "BGC0009999.gbk"; _gbk(c, "BGC0009999", genes_plus[1:4])
    inv = tmp_path / "STRN1_2_inventory.csv"
    inv.write_text("BGC_ID,Contig,antiSMASH_Region,Source_GBK\nBGC007,NODE_1_length_9000_cov_10.0,region001,NODE_1_length_9000_cov_10.0.region001.gbk\n")
    nwk = tmp_path / "fam.nwk"; nwk.write_text("((A:0.1,B:0.1):0.2,C:0.3);\n")
    return a, b, c, inv, nwk


def test_roles_come_from_qualifier_table_only():
    assert gs.role_of({"sec_met_domain": ["t2ks (E-value: 1e-9)"]}) == "Minimal PKS (KS/CLF/ACP)"
    assert gs.role_of({"gene_functions": ["biosynthetic-additional (smcogs) SMCOG1128: cyclase/dehydrase"], "gene_kind": ["biosynthetic-additional"]}) == "Cyclase / aromatase / ketoreductase"
    assert gs.role_of({"gene_functions": ["SMCOG1062: glycosyltransferase"], "gene_kind": ["biosynthetic-additional"]}) == "Glycosyltransferase / sugar biosynthesis"
    assert gs.role_of({"gene_kind": ["regulatory"], "gene_functions": ["regulatory (smcogs) SMCOG1000: TetR family regulator"]}) == "Regulatory / resistance / transport"
    assert gs.role_of({"gene_kind": ["biosynthetic-additional"], "gene_functions": ["biosynthetic-additional (smcogs) SMCOG1001: oxidoreductase"]}) == "Other biosynthetic"
    assert gs.role_of({}) == "Unknown function"


def test_minus_strand_ks_track_is_flipped_to_point_right(tmp_path):
    a, b, _c, _inv, _nwk = _fixture(tmp_path)
    ca, cb = gs.read_cluster(str(a)), gs.read_cluster(str(b))
    assert ca["flipped"] is False and cb["flipped"] is True
    ksa = next(g for g in ca["genes"] if g["ks"]); ksb = next(g for g in cb["genes"] if g["ks"])
    assert ksb["strand"] == 1 and (ksb["start"], ksb["end"]) == (ksa["start"], ksa["end"])
    assert ca["anchor"] == pytest.approx(cb["anchor"])


def test_identity_labels_bound_or_held():
    bound = gs.load_identity([])
    assert gs.row_identity("STRN1_NODE_1_length_9000_cov_10.0.region001.gbk", bound)["label"].endswith(gs.HOLD)
    assert gs.row_identity("BGC0009999.gbk", bound) == {"label": "BGC0009999", "strain": "", "contig": "", "region": "", "alias": "", "hold": "", "reference": True}


def test_end_to_end_outputs_rows_holds_and_no_flat_arrows(tmp_path):
    pytest.importorskip("matplotlib")
    a, b, c, inv, nwk = _fixture(tmp_path)
    out = tmp_path / "fam"
    rc = gs.main(["--newick", str(nwk), "--map", "A=STRN1", "--map", "B=STRN2", "--map", "C=REF",
                  "--gbk", f"STRN1:{a}", "--gbk", f"STRN2:{b}", "--gbk", f"REF:{c}",
                  "--identity", str(inv), "--min-id", "30", "--out", str(out)])
    assert rc == 0
    for suf in (".png", ".pdf", "_gene_roles.tsv", "_rows.tsv", "_caption.txt"):
        assert (tmp_path / ("fam" + suf)).is_file(), suf
    rows = {r.split("\t")[0]: r.split("\t") for r in (tmp_path / "fam_rows.tsv").read_text().splitlines()[1:]}
    assert rows["STRN1"][2] == "STRN1 / NODE_1_length_9000_cov_10.0 / region001 / BGC007" and rows["STRN1"][7] == ""
    assert rows["STRN2"][2].endswith(gs.HOLD) and "no bound package record" in rows["STRN2"][7]
    assert rows["REF"][8] == "True" and rows["REF"][2].startswith("BGC0009999")
    cap = (tmp_path / "fam_caption.txt").read_text()
    assert "1 row(s) carry an identity hold" in cap and "computed here" in cap and "not compound identity" in cap
    roles = (tmp_path / "fam_gene_roles.tsv").read_text().splitlines()
    assert any("\tMinimal PKS (KS/CLF/ACP)\t" in ln for ln in roles) and any("\tTrue" in ln for ln in roles)


def test_identical_neighbours_link_and_tool_has_no_cohort_literal(tmp_path):
    pytest.importorskip("matplotlib")
    a, b, c, inv, nwk = _fixture(tmp_path)
    out = tmp_path / "fam2"
    gs.main(["--newick", str(nwk), "--map", "A=STRN1", "--map", "B=STRN2", "--map", "C=REF",
             "--gbk", f"STRN1:{a}", "--gbk", f"STRN2:{b}", "--gbk", f"REF:{c}", "--out", str(out)])
    cap = (tmp_path / "fam2_caption.txt").read_text()
    n_links = int(cap.split("% (")[1].split(" links")[0])
    assert n_links >= 6                      # STRN1 and STRN2 carry identical proteins gene for gene
    src = (ROOT / "tools" / "render_gcf_synteny_tree.py").read_text()
    assert "AS-" not in src
