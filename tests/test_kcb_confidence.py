"""kcb_confidence: hermetic test for the antiSMASH v8 Similarity-Confidence extractor."""
import importlib.util, tempfile, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("kcb_confidence", ROOT/"tools"/"kcb_confidence.py")
kc = importlib.util.module_from_spec(_s); _s.loader.exec_module(kc)

_HTML = """
<tr class="linked-row odd" data-anchor="#r2c1"><td>x</td>
<td class="similarity-text" style="background: rgb(178, 208, 178)">High</td>
<td><a href="#">streptophenazine B</a></td></tr>
<tr class="linked-row even" data-anchor="#r16c1"><td>y</td>
<td class="similarity-text" style="background: rgb(249, 178, 178)">Low</td>
<td><a href="#">cinnapeptin</a></td></tr>
"""

def test_extract_confidence_and_summary():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "index.html"), "w").write(_HTML)
        rows = kc.extract_kcb_confidence(d)
        assert len(rows) == 2
        assert rows[0]["confidence"] == "High" and "streptophenazine" in rows[0]["known_cluster"]
        assert rows[1]["confidence"] == "Low" and rows[1]["known_cluster"] == "cinnapeptin"
        s = kc.confidence_summary(rows)
        assert s == {"n_kcb_hits": 2, "High": 1, "Medium": 0, "Low": 1}


def test_dedup_double_overview_tables():
    # v8 renders the region-overview table twice (per-record + global); the extractor must dedup by anchor
    doubled = _HTML + _HTML   # same two regions, rendered twice
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "index.html"), "w").write(doubled)
        rows = kc.extract_kcb_confidence(d)
        assert len(rows) == 2, [r["region_anchor"] for r in rows]   # not 4
        assert {r["region_anchor"] for r in rows} == {"r2c1", "r16c1"}
