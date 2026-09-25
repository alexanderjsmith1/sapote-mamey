import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import bigscape_input_decontam_guard as g  # noqa: E402


def _stage(tmp):
    d = tmp / "input"; d.mkdir()
    for n in ("AS-1_NODE_5_length_900_cov_3.9.region001.gbk", "AS-1_NODE_7_length_800_cov_40.1.region001.gbk",
              "AS-2_NODE_5_length_900_cov_3.9.region001.gbk"):
        (d / n).write_text("LOCUS")
    man = tmp / "removed.tsv"
    man.write_text("contig\tlength\tgc\tcoverage\tremoved_reason\nNODE_5_length_900_cov_3.912345\t900\t0.5\t3.9\tGC<0.64\n")
    return d, man


def test_flags_only_the_named_strain_and_matches_trimmed_coverage(tmp_path, capsys):
    d, man = _stage(tmp_path)
    assert g.main(["--regions", str(d), "--removed", f"AS-1={man}"]) == 4
    out = capsys.readouterr().out
    assert "AS-1_NODE_5" in out and "AS-2_NODE_5" not in out and "AS-1: 1 of 2" in out


def test_clean_inputs_pass(tmp_path):
    d, man = _stage(tmp_path)
    (d / "AS-1_NODE_5_length_900_cov_3.9.region001.gbk").unlink()
    assert g.main(["--regions", str(d), "--removed", f"AS-1={man}"]) == 0
