"""Property tests for the v9.7.91 manual-BLASTP worklist fix.

Guards the *class* of bug (silent-empty worklist + missing node/contig locator),
not one strain. The current minimal object fixture is authored entirely in code:
WORKLIST-FIXTURE-001 uses a 300-base toy contig, CDS 30..90, one-letter M translation,
and chosen qualifier/score inputs; it is not a biological observation.
Regression lock on the v9.7.90 defect where candidate_blastp_rows
scored only locus_tag + product (product is None on these GBKs) -> 0 rows.
"""
from mamey.models import BGCRecord, CDSFeature
from mamey.crosswalk import candidate_blastp_rows, kcb_closest_gene


def _bgc(bgc_id="BGC008", contig="NODE_1_length_300_cov_1.0", node_id="1"):
    return BGCRecord(
        bgc_id=bgc_id, contig=contig, region_number=1, start=0, end=300,
        contig_length=300, node_id=node_id, antismash_region="region001",
        source_gbk="NODE_1.region001.gbk", user_label="",
    )


def _cds(locus_tag, contig="NODE_1_length_300_cov_1.0", sec_met_domain="",
         gene_functions="", product=None, translation="M", start=30, end=90):
    q = {}
    if sec_met_domain:
        q["sec_met_domain"] = [sec_met_domain]
    if gene_functions:
        q["gene_functions"] = [gene_functions]
    return CDSFeature(
        contig=contig, start=start, end=end, strand=1, locus_tag=locus_tag,
        product=product, translation=translation, qualifiers=q,
    )


def test_worklist_nonempty_when_biosynthetic_cds_present():
    """The v9.7.90 regression: product=None but sec_met_domain/gene_functions populated -> NOT empty."""
    cds = [_cds("fixture_cds_1",
                sec_met_domain="nikJ (E-value: 1e-8, bitscore: 25.0, seeds: 4, tool: rule-based-clusters)",
                gene_functions="biosynthetic (rule-based-clusters) nucleoside: nikJ")]
    rows = candidate_blastp_rows([_bgc()], cds, strain="WORKLIST-FIXTURE-001")
    assert rows, "worklist empty despite a biosynthetic CDS (product=None, qualifiers set)"


def test_worklist_surfaces_kcb_gene_and_locator():
    cds = [_cds("fixture_cds_1",
                sec_met_domain="nikJ (E-value: 1e-8, bitscore: 25.0, seeds: 4, tool: rule-based-clusters)",
                gene_functions="biosynthetic (rule-based-clusters) nucleoside: nikJ")]
    r = candidate_blastp_rows([_bgc()], cds, strain="WORKLIST-FIXTURE-001")[0]
    assert r["kcb_closest_gene"] == "nikJ"
    assert r["kcb_bitscore"] == "25.0"
    # node/contig-locator invariant: every row must carry contig + locus_tag
    assert r["contig"].startswith("NODE_1") and r["protein_id"] == "fixture_cds_1"
    assert r["user_blastp_label"] == "WORKLIST-FIXTURE-001 fixture_cds_1"


def test_kcb_extractor_skips_pfam_accessions():
    c = _cds("ctg1_1", sec_met_domain="PF04055 (E-value: 7.2e-15, bitscore: 45.4, seeds: 518)",
             gene_functions="biosynthetic-additional (rule-based-clusters) PF04055")
    assert kcb_closest_gene(c) == ("", "")  # Pfam accession is not a gene name


def test_kcb_extractor_prefers_rule_based_clusters_gene():
    # rule-based-clusters assignment in gene_functions confirms the gene; bitscore from sec_met_domain
    c = _cds("ctg1_2",
             sec_met_domain="truD (E-value: 1e-4, bitscore: 12.0) nikJ (E-value: 1e-8, bitscore: 25.0)",
             gene_functions="biosynthetic (rule-based-clusters) nucleoside: nikJ")
    name, bs = kcb_closest_gene(c)
    assert name == "nikJ" and bs == "25.0"


def test_kcb_extractor_conservative_without_rbc_assignment():
    # no rule-based-clusters gene assignment -> we do NOT guess from sec_met_domain (avoids
    # surfacing catalytic-domain fragments like 'synt'/'Condensation' as a gene name)
    c = _cds("ctg1_3", sec_met_domain="Condensation (E-value: 1e-50, bitscore: 226.1)", gene_functions="")
    assert kcb_closest_gene(c) == ("", "")


def test_worklist_empty_when_no_biosynthetic_signal():
    # a CDS with no priority term and no sec_met_domain should not be selected
    cds = [_cds("ctg9_4", sec_met_domain="", product=None)]
    assert candidate_blastp_rows([_bgc()], cds, strain="WORKLIST-FIXTURE-001") == []
