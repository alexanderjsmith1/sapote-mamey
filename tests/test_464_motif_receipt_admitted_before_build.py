"""The motif sidecar checks its receipt path before building the database."""
import json

import pytest

from mamey import structured_domain_motif_extension as mod
from tests.test_structured_domain_motif_extension import fixture


def _args(tmp_path, out, receipt):
    source, base, row = fixture(tmp_path)
    inv = tmp_path / "inventory.json"
    inv.write_text(json.dumps([row]))
    return ["--inventory", str(inv), "--inventory-pin", mod.sha(inv), "--source-root", str(source),
            "--base", str(base), "--base-pin", mod.sha(base), "--out", str(out),
            "--allowed-root", str(tmp_path), "--receipt", str(receipt)], base


def test_receipt_outside_root_builds_nothing(tmp_path):
    out = tmp_path / "sidecar.sqlite"
    argv, _ = _args(tmp_path, out, tmp_path.parent / "elsewhere_receipt.json")
    with pytest.raises(ValueError, match="RECEIPT_ROOT_DRIFT"):
        mod.main(argv)
    assert not out.exists()


@pytest.mark.parametrize("target", ["out", "journal", "base"])
def test_receipt_cannot_overwrite_the_database_or_an_input(tmp_path, target):
    out = tmp_path / "sidecar.sqlite"
    receipt = {"out": out, "journal": tmp_path / "sidecar.sqlite-journal", "base": tmp_path / "base.sqlite"}[target]
    argv, base = _args(tmp_path, out, receipt)
    base_before = mod.sha(base)
    with pytest.raises(ValueError, match="RECEIPT_PATH_COLLISION"):
        mod.main(argv)
    assert not out.exists() and mod.sha(base) == base_before


def test_existing_receipt_needs_resume(tmp_path):
    out, receipt = tmp_path / "sidecar.sqlite", tmp_path / "receipt.json"
    receipt.write_text("{}")
    argv, _ = _args(tmp_path, out, receipt)
    with pytest.raises(FileExistsError):
        mod.main(argv)
    assert not out.exists() and receipt.read_text() == "{}"
