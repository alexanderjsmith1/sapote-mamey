"""v9.7.404 — the release manifest must describe HOW its test counts were obtained.

`gen_release_manifest.py` hardcoded the phrase "receipt-bound log" into the full-suite evidence
row no matter where the numbers came from, so a count typed on the command line was published as
if a log had been parsed and could be re-checked. The sealed v9.7.403 manifest carries that
mislabel. A release manifest is read later as evidence by people who were not in the room; the
house rule is that a metric travels with its provenance.

An independent QA pass flagged that the fix shipped with **no test** — every new branch could
regress while the focused suite stayed green. That is what this file closes. It drives `main()`
through the CLI, not the helper, because the routing from arguments to label is the part that can
break.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gen_release_manifest",
                                              ROOT / "tools" / "gen_release_manifest.py")
grm = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(grm)

ROW = "| Full pytest suite |"


def _fake_root(tmp_path: Path) -> None:
    """The three identity sources `read_truth()` reads, so the tool runs against a throwaway root
    instead of the real bundle — no test here may rewrite the candidate's own manifest."""
    (tmp_path / "mamey").mkdir(exist_ok=True)
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "CITATION.cff").write_text("version: '8.8.8'\n", encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text("build=20200101v1a\n", encoding="utf-8")


def _manifest(tmp_path: Path, row: str | None = None) -> Path:
    """A minimal manifest carrying the self-describing fields the tool rewrites."""
    _fake_root(tmp_path)
    body = [
        "# Release Manifest",
        "",
        "**Cut/build date:** 2020-01-01  ",
        "**Bundle version:** `sapote-mamey-v0.0.0`  ",
        "**Engine:** Mamey v0.0.0  ",
        "**Build stamp:** OLD  ",
        "",
        "## Validation status",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    if row:
        body.append(row)
    body += ["", "All four tiers share build stamp `OLD`.", ""]
    p = tmp_path / "RELEASE_MANIFEST.md"
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p


def _row_of(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(ROW):
            return line
    raise AssertionError(f"no evidence row in:\n{path.read_text(encoding='utf-8')}")


def _log(tmp_path: Path, passed: int, skipped: int) -> Path:
    p = tmp_path / "pytest.log"
    p.write_text(f"= {passed} passed, {skipped} skipped in 1.00s =\n", encoding="utf-8")
    return p


# --- the provenance contract ------------------------------------------------------------------

def test_explicit_counts_are_labelled_operator_supplied(tmp_path, monkeypatch):
    """The case that produced the defect: no log exists, so do not claim one."""
    _manifest(tmp_path)
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--apply", "--tests-passed", "12", "--tests-skipped", "3"])
    row = _row_of(tmp_path / "RELEASE_MANIFEST.md")
    assert "12 passed, 3 skipped" in row
    assert "operator-supplied counts, no log bound" in row
    assert "receipt-bound log" not in row, "a typed count must never be published as receipt-bound"


def test_parsed_log_is_labelled_receipt_bound(tmp_path, monkeypatch):
    _manifest(tmp_path)
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--apply", "--pytest-log", str(_log(tmp_path, 40, 5))])
    row = _row_of(tmp_path / "RELEASE_MANIFEST.md")
    assert "40 passed, 5 skipped" in row
    assert "receipt-bound log" in row and "operator-supplied" not in row


def test_log_plus_partial_override_is_labelled_as_mixed(tmp_path, monkeypatch):
    """Half a receipt is not a receipt, and must not read as one."""
    _manifest(tmp_path)
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--apply",
              "--pytest-log", str(_log(tmp_path, 40, 5)), "--tests-passed", "41"])
    row = _row_of(tmp_path / "RELEASE_MANIFEST.md")
    assert "41 passed, 5 skipped" in row
    assert "receipt-bound log, partly operator-supplied" in row


def test_log_fully_overridden_is_not_called_receipt_bound(tmp_path, monkeypatch):
    """Both counts given explicitly: the log is never read, so it binds nothing."""
    _manifest(tmp_path)
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--apply", "--pytest-log", str(_log(tmp_path, 40, 5)),
              "--tests-passed", "41", "--tests-skipped", "6"])
    row = _row_of(tmp_path / "RELEASE_MANIFEST.md")
    assert "41 passed, 6 skipped" in row
    assert "operator-supplied counts, no log bound" in row


# --- row placement and preservation -----------------------------------------------------------

def test_missing_row_is_inserted_under_the_validation_anchor(tmp_path, monkeypatch):
    """Older manifests have no evidence row at all; the tool must add one, not fail."""
    m = _manifest(tmp_path)
    assert ROW not in m.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--apply", "--tests-passed", "7", "--tests-skipped", "1"])
    text = (tmp_path / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    assert text.count(ROW) == 1, "exactly one canonical evidence row"
    assert text.index("## Validation status") < text.index(ROW)


def test_existing_row_is_replaced_not_duplicated(tmp_path, monkeypatch):
    _manifest(tmp_path, row="| Full pytest suite | PASS (1 passed, 0 skipped; receipt-bound log) |")
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--apply", "--tests-passed", "99", "--tests-skipped", "8"])
    text = (tmp_path / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    assert text.count(ROW) == 1
    assert "99 passed, 8 skipped" in text and "1 passed, 0 skipped" not in text


def test_check_without_counts_leaves_the_row_untouched(tmp_path, monkeypatch):
    """A source-tree --check runs before the final suite. It must not fabricate or drop the row."""
    original = "| Full pytest suite | PASS (5436 passed, 678 skipped; receipt-bound log) |"
    _manifest(tmp_path, row=original)
    monkeypatch.chdir(tmp_path)
    grm.main(["--root", str(tmp_path), "--check"])
    assert _row_of(tmp_path / "RELEASE_MANIFEST.md") == original


def test_apply_without_any_count_is_refused(tmp_path, monkeypatch):
    """Fail closed: a manifest may not be rewritten with an unmeasured evidence row."""
    _manifest(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert grm.main(["--root", str(tmp_path), "--apply"]) == 2
