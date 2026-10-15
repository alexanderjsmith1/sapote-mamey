"""Card attine_452_bgc_class_summary: tools/bgc_class_summary.py builds the class summary the BGC class figures read.

The bee and moss class figures were drawn from summaries made by a paper script (summarise.py) outside the bundle.
The tool carries the same rules: a region counts once per class, a region with several classes is a hybrid, display
names and families as in the bee and moss papers, saccharide its own family. Synthetic IDs only.
"""
import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/bgc_class_summary.py"
spec = importlib.util.spec_from_file_location("bgc_class_summary_t", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
REGIONS = [("AS-971", "r1", "T1PKS;NRPS"), ("AS-971", "r2", "saccharide"), ("AS-971", "r3", "lanthipeptide-class-i"),
           ("AS-972", "r1", "T1PKS"), ("AS-972", "r2", "HR-T2PKS"), ("AS-973", "r1", "terpene;NRPS-like")]


def write(tmp_path, rows=REGIONS, groups=None):
    p = tmp_path / "regions.tsv"
    p.write_text("strain\tstrictness\trecord\tregion_file\tproducts\n" + "".join(f"{s}\tloose\tc\t{r}\t{x}\n" for s, r, x in rows))
    g = None
    if groups:
        g = tmp_path / "groups.tsv"
        g.write_text("strain\tgroup\n" + "".join(f"{s}\t{v}\n" for s, v in groups.items()))
    return p, g


def run(tmp_path, **kw):
    p, g = write(tmp_path, **kw)
    out = tmp_path / "summary.tsv"
    argv = ["--regions", str(p), "--out", str(out)] + (["--groups", str(g)] if g else [])
    assert mod.main(argv) == 0
    return {r["antismash_class"] + "|" + r["group"]: r for r in csv.DictReader(out.open(), delimiter="\t")}


def test_counts_hybrids_and_genomes(tmp_path):
    s = run(tmp_path)
    assert (s["T1PKS|All"]["regions"], s["T1PKS|All"]["hybrid_regions"], s["T1PKS|All"]["genomes"]) == ("2", "1", "2")
    assert s["NRPS|All"]["hybrid_regions"] == "1" and s["saccharide|All"]["hybrid_regions"] == "0"


def test_display_names_and_families(tmp_path):
    s = run(tmp_path)
    assert (s["T1PKS|All"]["display"], s["T1PKS|All"]["family"]) == ("Type I PKS", "PKS")
    assert (s["HR-T2PKS|All"]["display"], s["HR-T2PKS|All"]["family"]) == ("Highly reducing type II PKS", "PKS")
    assert (s["lanthipeptide-class-i|All"]["display"], s["lanthipeptide-class-i|All"]["family"]) == ("Lanthipeptide (class I)", "RiPP")
    assert s["saccharide|All"]["family"] == "Saccharide" and s["terpene|All"]["family"] == "Terpene"
    assert s["NRPS-like|All"]["family"] == "NRPS"


def test_groups_split_the_counts(tmp_path):
    s = run(tmp_path, groups={"AS-971": "A", "AS-972": "B", "AS-973": "B"})
    assert s["T1PKS|A"]["regions"] == "1" and s["T1PKS|B"]["regions"] == "1"


def test_refusals(tmp_path):
    (tmp_path / "a").mkdir()
    with pytest.raises(ValueError, match="different strains"):
        run(tmp_path / "a", groups={"AS-971": "A"})
    (tmp_path / "b").mkdir()
    with pytest.raises(ValueError, match="duplicate region"):
        run(tmp_path / "b", rows=REGIONS + [REGIONS[0]])
    (tmp_path / "c").mkdir()
    p, _ = write(tmp_path / "c")
    out = tmp_path / "c" / "x.tsv"
    out.write_text("")
    with pytest.raises(FileExistsError):
        mod.main(["--regions", str(p), "--out", str(out)])


def test_help():
    assert subprocess.run([sys.executable, str(TOOL), "--help"], capture_output=True).returncode == 0
