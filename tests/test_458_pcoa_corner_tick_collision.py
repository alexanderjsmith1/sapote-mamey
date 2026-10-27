"""458_pcoa_corner_tick_collision: a page panel whose lowest y break sits on the bottom axis line and whose first x break
sits just right of the left axis line puts two tick labels in the bottom-left corner. tools/protein_pcoa_page.R now blanks the
lowest y label there, and the min-text gate passes at 8 pt. The panel limits are those of the AS-40 TriMap HALO panel (Attine
Fig. S8 page 2), where the .457 page script refused with "-80 | -150". Synthetic points; nothing is refitted."""
import json
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE_R = ROOT / "tools" / "protein_pcoa_page.R"
HALO_XLIM = [-154.398, 133.991]   # TriMap HALO data range +/- PAGE_EXPAND (0.22, 0.22)
HALO_YLIM = [-80.004, 83.898]     # data range +/- PAGE_EXPAND (0.18, 0.22): the lower limit lands on the default break -80
LEGEND = {"ref": "reference genomes (cluster centroids)", "mibig": "MIBiG characterized clusters",
          "iso_low": "AS-40 protein, best reference/MIBiG match < 70% identity",
          "iso_mid": "AS-40 protein, best reference/MIBiG match 70-85% identity",
          "iso_high": "AS-40 protein, best reference/MIBiG match >= 85% identity"}
R_PACKAGES = ("ggplot2", "jsonlite", "patchwork", "svglite", "xml2", "systemfonts", "ggtext")


def _rscript():
    exe = shutil.which("Rscript")
    if exe is None:
        pytest.skip("Rscript is not installed")
    probe = subprocess.run([exe, "-e", "for (p in c(%s)) library(p, character.only = TRUE)" % ", ".join(f'"{p}"' for p in R_PACKAGES)],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        pytest.skip("R page packages are not installed")
    return exe


def _panel(tag, xlab, ylab):
    pts = [(-110.34, -58.93, "ref"), (89.93, 58.15, "ref"), (0.0, 0.0, "mibig"), (-20.0, 10.0, "iso_low"),
           (30.0, -20.0, "iso_mid"), (45.0, 40.0, "iso_high")]
    return dict(tag=tag, xlab=xlab, ylab=ylab, xlim=HALO_XLIM, ylim=HALO_YLIM,
                points=dict(x=[p[0] for p in pts], y=[p[1] for p in pts], layer=[p[2] for p in pts], size=[4] * len(pts)),
                labels={k: [] for k in ("x", "y", "label", "hjust", "vjust", "sx", "sy", "face")})


def _draw(tmp_path, script, xlab="TriMap 1", ylab="TriMap 2"):
    stamp = uuid.uuid4().hex
    page = dict(stamp=stamp, probe=False, ncol=2, panel_height=2.6, tags=["g", "h"], italic_labels=False, legend=LEGEND,
                leader_colour="#555555", label_box=False, legend_slot=False,
                panels=[_panel("SARP-family regulators", xlab, ylab), _panel("Flavin-dependent halogenases", xlab, ylab)],
                min_text=dict(min_text_pt=8, print_width=6.5, helper=str(ROOT / "tools" / "sapote_min_text.R"),
                              layout=str(ROOT / "tools" / "sapote_pub_layout.R")))
    spec = tmp_path / f"page_{stamp}.json"
    spec.write_text(json.dumps(page))
    prefix = tmp_path / f"PAGE_{stamp}"
    r = subprocess.run([_rscript(), str(script), str(spec), str(prefix), stamp], capture_output=True, text=True)
    return r, prefix


def _without_fix(tmp_path):
    """The same page script with the corner check switched off: the .457 behaviour (on .457 itself, the script as it is)."""
    src = PAGE_R.read_text()
    head = "corner_tick_fix <- function(g, sp, pw_pt, ph_pt) {\n"
    if head not in src:
        return PAGE_R
    assert src.count(head) == 1
    off = tmp_path / "protein_pcoa_page_without_corner_fix.R"
    off.write_text(src.replace(head, head + "  return(list(g = g, blanked = NULL))\n"))
    return off


def test_corner_collision_reproduces_without_the_fix(tmp_path):
    r, _ = _draw(tmp_path, _without_fix(tmp_path))
    assert r.returncode != 0
    assert "MIN_TEXT_DOES_NOT_FIT" in r.stderr and "-80 | -150" in r.stderr


def test_fix_blanks_the_corner_y_label_and_passes_the_gate(tmp_path):
    r, prefix = _draw(tmp_path, PAGE_R)
    assert r.returncode == 0, r.stderr[-600:]
    blanked = json.loads(Path(f"{prefix}_runtime.json").read_text())["corner_tick_labels_blanked"]
    assert [(b["axis"], b["label"], b["other"]) for b in blanked] == [("y", "-80", "-150")] * 2
    check = json.loads(Path(f"{prefix}_min_text.json").read_text())
    assert check["min_text_pt"] == 8 and not check["overlapping_text"] and not check["clipped_text"]
    svg = Path(f"{prefix}.svg").read_text()
    assert ">-80<" not in svg and ">-40<" in svg and ">-150<" in svg   # only the corner label goes; its neighbours stay


def test_tsne_panels_are_untouched(tmp_path):
    r, prefix = _draw(tmp_path, PAGE_R, xlab="t-SNE 1", ylab="t-SNE 2")
    assert r.returncode == 0, r.stderr[-600:]
    assert json.loads(Path(f"{prefix}_runtime.json").read_text())["corner_tick_labels_blanked"] == []
