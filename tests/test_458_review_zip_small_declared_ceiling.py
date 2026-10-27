"""A declared path ceiling binds below the global large-file cutoff too."""
import zipfile

import pytest

from tools import preflight_zip_hygiene as hygiene


@pytest.mark.parametrize("suffix", ["pdf", "xlsx", "bin"])
def test_declared_small_ceiling_binds(suffix):
    name = "docs/limited." + suffix
    assert hygiene._oversized(name, 2 * 1024 * 1024,
                              {"./" + name: (1024 * 1024, "reviewed cap")})


def test_scan_reports_small_file_above_its_declared_ceiling(tmp_path, monkeypatch):
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("docs/limited.pdf", b"x" * 64)
    monkeypatch.setattr(hygiene, "_load_path_allowlist",
                        lambda: {"./docs/limited.pdf": (32, "reviewed cap")})
    result = hygiene.scan(archive)
    assert result["large"] and "docs/limited.pdf" in str(result["large"])


def test_unlisted_small_file_still_uses_global_cutoff():
    assert not hygiene._oversized("docs/unlisted.bin", 64, {})
