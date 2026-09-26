"""An explicitly supplied contig roster must not fail open when unusable."""

import os
from pathlib import Path
import subprocess


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "make_public_tier.sh"


def _scan(tmp_path: Path, roster: Path) -> tuple[str, str]:
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "generic.txt").write_text("NODE_1_length_100_cov_1.0\n")
    source = SCRIPT.read_text()
    start = source.index('CONTIG_LEAK_SCAN="${CONTIG_LEAK_SCAN:-1}"')
    end = source.index("\n_contig_leak_scan\n", start) + len("\n_contig_leak_scan\n")
    shell = "FAIL=0\n" + source[start:end] + 'printf "AUDIT_FAIL=%s\\n" "$FAIL"\n'
    env = dict(os.environ, STAGE=str(stage), CONTIG_LEAK_SCAN="1", CONTIG_LEAK_FAIL="1",
               CONTIG_ROSTER=str(roster))
    run = subprocess.run(["bash", "-c", shell], env=env, text=True,
                         capture_output=True, check=True)
    return run.stdout, run.stderr


def test_missing_explicit_roster_refuses_classification(tmp_path):
    out, err = _scan(tmp_path, tmp_path / "missing.txt")
    assert "AUDIT_FAIL=1" in out, err
    assert "CONTIG_ROSTER" in err


def test_empty_explicit_roster_refuses_classification(tmp_path):
    roster = tmp_path / "roster.txt"
    roster.write_text("")
    out, err = _scan(tmp_path, roster)
    assert "AUDIT_FAIL=1" in out, err
    assert "CONTIG_ROSTER" in err


def test_malformed_explicit_roster_refuses_classification(tmp_path):
    roster = tmp_path / "roster.txt"
    roster.write_text("not-a-contig\n")
    out, err = _scan(tmp_path, roster)
    assert "AUDIT_FAIL=1" in out, err
    assert "CONTIG_ROSTER" in err


def test_valid_roster_without_a_match_reports_zero(tmp_path):
    roster = tmp_path / "roster.txt"
    roster.write_text("NODE_2_length_200_cov_2.0\n")
    out, err = _scan(tmp_path, roster)
    assert "AUDIT_FAIL=0" in out, err
    assert "0 match the roster" in err


def test_valid_matching_roster_keeps_hard_fail(tmp_path):
    roster = tmp_path / "roster.txt"
    roster.write_text("NODE_1_length_100_cov_1.0\n")
    out, err = _scan(tmp_path, roster)
    assert "AUDIT_FAIL=1" in out, err
    assert "1 real cohort contig name(s)" in err
