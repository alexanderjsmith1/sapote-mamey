"""`guide --bgc` help must say what happens when --bgc is omitted: the first --top-n BGC IDs in
gene-table order (mamey/bgc_guide.py), not the top-ranked leads."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_guide_bgc_help_states_gene_table_order():
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "guide", "--help"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120)
    text = " ".join((out.stdout + out.stderr).split())
    assert out.returncode == 0, text[-500:]
    assert "omit to cover --top-n leads" not in text
    assert "gene-table order" in text
