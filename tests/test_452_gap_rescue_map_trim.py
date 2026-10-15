"""tools/gap_rescue_locus_map.py trim_kb and gap_directed_rescue.py --trim-kb (card .452 gap_rescue_map_trim).

The owner, 13 Oct: "we could truncate both sides of the locus and mention that in the caption text". With trim_kb the
reference row and the core contig are cropped to the matched genes plus the margin; the title and footnote say so.
Without it the map is drawn as before. Synthetic data only.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load(HERE / "tools" / "gap_rescue_locus_map.py", "gap_rescue_locus_map_452t")
# a 20-gene reference whose middle 8 genes are matched; flanking reference genes 0-5 and 14-19 are unmatched
REF = [{"i": i + 1, "name": f"synA{i}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
        "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(20)]
REF_LEN = REF[-1]["e"] + 0.5
MATCHED = range(6, 14)


def _genome():
    prots, rows = {}, []
    for k in range(len(REF)):   # one row per reference gene, in reference order (the gap_rescue.tsv layout)
        if k not in MATCHED:
            rows.append({"status": "MISSING_NOT_FOUND", "best_protein": "", "best_identity_pct": "",
                         "reciprocal_best": False, "partner_verdict": ""})
            continue
        g = REF[k]; start = 40000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": "core", "start": start,
                          "end": start + int((g["e"] - g["s"]) * 1000), "strand": 1, "contig_len": 200000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}",
                     "best_identity_pct": 60.0, "reciprocal_best": True, "partner_verdict": ""})
    for j in range(30):   # unmatched genes across a long antiSMASH region
        start = 5000 + j * 3000
        if 40000 <= start <= 54000:
            continue
        prots[f"g{j}"] = {"tag": f"other_{j}", "contig": "core", "start": start, "end": start + 1200, "strand": 1,
                          "contig_len": 200000}
    core = {"contig": "core", "start": 5000, "end": 95000, "identity": "SYN-970 / core / region001 / BGC001"}
    return prots, rows, core


def _draw(monkeypatch, tmp_path, trim):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: ([dict(g) for g in REF], REF_LEN))
    prots, rows, core = _genome()
    return glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "SYN-970", "synthetic",
                              tmp_path / f"m_{trim}.png", print_width="double", trim_kb=trim)


def test_trim_crops_both_rows_and_says_so(monkeypatch, tmp_path):
    out = _draw(monkeypatch, tmp_path, 1)
    lo = min(s["lo"] for s in out["segments"] if s["contig"] == "core")
    hi = max(s["hi"] for s in out["segments"] if s["contig"] == "core")
    first = 40000 + int(REF[MATCHED[0]]["s"] * 1000); last = 40000 + int(REF[MATCHED[-1]]["e"] * 1000)
    assert lo >= first - 1000 and hi <= last + 1000          # the isolate row follows the matches, not the region
    assert out["trim_kb"] == 1.0
    shown = REF[MATCHED[-1]]["e"] - REF[MATCHED[0]]["s"] + 2
    assert out["reference_kb"]["shown"] == pytest.approx(shown, abs=0.01)
    assert out["reference_kb"]["full"] == pytest.approx(REF_LEN, abs=0.01)
    assert "cropped to the matched genes plus 1 kb on each side" in out["footnote"]


def test_default_is_unchanged(monkeypatch, tmp_path):
    out = _draw(monkeypatch, tmp_path, None)
    lo = min(s["lo"] for s in out["segments"] if s["contig"] == "core")
    assert lo <= 5000                                      # the whole region is drawn, as before
    assert out["trim_kb"] is None and out["reference_kb"]["shown"] == out["reference_kb"]["full"]
    assert "cropped" not in out["footnote"]


def test_negative_trim_refused(monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="trim_kb"):
        _draw(monkeypatch, tmp_path, -1)


def test_cli_has_trim_option():
    src = (HERE / "tools" / "gap_directed_rescue.py").read_text()
    assert '"--trim-kb"' in src and "trim_kb=trim_kb" in src
