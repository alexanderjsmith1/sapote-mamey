"""plot_examples.py runs on the CSVs export_figure_ready.py actually writes.

The exporter keys every table by `strain`. plot_examples.py read `sid` from strain_summary.csv and
class_by_strain.csv, so the documented command stopped with KeyError: 'sid' at Fig 3. The fixture
headers are read from the exporter's own W() calls, so this test follows the real schema.
"""
import ast
import csv
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _exporter_headers():
    tree = ast.parse((ROOT / "tools" / "export_figure_ready.py").read_text(encoding="utf-8"))
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names[t.id] = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
    out = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "W" and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)):
            h = node.args[1]
            out[node.args[0].value] = ([e.value for e in h.elts] if isinstance(h, ast.List) else names[h.id])
    return out


def _write(d, name, header, rows):
    with open(d / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def test_plot_examples_runs_on_exporter_schema(tmp_path):
    H = _exporter_headers()
    assert "sid" not in H["strain_summary.csv"] and "strain" in H["strain_summary.csv"]
    _write(tmp_path, "strain_summary.csv", H["strain_summary.csv"], [
        {"strain": "REF-1", "assembly_tier": "GOOD", "n50": "250000", "fragmentation_loss": "0"},
        {"strain": "REF-2", "assembly_tier": "POOR", "n50": "12000", "fragmentation_loss": "3"},
    ])
    _write(tmp_path, "class_by_strain.csv", H["class_by_strain.csv"], [
        {"strain": "REF-1", "product_class": "NRPS", "n_bgcs": "4"},
        {"strain": "REF-2", "product_class": "NRPS", "n_bgcs": "2"},
        {"strain": "REF-2", "product_class": "terpene", "n_bgcs": "1"},
    ])
    _write(tmp_path, "class_prevalence.csv", H["class_prevalence.csv"], [
        {"product_class": "NRPS", "n_strains": "2", "band": "CORE"},
        {"product_class": "terpene", "n_strains": "1", "band": "UNIQUE"},
    ])
    env = dict(os.environ, MPLBACKEND="Agg")
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "plot_examples.py"), str(tmp_path)],
                          capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-600:]
    for name in ("fig1_fragmentation_gradient.png", "fig2_class_prevalence.png", "fig3_class_by_strain_heatmap.png"):
        assert (tmp_path / name).stat().st_size > 0
