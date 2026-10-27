"""A04 point labels by layout (card 452_bioassay_a04_point_labels): all (default), strong (>=80% on both
targets, with leader lines) or none; the caption names the Candida split and the label rule. Synthetic data only."""
import shutil
import json
from pathlib import Path

import pytest
from pypdf import PdfReader
from mamey.bioassay_paper import cli, sha, write, LAYOUTS, CANDIDA

ROOT = Path(__file__).resolve().parents[1]


def run(tmp_path, mode, split=True):
    profile = dict(next(v for k, v in json.loads(LAYOUTS.read_text()).items() if not k.startswith("_")))
    for k in ("a04_pool_candida", "a04_candida_axis_label"): profile.pop(k, None)   # these tests cover the split and pooled defaults
    profile.update(split_candida=split, a04_source_shape=False, unassigned_label="Unassigned")
    if mode is None:
        profile.pop("a04_point_labels", None)
    else:
        profile["a04_point_labels"] = mode
    cfg = tmp_path / "profiles.json"; cfg.write_text(json.dumps({"synthetic": profile}))
    table, roster, aliases, lock = (tmp_path / n for n in ("assay.tsv", "roster.tsv", "aliases.json", "lock.json"))
    aliases.write_text("{}"); lock.write_text("{}")
    write(roster, [dict(strain=f"SYN-{970 + i}", genus="Streptomyces", group="Group A") for i in range(3)])
    values = ((90, 50, 95, 92), (30, 20, 85, 40), (85, 88, 60, 81))   # C. albicans, C. auris, not recorded, MRSA
    write(table, [dict(strain=f"SYN-{970 + i}", organism=t, material="Crude extract", best_pct=v)
                  for i, vals in enumerate(values) for t, v in zip((*CANDIDA, "MRSA"), vals)])
    out = tmp_path / f"out_{mode}"
    cli("A04", ROOT / "tools/bioassay_a04.R",
        ["--table", str(table), "--roster", str(roster), "--aliases", str(aliases), "--lock", str(lock),
         "--table-sha256", sha(table), "--lock-sha256", sha(lock), "--layout", "synthetic", "--layout-config", str(cfg),
         "--out", str(out)])
    return out, PdfReader(next(out.glob("*.pdf"))).pages[0].extract_text()


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_strong_labels_only_points_strong_on_both(tmp_path):
    out, text = run(tmp_path, "strong")
    assert "SYN-970" in text and "SYN-972" in text      # 90/92 and 85/81 (and 88/81)
    assert "SYN-971" not in text                        # MRSA 40
    cap = (out / "CAPTION.md").read_text()
    assert "shown separately" in cap and "at least 80% inhibition of both targets" in cap and "pools C. albicans" not in cap


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_none_labels_nothing(tmp_path):
    out, text = run(tmp_path, "none")
    assert "SYN-97" not in text
    assert "not labelled" in (out / "CAPTION.md").read_text()


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_all_is_the_default(tmp_path):
    _, text = run(tmp_path, None)
    assert "SYN-971" in text                    # the earlier rule labels every named point >=10%


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_pooled_caption_unchanged_without_split(tmp_path):
    out, _ = run(tmp_path, None, split=False)
    assert "Candida sp. pools C. albicans" in (out / "CAPTION.md").read_text()
