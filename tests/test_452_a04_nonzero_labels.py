"""A04 'nonzero' point labels (card attine_452_a04_nonzero_labels): every isolate not at 0% against both targets is
labelled, whatever its genus (unassigned included); points at 0/0 are not. The attine profile uses it (owner, 13 Oct:
"label all the strains not at zero/zero"); moss keeps 'strong'. Synthetic data only."""
import pytest
import shutil
import json
from pathlib import Path

from pypdf import PdfReader
from mamey.bioassay_paper import cli, sha, write, LAYOUTS, CANDIDA

ROOT = Path(__file__).resolve().parents[1]


def run(tmp_path):
    profile = dict(json.loads(LAYOUTS.read_text())["attine"])
    for k in ("a04_pool_candida", "a04_candida_axis_label"): profile.pop(k, None)
    profile.update(split_candida=True, a04_source_shape=False, unassigned_label="Unassigned", a04_point_labels="nonzero")   # this file tests the nonzero mode itself; the attine profile uses "either" since card 472
    for k in ("a04_label_max", "a04_legend_compact"): profile.pop(k, None)
    cfg = tmp_path / "profiles.json"; cfg.write_text(json.dumps({"synthetic": profile}))
    table, roster, aliases, lock = (tmp_path / n for n in ("assay.tsv", "roster.tsv", "aliases.json", "lock.json"))
    aliases.write_text("{}"); lock.write_text("{}")
    genera = ["Streptomyces", "Unassigned", "Streptomyces", "Unassigned"]
    write(roster, [dict(strain=f"SYN-{970 + i}", genus=g, group="Group A") for i, g in enumerate(genera)])
    values = ((0, 0, 0, 0), (3, 0, 0, 0), (0, 0, 0, 6), (40, 0, 0, 90))   # C. albicans, C. auris, not recorded, MRSA
    write(table, [dict(strain=f"SYN-{970 + i}", organism=t, material="Crude extract", best_pct=v)
                  for i, vals in enumerate(values) for t, v in zip((*CANDIDA, "MRSA"), vals)])
    out = tmp_path / "out"
    cli("A04", ROOT / "tools/bioassay_a04.R",
        ["--table", str(table), "--roster", str(roster), "--aliases", str(aliases), "--lock", str(lock),
         "--table-sha256", sha(table), "--lock-sha256", sha(lock), "--layout", "synthetic", "--layout-config", str(cfg),
         "--out", str(out)])
    return out, PdfReader(next(out.glob("*.pdf"))).pages[0].extract_text()


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_every_point_off_the_origin_is_labelled(tmp_path):
    out, text = run(tmp_path)
    assert "SYN-970" not in text                                      # 0 / 0
    assert all(s in text for s in ("SYN-971", "SYN-972", "SYN-973"))  # unassigned at 3%, 6% MRSA, 40/90
    assert "not at 0% inhibition of both targets" in (out / "CAPTION.md").read_text()


def test_profiles():
    prof = json.loads(LAYOUTS.read_text())
    # owner, 21 Oct (card 472, Attine Fig. S19): attine labels isolates strong against either target; moss keeps strong
    assert prof["attine"]["a04_point_labels"] == "either" and prof["moss"]["a04_point_labels"] == "strong"
