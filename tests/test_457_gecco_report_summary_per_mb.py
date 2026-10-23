"""tools/gecco_cohort_report.py --summary and --per-mb: the calls-against-references figure from a per-genome summary
computed elsewhere (reference zips on another machine), optionally per Mb of genome; synthetic data only."""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("gcr_s", ROOT / "tools" / "gecco_cohort_report.py")
gcr = importlib.util.module_from_spec(spec); spec.loader.exec_module(gcr)

COLS = ["strain", "group", "role", "genus", "gecco_calls", "calls_outside_regions", "genome_bp"]


def summary(tmp_path, rows):
    p = tmp_path / "summary.tsv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, COLS, delimiter="\t"); w.writeheader(); w.writerows(rows)
    return p


def rows():
    out = [dict(strain="I-1", group="G1", role="isolate", genus="Genus", gecco_calls=20, calls_outside_regions=6, genome_bp=5_000_000)]
    for i, (n, o, bp) in enumerate([(10, 2, 5e6), (20, 3, 10e6), (30, 4, 10e6), (40, 5, 10e6), (50, 6, 10e6)]):
        out.append(dict(strain=f"R-{i}", group="ref", role="reference", genus="Genus", gecco_calls=n, calls_outside_regions=o, genome_bp=int(bp)))
    out.append(dict(strain="S-1", group="ref", role="SID", genus="Genus", gecco_calls=99, calls_outside_regions=99, genome_bp=1_000_000))
    return out


def pct(out, measure):
    with open(out / "calls_vs_references" / "isolate_percentiles.tsv") as fh:
        return {r["measure"]: r for r in csv.DictReader(fh, delimiter="\t")}[measure]


def test_summary_mode_draws_raw_counts(tmp_path):
    s = summary(tmp_path, rows())
    assert gcr.main(["--summary", str(s), "--out", str(tmp_path / "out")]) == 0
    r = pct(tmp_path / "out", "gecco_calls")
    # raw calls 20 against 10, 20, 30, 40, 50: one below, one tied -> (1 + 0.5) / 5 = 30; SID not in the reference pool
    assert r["isolate_value"] == "20" and r["reference_genomes"] == "5" and r["midrank_percentile"] == "30"
    assert (tmp_path / "out" / "receipt.json").is_file()


def test_per_mb_changes_the_ranking(tmp_path):
    s = summary(tmp_path, rows())
    assert gcr.main(["--summary", str(s), "--per-mb", "--out", str(tmp_path / "out")]) == 0
    r = pct(tmp_path / "out", "gecco_calls_per_Mb")
    # per Mb: isolate 4.0 against 2, 2, 3, 4, 5 -> three below, one tied -> 70
    assert r["isolate_value"] == "4" and r["midrank_percentile"] == "70"
    cap = (tmp_path / "out" / "calls_vs_references" / "gecco_calls_vs_references_CAPTION.md").read_text()
    assert "per Mb" in cap


def test_per_mb_needs_genome_size(tmp_path):
    bad = rows(); bad[1]["genome_bp"] = ""
    s = summary(tmp_path, bad)
    assert gcr.main(["--summary", str(s), "--per-mb", "--out", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()


def test_genomes_and_summary_are_exclusive(tmp_path):
    s = summary(tmp_path, rows())
    assert gcr.main(["--summary", str(s), "--genomes", str(s), "--out", str(tmp_path / "o1")]) == 2
    assert gcr.main(["--out", str(tmp_path / "o2")]) == 2


def test_blank_reference_value_is_left_out_of_that_measure_only(tmp_path):
    rs = rows(); rs[1]["calls_outside_regions"] = ""     # reference R-0: outside count withheld (e.g. unparsable region ends)
    s = summary(tmp_path, rs)
    assert gcr.main(["--summary", str(s), "--out", str(tmp_path / "out")]) == 0
    assert pct(tmp_path / "out", "gecco_calls")["reference_genomes"] == "5"
    assert pct(tmp_path / "out", "calls_outside_regions")["reference_genomes"] == "4"
