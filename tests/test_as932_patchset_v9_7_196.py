"""v9.7.196 — regression guards for the AS-932 patch set (verified in isolation by the audit tier,
run through the suite here). Three defects: cds[] shape, blastp false-orphan, blastp scoping."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from mamey.modeb_template_emitter import _gene_rows_for_bgc
from mamey.bgc_guide import render_blastp_readout
from mamey.blastp_online import _scope_feats


# --- Patch A: cds[] shape ---
def test_gene_rows_reads_cds_array_shape():
    """The real writer emits {"bgc_id":X,"cds":[...]} (header line first). Without the cds[] branch
    the wrapper is appended as 1 row and every §4 table is empty."""
    d = Path(tempfile.mkdtemp())
    gc = d / "gene_context.jsonl"
    with open(gc, "w") as f:
        f.write(json.dumps({"schema_version": "x", "n_cds": 2}) + "\n")  # header line
        f.write(json.dumps({"bgc_id": "BGC001", "cds": [
            {"locus_tag": "g1", "start": 100}, {"locus_tag": "g2", "start": 200}]}) + "\n")
    rows = _gene_rows_for_bgc(d, "BGC001")
    assert len(rows) == 2, f"expected 2 CDS rows, got {len(rows)}"
    assert rows[0]["locus_tag"] == "g1"


# --- Patch B2 / BUG2: false-orphan ---
def test_unqueried_gene_not_labeled_orphan():
    """A gene never submitted to BLASTp must NOT render as a no-hit orphan (claim-safety)."""
    not_queried = render_blastp_readout(None, has_translation=True, was_queried=False)
    genuine_orphan = render_blastp_readout(None, has_translation=True, was_queried=True)
    # the un-queried message explicitly disclaims an orphan call; it must not ASSERT orphan status
    assert "not run for this gene" in not_queried
    assert "orphan / fast-evolving" not in not_queried  # the actual no-hit orphan label
    assert "orphan / fast-evolving" in genuine_orphan   # genuine no-hit still labeled orphan


# --- Patch B: crosswalk-grounded scoping ---
def test_scope_feats_by_contig_window():
    xw = {"BGC006": {"contig": "NODE_13_x", "start": "10000", "end": "60000"}}
    feats = [
        SimpleNamespace(contig="NODE_13_x", start=12000, end=13000, translation="M", locus_tag="in"),
        SimpleNamespace(contig="NODE_13_x", start=90000, end=91000, translation="M", locus_tag="out_win"),
        SimpleNamespace(contig="NODE_9_y", start=100, end=200, translation="M", locus_tag="out_contig"),
    ]
    scoped = _scope_feats(feats, bgc="BGC006", crosswalk=xw)
    assert [f.locus_tag for f in scoped] == ["in"]


def test_scope_feats_unresolved_returns_empty():
    """Unresolved BGC → [] so the caller refuses, never falls through to the whole proteome."""
    xw = {"BGC006": {"contig": "NODE_13_x", "start": "0", "end": "9999"}}
    feats = [SimpleNamespace(contig="NODE_13_x", start=1, end=2, translation="M", locus_tag="g")]
    assert _scope_feats(feats, bgc="BGC999", crosswalk=xw) == []
