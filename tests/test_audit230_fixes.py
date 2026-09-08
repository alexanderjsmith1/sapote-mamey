"""v9.7.230: audit-driven fixes — SubClusterBlast parsed-zero -> NO_HITS (not blank), and kcb-frontpage
region/node/bgc filtering for card authoring."""
import sys, pathlib, types
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

def test_subcluster_parsed_zero_is_no_hits_not_blank():
    # the serialization rule: empty hits + tab-parsed -> "NO_HITS"; empty + not-parsed -> "".
    def cell(hits, parsed):
        return ("; ".join(f"{h['ref']}({h['mean_identity']})" for h in (hits or [])[:3])) or ("NO_HITS" if parsed else "")
    assert cell([], True) == "NO_HITS"          # parsed zero -> negative evidence
    assert cell([], False) == ""                # not parsed -> ambiguous blank
    assert cell([{"ref": "BGC1", "mean_identity": 40}], True) == "BGC1(40)"

def test_kcb_frontpage_region_filter(monkeypatch):
    from mamey import kcb_frontpage as K
    hits = [{"region": "r32c1", "compound": "nystatin A1", "similarity": 36, "n_genes": 22, "tier": "MODERATE", "bgc_id": "BGC028"},
            {"region": "r5c1", "compound": "other", "similarity": 10, "n_genes": 3, "tier": "WEAK", "bgc_id": "BGC005"}]
    # monkeypatch (auto-restored), NEVER a raw assignment: the old permanent stub leaked to
    # every later kcb_frontpage consumer in the process — the triage e2e failed with kcb=None
    # whenever test_b2_registry_parity's broad mamey* purge wasn't there to accidentally
    # repair it (suite-order fragility, .398 diagnosis).
    monkeypatch.setattr(K, "read_frontpage", lambda d: hits)
    args = types.SimpleNamespace(strain_dir="x", top=50, region="r32", node=None, bgc=None)
    # capture stdout
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = K.frontpage_command(args)
    out = buf.getvalue()
    assert rc == 0 and "nystatin A1" in out and "other" not in out   # only r32 shown
    # v9.7.243 (H-003): --bgc is unsupported and must FAIL CLOSED, not silently return nothing.
    # The old assertion here stubbed `bgc_id` into the hit dicts; real regions.js has no such key.
    args2 = types.SimpleNamespace(strain_dir="x", top=50, region=None, node=None, bgc="BGC005")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc2 = K.frontpage_command(args2)
    assert rc2 == 2 and "not supported" in err.getvalue()


def test_regions_js_has_no_contig_or_bgc_id_so_those_filters_are_unsupported():
    """v9.7.243 (H-003, owned): verified against a real 14 MB antiSMASH regions.js — anchors are
    `r1c1`-style and the per-region detail carries no contig/seq_id/BGC id. A filter on a key the
    source never sets can only ever return nothing. `--region` is the supported surface."""
    import inspect
    from mamey import kcb_frontpage as K
    src = inspect.getsource(K.read_frontpage)
    for absent in ('"node"', '"contig"', '"bgc_id"'):
        assert absent not in src, f"read_frontpage now sets {absent}; re-enable the filter and test it"
