"""Offline R source ZIPs select the package root, not archive metadata."""

import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bundle_support" / "install_r_figure_packages.R"
RSCRIPT = shutil.which("Rscript")
pytestmark = pytest.mark.skipif(not RSCRIPT, reason="Rscript not installed")


def _package(z: ZipFile, name: str) -> None:
    z.writestr(
        f"{name}/DESCRIPTION",
        f"Package: {name}\nVersion: 0.1\nTitle: Toy\nDescription: Toy fixture.\n"
        "License: MIT\nAuthor: fixture\nMaintainer: fixture <fixture@example.org>\n",
    )
    z.writestr(f"{name}/NAMESPACE", f"export(f_{name})\n")
    z.writestr(f"{name}/R/f.R", f"f_{name} <- function() 1\n")


def _run(tmp_path: Path, names: tuple[str, ...]) -> tuple[subprocess.CompletedProcess, Path]:
    source = tmp_path / "from"
    library = tmp_path / "lib"
    source.mkdir()
    library.mkdir()
    with ZipFile(source / "toy_0.1.zip", "w") as z:
        z.writestr("__MACOSX/._toy", "metadata")
        for name in names:
            _package(z, name)
    env = dict(
        os.environ,
        R_LIBS=str(library),
        http_proxy="http://127.0.0.1:9",
        https_proxy="http://127.0.0.1:9",
    )
    env.pop("no_proxy", None)
    env.pop("NO_PROXY", None)
    result = subprocess.run(
        [RSCRIPT, str(INSTALLER), "--from", str(source)],
        env=env, text=True, capture_output=True, timeout=120,
    )
    return result, library


def test_zip_ignores_mac_metadata_and_installs_package(tmp_path):
    result, library = _run(tmp_path, ("toyfixture",))
    assert (library / "toyfixture").is_dir(), result.stderr[-2000:]


def test_zip_with_two_package_roots_refuses_ambiguity(tmp_path):
    result, library = _run(tmp_path, ("toyfixture", "otherfixture"))
    assert result.returncode != 0
    assert "exactly one" in result.stderr.lower()
    assert not (library / "toyfixture").exists()
    assert not (library / "otherfixture").exists()
