"""SM_HMM_DB must name a regular file.

Before: the override was checked with os.path.exists, so a directory was selected as the HMM
database. Now a directory is refused with a reason, and it does not fall through to another model.
"""
from pathlib import Path

from mamey import wheelhouse as wh


def test_directory_override_is_refused_not_selected(tmp_path, monkeypatch):
    for name in ("MAMEY_HMM_DIR", "MAMEY_DATA_ROOT"):
        monkeypatch.delenv(name, raising=False)
    bundle = tmp_path / "bundle"
    (bundle / "Wheelhouse" / "hmm").mkdir(parents=True)
    (bundle / "Wheelhouse" / "hmm" / "scanner_pfam_150.hmm").write_text("HMMER3/f\n")
    folder = tmp_path / "models"
    folder.mkdir()
    monkeypatch.setenv("SM_HMM_DB", str(folder))
    r = wh.resolve_hmm_database(bundle)
    assert r["path"] is None and r["tier"] == "none"
    assert "not a regular file" in r["reason"]


def test_file_override_still_wins(tmp_path, monkeypatch):
    model = tmp_path / "any_name.hmm"
    model.write_text("HMMER3/f\n")
    monkeypatch.setenv("SM_HMM_DB", str(model))
    r = wh.resolve_hmm_database(tmp_path / "bundle")
    assert r["path"] == str(model) and r["tier"] == "env-override"
