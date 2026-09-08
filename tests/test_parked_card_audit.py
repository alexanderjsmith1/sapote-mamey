"""Self-test for parked_card_audit.py — synthetic sealed tree + pool, all three verdicts pinned.

Placement: run beside the tool. `python3 -m pytest test_parked_card_audit.py`.
Deterministic: builds a fake sealed tree and a fake pool on tmp_path; no real bundle needed.
"""
import os
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import parked_card_audit as pca  # noqa: E402


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _make_patch(tmp, base_text, new_text, relpath):
    """Produce a unified diff turning base_text into new_text for `relpath`, via diff(1)."""
    a = tmp / "a" / relpath
    b = tmp / "b" / relpath
    _write(a, base_text)
    _write(b, new_text)
    r = subprocess.run(["diff", "-urN", f"a/{relpath}", f"b/{relpath}"],
                       cwd=tmp, capture_output=True, text=True)
    return r.stdout  # non-empty; diff returns 1 when files differ


@pytest.fixture
def sealed(tmp_path):
    tree = tmp_path / "sealed"
    _write(tree / "tools" / "foo.py", "line1\nline2\nline3\n")
    return tree


def _pool_with_card(tmp_path, name, patch_text):
    pool = tmp_path / "Patches for X (v9.7.400)"
    card = pool / name
    card.mkdir(parents=True, exist_ok=True)
    (card / "x.patch").write_text(patch_text, encoding="utf-8")
    return pool


def test_parked_when_patch_applies_forward(tmp_path, sealed):
    # patch changes line2 -> line2 MODIFIED; sealed still has plain line2 -> applies forward -> PARKED
    patch = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 MODIFIED\nline3\n", "tools/foo.py")
    pool = _pool_with_card(tmp_path, "CARD_parked", patch)
    rows, flagged = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "PARKED" and rows[0]["flag"], rows


def test_folded_when_added_lines_present_but_context_drifted(tmp_path, sealed):
    # the change ALREADY landed (sealed has 'line2 FOLDED'), and context drifted so forward fails.
    _write(sealed / "tools" / "foo.py", "HEADER\nline1\nline2 FOLDED\nline3\n")
    patch = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 FOLDED\nline3\n", "tools/foo.py")
    pool = _pool_with_card(tmp_path, "CARD_folded", patch)
    rows, flagged = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "FOLDED" and not rows[0]["flag"], rows


def test_drifted_when_absent_and_not_applicable(tmp_path, sealed):
    # sealed drifted so forward fails, AND the added line is nowhere present -> DRIFTED (the danger).
    _write(sealed / "tools" / "foo.py", "COMPLETELY\nDIFFERENT\nFILE\nNOW\n")
    patch = _make_patch(tmp_path, "line1\nline2\nline3\n",
                        "line1\nline2 UNIQUE_ADDED_TOKEN_ZZZ\nline3\n", "tools/foo.py")
    pool = _pool_with_card(tmp_path, "CARD_drifted", patch)
    rows, flagged = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "DRIFTED" and rows[0]["flag"], rows


def test_parked_within_ttl_not_flagged(tmp_path, sealed):
    patch = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 MODIFIED\nline3\n", "tools/foo.py")
    pool = _pool_with_card(tmp_path, "CARD_recent", patch)
    # current == pool version -> age 0 < ttl -> PARKED but NOT flagged (test-gap guard off to
    # isolate the TTL logic; the code-change-without-test guard has its own dedicated tests).
    rows, flagged = pca.audit([str(pool)], str(sealed), current_version=400, ttl=2, require_tests=False)
    assert rows[0]["status"] == "PARKED" and not rows[0]["flag"], rows


def test_new_file_add_folded_iff_file_exists(tmp_path, sealed):
    # a /dev/null add whose target now EXISTS in sealed -> FOLDED
    (sealed / "tools" / "newtool.py").write_text("print('hi')\n", encoding="utf-8")
    patch = ("--- /dev/null\t1969-12-31\n+++ b/tools/newtool.py\t2026-09-03\n"
             "@@ -0,0 +1,1 @@\n+print('hi')\n")
    pool = _pool_with_card(tmp_path, "CARD_newfile_folded", patch)
    rows, _ = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "FOLDED", rows


def test_new_file_add_parked_iff_file_absent(tmp_path, sealed):
    # a /dev/null add whose target does NOT exist -> forward applies -> PARKED
    patch = ("--- /dev/null\t1969-12-31\n+++ b/tools/absent.py\t2026-09-03\n"
             "@@ -0,0 +1,1 @@\n+print('nope')\n")
    pool = _pool_with_card(tmp_path, "CARD_newfile_parked", patch)
    rows, _ = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "PARKED", rows


def test_out_of_scope_when_modify_target_absent(tmp_path, sealed):
    # a card patching a file that does NOT exist in this tree (e.g. workspace Tools/ vs engine
    # tools/) is OUT_OF_SCOPE, never DRIFTED — it simply belongs to a different tree.
    patch = _make_patch(tmp_path, "a\nb\nc\n", "a\nb CHANGED\nc\n", "Tools/elsewhere.py")
    pool = _pool_with_card(tmp_path, "CARD_out_of_scope", patch)
    rows, flagged = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "OUT_OF_SCOPE" and not rows[0]["flag"], rows


def test_new_file_add_epoch_timestamp_style(tmp_path, sealed):
    # BSD/macOS `diff -urN` marks a new file with an epoch timestamp on the '---' line, keeping the
    # a/<path> name (not /dev/null). Must be recognized as new -> PARKED when the file is absent.
    patch = ("--- a/tools/macnew.py\t1969-12-31 16:00:00\n"
             "+++ b/tools/macnew.py\t2026-09-03 10:00:00\n"
             "@@ -0,0 +1,1 @@\n+print('mac new file')\n")
    pool = _pool_with_card(tmp_path, "CARD_mac_newfile", patch)
    rows, _ = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["status"] == "PARKED", rows


def test_test_gap_flagged_for_code_change_without_test(tmp_path, sealed):
    # a PARKED card that changes tools/ but ships no tests/ target -> test_gap flagged.
    patch = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 X\nline3\n", "tools/foo.py")
    pool = _pool_with_card(tmp_path, "CARD_no_test", patch)
    rows, flagged = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert rows[0]["test_gap"] and rows[0]["flag"], rows


def test_no_test_gap_when_card_has_a_tests_target(tmp_path, sealed):
    # same code change but the card ALSO adds a tests/ file -> no test_gap.
    code = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 X\nline3\n", "tools/foo.py")
    tst = ("--- /dev/null\t1969-12-31\n+++ b/tests/test_foo.py\t2026-09-03\n"
           "@@ -0,0 +1,1 @@\n+def test_x(): assert True\n")
    pool = tmp_path / "Patches for X (v9.7.400)"
    card = pool / "CARD_with_test"
    card.mkdir(parents=True, exist_ok=True)
    (card / "a.patch").write_text(code, encoding="utf-8")
    (card / "b.patch").write_text(tst, encoding="utf-8")
    rows, _ = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert not rows[0]["test_gap"], rows


def test_test_gap_suppressed_by_flag(tmp_path, sealed):
    patch = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 X\nline3\n", "tools/foo.py")
    pool = _pool_with_card(tmp_path, "CARD_no_test2", patch)
    rows, _ = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2, require_tests=False)
    assert not rows[0]["test_gap"], rows


def test_no_test_gap_when_loose_test_file_beside_patch(tmp_path, sealed):
    # code change in the .diff, but the test ships as a loose test_*.py in the card dir (not a
    # tests/ hunk) -> still counts, no test_gap.
    code = _make_patch(tmp_path, "line1\nline2\nline3\n", "line1\nline2 X\nline3\n", "tools/foo.py")
    pool = tmp_path / "Patches for X (v9.7.400)"
    card = pool / "CARD_loose_test"
    card.mkdir(parents=True, exist_ok=True)
    (card / "a.patch").write_text(code, encoding="utf-8")
    (card / "test_foo_v97407.py").write_text("def test_x(): assert True\n", encoding="utf-8")
    rows, _ = pca.audit([str(pool)], str(sealed), current_version=406, ttl=2)
    assert not rows[0]["test_gap"], rows
