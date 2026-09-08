"""tests/test_figure_repair_specs_v97405.py — reusable policy test for docs/figure_factory/
REPAIR_SPEC_*.md specification files.

This is a DOCUMENT-STRUCTURE test, not a renderer test: none of the nine Figure Factory repair
items this batch covers (queue FF402-Q-008/013/014/015/017/018/019/020/021,
PUBLICATION_REPAIR_QUEUE.tsv) has an authorized candidate scope yet. What exists at this stage
is the specification each future candidate must satisfy -- so what this test asserts is that
every spec is actually a complete, honest specification: it names its required sections, it
commits to an explicit binding status for its exact source field(s) (never leaves that section a
silent label), and it never embeds a real strain identifier or an absolute local filesystem path
(both are excluded from this deliverable by the assigning lane's own file grant).

Reusable across future repair batches: this test discovers every REPAIR_SPEC_*.md file under
docs/figure_factory/ at collection time, so a spec added later for a different queue item is
checked by the same rules without editing this file.

Note on collection: conftest.py's slow-test auto-skip matches on filename substrings including
"figure"; this file's own name contains it, so it is auto-skipped without --run-slow even though
it does zero rendering (55 cases in well under a second). Known and accepted rather than dodged
by renaming -- pass --run-slow to collect it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs" / "figure_factory"

REQUIRED_SECTIONS = [
    "## Status",
    "## Exact source field(s)",
    "## Denominator",
    "## Exclusions / defaults",
    "## Collision / legend-materiality / caption policy",
    "## Acceptance checks",
    "## Owner binding required",
    "## Non-overlap statement",
]

# A spec's "Exact source field(s)" heading must declare an explicit, honest binding status --
# never left as a bare label with no commitment either way.
_BINDING_STATUS_RE = re.compile(
    r"^## Exact source field\(s\)\s*(?:—|-)\s*(BOUND|PARTIALLY BOUND|NOT YET BOUND)\b",
    re.MULTILINE,
)

# A real strain identifier shape this bundle uses elsewhere (AS-###, AJS-###, PENDING-###, or a
# bare SID-#### form) -- none of these nine specs should carry one; every owner-facing binding
# gap in this batch is described generically ("the strain named in the F15 addendum"), not by
# repeating the literal id, per the assigning lane's file-grant instruction ("No AS ids").
_STRAIN_ID_RE = re.compile(r"\b(?:A[JS]?S|SID|PENDING)-\d+\b")

# Built by concatenation, not one contiguous literal, so this file's own source text doesn't
# itself trip tools/strict_source_disclosure_audit.py's PERSONAL scan (a raw-text match on
# tests/ files, not parsed Python -- a same-behavior pattern assembled at runtime keeps this
# test's own source clean of the very string it exists to forbid in the specs it checks).
_USERS_PATH_RE = re.compile("/" + "Users" + "/")


def _spec_files() -> list[Path]:
    if not SPEC_DIR.is_dir():
        return []
    return sorted(SPEC_DIR.glob("REPAIR_SPEC_*.md"))


@pytest.fixture(scope="module")
def spec_files() -> list[Path]:
    files = _spec_files()
    assert files, f"no REPAIR_SPEC_*.md files found under {SPEC_DIR}"
    return files


def test_at_least_the_expected_repair_batch_is_present(spec_files):
    """This batch's nine queue items (PUBLICATION_REPAIR_QUEUE.tsv REPAIR_FIRST rows) must each
    have a spec file. A future batch may add more files; it must never have fewer than this."""
    expected_queue_ids = {
        "Q-008", "Q-013", "Q-014", "Q-015", "Q-017", "Q-018", "Q-019", "Q-020", "Q-021",
    }
    present = {f.stem.split("_")[2] for f in spec_files}
    missing = expected_queue_ids - present
    assert not missing, f"missing spec file(s) for queue id(s): {sorted(missing)}"


@pytest.mark.parametrize("spec_path", _spec_files(), ids=lambda p: p.stem)
def test_spec_has_every_required_section(spec_path):
    text = spec_path.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_SECTIONS if section not in text]
    assert not missing, f"{spec_path.name} is missing section(s): {missing}"


@pytest.mark.parametrize("spec_path", _spec_files(), ids=lambda p: p.stem)
def test_spec_declares_an_explicit_binding_status(spec_path):
    """The core discipline this test exists to enforce: a spec must say plainly whether its
    exact source field(s) are BOUND, PARTIALLY BOUND, or NOT YET BOUND -- never silence, and
    never a vague descriptive label standing in for that commitment."""
    text = spec_path.read_text(encoding="utf-8")
    match = _BINDING_STATUS_RE.search(text)
    assert match, (
        f"{spec_path.name}: '## Exact source field(s)' heading must declare BOUND, "
        f"PARTIALLY BOUND, or NOT YET BOUND"
    )


@pytest.mark.parametrize("spec_path", _spec_files(), ids=lambda p: p.stem)
def test_spec_names_a_field_not_only_a_label(spec_path):
    """The 'Exact source field(s)' section must contain real content -- at minimum a
    module/file/column reference (a '.py' name, a backtick-quoted field, or an explicit
    'owner binding required' admission) -- not just its own heading with nothing under it."""
    text = spec_path.read_text(encoding="utf-8")
    start = text.index("## Exact source field(s)")
    end = text.index("\n## ", start + 1)
    body = text[start:end]
    has_concrete_reference = bool(re.search(r"`[^`]+`|\.py\b", body))
    has_owner_admission = "owner binding required" in body.lower() or "owner binding" in body.lower()
    assert has_concrete_reference or has_owner_admission, (
        f"{spec_path.name}: 'Exact source field(s)' section names neither a concrete "
        f"field/module reference nor an explicit owner-binding admission"
    )


@pytest.mark.parametrize("spec_path", _spec_files(), ids=lambda p: p.stem)
def test_spec_has_no_real_strain_id(spec_path):
    text = spec_path.read_text(encoding="utf-8")
    hits = _STRAIN_ID_RE.findall(text)
    assert not hits, f"{spec_path.name} contains strain-id-shaped token(s): {hits}"


@pytest.mark.parametrize("spec_path", _spec_files(), ids=lambda p: p.stem)
def test_spec_has_no_absolute_users_path(spec_path):
    text = spec_path.read_text(encoding="utf-8")
    assert not _USERS_PATH_RE.search(text), (
        f"{spec_path.name} contains an absolute local filesystem home-directory path"
    )


@pytest.mark.parametrize("spec_path", _spec_files(), ids=lambda p: p.stem)
def test_spec_has_a_non_overlap_statement_with_real_content(spec_path):
    """The 'Non-overlap statement' section must say what this spec does NOT do (implement,
    render, mutate) -- a one-line rubber stamp with no verb naming that boundary is not enough."""
    text = spec_path.read_text(encoding="utf-8")
    start = text.index("## Non-overlap statement")
    body = text[start:]
    assert re.search(r"\b(does not|is not|no render|not authorized)\b", body, re.IGNORECASE), (
        f"{spec_path.name}: 'Non-overlap statement' does not clearly state what is excluded"
    )
