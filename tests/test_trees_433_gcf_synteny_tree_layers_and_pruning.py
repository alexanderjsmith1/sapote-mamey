"""TREES_433 — render_gcf_synteny_tree: label fit, reference-layer rows, pruned view.

Checks: a reference-layer file (`SID_…`, `TYPE_…`, `<stem>__<region>`) is a reference row labelled by layer,
organism and accession and never gets a package identity hold; a query row is wrapped onto two lines and the
figure is at least as wide as its longest label line needs; a family above --max-tips is pruned keeping every
query and MIBiG tip and the references nearest the focal rows, and the title and caption say so; the rows table
carries the layer column; the tool still has no cohort literal.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("gcf_synteny_433", ROOT / "tools" / "render_gcf_synteny_tree.py")
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)

pytest.importorskip("Bio")

AA = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHFTVAL"


def _gbk(path, name, genes, organism=None, length=9000):
    from Bio.Seq import Seq
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio.SeqRecord import SeqRecord
    from Bio import SeqIO
    rec = SeqRecord(Seq("ACGT" * (length // 4)), id=name, name=name[:16], description=f"{name} Genus refspecies strain X1 chromosome, complete genome")
    rec.annotations["molecule_type"] = "DNA"; rec.annotations["organism"] = organism if organism is not None else f"Genus sp. {name}"
    for i, (s, e, strand, kind, doms, funcs) in enumerate(genes):
        q = {"locus_tag": [f"{name}_{i}"], "translation": [AA[: (e - s) // 3]]}
        if kind: q["gene_kind"] = [kind]
        if doms: q["sec_met_domain"] = doms
        if funcs: q["gene_functions"] = funcs
        rec.features.append(SeqFeature(FeatureLocation(s, e, strand=strand), type="CDS", qualifiers=q))
    SeqIO.write(rec, str(path), "genbank")


GENES = [(100, 700, 1, "regulatory", [], ["regulatory (smcogs) SMCOG1000: TetR family regulator"]),
         (1000, 2200, 1, "biosynthetic", ["t2ks (E-value: 1e-100, bitscore: 300, seeds: 25)"], ["biosynthetic (rule-based-clusters) T2PKS: t2ks"]),
         (2300, 3500, 1, "biosynthetic", ["t2clf (E-value: 1e-80, bitscore: 250, seeds: 25)"], ["biosynthetic (rule-based-clusters) T2PKS: t2clf"]),
         (3600, 4300, 1, "biosynthetic-additional", [], ["biosynthetic-additional (smcogs) SMCOG1128: cyclase/dehydrase"])]


def _family(tmp_path, n_ref=6):
    """One query, one MIBiG, one SID, one TYPE, one stem__region file and n_ref extra TYPE references."""
    files = {}
    q = tmp_path / "STRN1_NODE_12_length_123456_cov_10.123456.region003.gbk"; _gbk(q, "STRN1", GENES); files["Q"] = q
    m = tmp_path / "BGC0009999.gbk"; _gbk(m, "BGC0009999", GENES[1:]); files["M"] = m
    s = tmp_path / "SID_SID42_WWXX01000001.1.region001.gbk"; _gbk(s, "SID42", GENES, organism="Genus sp. SID42"); files["S"] = s
    t = tmp_path / "TYPE_Genus_typicus_DSM_1_CP000001.1.region002.gbk"; _gbk(t, "TYPEX", GENES, organism="."); files["T"] = t
    c = tmp_path / "Genus_other__GCF_000000001.1__NZ_ABCD01000001.1.region001.gbk"; _gbk(c, "OTHER", GENES, organism="."); files["C"] = c
    for i in range(n_ref):
        r = tmp_path / f"TYPE_Genus_ref{i}_CP00000{i}.1.region001.gbk"; _gbk(r, f"REF{i}", GENES[:2], organism=f"Genus ref{i}"); files[f"R{i}"] = r
    inv = tmp_path / "STRN1_2_inventory.csv"
    inv.write_text("BGC_ID,Contig,antiSMASH_Region,Source_GBK\nBGC012,NODE_12_length_123456_cov_10.123456,region003,NODE_12_length_123456_cov_10.123456.region003.gbk\n")
    refs = ",".join(f"R{i}:0.{5+i}" for i in range(n_ref))
    tail = f"(C:0.3,({refs}):0.2):0.1" if n_ref else "C:0.4"
    nwk = tmp_path / "fam.nwk"; nwk.write_text(f"(((Q:0.05,M:0.05):0.1,(S:0.1,T:0.1):0.1):0.1,{tail});\n")
    return files, inv, nwk


def _args(files, inv, nwk, out, extra=()):
    args = ["--newick", str(nwk), "--identity", str(inv), "--min-id", "30", "--out", str(out)]
    for k, p in files.items():
        args += ["--map", f"{k}={k}", "--gbk", f"{k}:{p}"]
    return args + list(extra)


def test_layer_files_are_reference_rows_without_identity_hold():
    sid = gs.layer_identity("SID_SID42_WWXX01000001.1.region001.gbk", "Genus sp. SID42")
    assert sid["reference"] and sid["hold"] == "" and sid["layer"] == "SID" and sid["label"] == "SID Genus sp. SID42 WWXX01000001.1 region001"
    typ = gs.layer_identity("TYPE_Genus_typicus_DSM_1_CP000001.1.region002.gbk", "")
    assert typ["layer"] == "TYPE" and "Genus typicus DSM 1" in typ["label"] and typ["label"].endswith("CP000001.1 region002") and gs.HOLD not in typ["label"]
    stem = gs.layer_identity("Genus_other__GCF_000000001.1__NZ_ABCD01000001.1.region001.gbk", "")
    assert stem["layer"] == "REF" and stem["label"].startswith("REF Genus other") and stem["contig"] == "GCF_000000001.1__NZ_ABCD01000001.1"
    assert gs.layer_identity("STRN1_NODE_1_length_9000_cov_10.0.region001.gbk", "Genus sp.") is None
    assert gs.layer_identity("BGC0009999.gbk", "Genus sp.") is None


def test_definition_line_supplies_the_organism_when_organism_is_a_dot(tmp_path):
    p = tmp_path / "TYPE_Genus_typicus_DSM_1_CP000001.1.region002.gbk"; _gbk(p, "CP000001.1", GENES, organism=".")
    assert gs.definition_organism(str(p)) == "Genus refspecies strain X1"


def test_query_label_wraps_to_two_lines_and_figure_is_wide_enough(tmp_path):
    pytest.importorskip("matplotlib")
    files, inv, nwk = _family(tmp_path, n_ref=0)
    out = tmp_path / "fam"
    assert gs.main(_args(files, inv, nwk, out)) == 0
    assert gs.wrap_label("STRN1 / NODE_12_length_123456_cov_10.123456 / region003 / BGC012") == "STRN1 / NODE_12_length_123456_cov_10.123456\nregion003 / BGC012"
    from pypdf import PdfReader
    w_pt = float(PdfReader(str(out) + ".pdf").pages[0].mediabox.width)
    longest = len("STRN1 / NODE_12_length_123456_cov_10.123456")
    assert w_pt >= (longest * gs.LABEL_PT * 0.56 / 72.0 + 0.25 + 4.0 + 1.2) * 72 - 1   # label + tracks + tree
    rows = {r.split("\t")[0]: r.split("\t") for r in (tmp_path / "fam_rows.tsv").read_text().splitlines()[1:]}
    LABEL, HOLD, REF, LAYER = 2, 7, 8, 10                   # the layer column is appended last: older readers keep their positions
    assert rows["Q"][LAYER] == "query" and rows["Q"][LABEL] == "STRN1 / NODE_12_length_123456_cov_10.123456 / region003 / BGC012"
    assert rows["S"][LAYER] == "SID" and rows["S"][HOLD] == "" and rows["S"][REF] == "True"
    assert rows["T"][LAYER] == "TYPE" and rows["T"][HOLD] == "" and "Genus refspecies strain X1" in rows["T"][LABEL]
    assert rows["C"][LAYER] == "REF" and rows["C"][HOLD] == ""
    assert rows["M"][LAYER] == "MIBiG" and rows["M"][LABEL].startswith("BGC0009999")
    cap = (tmp_path / "fam_caption.txt").read_text()
    assert "0 row(s) carry an identity hold" in cap and "cohort reference-layer rows by layer, organism and accession" in cap


def test_pruned_view_keeps_query_and_mibig_and_nearest_references(tmp_path):
    pytest.importorskip("matplotlib")
    files, inv, nwk = _family(tmp_path, n_ref=6)          # 11 tips
    out = tmp_path / "pruned"
    assert gs.main(_args(files, inv, nwk, out, ["--max-tips", "5", "--focal", "STRN1"])) == 0
    rows = [r.split("\t") for r in (tmp_path / "pruned_rows.tsv").read_text().splitlines()[1:]]
    tips = {r[0] for r in rows}
    assert tips == {"Q", "M", "S", "T", "C"}                # query + MIBiG kept; S, T, C are the references nearest STRN1; R0..R5 pruned
    cap = (tmp_path / "pruned_caption.txt").read_text()
    assert "pruned view: 5 of 11 members" in cap and "every query and MIBiG member kept" in cap
    full = tmp_path / "full"
    assert gs.main(_args(files, inv, nwk, full)) == 0     # max-tips 0 (default) never prunes
    assert len((tmp_path / "full_rows.tsv").read_text().splitlines()) == 12


def test_halogenase_and_oxidative_tailoring_get_their_own_role():
    assert gs.role_of({"gene_kind": ["biosynthetic-additional"], "gene_functions": ["biosynthetic-additional (smcogs) SMCOG1119: halogenase"]}) == "Halogenase / oxidative tailoring"
    assert gs.role_of({"gene_kind": ["biosynthetic-additional"], "sec_met_domain": ["Trp_halogenase (E-value: 1e-50)"]}) == "Halogenase / oxidative tailoring"
    assert gs.role_of({"gene_kind": ["biosynthetic-additional"], "gene_functions": ["biosynthetic-additional (smcogs) SMCOG1007: cytochrome P450"]}) == "Halogenase / oxidative tailoring"
    assert gs.role_of({"gene_kind": ["biosynthetic-additional"], "gene_functions": ["biosynthetic-additional (smcogs) SMCOG1062: glycosyltransferase"]}) == "Glycosyltransferase / sugar biosynthesis"


def test_tool_has_no_cohort_literal():
    src = (ROOT / "tools" / "render_gcf_synteny_tree.py").read_text()
    assert "AS-" not in src


def test_prefilter_aligns_only_pfam_sharing_pairs_and_states_counts(tmp_path):
    """With --prefilter-db, a gene pair whose Pfam sets differ is never aligned (so never linked), an identical
    pair sharing a Pfam still links, and the caption reports candidate/total counts. Without the flag every pair
    is aligned as before."""
    pytest.importorskip("matplotlib")
    import sqlite3
    genes = [GENES[0], GENES[1], (2300, 3200, 1, "biosynthetic", GENES[2][4], GENES[2][5]), GENES[3]]   # distinct lengths: the scan is keyed by protein sequence
    a = tmp_path / "STRN1_NODE_1_length_9000_cov_10.0.region001.gbk"; _gbk(a, "STRN1", genes)
    b = tmp_path / "STRN2_NODE_5_length_9000_cov_12.5.region002.gbk"; _gbk(b, "STRN2", genes)
    db = tmp_path / "scan.db"; con = sqlite3.connect(db)
    con.executescript("create table gbk(id integer primary key, path text); create table cds(id integer primary key, gbk_id int, aa_seq text);"
                      "create table hsp(cds_id int, accession text);")
    from Bio import SeqIO
    cid = 0
    for gid, p in ((1, a), (2, b)):
        con.execute("insert into gbk values (?,?)", (gid, str(p)))
        for i, f in enumerate(next(SeqIO.parse(str(p), "genbank")).features):
            cid += 1; con.execute("insert into cds values (?,?,?)", (cid, gid, f.qualifiers["translation"][0]))
            # gene 0 (regulator): different Pfam in the two clusters -> not a candidate; gene 1 (KS): shared Pfam
            acc = f"PF0000{i}" if not (i == 0 and gid == 2) else "PF09999"
            con.execute("insert into hsp values (?,?)", (cid, acc))
    con.commit(); con.close()
    nwk = tmp_path / "t.nwk"; nwk.write_text("(A:0.1,B:0.1);\n")
    base = ["--newick", str(nwk), "--map", "A=STRN1", "--map", "B=STRN2", "--gbk", f"STRN1:{a}", "--gbk", f"STRN2:{b}", "--min-id", "30"]
    assert gs.main(base + ["--prefilter-db", str(db), "--out", str(tmp_path / "pf")]) == 0
    assert gs.main(base + ["--out", str(tmp_path / "full")]) == 0
    cap_pf = (tmp_path / "pf_caption.txt").read_text(); cap_full = (tmp_path / "full_caption.txt").read_text()
    n_pf = int(cap_pf.split("% (")[1].split(" links")[0]); n_full = int(cap_full.split("% (")[1].split(" links")[0])
    assert n_pf == 3 and n_full > n_pf                              # same-index pairs share a Pfam (KS, CLF, cyclase link); the regulator pair, whose Pfam differs, is excluded; without the filter every prefix-related pair aligns
    assert "alignment was computed for the" in cap_pf and "alignment was computed for the" not in cap_full
    cand, total = [int(x) for x in cap_pf.split("alignment was computed for the ")[1].split(" neighbouring")[0].split(" of ")]
    assert total == len(genes) ** 2 and cand == 3
