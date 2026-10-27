"""cddr-pks --directed-study-dir exits nonzero when the folder holds no study receipt.

Before, status UNKNOWN (no readable DIRECTED_PKS_STUDY_RECEIPT.json) exited 0, so an empty or
mistyped study folder looked like a finished report.
"""
import argparse

from mamey.cli import cddr_pks_command


def test_empty_study_dir_is_not_success(tmp_path):
    study = tmp_path / "study"; study.mkdir()
    args = argparse.Namespace(directed_study_dir=str(study), out=str(tmp_path / "report"),
                              report_name="CDDR_PKS_REPORT.md")
    assert cddr_pks_command(args) == 2
    assert (tmp_path / "report" / "CDDR_PKS_REPORT.md").is_file()   # the report still shows the gaps
