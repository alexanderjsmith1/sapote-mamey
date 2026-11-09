"""check_antismash_profile: an empty discovery under --warn-only carries the advisory marker.

Before: mixed, mismatch and duplicate cases printed "[--warn-only: advisory exit 0, not
acceptance]", but an empty discovery exited 0 without it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import check_antismash_profile as cap


def test_empty_discovery_with_warn_only_says_advisory(tmp_path, capsys):
    assert cap.main([str(tmp_path), "--warn-only"]) == 0
    assert "advisory exit 0, not acceptance" in capsys.readouterr().err


def test_empty_discovery_without_warn_only_still_fails(tmp_path, capsys):
    assert cap.main([str(tmp_path)]) == 1
    assert "advisory" not in capsys.readouterr().err
