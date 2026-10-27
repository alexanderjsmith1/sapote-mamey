"""The pangenome summary does not claim more strains will yield new chemistry.

build_pangenome.py always wrote that additional strains "are expected to keep yielding new
chemistry; the collection is not saturated". The owner ruled the sentence removed: the data do not
test it. The measured rarefaction numbers stay.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_summary_keeps_numbers_and_drops_the_claim(tmp_path):
    strains = [f"SYNTHETIC-CASE-{i:03d}" for i in range(1, 13)]
    bgcs = []
    for i, sid in enumerate(strains):
        bgcs.append({"sid": sid, "closest_mibig": "BGC0000001", "closest_kcb_product": "alpha", "products": "NRPS"})
        bgcs.append({"sid": sid, "closest_mibig": f"BGC00009{i:02d}", "closest_kcb_product": "beta", "products": "PKS"})
        bgcs.append({"sid": sid, "closest_mibig": "UNRESOLVED", "closest_kcb_product": "", "products": "terpene"})
    banked = tmp_path / "cohort"
    banked.mkdir()
    (banked / "bgc_data.json").write_text(json.dumps({"strains": strains, "bgcs": bgcs}), encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_pangenome.py"), "--banked-dir", str(banked),
                        "--out-dir", str(out)], capture_output=True, text=True, timeout=120, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    md = (out / "Pangenome_Summary.md").read_text(encoding="utf-8")
    for phrase in ("not saturated", "keep yielding new chemistry", "has not plateaued"):
        assert phrase not in md, phrase
    rare = md.split("## Rarefaction", 1)[1].split("##", 1)[0]
    assert "families over the last 10 strains" in rare
