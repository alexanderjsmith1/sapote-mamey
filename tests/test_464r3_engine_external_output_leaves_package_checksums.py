"""An authoring command with its output outside the package does not refresh the package's checksums.

`domain-level --out <external>` (and every other post-seal authoring command with an output
option) refreshed the package's `post_seal_checksums.txt` after running, so the package's bytes
changed although nothing was written inside it. Only `guide` had the external-output exemption.
"""
from pathlib import Path

import pytest

from mamey import cli, packaging


@pytest.mark.parametrize("destination,expected", [("external", False), ("default", True), ("inside", True)])
def test_domain_level_refreshes_only_for_package_output(tmp_path, monkeypatch, destination, expected):
    package = tmp_path / "package"
    package.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    monkeypatch.setattr(cli, "_domain_level_command", lambda args: 0)
    called = []
    monkeypatch.setattr(packaging, "refresh_post_seal_checksums", lambda root: called.append(root))
    argv = ["domain-level", "--package", str(package)]
    if destination != "default":
        argv += ["--out", str(external if destination == "external" else package / "domain_level")]
    assert cli.main(argv) == 0
    assert bool(called) == expected
