"""build_size_profile.py: --unit label (default kb, unchanged) and the supplied-table mode at print size."""
import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_size_profile.py"


def load():
    spec = importlib.util.spec_from_file_location("bsp_455", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def labels_drawn(monkeypatch, tmp_path, **kw):
    """Run plot_all on three synthetic strains and collect every axis label and title it sets."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.axes import Axes
    from collections import Counter
    seen = []
    for name in ("set_ylabel", "set_xlabel", "set_title"):
        orig = getattr(Axes, name)
        monkeypatch.setattr(Axes, name, lambda self, s, *a, _o=orig, **k: (seen.append(str(s)), _o(self, s, *a, **k))[1])
    mod = load()
    strains = {f"SYN-{i}": {"contigs": 10 * (i + 1)} for i in range(3)}
    sids = list(strains)
    siz = {s: Counter({"T1PKS": 10.0 + i, "NRPS": 5.0 + 2 * i}) for i, s in enumerate(sids)}
    cnt = {s: Counter({"T1PKS": 1, "NRPS": 2}) for s in sids}
    mod.plot_all(str(tmp_path), strains, sids, ["T1PKS", "NRPS"], siz, cnt, **kw)
    return seen


def test_default_unit_keeps_kb_labels(monkeypatch, tmp_path):
    seen = labels_drawn(monkeypatch, tmp_path)
    assert "total BGC size (kb)" in seen
    assert any("BGC size kb (r=" in s for s in seen)
    assert any(s.startswith("BGC count and BGC size (kb) by class") for s in seen)


def test_unit_replaces_kb_everywhere(monkeypatch, tmp_path):
    seen = labels_drawn(monkeypatch, tmp_path, unit="thousand aa")
    assert "total BGC size (thousand aa)" in seen
    assert not any("kb" in s for s in seen)


def write_table(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, ["strain", "genus", "bgc_class", "core_aa_total"], delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, cwd=ROOT)


def synthetic_rows():
    return [dict(strain=s, genus="Synthia", bgc_class=c, core_aa_total=v)
            for s, base in (("SYN-1", 1000), ("SYN-2", 3000)) for c, v in (("PKS", base), ("NRPS", base // 2), ("Other", 400))]


def test_table_mode_draws_print_size_8pt(tmp_path):
    t = tmp_path / "t.tsv"
    write_table(t, synthetic_rows())
    out = tmp_path / "out"
    r = run("--table", t, "--value-scale", "0.001", "--unit", "Core biosynthetic protein (thousand aa)", "--out-dir", out)
    assert r.returncode == 0, r.stderr
    svg = (out / "fig_size_by_class_table.svg").read_text()
    assert (out / "fig_size_by_class_table.png").exists()
    width_in = float(re.search(r'<svg[^>]*width="([0-9.]+)pt"', svg).group(1)) / 72
    assert abs(width_in - 6.5) < 0.01
    sizes = {float(x) for x in re.findall(r"font-size[:=]\s*\"?([0-9.]+)px", svg) + re.findall(r"font:[^;\"]*?([0-9.]+)px", svg)}
    assert sizes and min(sizes) >= 8.0
    assert "thousand aa" in svg and "kb" not in svg
    data = list(csv.DictReader(open(out / "fig_size_by_class_table_data.tsv"), delimiter="\t"))
    assert [d["strain"] for d in data] == ["SYN-1", "SYN-2"]
    assert float(data[1]["PKS"]) == 3.0 and float(data[0]["total"]) == pytest.approx(1.9)


def test_table_mode_refuses_bad_values(tmp_path):
    t = tmp_path / "bad.tsv"
    rows = synthetic_rows()
    rows[0]["core_aa_total"] = "-5"
    write_table(t, rows)
    r = run("--table", t, "--out-dir", tmp_path / "o1")
    assert r.returncode != 0 and "REFUSED" in (r.stdout + r.stderr)
    rows[0]["core_aa_total"] = "n/a"
    write_table(t, rows)
    r = run("--table", t, "--out-dir", tmp_path / "o2")
    assert r.returncode != 0 and "REFUSED" in (r.stdout + r.stderr)


def test_table_mode_refuses_missing_column(tmp_path):
    t = tmp_path / "t.tsv"
    write_table(t, synthetic_rows())
    r = run("--table", t, "--value-column", "absent_column", "--out-dir", tmp_path / "o")
    assert r.returncode != 0 and "REFUSED" in (r.stdout + r.stderr)
