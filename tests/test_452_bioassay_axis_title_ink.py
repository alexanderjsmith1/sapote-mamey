"""Bioassay theme profile key axis_title_ink (card 018c0f08_452_bioassay_axis_title_ink): axis titles in ink instead of
the sealed theme's grey when the layout asks; unchanged otherwise. Synthetic data, read from the SVG."""
import pytest
import shutil
import json, re
from pathlib import Path
from mamey.bioassay_paper import cli, sha, write, LAYOUTS, CANDIDA

ROOT = Path(__file__).resolve().parents[1]


def render(tmp_path, ink):
    profile = dict(next(v for k, v in json.loads(LAYOUTS.read_text()).items() if not k.startswith("_")))
    profile.update(split_candida=False, a04_source_shape=False, unassigned_label="Unassigned")
    profile.pop("axis_title_ink", None)
    if ink:
        profile["axis_title_ink"] = True
    cfg = tmp_path / "p.json"; cfg.write_text(json.dumps({"synthetic": profile}))
    table, roster, aliases, lock = (tmp_path / n for n in ("a.tsv", "r.tsv", "al.json", "l.json"))
    aliases.write_text("{}"); lock.write_text("{}")
    write(roster, [dict(strain=f"SYN-{970 + i}", genus="Streptomyces", group="Group A") for i in range(2)])
    write(table, [dict(strain=f"SYN-{970 + i}", organism=t, material="Crude extract", best_pct=v)
                  for i in range(2) for t, v in zip((*CANDIDA, "MRSA"), (20, 30, 40, 90 - 50 * i))])
    out = tmp_path / ("ink" if ink else "grey")
    cli("A04", ROOT / "tools/bioassay_a04.R", ["--table", str(table), "--roster", str(roster), "--aliases", str(aliases),
        "--lock", str(lock), "--table-sha256", sha(table), "--lock-sha256", sha(lock), "--layout", "synthetic",
        "--layout-config", str(cfg), "--out", str(out)])
    return next(out.glob("*.svg")).read_text()


def title_fills(svg):
    return set(re.findall(r"fill:\s*#([0-9A-Fa-f]{6})", svg))


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_ink_titles(tmp_path):
    g = title_fills(render(tmp_path, False)); i = title_fills(render(tmp_path, True))
    assert "54637A" in {c.upper() for c in g}
    assert "54637A" not in {c.upper() for c in i}
