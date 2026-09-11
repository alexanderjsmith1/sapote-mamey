"""Deterministic unit tests for the in-engine PKS-KS clade channel — no shipped data required.

Builds a tiny synthetic antiSMASH-style region-GBK zip in tmp_path (two contigs; the two KS on different contigs
are near-identical), then asserts the scan finds a cross-contig KS_CLADE_LINK and stays claim-safe.
"""
import os
import zipfile

from mamey.pks_ks_scan import (run_pks_ks_scan, write_pks_ks_csv, ks_domains_from_gbk,
                               _containment, _kmers)

# a ~120 aa KS-like sequence and a near-identical variant (few substitutions) + an unrelated one
KS_A = ("MTDSEKVAIVGMACRFPGADNPEEFWQLLREGRDAISEVPADRWДISEDYYDPDPEAPGKمYTRRGGFLДDVД" .encode("ascii", "ignore").decode()
        + "AGFDAEFFGISPREАРАМDPQQRLLLEТSWEALEDAGIДPКSLАGSДТGVFVGISНЗ")[:120].ljust(120, "A")
KS_A2 = KS_A[:60] + "C" + KS_A[61:]                       # 1 substitution -> near-identical
KS_B = ("MKRVVITGМGАVTPLGЕТVДЕТWКАLLАGКSGIГПITРFDАSКYПТКIАGЕVКДFДПТДYМДККЕАКRМDР" .encode("ascii", "ignore").decode()
        + "FIQFGМААSКQАLАDАGLЕIТЕЕNАДRIGVIIGSGIGGLПVIЕ")[:120].ljust(120, "G")


def _region_gbk(contig, seqs, subtype="Modular-KS"):
    """Minimal GBK text with `region` + `aSDomain PKS_KS` features carrying /translation.

    Real antiSMASH PKS_KS aSDomains carry /domain_subtypes; since .366 the _4B scan partitions the clade
    pass by that subtype, so the synthetic fixture must carry one too. A same-gene split (KS_A/KS_A2) shares
    a subtype by construction, which is exactly what these tests model.
    """
    feats = []
    pos = 100
    for i, s in enumerate(seqs, 1):
        feats.append(
            f"     aSDomain       {pos}..{pos+360}\n"
            f'                     /aSDomain="PKS_KS"\n'
            f'                     /locus_tag="ctg_{contig}_{i}"\n'
            f'                     /domain_subtypes="{subtype}"\n'
            f'                     /translation="{s}"\n'
        )
        pos += 500
    header = (f"LOCUS       {contig}            9000 bp    DNA     linear\n"
              "FEATURES             Location/Qualifiers\n"
              "     region          1..9000\n"
              '                     /product="T1PKS"\n')
    return header + "".join(feats) + "//\n"


def _make_zip(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("NODE_1_length_9000_cov_50.region001.gbk", _region_gbk("NODE_1", [KS_A, KS_B]))
        zf.writestr("NODE_2_length_9000_cov_50.region001.gbk", _region_gbk("NODE_2", [KS_A2]))
    return path


def test_ks_extraction_parses_translations():
    txt = _region_gbk("NODE_1", [KS_A, KS_B])
    doms = ks_domains_from_gbk(txt, "NODE_1_length_9000_cov_50", 1)
    assert len(doms) == 2
    assert all(d["length"] >= 100 for d in doms)
    assert doms[0]["short"] == "NODE_1"


def test_containment_symmetry_and_range():
    a, b = _kmers(KS_A), _kmers(KS_A2)
    c = _containment(a, b)
    assert 0.0 <= c <= 1.0
    assert _containment(a, b) == _containment(b, a)
    assert _containment(a, a) == 1.0


def test_cross_contig_clade_detected(tmp_path):
    z = _make_zip(os.path.join(tmp_path, "SYN-1_new.zip"))
    scan = run_pks_ks_scan(z)
    assert scan["n_ks"] == 3
    assert scan["n_contigs"] == 2
    # KS_A (NODE_1) and KS_A2 (NODE_2) are near-identical across contigs -> one cross-contig clade
    assert len(scan["cross_contig_clades"]) == 1
    cl = scan["cross_contig_clades"][0]
    assert set(cl["contigs"]) == {"NODE_1", "NODE_2"}
    # near-identical -> flagged iterative/same-gene, not a bare link
    assert cl["flag"] == "ITERATIVE/SAME-GENE_SPLIT"


def test_csv_is_claim_safe(tmp_path):
    z = _make_zip(os.path.join(tmp_path, "SYN-1_new.zip"))
    scan = run_pks_ks_scan(z)
    out = write_pks_ks_csv(scan, os.path.join(tmp_path, "SYN-1_4B_pks_ks_fragment_scan.csv"), "SYN-1")
    body = open(out).read()
    assert "candidate" in body.lower() and "not a rescue" in body.lower()
    assert "Judgment deferred" in body


def test_missing_zip_never_raises():
    scan = run_pks_ks_scan("/no/such/file.zip")
    assert scan["n_ks"] == 0 and "summary_line" in scan     # degrades, never fails the core run
