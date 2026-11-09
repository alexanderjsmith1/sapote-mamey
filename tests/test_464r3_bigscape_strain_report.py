"""Strain BiG-SCAPE report: true median, KNOWN rows without a reference stay unresolved, no 'identical' distance wording."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = "strain\tlocator\tantismash_class\tfamily_status\tnearest_mibig\tnearest_distance\n"


def _run(tmp_path, rows):
    spec = importlib.util.spec_from_file_location("_sbr_464r3", ROOT / "tools" / "strain_bigscape_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    per = tmp_path / "per_bgc.tsv"
    per.write_text(HEADER + "".join(rows))
    out = tmp_path / "EX-1_bigscape_report.md"
    argv = sys.argv[:]
    sys.argv = ["x", "--strain", "EX-1", "--per-bgc", str(per), "--out", str(out)]
    try:
        module.main()
    finally:
        sys.argv = argv
    return out.read_text()


def test_even_count_median_is_mean_of_middle_values(tmp_path):
    txt = _run(tmp_path, [
        "EX-1\tNODE_1_length_10000_cov_5.region001\tNRPS\tNOVEL\t\t\n",
        "EX-1\tNODE_2_length_20000_cov_5.region001\tNRPS\tNOVEL\t\t\n",
    ])
    assert "median 15,000" in txt
    assert "median 20,000" not in txt


def test_known_row_without_reference_is_unresolved_not_an_anchor(tmp_path):
    txt = _run(tmp_path, [
        "EX-1\tNODE_1_length_50000_cov_5.region001\tNRPS\tKNOWN\t\t\n",
        "EX-1\tNODE_2_length_50000_cov_5.region001\tNRPS\tKNOWN\tBGC0000001 (examplomycin)\t0.2\n",
    ])
    assert "1 of 2 KNOWN rows give no nearest MIBiG reference or no distance" in txt
    assert "| not given | — | NRPS | not given | NODE_1" in txt
    # resolved row sorts first
    assert txt.index("examplomycin") < txt.index("| not given |")
    assert "anchor to a characterized MIBiG cluster" not in txt


def test_distance_wording_does_not_call_zero_identical(tmp_path):
    txt = _run(tmp_path, ["EX-1\tNODE_1_length_50000_cov_5.region001\tNRPS\tKNOWN\tBGC0000001 (x)\t0\n"])
    assert "0 identical" not in txt
    assert "distance 0 does not show identical sequences" in txt
