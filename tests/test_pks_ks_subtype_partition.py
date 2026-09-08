"""_4B KS-clade subtype partition (AMBER_366_C12, engine 1.9.121).

A cross-contig KS pair may co-cluster ONLY when both domains carry the same antiSMASH /domain_subtypes.
Hybrid-KS joins only Hybrid-KS; UNCLASSIFIED stands as its own group. These tests pin Amber's edge policy
so a trans-AT KS can never bridge into a cis-AT clade by transitivity.
"""
import io
import os
import zipfile

import pytest

from mamey import pks_ks_scan as P

# One ~120-aa KS slice, identical on both contigs so k-mer containment = 1.0 (>= DEFAULT_THRESHOLD).
_KS_SEQ = ("MRAVVTGLGVVTPLGNTVeeswknllagksgigpitrfdasgyptriagevkdfdpaeym"
           "drkearrmdrfaqfavaaakeavadsglditpeneraigvviGSGIGGLPTiedaqtvlk"
           "ekgprrvspffvpmimpNMAAGQVAIRLGA").replace("\n", "").upper()


def _gbk(locus, subtype):
    """Minimal antiSMASH-style GBK text with one PKS_KS aSDomain carrying /domain_subtypes."""
    sub = f'\n                     /domain_subtypes="{subtype}"' if subtype else ""
    return (
        "LOCUS       synthetic 1000 bp DNA linear\n"
        "FEATURES             Location/Qualifiers\n"
        "     aSDomain        1..360\n"
        '                     /aSDomain="PKS_KS"\n'
        f'                     /locus_tag="{locus}"'
        f"{sub}\n"
        f'                     /translation="{_KS_SEQ}"\n'
        "//\n"
    )


def _zip_two(sub_a, sub_b):
    """Two region GBKs on different NODE contigs; return an in-memory zip path-like bytes buffer."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("NODE_1.region1.gbk", _gbk("ctgA_1", sub_a))
        zf.writestr("NODE_2.region1.gbk", _gbk("ctgB_1", sub_b))
    buf.seek(0)
    return buf


def test_parse_captures_subtype():
    doms = P.ks_domains_from_gbk(_gbk("x", "Trans-AT-KS"), "NODE_1", 1)
    assert len(doms) == 1
    assert doms[0]["subtype"] == "Trans-AT-KS"


def test_missing_subtype_is_unclassified():
    doms = P.ks_domains_from_gbk(_gbk("x", ""), "NODE_1", 1)
    assert doms[0]["subtype"] == P._UNCLASSIFIED_SUBTYPE


def test_same_subtype_cross_contig_unions():
    scan = P.run_pks_ks_scan(_zip_two("Trans-AT-KS", "Trans-AT-KS"))
    assert scan["n_ks"] == 2
    clades = scan["cross_contig_clades"]
    assert len(clades) == 1, "identical KS + same subtype on two contigs must form one cross-contig clade"
    assert clades[0]["ks_subtype"] == "Trans-AT-KS"
    assert sorted(clades[0]["contigs"]) == ["NODE_1", "NODE_2"]


def test_mismatched_subtype_does_not_union():
    # trans-AT vs cis-AT (Modular): identical sequence, but MUST NOT bridge -> no cross-contig clade.
    scan = P.run_pks_ks_scan(_zip_two("Trans-AT-KS", "Modular-KS"))
    assert scan["n_ks"] == 2
    assert scan["cross_contig_clades"] == []


def test_hybrid_only_with_hybrid():
    # Hybrid must not bridge into a named cis/trans clade.
    assert P.run_pks_ks_scan(_zip_two("Hybrid-KS", "Trans-AT-KS"))["cross_contig_clades"] == []
    assert len(P.run_pks_ks_scan(_zip_two("Hybrid-KS", "Hybrid-KS"))["cross_contig_clades"]) == 1


def test_unclassified_pair_surfaces_pairwise():
    # Amber ASK-1 ruling (b): two UNCLASSIFIED KS, identical seq, different contigs -> surface as ONE
    # pairwise candidate (not dropped). It is a KSU clade of exactly 2 members carrying UNCLASSIFIED.
    scan = P.run_pks_ks_scan(_zip_two("", ""))
    clades = scan["cross_contig_clades"]
    assert len(clades) == 1
    assert clades[0]["ks_subtype"] == P._UNCLASSIFIED_SUBTYPE
    assert clades[0]["n_ks"] == 2
    assert clades[0]["clade_id"].startswith("KSU")


def _zip_three_unclassified():
    """Three UNCLASSIFIED KS, identical seq, on three different contigs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for node in ("NODE_1", "NODE_2", "NODE_3"):
            zf.writestr(f"{node}.region1.gbk", _gbk(f"ctg_{node}", ""))
    buf.seek(0)
    return buf


def test_unclassified_pairwise_not_bridge():
    # pairwise-not-bridge condition: 3 identical UNCLASSIFIED KS on 3 contigs must surface as 3 PAIRWISE
    # candidates (C(3,2)=3), NEVER collapse into one 3-member bridged clade.
    scan = P.run_pks_ks_scan(_zip_three_unclassified())
    clades = scan["cross_contig_clades"]
    assert len(clades) == 3, "3 unclassified KS must be 3 pairwise pairs, not 1 merged blob"
    assert all(c["n_ks"] == 2 for c in clades), "no unclassified clade may exceed a pair (no transitive bridge)"
    assert all(c["ks_subtype"] == P._UNCLASSIFIED_SUBTYPE for c in clades)


def test_partition_version_in_csv(tmp_path):
    scan = P.run_pks_ks_scan(_zip_two("Iterative-KS", "Iterative-KS"))
    out = tmp_path / "AS-TEST_4B_pks_ks_fragment_scan.csv"
    P.write_pks_ks_csv(scan, str(out), strain_id="AS-TEST")
    head = out.read_text().splitlines()[0]
    assert "ks_subtype" in head
    assert "ks_subtype_partition_version" in head
    assert P.KS_SUBTYPE_PARTITION_VERSION == "1"
