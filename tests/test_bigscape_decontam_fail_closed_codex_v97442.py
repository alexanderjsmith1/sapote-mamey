"""A clean exit requires an existing, nonempty staged input and a bound manifest."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import bigscape_input_decontam_guard as guard  # noqa: E402


def test_missing_and_empty_region_roots_refuse(tmp_path):
    manifest = tmp_path / "removed.tsv"
    manifest.write_text("NODE_1_length_100_cov_1\n")
    for folder in (tmp_path / "absent", tmp_path / "empty"):
        if folder.name == "empty":
            folder.mkdir()
        with pytest.raises(SystemExit) as error:
            guard.main(["--regions", str(folder), "--removed", f"fixture={manifest}"])
        assert error.value.code == 2


def test_no_manifest_refuses_even_with_staged_gbk(tmp_path):
    (tmp_path / "fixture_NODE_2_length_100_cov_1.region001.gbk").write_text("LOCUS\n//\n")
    with pytest.raises(SystemExit) as error:
        guard.main(["--regions", str(tmp_path)])
    assert error.value.code == 2


def test_staged_authority_without_matching_manifest_refuses(tmp_path, capsys):
    (tmp_path / "fixture_NODE_2_length_100_cov_1.region001.gbk").write_text("LOCUS\n//\n")
    (tmp_path / "_fixture_ASSEMBLY_AUTHORITY.md").write_text("fixture authority\n")
    manifest = tmp_path / "other_removed.tsv"
    manifest.write_text("NODE_1_length_100_cov_1\n")
    assert guard.main(["--regions", str(tmp_path), "--removed", f"other={manifest}",
                       "--authority-glob", str(tmp_path / "*_ASSEMBLY_AUTHORITY.md")]) == 4
    assert "MISSING_REMOVED_MANIFEST\tfixture" in capsys.readouterr().out
