"""The domain-prevalence widget footer reports channel coverage from its input.

It printed "Swiss-Prot is complete" in every widget, whatever the input. The owner approved
"Channel coverage: see AUDIT_RECEIPT.json" with each channel's state read from the ranking JSON.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _row(label, nr, sp):
    zero = {"hit": 0, "nohit": 0, "missing": 0, "mixed": 0}
    return {"source_tool": "clusterhmmer", "domain_label": label, "feature_occurrences": 1, "loci": 1, "strains": 1,
            "biosynthetic_relevance": "tailoring_or_pfam", "by_host": {"bee": {"strains": 1}}, "strain_idx": [0],
            "evidence": {"nr": dict(zero, **nr), "cnr": dict(zero), "sp": dict(zero, **sp)}, "loci_list": []}


def test_footer_reads_channel_states_from_the_ranking(tmp_path):
    ranking = {"scope": {"strains": 1, "loci": 2, "genes": 2}, "host_distribution": {"bee": 1},
               "strains_sorted": ["AS-1"], "strain_host": {"AS-1": "bee"},
               "rows": [_row("DomA", {"hit": 2, "missing": 1}, {}), _row("DomB", {"nohit": 1, "missing": 2}, {})]}
    (tmp_path / "domain_prevalence_ranking.json").write_text(json.dumps(ranking), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "domain_prevalence_widget.py"), str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    page = (tmp_path / "domain_prevalence_widget.html").read_text(encoding="utf-8")
    assert "Swiss-Prot is complete" not in page
    assert "Channel coverage: see AUDIT_RECEIPT.json." in page
    assert "nr 2 hit, 1 no-hit, 0 mixed, 3 missing" in page
    assert "ClusteredNR no saved states" in page
    assert "Swiss-Prot no saved states" in page
