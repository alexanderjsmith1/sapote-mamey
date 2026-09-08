"""§4 gene table in Mode B cards (v9.7.155).

the Developer or User asked for actual gene tables alongside the §4 gene-by-gene prose. The Mode B
contract requires §4 to be prose-first (no table *replacing* the interpretation),
so the table is rendered ABOVE the prose authoring guidance: observed fact grid from
gene_context.jsonl (locus_tag, coords, strand, aa, sec_met domains, TTA, product),
node/contig on every row per the standing rule, catalytic-core genes flagged, and an
explicit claim-safe footnote that the product column is antiSMASH annotation, not a
product-identity claim. The prose walkthrough remains the interpretation.
"""
import json
import tempfile
from pathlib import Path

from mamey.modeb_template_emitter import (
    _bgc_facts, _gene_rows_for_bgc, _render_gene_table, _section_body,
)

ROWS = [
    {"bgc_id": "BGC008", "locus_tag": "ctg162_3", "contig": "NODE_162",
     "start": 2859, "end": 3950, "strand": 1, "aa_length": 363,
     "product": "KS-AT-DH PKS module", "sec_met_domains": ["PKS_KS", "PKS_AT"],
     "gene_kind": "biosynthetic", "tta_codons": 2},
    {"bgc_id": "BGC008", "locus_tag": "ctg162_5", "contig": "NODE_162",
     "start": 4650, "end": 5100, "strand": -1, "aa_length": 149,
     "product": "hypothetical protein", "sec_met_domains": [],
     "gene_kind": "other", "tta_codons": 1},
]


def _pkg(tmp, with_gc=True):
    p = Path(tmp)
    (p / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-901"}))
    (p / "AS-901_4_triage_board.csv").write_text(
        "BGC_ID,Node_ID,Contig\nBGC008,NODE_162,NODE_162\n")
    if with_gc:
        with (p / "AS-901_gene_context.jsonl").open("w") as f:
            for r in ROWS:
                f.write(json.dumps(r) + "\n")
    return p


def test_gene_rows_loaded_and_ordered():
    with tempfile.TemporaryDirectory() as d:
        p = _pkg(d)
        rows = _gene_rows_for_bgc(p, "BGC008")
        assert len(rows) == 2
        # genomic order by start
        assert rows[0]["start"] < rows[1]["start"]


def test_section4_contains_table_with_node_on_every_row():
    with tempfile.TemporaryDirectory() as d:
        p = _pkg(d)
        facts = _bgc_facts(p, "BGC008")
        body = _section_body(4, facts, {})
        assert "Gene table" in body
        assert "| Locus tag |" in body and "Node / contig |" in body
        # node/contig on every data row (standing rule)
        assert body.count("NODE_162") >= 2
        # locus tags present
        assert "ctg162_3" in body and "ctg162_5" in body


def test_core_genes_flagged():
    with tempfile.TemporaryDirectory() as d:
        p = _pkg(d)
        facts = _bgc_facts(p, "BGC008")
        body = _section_body(4, facts, {})
        # exactly one core gene (the PKS module); the hypothetical is not core
        assert "1 catalytic-core" in body


def test_claim_safe_footnote_present():
    """The product column must be labelled antiSMASH annotation, not an identity claim."""
    table = _render_gene_table(ROWS, "NODE_162")
    assert "not a product-identity claim" in table


def test_prose_first_guidance_retained():
    """§4 stays prose-first: the authoring comment for the gene-by-gene walkthrough
    must remain even though the table is now present."""
    with tempfile.TemporaryDirectory() as d:
        p = _pkg(d)
        facts = _bgc_facts(p, "BGC008")
        body = _section_body(4, facts, {})
        assert "gene-by-gene PROSE" in body
        assert "prose-first" in body


def test_graceful_degrade_without_gene_context():
    """No gene_context.jsonl → honest note, no crash, prose guidance intact."""
    with tempfile.TemporaryDirectory() as d:
        p = _pkg(d, with_gc=False)
        facts = _bgc_facts(p, "BGC008")
        body = _section_body(4, facts, {})
        assert "No per-gene rows available" in body
        assert "gene-by-gene PROSE" in body


def test_strand_and_coords_formatting():
    table = _render_gene_table(ROWS, "NODE_162")
    assert "2,859–3,950" in table   # thousands sep, en-dash range
    assert "| + |" in table and "| − |" in table  # both strands rendered


def test_section4_documents_offline_ingest_route_v9_7_260():
    """The token-friendly offline BLASTp route must stay wired into §4 authoring guidance so
    authors are not pushed to live-poll NCBI when pre-run results already exist. Guards against the
    template silently reverting to live-only (the 'capability built but never invoked' class)."""
    with tempfile.TemporaryDirectory() as d:
        p = _pkg(d)
        facts = _bgc_facts(p, "BGC008")
        body = _section_body(4, facts, {})
        # offline ingest path present, named, and framed as the token-friendly/preferred route
        assert "ingest-blastp" in body, "offline ingest route dropped from §4 guidance"
        assert "--hit-table" in body
        assert "offline" in body.lower()
        # live path still documented, but its polling cost is stated so it reads as the fallback
        assert "blastp-online" in body
        assert ("poll" in body.lower()) or ("min/query" in body.lower())
