"""v9.7.117: cds_rows_from_gene_context — explicit rich-blob loader for locus maps.

The loader reads the full sec_met_domains + smCOG gene_functions blob from a gene_context.jsonl so
smCOG-only genes get their real role instead of grey. (Reconciliation: this is NOT a fix for a live
bug — the current in-run and post-seal render paths already read the rich blob; this is an explicit
file-path entry point. See the loader docstring.) Tests skip cleanly if no real package is present.
"""
import os
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from mamey.locus_map import cds_rows_from_gene_context, cds_rows_from_table  # noqa: E402
import mamey.locus_map as LM  # noqa: E402

_DEFAULT = LM._DEFAULT_ROLE[0]
# operator-supplied real package (env), else skip — no real strain literal in source
_GC = os.environ.get("LOCUS_GC_JSONL", "/data/mamey-local/_local_gene_context.jsonl")
_have = os.path.exists(_GC)


def test_missing_file_returns_empty():
    assert cds_rows_from_gene_context("/no/such/path.jsonl", "BGC001") == []


@pytest.mark.skipif(not _have, reason="no real gene_context.jsonl present (set LOCUS_GC_JSONL)")
def test_loader_recovers_smcog_genes():
    """Loader must recover smCOG-annotated genes vs a sec_met-only blob (rich > thin)."""
    import json, ast
    # pick the first BGC with >=15 CDS
    bid = None
    for line in open(_GC).readlines()[1:]:
        d = json.loads(line)
        cds = d.get("cds", [])
        if isinstance(cds, str):
            cds = ast.literal_eval(cds)
        if len(cds) >= 15:
            bid = d["bgc_id"]
            thin = [{"start": c.get("start", 0), "end": c.get("end", 0),
                     "sec_met_domains": (ast.literal_eval(c["sec_met_domains"])
                                         if isinstance(c.get("sec_met_domains"), str)
                                         and c["sec_met_domains"].startswith("[")
                                         else c.get("sec_met_domains", []))}
                    for c in cds]
            break
    rich_rows = cds_rows_from_gene_context(_GC, bid)
    thin_rows = cds_rows_from_table(thin)
    rich_grey = sum(1 for r in rich_rows if r["role"] == _DEFAULT)
    thin_grey = sum(1 for r in thin_rows if r["role"] == _DEFAULT)
    assert len(rich_rows) == len(thin_rows) > 0
    assert rich_grey < thin_grey   # the rich blob recovers genes


@pytest.mark.skipif(not _have, reason="no real gene_context.jsonl present")
def test_loader_rows_match_table_format():
    """Returned rows must be in the cds_rows_from_table dict format (role/color/is_core present)."""
    import json, ast
    bid = None
    for line in open(_GC).readlines()[1:]:
        d = json.loads(line)
        if d.get("cds"):
            bid = d["bgc_id"]
            break
    rows = cds_rows_from_gene_context(_GC, bid)
    assert rows and all({"role", "color", "is_core", "start", "end", "strand"} <= set(r) for r in rows)
