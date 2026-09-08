"""v9.7.42 — RG-GMCI reference-keying fixes (Bug A: accession regex; Bug B: locus version suffix).

Found by the v9.7.41 lateral audit: MIBiG cluster references were keyed to garbage (ACCESSION_RE matched
all-caps keywords like NRPS/BLAST and never matched BGC#######), and GenBank-protein subject accessions
parsed their version suffix as the locus number — so MIBiG co-cluster references could never count toward
`good_geometry_references`, the exact axis the v9.7.41 gg>=2 gate tightened.
"""
import mamey.rggmci as rg


# ---- Bug A: accession regex ----

def test_accession_matches_mibig_bgc():
    assert rg.ACCESSION_RE.search("1. BGC0002460").group(0) == "BGC0002460"


def test_accession_matches_genome_accessions():
    for s in ("NZ_CP029601.1", "NZ_CP000001", "CP029601", "JAAA01000001"):
        assert rg.ACCESSION_RE.search(s), s


def test_accession_rejects_class_and_header_keywords():
    for kw in ("NRPS", "BLAST", "PKS", "Type", "Source", "Cumulative", "Number"):
        assert rg.ACCESSION_RE.search(kw) is None, kw


def test_first_accession_picks_bgc_not_keyword():
    block = (">>\n1. BGC0002460\nSource: Salinispora loonamycin biosynthetic gene cluster\n"
             "Type: NRPS,T1PKS\nCumulative BLAST score: 4200\n")
    assert rg._first_accession(block) == "BGC0002460"


# ---- Bug B: locus version suffix ----

def test_locus_num_strips_version_suffix():
    assert rg._locus_num("QJU69504.1") == 69504
    assert rg._locus_num("QJU69510.1") == 69510


def test_locus_key_strips_version_suffix():
    assert rg._locus_key("QJU69504.1") == ("QJU", 69504)


def test_locus_key_unchanged_for_normal_tags():
    assert rg._locus_key("AMK09_RS30055") == ("AMK09_RS", 30055)
    assert rg._locus_key("X_RS30040") == ("X_RS", 30040)


# ---- Integration: the two fixes restore MIBiG-protein proxy adjacency ----

def test_mibig_protein_subjects_now_adjacent_via_proxy():
    # two protein accessions from the same MIBiG cluster, 6 loci apart -> ADJACENT under the proxy.
    def ref(subjects):
        return rg.ClusterBlastReference(
            bgc_id="b", contig="c", region_number=1, region_key=None, ref="BGC0002460",
            source="s", reference_type="nrps", rank=1, nprot=8, cumulative_score=4200.0,
            mean_identity=70, interval_start=None, interval_end=None, source_file="f",
            subjects=tuple(subjects))
    cls, gap, ov, ofrac, basis, span = rg._adjacency(
        ref(["QJU69504.1", "QJU69505.1"]), ref(["QJU69510.1", "QJU69511.1"]))
    assert basis == "LOCUS_PROXY"
    assert cls == "ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS"
    assert gap <= rg.ADJ_MAX_LOCUS_GAP
