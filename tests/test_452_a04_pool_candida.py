"""Card 452_bioassay_a04_pool_candida: A04 can draw one Candida axis while A01 keeps the species panels.

The owner, 13 Oct: "combine this into 1 candida panel and label it as C. albicans and C. auris." Synthetic IDs only.
"""
import pytest
import shutil
import json
from pathlib import Path

from pypdf import PdfReader

from mamey.bioassay_paper import CANDIDA, LAYOUTS, cli, prepare, sha, write

ROOT = Path(__file__).resolve().parents[1]
LABEL = "C. albicans and C. auris"


def _inputs(tmp_path, **extra):
    profile = dict(next(v for k, v in json.loads(LAYOUTS.read_text()).items() if not k.startswith("_")))
    profile.update(split_candida=True, a04_source_shape=False, unassigned_label="Unassigned", a04_point_labels="none")
    profile.update(extra)
    cfg = tmp_path / "profiles.json"
    cfg.write_text(json.dumps({"synthetic": profile}))
    table, roster, aliases, lock = (tmp_path / n for n in ("assay.tsv", "roster.tsv", "aliases.json", "lock.json"))
    aliases.write_text("{}")
    lock.write_text("{}")
    write(roster, [dict(strain=f"SYN-{970 + i}", genus="Streptomyces", group="Group A") for i in range(3)])
    values = ((20, 50, 90, 0), (30, "n.t.", "+", 40), (80, 70, 60, "−"))
    write(table, [dict(strain=f"SYN-{970 + i}", organism=t, material="Crude extract", best_pct=v)
                  for i, vals in enumerate(values) for t, v in zip((*CANDIDA, "MRSA"), vals)])
    args = ["--table", str(table), "--roster", str(roster), "--aliases", str(aliases), "--lock", str(lock),
            "--table-sha256", sha(table), "--lock-sha256", sha(lock), "--layout", "synthetic", "--layout-config", str(cfg)]
    return (table, roster, aliases, cfg), args


def test_pooled_a04_takes_the_higher_candida_value(tmp_path):
    (t, r, a, c), _ = _inputs(tmp_path, a04_pool_candida=True, a04_candida_axis_label=LABEL)
    plot = prepare(t, r, a, "A04", "synthetic", layouts=c)["plot"]
    assert [(p["strain"], p["x"], p["y"]) for p in plot] == [("SYN-970", 90, 0), ("SYN-971", 30, 40)]
    assert all("target" not in p for p in plot)
    # A01 keeps the species panels under the same profile
    a01 = prepare(t, r, a, "A01", "synthetic", layouts=c)["plot"]
    assert {"C. albicans", "C. auris"} <= {p["target"] for p in a01}


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_pooled_a04_prints_one_panel_with_the_label_and_caption(tmp_path):
    _, args = _inputs(tmp_path, a04_pool_candida=True, a04_candida_axis_label=LABEL)
    out = tmp_path / "pooled"
    cli("A04", ROOT / "tools/bioassay_a04.R", args + ["--out", str(out)])
    text = PdfReader(next(out.glob("*.pdf"))).pages[0].extract_text().replace(" ", "")
    assert ("Bestinhibitionof" + LABEL.replace(" ", "")) in text
    assert "(notrecorded)" not in text          # no third facet strip
    cap = (out / "CAPTION.md").read_text()
    assert LABEL + " is the higher best inhibition" in cap and "shown separately" not in cap


def test_moss_profile_pools_a04_only():
    prof = json.loads(LAYOUTS.read_text())["moss"]
    assert prof["split_candida"] is True and prof["a04_pool_candida"] is True
    assert prof["a04_candida_axis_label"] == LABEL
