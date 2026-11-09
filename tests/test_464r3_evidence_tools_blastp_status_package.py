"""blastp_status refuses a path that is not a package instead of reporting an empty overlay."""
import pytest
from mamey.blastp_ingest import blastp_status


def test_nonexistent_package_is_refused(tmp_path):
    with pytest.raises(FileNotFoundError, match="BLASTP_STATUS_PACKAGE_NOT_FOUND"):
        blastp_status(tmp_path / "no_such_package")


def test_folder_without_manifest_is_refused(tmp_path):
    with pytest.raises(FileNotFoundError, match="BLASTP_STATUS_PACKAGE_NOT_FOUND"):
        blastp_status(tmp_path)


def test_real_package_without_overlay_is_empty(tmp_path):
    (tmp_path / "manifest.json").write_text("{}\n")
    assert blastp_status(tmp_path) == []
