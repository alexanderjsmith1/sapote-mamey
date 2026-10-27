"""Card 452_bioassay_a06_n_below_bars.

Owner review of the A06 figure (strong activity by 16S genus group): no strong/tested fractions above the bars, and
"n=<tested>" under each bar instead, with room made for it. `--bar-labels` brings the fractions back. Synthetic data.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.bioassay_paper import cli, prepare, write  # noqa: E402


def _inputs(tmp_path):
    roster = tmp_path / "roster.tsv"
    write(roster, [dict(strain="SYN-1", genus="Streptomyces", group="GroupA"),
                   dict(strain="SYN-2", genus="Streptomyces", group="GroupA"),
                   dict(strain="SYN-3", genus="Nocardia", group="GroupA"),
                   dict(strain="SYN-4", genus="Unassigned", group="GroupA")])
    rows = []
    for strain, values in {"SYN-1": ("90", "10", "85"), "SYN-2": ("20", "95", "0"),
                           "SYN-3": ("81", "5", "3"), "SYN-4": ("50", "50", "50")}.items():
        for organism, value in zip(("Candida albicans", "MRSA", "Foulbrood 818"), values):
            rows.append(dict(strain=strain, organism=organism, material="Crude extract", best_pct=value))
    table = tmp_path / "best.tsv"
    write(table, rows)
    aliases = tmp_path / "aliases.json"
    aliases.write_text("{}")
    lock = tmp_path / "lock.md"
    lock.write_text("quadrant lock\n")
    layouts = tmp_path / "layouts.json"
    layouts.write_text(json.dumps({"synthetic": {
        "focal_group": "GroupA", "a06_subset_group": "GroupA", "split_larvae": False,
        "group_axis_label": "Source group", "unassigned_label": "No 16S sequence", "plain_rows": [],
        "a03_genus_keep": None, "a03_source_shape": False, "a04_source_shape": False,
        "a02_width_in": 5.6, "a03_height_in": 4.6}}))
    return table, roster, aliases, lock, layouts


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_each_bar_carries_its_tested_count(tmp_path):
    table, roster, aliases, _, layouts = _inputs(tmp_path)
    plot = prepare(table, roster, aliases, "A06", "synthetic", layouts=layouts)["plot"]
    strep = next(r for r in plot if r["group"] == "Streptomyces" and r["target"] == "Candida sp.")
    assert (strep["n_label"], strep["label"]) == ("n=2", "1/2")
    untested = next(r for r in plot if r["group"] == "Streptomyces" and r["target"] == "E. coli")
    assert untested["n_tested"] == 0 and untested["n_label"] == untested["label"]   # the recorded state, never "n=0"


def _render(tmp_path, *extra):
    table, roster, aliases, lock, layouts = _inputs(tmp_path)
    out = tmp_path / ("out" + "_".join(extra))
    cli("A06", ROOT / "tools" / "bioassay_a06.R",
        ["--table", str(table), "--table-sha256", _sha(table), "--roster", str(roster), "--aliases", str(aliases),
         "--lock", str(lock), "--lock-sha256", _sha(lock), "--out", str(out), "--layout", "synthetic",
         "--layout-config", str(layouts), *extra])
    return out


def test_bar_labels_option_reaches_the_render_config(tmp_path):
    table, roster, aliases, lock, layouts = _inputs(tmp_path)
    for extra, expected in (((), False), (("--bar-labels",), True)):
        out = tmp_path / f"cfg{expected}"
        cli("A06", ROOT / "tools" / "bioassay_a06.R",
            ["--table", str(table), "--table-sha256", _sha(table), "--roster", str(roster), "--aliases", str(aliases),
             "--lock", str(lock), "--lock-sha256", _sha(lock), "--out", str(out), "--layout", "synthetic",
             "--layout-config", str(layouts), "--prepare-only", *extra])
        assert json.loads((out / "render_config.json").read_text())["bar_labels"] is expected


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")
def test_render_has_n_under_bars_and_no_fractions_by_default(tmp_path):
    svg = (_render(tmp_path) / "A06_synthetic_crude.svg").read_text()
    text = " ".join(re.findall(r">([^<>]+)</text>", svg)) or svg
    assert "n=2" in text and "n=1" in text
    assert not re.search(r"\b\d+/\d+\b", text)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")
def test_render_with_bar_labels_prints_the_fractions(tmp_path):
    svg = (_render(tmp_path, "--bar-labels") / "A06_synthetic_crude.svg").read_text()
    assert "1/2" in svg and "n=2" in svg
