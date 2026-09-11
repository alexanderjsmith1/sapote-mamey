"""v9.7.43 — _blast_hits must accept locus-tag-named query genes, not only ctg-prefixed ones.

Shake-down finding: public WGS genomes name query genes by locus tag (e.g. GTY48_01375), whereas the
internal AS assemblies name them ctg1_45. The old filter required the query gene to start with 'ctg', so
every Blast-hits row was skipped on locus-tag genomes -> 0 subjects, 0 identity -> RG-GMCI silently
degenerate (adjacency basis all NONE). The gate now keys on the 6-column data-row structure instead.
"""
import mamey.rggmci as rg

LOCUS_TAG_BLOCK = """1. BGC0000309.5
Source: bacillibactin
Type: NRPS:Type I
Number of proteins with BLAST hits to this cluster: 6
Cumulative BLAST score: 5162.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
GTY48_01375\tBSU_31959\t60\t94\t83.78\t5.77e-27
GTY48_01380\tBSU_31960\t65\t3129\t99.83\t0.0
GTY48_01385\tBSU_31970\t59\t373\t103.0\t2.31e-130
"""

CTG_BLOCK = """1. BGC0001234.1
Source: enduracidin
Type: NRPS

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg1_45\tAEN_00112\t72\t880\t98.1\t1e-200
ctg1_46\tAEN_00113\t68\t640\t95.0\t1e-150
"""


def test_locus_tag_query_genes_parse():
    hits = rg._blast_hits(LOCUS_TAG_BLOCK)
    assert len(hits) == 3, "locus-tag query genes must not be filtered out"
    assert hits[0] == ("BSU_31959", 60.0)
    assert [s for s, _ in hits] == ["BSU_31959", "BSU_31960", "BSU_31970"]


def test_ctg_query_genes_still_parse():
    hits = rg._blast_hits(CTG_BLOCK)  # no regression on internal-assembly naming
    assert len(hits) == 2
    assert hits[0] == ("AEN_00112", 72.0)


def test_header_and_blank_lines_rejected():
    # the table header line and blank lines have <6 tab columns / non-numeric col 3 -> skipped.
    hits = rg._blast_hits(LOCUS_TAG_BLOCK)
    assert all(s and not s.startswith("Table") for s, _ in hits)


def test_identity_populated_from_blast_hits():
    idents = [i for _, i in rg._blast_hits(LOCUS_TAG_BLOCK)]
    assert idents == [60.0, 65.0, 59.0]
    assert rg._extract_mean_identity(LOCUS_TAG_BLOCK) == 61.3  # round((60+65+59)/3,1)
