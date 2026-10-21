"""Cross-strain summary figures treat a blank count as missing, not zero.

`build_cross_strain_figures` read blank and NA cells as 0 through `_num()`. A strain with no
corrected count showed a fragmentation loss of every BGC, by-strain bar charts drew a 0 bar for
missing values, scatters plotted them at 0, the HIGH/MODERATE stacked bar drew a zero segment and
the assembly-tier box plot counted a missing pair total as zero pairs. An observed 0 is still drawn.
"""
import csv
from pathlib import Path

from mamey.cross_strain_figures import build_cross_strain_figures


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["strain"]: r for r in csv.DictReader(fh)}


def _summary(rg: Path, text: str) -> None:
    rg.mkdir()
    (rg / "demo_priority_summary.csv").write_text(text, encoding="utf-8")


def test_blank_corrected_count_is_missing_not_a_loss(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    rg, out = tmp_path / "rg", tmp_path / "out"
    _summary(rg, "strain,raw_bgcs,corrected_bgcs,pairs_total\nREF-1,10,8,3\nREF-2,7,,2\nREF-3,5,0,1\n")
    res = build_cross_strain_figures(rg, out, make_zip=False)
    loss = _rows(next(out.glob("*_fragmentation_loss_by_strain_data.csv")))
    assert set(loss) == {"REF-1", "REF-3"}
    assert float(loss["REF-1"]["fragmentation_loss"]) == 2 and float(loss["REF-3"]["fragmentation_loss"]) == 5
    corrected = _rows(next(out.glob("*_corrected_bgcs_by_strain_data.csv")))
    assert "REF-2" not in corrected and corrected["REF-3"]["corrected_bgcs"] == "0"  # observed zero kept
    raw = _rows(next(out.glob("*_raw_bgcs_by_strain_data.csv")))
    assert set(raw) == {"REF-1", "REF-2", "REF-3"}
    scatter = _rows(next(out.glob("*_fragmentation_loss_vs_pairs_total_data.csv")))
    assert set(scatter) == {"REF-1", "REF-3"}  # REF-2 is not plotted at a loss of 0
    captions = {f["name"]: f["caption"] for f in res["figures"]}
    assert any("2 of 3 strains have a value" in c for n, c in captions.items() if "corrected_bgcs" in n)


def test_missing_pair_counts_are_not_zero_segments_or_box_values(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    rg, out = tmp_path / "rg", tmp_path / "out"
    _summary(rg, "strain,assembly_tier,pairs_total,high_pairs,moderate_pairs\n"
                 "REF-1,GOOD,4,1,3\nREF-2,GOOD,,NA,2\nREF-3,POOR,0,0,0\n")
    res = build_cross_strain_figures(rg, out, make_zip=False)
    stacked = _rows(next(out.glob("*_high_moderate_pairs_by_strain_data.csv")))
    assert set(stacked) == {"REF-1", "REF-3"}  # observed zeros kept, missing HIGH count left out
    assert stacked["REF-3"]["high_plus_moderate"] in {"0", "0.0"}
    with open(next(out.glob("*_pairs_total_by_assembly_tier_data.csv")), newline="", encoding="utf-8") as fh:
        box = [(r["assembly_tier"], float(r["pairs_total"])) for r in csv.DictReader(fh)]
    assert sorted(box) == [("GOOD", 4.0), ("POOR", 0.0)]
    captions = {f["name"]: f["caption"] for f in res["figures"]}
    assert any("2 of 3 strains have both values" in c for n, c in captions.items() if "high_moderate" in n)
