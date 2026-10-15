"""tools/placement_display.py --activity-palette (card .452 placement_activity_palette_calm).

The owner, 13 Oct, on moss Fig. S1b: "The calmer S1b version looks good." The calm palette (dark blue / blue-grey / pale
grey, palette field activity_calm) is an option; the default stays red / dark grey / grey, so earlier trees are
unchanged. Synthetic data only (the toy run of the rect02 shipping card)."""
import shutil
import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from tools import placement_display as display
from .test_452_rect02_shipping import toy_run

CALM = {"#1F4E79", "#B8C4D2", "#ECEFF3"}
RED = "#B00020"


def _render(tmp_path, monkeypatch, palette):
    run, _ = toy_run(tmp_path, monkeypatch)
    ids = [line[1:] for line in (run / "query.aligned.fasta").read_text().splitlines() if line.startswith(">")]
    (run / "split.tsv").write_text("strain\tC. albicans\tC. auris\tanti_Candida_unspecified\tanti_MRSA\n"
                                   f"{ids[0]}\t+\t-\tn.t.\t+\n{ids[1]}\t\t+\t-\t\n")
    config = run / "layouts.json"; config.write_text('{"synthetic":{"split_candida":true}}')
    out = tmp_path / f"out_{palette}"
    args = [str(run), "--name", "toy", "--group", "Example", "--host-table", str(run / "hosts.tsv"),
            "--ref-source-db", str(run / "refs.sqlite"), "--strip-set", "activity", "--bioassay-table", str(run / "split.tsv"),
            "--layout", "synthetic", "--layout-config", str(config), "--label-style", "short", "--keep-all-references",
            "--out", str(out)] + (["--activity-palette", palette] if palette else [])
    assert display.main(args) == 0
    return out


def _colours(png):
    im = Image.open(png).convert("RGB")
    return {"#%02X%02X%02X" % c for _, c in im.getcolors(im.width * im.height)}


def test_palette_rows():
    rows = list(csv.reader((Path(display.__file__).with_name("phylo_display_palette.tsv")).open(), delimiter="\t"))
    act = [r[1] for r in rows if r[0] == "activity"]
    calm = {r[1]: r[2] for r in rows if r[0] == "activity_calm"}
    assert list(calm) == act                                   # same states, same order
    assert set(calm.values()) == CALM


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_calm_draws_calm_colours_and_replays(tmp_path, monkeypatch):
    out = _render(tmp_path, monkeypatch, "calm")
    cols = _colours(out / "toy_rect02.png")
    assert {"#1F4E79", "#B8C4D2"} <= cols and RED not in cols
    script = (out / "standalone_R_package" / "toy_rerender_captioned.sh").read_text()
    assert "export GG_ACTIVITY_PALETTE=calm" in script
    env = dict(os.environ, SAPOTE_PYTHON=sys.executable, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    proc = subprocess.run(["sh", "toy_rerender_captioned.sh"], cwd=out / "standalone_R_package", env=env,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert RED not in _colours(out / "standalone_R_package" / "toy_captioned.png")


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_default_is_unchanged(tmp_path, monkeypatch):
    cols = _colours(_render(tmp_path, monkeypatch, None) / "toy_rect02.png")
    assert RED in cols and "#1F4E79" not in cols


def test_calm_needs_activity_strips(tmp_path, monkeypatch, caplog):
    run, _ = toy_run(tmp_path, monkeypatch)
    rc = display.main([str(run), "--name", "toy", "--group", "Example", "--host-table", str(run / "hosts.tsv"),
                       "--ref-source-db", str(run / "refs.sqlite"), "--activity-palette", "calm", "--out", str(tmp_path / "x")])
    assert rc != 0 and "ACTIVITY_PALETTE_NEEDS_ACTIVITY_STRIPS" in caplog.text
