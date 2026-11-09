"""`mamey workflow --ledger-out` never replaces an existing file or a source file.

Before: both entry points opened --ledger-out in write mode, so an existing file, including a
selected deliverable or a package file, was replaced by the ledger. The default ledger inside the
package is unchanged.
"""
import json
import os
from types import SimpleNamespace

from mamey import sapote_workflow as wf


def _package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain": "SYN-1", "bgcs": [{"bgc_id": "BGC001"}]}))
    return pkg


def _args(pkg, ledger_out, deliverables=None):
    return SimpleNamespace(package=str(pkg), deliverables=deliverables, strict=False,
                           as_json=False, ledger_out=ledger_out)


def test_existing_file_is_not_replaced(tmp_path, capsys):
    pkg = _package(tmp_path)
    earlier = tmp_path / "review" / "ledger.md"
    earlier.parent.mkdir()
    earlier.write_text("earlier ledger")
    assert wf.workflow_command(_args(pkg, str(earlier))) == 2
    assert earlier.read_text() == "earlier ledger"
    assert "OUTPUT_REFUSED" in capsys.readouterr().err


def test_deliverable_file_is_not_replaced(tmp_path):
    pkg = _package(tmp_path)
    deliv = tmp_path / "deliverables"
    deliv.mkdir()
    manifest = deliv / "DELIVERABLE_MANIFEST.md"
    manifest.write_text("authored")
    assert wf.workflow_command(_args(pkg, str(manifest), str(deliv))) == 2
    assert manifest.read_text() == "authored"


def test_path_inside_the_package_is_refused(tmp_path):
    pkg = _package(tmp_path)
    before = (pkg / "manifest.json").read_text()
    assert wf.workflow_command(_args(pkg, str(pkg / "manifest.json"))) == 2
    assert wf.workflow_command(_args(pkg, str(pkg / "new_ledger.md"))) == 2
    assert (pkg / "manifest.json").read_text() == before
    assert not (pkg / "new_ledger.md").exists()


def test_fresh_outside_path_is_written(tmp_path):
    pkg = _package(tmp_path)
    out = tmp_path / "review" / "ledger.md"
    out.parent.mkdir()
    assert wf.workflow_command(_args(pkg, str(out))) == 0
    assert out.read_text().strip()


def test_default_ledger_inside_the_package_still_rewrites(tmp_path):
    pkg = _package(tmp_path)
    assert wf.workflow_command(_args(pkg, None)) == 0
    assert wf.workflow_command(_args(pkg, None)) == 0
    assert any(n.endswith("_SAPOTE_WORKFLOW_LEDGER.md") for n in os.listdir(pkg))


def test_w9_message_does_not_promise_the_receipt_tool_clears_it(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain": "SYN-1", "gold_completeness": "JUDGMENT_PENDING"}))
    status, detail = wf.s9_receipt(str(pkg), None, {})
    assert status == wf.PENDING
    assert "flip gold_completeness" not in detail and "does not change it" in detail
