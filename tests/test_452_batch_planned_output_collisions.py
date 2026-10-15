"""Publisher-boundary regressions; the comparator enhancer is intentionally stubbed.

Read the actual build function from its owner without importing the heavyweight
enhancer module. These tests cover path admission, publication and receipt hashes,
not comparator interpretation, scientific evidence or full CLI integration.
"""

import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


OWNER = (
    Path(__file__).resolve().parents[1]
    / "deliverable_tools"
    / "batch_mibig_comparator_context.py"
)
ENHANCED_HTML = "<html>synthetic enhanced report</html>"
CONTEXT_FIELDS = (
    "rows",
    "unique_comparators",
    "activity_verified_context_rows",
    "mechanism_verified_context_rows",
    "no_admitted_comparator_rows",
    "comparator_context_unresolved_rows",
    "component_bound_rows",
)
COLLISION = "MIBIG_BATCH_GATE: output and receipt paths must be distinct"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def publisher():
    tree = ast.parse(OWNER.read_text(encoding="utf-8"), filename=str(OWNER))
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build"
    ]
    assert len(functions) == 1, "expected one actual publisher build function"
    calls = []

    def enhance(*args):
        calls.append(args)
        return ENHANCED_HTML, dict.fromkeys(CONTEXT_FIELDS, 0)

    namespace = {
        "__file__": str(OWNER),
        "Path": Path,
        "json": json,
        "sha256": _sha256,
        "enhance_mibig_summary": enhance,
    }
    isolated = ast.Module(body=functions, type_ignores=[])
    exec(compile(isolated, str(OWNER), "exec"), namespace)
    return SimpleNamespace(build=namespace["build"], calls=calls)


@pytest.fixture
def reports(tmp_path):
    root = tmp_path / "authoritative_reports"
    root.mkdir()
    (root / "REPORT.html").write_text("original first report", encoding="utf-8")
    later = root / "later" / "REPORT.html"
    later.parent.mkdir()
    later.write_text("original later report", encoding="utf-8")
    (root / "source_note.txt").write_text("preserve source tree", encoding="utf-8")
    return root, _snapshot(root)


@pytest.mark.parametrize(
    "mode",
    ["same_first", "same_later", "ancestor", "descendant", "resolved_alias"],
)
def test_receipt_collision_refused_before_any_publication(
    tmp_path, reports, publisher, mode
):
    source, original = reports
    output = tmp_path / "output"
    first = output / "REPORT.html"
    later = output / "later" / "REPORT.html"
    if mode == "same_first":
        receipt = first
    elif mode == "same_later":
        receipt = later
    elif mode == "ancestor":
        receipt = output / "later"
    elif mode == "descendant":
        receipt = later / "receipt.json"
    else:
        alias = tmp_path / "output_alias"
        alias.symlink_to(output, target_is_directory=True)
        receipt = alias / "later" / "REPORT.html"

    with pytest.raises(ValueError, match=COLLISION):
        publisher.build(source, output, tmp_path / "mibig", receipt_out=receipt)

    assert _snapshot(source) == original
    assert publisher.calls == [], "path refusal must precede enhancement"
    assert not output.exists(), "even the earlier planned output must remain absent"
    assert not first.exists() and not later.exists()
    assert not receipt.exists()


@pytest.mark.parametrize("mode", ["default", "inside_sibling", "outside", "prefix_sibling"])
def test_separate_receipt_preserves_html_hashes_and_authoritative_sources(
    tmp_path, reports, publisher, mode
):
    source, original = reports
    output = tmp_path / "output"
    receipt_out = {
        "default": None,
        "inside_sibling": output / "receipt.json",
        "outside": tmp_path / "receipts" / "batch.json",
        "prefix_sibling": output / "REPORT.html.receipt.json",
    }[mode]
    result = publisher.build(
        source, output, tmp_path / "mibig", receipt_out=receipt_out
    )
    receipt = receipt_out or output / "MIBIG_COMPARATOR_CONTEXT_BATCH_RECEIPT.json"

    assert result["status"] == "PASS" and result["report_count"] == 2
    assert result["authoritative_inputs_mutated"] is False
    assert json.loads(receipt.read_text(encoding="utf-8")) == result
    assert len(publisher.calls) == 2
    assert {row["output_locator"] for row in result["records"]} == {
        "REPORT.html", "later/REPORT.html"
    }
    for row in result["records"]:
        destination = output / row["output_locator"]
        assert destination.read_text(encoding="utf-8") == ENHANCED_HTML
        assert row["output_sha256"] == _sha256(destination)
        assert row["source_sha256"] == _sha256(source / row["source_locator"])
    assert _snapshot(source) == original
