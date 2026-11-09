# Synthetic regression inputs only.
"""A strain with no BGC rows gets a blank novelty percentage, not 0%, and is not ranked."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_zero_bgc_strain_is_blank_and_listed_separately(tmp_path):
    strains = [f"SYN-{i:02d}" for i in range(1, 6)] + ["SYN-EMPTY"]
    bgcs = []
    for i, sid in enumerate(strains[:-1]):
        bgcs.append({"sid": sid, "closest_mibig": "BGC0000001", "closest_kcb_product": "alpha", "products": "NRPS"})
        bgcs.append({"sid": sid, "closest_mibig": f"BGC00009{i:02d}", "closest_kcb_product": "beta", "products": "PKS"})
    banked = tmp_path / "cohort"
    banked.mkdir()
    (banked / "bgc_data.json").write_text(json.dumps({"strains": strains, "bgcs": bgcs}), encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_pangenome.py"), "--banked-dir", str(banked),
                        "--out-dir", str(out)], capture_output=True, text=True, timeout=120, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    rows = list(csv.DictReader((out / "Pangenome_Novelty.csv").open(encoding="utf-8")))
    empty = next(x for x in rows if x["strain"] == "SYN-EMPTY")
    assert empty["novel_pct"] == "" and empty["total_BGC"] == "0"
    assert rows[-1]["strain"] == "SYN-EMPTY"
    md = (out / "Pangenome_Summary.md").read_text(encoding="utf-8")
    ranked = md.split("## Most novel strains", 1)[1].split("_Novelty", 1)[0]
    assert "SYN-EMPTY: 0/0" not in ranked
    assert "no BGC rows in the bank" in md and "SYN-EMPTY" in md
