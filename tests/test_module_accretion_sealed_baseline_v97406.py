"""G1: editable manifest rows cannot erase deltas from the sealed checksum inventory."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_module_accretion.py"


def _load():
    spec = importlib.util.spec_from_file_location("module_accretion_g1", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checksum_row(path: str, payload: bytes = b"fixture") -> str:
    return f"{hashlib.sha256(payload).hexdigest()}  ./{path}\n"


def _fixture(gate, root: Path) -> None:
    (root / "mamey").mkdir()
    (root / "mamey" / "base.py").write_text('"""base"""\n', encoding="utf-8")
    (root / "MODULE_MANIFEST.txt").write_text("mamey/base.py\tbase\n", encoding="utf-8")
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text(
        _checksum_row("mamey/base.py"), encoding="utf-8"
    )
    gate.ROOT = root
    gate.MAMEY = root / "mamey"
    gate.MANIFEST = root / "MODULE_MANIFEST.txt"
    gate.SOURCE_CHECKSUMS = root / "SOURCE_CHECKSUMS_SHA256.txt"
    gate.CHANGELOG = root / "CHANGELOG.md"


def test_module_plus_editable_manifest_row_without_justification_fails(tmp_path):
    gate = _load()
    _fixture(gate, tmp_path)
    (tmp_path / "mamey" / "zz_new.py").write_text('"""new"""\n', encoding="utf-8")
    (tmp_path / "MODULE_MANIFEST.txt").write_text(
        "mamey/base.py\tbase\nmamey/zz_new.py\tnew\n", encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_text("# v9.7.406\n- unrelated\n", encoding="utf-8")

    assert gate.check() == 1


def test_same_fixture_with_exact_accretion_justification_passes(tmp_path):
    gate = _load()
    _fixture(gate, tmp_path)
    (tmp_path / "mamey" / "zz_new.py").write_text('"""new"""\n', encoding="utf-8")
    (tmp_path / "MODULE_MANIFEST.txt").write_text(
        "mamey/base.py\tbase\nmamey/zz_new.py\tnew\n", encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# v9.7.406\n- Accretion-justified: mamey/zz_new.py — focused capability\n",
        encoding="utf-8",
    )

    assert gate.check() == 0


def test_checksum_inventory_parser_fails_closed(tmp_path):
    gate = _load()
    _fixture(gate, tmp_path)
    checksums = tmp_path / "SOURCE_CHECKSUMS_SHA256.txt"

    checksums.write_text("not-a-digest  ./mamey/base.py\n", encoding="utf-8")
    assert gate.check() == 1
    row = _checksum_row("mamey/base.py")
    checksums.write_text(row + row, encoding="utf-8")
    assert gate.check() == 1
    checksums.write_text(_checksum_row("README.md"), encoding="utf-8")
    assert gate.check() == 1


def test_seal_scripts_are_not_changed_for_g1():
    checker = GATE.read_text(encoding="utf-8")
    assert "SOURCE_CHECKSUMS_SHA256.txt" in checker
    assert "MODULE_MANIFEST.sealed.txt" not in checker
