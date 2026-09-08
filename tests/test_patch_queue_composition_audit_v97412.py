"""v9.7.412 (Goldenrod): the patch-queue composition auditor.

Pins the one behaviour the tool exists for: a whole-file drop that REMOVES lines the sealed
tree has is a WARN, because copying it over the sealed file reverts that content with no
conflict and no signal. Everything else stays quiet, because a guard that shouts about
correct cards is one people learn to skip.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "patch_queue_composition_audit.py"


def _load():
    spec = importlib.util.spec_from_file_location("pqca_ut", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pqca_ut"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def trees(tmp_path):
    base = tmp_path / "sealed"
    (base / "tools").mkdir(parents=True)
    (base / "tools" / "fig.R").write_text("keep_me <- 1\nshared <- 2\n")
    queue = tmp_path / "queue"
    queue.mkdir()
    return base, queue


def _item(queue: Path, name: str) -> Path:
    d = queue / name / "tools"
    d.mkdir(parents=True)
    return d


def test_drop_that_removes_sealed_content_is_warned(trees):
    base, queue = trees
    # drops `keep_me`, keeps `shared`, adds a new line -> a silent revert of keep_me
    _item(queue, "CARD_A").joinpath("fig.R").write_text("shared <- 2\nnew <- 3\n")
    m = _load()
    f = [x for x in m.audit_queue(queue, base) if x["path"].endswith("fig.R")][0]
    assert f["code"] == m.CODE_REVERT and f["severity"] == "WARN", f
    assert f["removed"] == 1
    assert any("keep_me" in s for s in f["sample"]), f["sample"]


def test_identical_copy_is_not_a_warning(trees):
    base, queue = trees
    _item(queue, "CARD_B").joinpath("fig.R").write_text("keep_me <- 1\nshared <- 2\n")
    m = _load()
    f = [x for x in m.audit_queue(queue, base) if x["path"].endswith("fig.R")][0]
    assert f["code"] == m.CODE_SAME and f["severity"] == "INFO", f


def test_pure_addition_is_not_a_warning(trees):
    base, queue = trees
    _item(queue, "CARD_C").joinpath("fig.R").write_text("keep_me <- 1\nshared <- 2\nextra <- 9\n")
    m = _load()
    f = [x for x in m.audit_queue(queue, base) if x["path"].endswith("fig.R")][0]
    assert f["code"] == m.CODE_ADDONLY and f["severity"] == "INFO", f


def test_new_file_is_reported_as_accretion_not_revert(trees):
    base, queue = trees
    _item(queue, "CARD_D").joinpath("brand_new.py").write_text("x = 1\n")
    m = _load()
    f = [x for x in m.audit_queue(queue, base) if x["path"].endswith("brand_new.py")][0]
    assert f["code"] == m.CODE_NEW and f["severity"] == "INFO", f


def test_an_audit_working_tree_is_named_once_not_walked(trees):
    base, queue = trees
    wt = queue / "CARD_WORKTREE"
    (wt / "tools").mkdir(parents=True)
    (wt / "BUILD_STAMP.txt").write_text("version=9.7.411\n")
    for i in range(5):
        (wt / "tools" / f"f{i}.py").write_text("x = 1\n")
    m = _load()
    rows = [x for x in m.audit_queue(queue, base) if x["item"] == "CARD_WORKTREE"]
    assert len(rows) == 1 and rows[0]["code"] == m.CODE_WORKTREE, rows


def test_a_diff_is_ok_and_card_prose_is_ignored(trees):
    base, queue = trees
    d = queue / "CARD_E"
    d.mkdir()
    (d / "001_fix.patch").write_text("--- a/x\n+++ b/x\n")
    (d / "PATCH_CARD.md").write_text("# notes\n")
    m = _load()
    rows = m.audit_queue(queue, base)
    codes = {r["code"] for r in rows if r["item"] == "CARD_E"}
    assert codes == {m.CODE_DIFF}, rows


def test_a_compiled_artefact_is_debris_not_a_phantom_content_removal(trees):
    """Regression: a .pyc decoded with errors="replace" invented "107 sealed lines absent" --
    a WARN on a file that has no meaningful line comparison at all. It is debris, and says so."""
    base, queue = trees
    d = queue / "CARD_F" / "tools" / "__pycache__"
    d.mkdir(parents=True)
    (d / "fig.cpython-313.pyc").write_bytes(b"\xcb\r\r\n\x00\x01\x02\xff\xfe")
    m = _load()
    rows = [x for x in m.audit_queue(queue, base) if x["item"] == "CARD_F"]
    assert len(rows) == 1, rows
    assert rows[0]["code"] == m.CODE_DEBRIS, rows
    assert rows[0]["removed"] == 0, "debris must never report phantom removed lines"


def test_a_binary_payload_is_not_line_compared(trees):
    base, queue = trees
    (base / "tools" / "chart.png").write_bytes(b"\x89PNG\r\n\x1a\nAAAA")
    d = queue / "CARD_G" / "tools"
    d.mkdir(parents=True)
    (d / "chart.png").write_bytes(b"\x89PNG\r\n\x1a\nBBBB")
    m = _load()
    assert [x for x in m.audit_queue(queue, base) if x["item"] == "CARD_G"] == []


def test_two_cards_dropping_one_target_with_different_content_collide(trees):
    """Either apply order silently loses the other card's content: no patch is involved, so a
    file drop just overwrites. Observed live between two BLACK_CHERRY_2 .412 cards."""
    base, queue = trees
    (base / "tests").mkdir()
    (base / "tests" / "test_shared.py").write_text("def test_a():\n    pass\n")
    for card, extra in (("CARD_H", "def test_h():\n    pass\n"), ("CARD_I", "def test_i():\n    pass\n")):
        d = queue / card
        d.mkdir()
        (d / "test_shared.py").write_text("def test_a():\n    pass\n" + extra)
    m = _load()
    coll = [x for x in m.audit_queue(queue, base) if x["code"] == m.CODE_COLLISION]
    assert len(coll) == 1, coll
    assert coll[0]["path"] == "tests/test_shared.py"
    assert "CARD_H" in coll[0]["item"] and "CARD_I" in coll[0]["item"]


def test_identical_drops_of_one_target_are_not_a_collision(trees):
    base, queue = trees
    (base / "tests").mkdir()
    (base / "tests" / "test_shared.py").write_text("x\n")
    for card in ("CARD_J", "CARD_K"):
        d = queue / card
        d.mkdir()
        (d / "test_shared.py").write_text("x\ny\n")   # same content in both
    m = _load()
    assert [x for x in m.audit_queue(queue, base) if x["code"] == m.CODE_COLLISION] == []


def test_a_bare_file_at_the_card_root_resolves_by_basename(trees):
    """Cards commonly drop `CARD/test_x.py` with no `tests/` directory. Without a basename
    fallback those payloads are invisible to the audit entirely."""
    base, queue = trees
    (base / "tests").mkdir()
    (base / "tests" / "test_thing.py").write_text("keep\nshared\n")
    d = queue / "CARD_L"
    d.mkdir()
    (d / "test_thing.py").write_text("shared\n")      # drops `keep`
    m = _load()
    rows = [x for x in m.audit_queue(queue, base) if x["item"] == "CARD_L"]
    assert rows and rows[0]["path"] == "tests/test_thing.py", rows
    assert rows[0]["code"] == m.CODE_REVERT, rows


def test_diffbuild_scaffolding_is_not_mistaken_for_a_file_drop(trees):
    """A card that ships a .patch often keeps the pre/post images it built the diff FROM under
    `diffbuild/`. Those are not payload. Reading them as drops reports the diff's own intended
    removals as silent reverts -- a false positive on a card that did exactly the right thing.
    Observed live against three .412 cards (AMBER x1, RAZZLE x2)."""
    base, queue = trees
    card = queue / "CARD_M"
    for side in ("a", "b"):
        d = card / "diffbuild" / side / "tools"
        d.mkdir(parents=True)
        (d / "fig.R").write_text("shared <- 2\n")     # drops keep_me vs sealed
    (card / "fix.patch").write_text("--- a/x\n+++ b/x\n")
    m = _load()
    codes = {r["code"] for r in m.audit_queue(queue, base) if r["item"] == "CARD_M"}
    assert codes == {m.CODE_DIFF}, f"scaffolding must not be audited as payload: {codes}"


def test_cli_refuses_a_missing_base_and_never_crashes(trees, tmp_path):
    base, queue = trees
    m = _load()
    assert m.main([str(queue), "--base", str(tmp_path / "nope")]) == 2
    assert m.main([str(queue), "--base", str(base)]) == 0
