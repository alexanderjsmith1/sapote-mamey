"""The strain BiG-SCAPE report counts NOVEL only from a NOVEL status and makes no novelty claim."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _report():
    spec = importlib.util.spec_from_file_location("_strain_bigscape_report_464", ROOT / "tools" / "strain_bigscape_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(tmp_path, rows):
    per = tmp_path / "per_bgc.tsv"
    per.write_text("strain\tlocator\tantismash_class\tfamily_status\tnearest_mibig\tanchor\tnearest_distance\n"
                   + "".join(rows))
    out = tmp_path / "ABC-12_bigscape_report.md"
    argv = sys.argv[:]
    sys.argv = ["x", "--strain", "ABC-12", "--per-bgc", str(per), "--out", str(out)]
    try:
        _report().main()
    finally:
        sys.argv = argv
    return out.read_text()


def test_blank_and_held_statuses_are_not_counted_as_novel(tmp_path):
    txt = _run(tmp_path, [
        "ABC-12\tNODE_1_length_50000_cov_10.region001\tNRPS\tKNOWN\tBGC1 (x)\tBGC1 (x)\t0.4\n",
        "ABC-12\tNODE_2_length_50000_cov_10.region001\tNRPS\tnovel\t\t\t1.0\n",
        "ABC-12\tNODE_3_length_50000_cov_10.region001\tNRPS\t\t\t\t\n",
        "ABC-12\tNODE_4_length_50000_cov_10.region001\tNRPS\tHELD\t\t\t\n",
    ])
    assert "1 labeled KNOWN" in txt and "1 labeled NOVEL" in txt
    assert "2 have no family status" in txt


def test_report_text_makes_no_novelty_or_chemistry_claim(tmp_path):
    txt = _run(tmp_path, ["ABC-12\tNODE_2_length_50000_cov_10.region001\tNRPS\tNOVEL\t\t\t1.0\n"])
    for phrase in ("no analog", "private chemistry", "new-chemistry", "discovery targets"):
        assert phrase not in txt
