"""v9.7.238 (F03): path-qualified references must resolve by FULL relative path, not basename.

Basename matching let `tools/sapote_workflow.py` be satisfied by `mamey/sapote_workflow.py`, so the
.237 cut shipped 9 references (including the ledger header written into every package) pointing at a
file that did not exist, and the dangling-ref guard passed. This pins the fix.
"""
import pathlib, sys, importlib.util

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cdr", ROOT / "tools" / "check_dangling_refs.py")
cdr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdr)


def test_shim_exists_so_the_ledger_header_cites_a_real_path():
    assert (ROOT / "tools" / "sapote_workflow.py").is_file(), \
        "tools/sapote_workflow.py is cited by the workflow ledger header, the contract, and cli.py"


def test_strict_paths_flags_a_path_qualified_ref_whose_exact_path_is_missing(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "mamey").mkdir()
    # a module with the same basename exists elsewhere -> basename matching would pass
    (tmp_path / "mamey" / "widget.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "docs" / "d.md").write_text("see `tools/widget.py` for details\n", encoding="utf-8")
    lenient = cdr.scan_tools(tmp_path, strict_paths=False)
    strict = cdr.scan_tools(tmp_path, strict_paths=True)
    assert "widget.py" not in lenient          # basename resolves -> miss (the F01 bug)
    assert "tools/widget.py" in strict         # full path does not exist -> caught


def test_strict_paths_accepts_a_ref_whose_exact_path_exists(tmp_path):
    (tmp_path / "docs").mkdir(); (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "widget.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "docs" / "d.md").write_text("see `tools/widget.py`\n", encoding="utf-8")
    assert "tools/widget.py" not in cdr.scan_tools(tmp_path, strict_paths=True)


def test_workflow_shim_holds_no_logic():
    src = (ROOT / "tools" / "sapote_workflow.py").read_text(encoding="utf-8")
    assert "sapote_workflow" in src and len(src.splitlines()) < 60, "the shim must stay a delegator"


def test_support_installer_resolves_without_masking_wrong_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "bundle_support").mkdir()
    (tmp_path / "bundle_support" / "installer.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    doc = tmp_path / "docs" / "setup.md"
    doc.write_text("Run `bundle_support/installer.sh`.\n", encoding="utf-8")
    assert cdr.scan_tools(tmp_path, strict_paths=False) == {}
    assert cdr.scan_tools(tmp_path, strict_paths=True) == {}
    doc.write_text("Run `tools/installer.sh`.\n", encoding="utf-8")
    assert cdr.scan_tools(tmp_path, strict_paths=False) == {}
    assert "tools/installer.sh" in cdr.scan_tools(tmp_path, strict_paths=True)
