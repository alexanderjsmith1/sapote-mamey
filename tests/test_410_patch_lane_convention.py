"""CLAUDE_410 patch_lane_convention — a lane's completeness and disposition are mechanically checkable.

The bundle already has `docs/PATCH_PACKET_POLICY.md` + `tools/patch_packet_preflight.py`, which fail
closed on BLOAT. Nothing checked STRUCTURE: that a lane carries its `.patch`, its `PATCH_CARD.md`, and
its test — and that a folder filed under a cut stream is actually a lane, not a mis-filed audit
report. This lane adds `docs/PATCH_WORKSPACE_LAYOUT.md` + `tools/check_patch_lane.py` for exactly that.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_patch_lane.py"
SPEC = ROOT / "docs" / "PATCH_WORKSPACE_LAYOUT.md"


def _load():
    spec = importlib.util.spec_from_file_location("check_patch_lane", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_lane(directory: Path, *, patch=True, card=True, test=True) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    if patch:
        # A minimal but real-looking diff that adds a test under tests/, so the soft
        # "test travels inside the diff" check is satisfied for the complete case.
        (directory / "CLAUDE_v9.7.410_demo.patch").write_text(
            "--- /dev/null\n+++ b/tests/test_410_demo.py\n@@ -0,0 +1 @@\n+def test_x():\n",
            encoding="utf-8",
        )
    if card:
        (directory / "PATCH_CARD.md").write_text("# demo\nPremise / fix / fail-before-pass-after.\n",
                                                 encoding="utf-8")
    if test:
        (directory / "test_410_demo.py").write_text("def test_x():\n    assert True\n",
                                                     encoding="utf-8")
    return directory


def test_spec_and_tool_ship() -> None:
    assert SPEC.is_file(), "docs/PATCH_WORKSPACE_LAYOUT.md missing"
    assert TOOL.is_file(), "tools/check_patch_lane.py missing"


def test_spec_references_the_existing_policy_not_a_rival() -> None:
    """The codebase's #1 disease is competing conventions. This one must build on the packet policy."""
    text = SPEC.read_text(encoding="utf-8")
    assert "PATCH_PACKET_POLICY.md" in text
    assert "patch_packet_preflight.py" in text
    assert "CUT_PROTOCOL.md" in text


def test_complete_lane_passes(tmp_path: Path) -> None:
    mod = _load()
    lane = _make_lane(tmp_path / "CLAUDE_v9.7.410_demo")
    assert mod.check_lane(lane) == []


@pytest.mark.parametrize("header", [
    "+++ b/../../../../etc/passwd",          # climbs out of the tree
    "+++ /Users/someone/x.py",               # absolute target
    "--- a/mamey/../../outside.py",          # `..` buried mid-path
    "+++ b\\..\\..\\outside.py",             # Windows separators, same escape
])
def test_lane_diff_may_not_target_paths_outside_the_tree(tmp_path: Path, header: str) -> None:
    """v9.7.410 hostile audit: a lane whose diff points at an absolute path or climbs out with
    `..` used to pass the gate with only the soft 'no tests/' note. That is a HARD problem."""
    mod = _load()
    lane = _make_lane(tmp_path / "CLAUDE_v9.7.410_escape")
    (lane / "CLAUDE_v9.7.410_demo.patch").write_text(
        f"{header}\n@@ -0,0 +1 @@\n+pwned\n--- /dev/null\n+++ b/tests/test_410_demo.py\n"
        "@@ -0,0 +1 @@\n+def test_x():\n", encoding="utf-8")
    problems = mod.check_lane(lane)
    assert any("outside the tree" in p for p in problems), problems


def test_dev_null_header_is_not_flagged(tmp_path: Path) -> None:
    mod = _load()
    assert mod._escaping_paths("--- /dev/null\n+++ b/tests/test_x.py\n") == []


@pytest.mark.parametrize("missing", ["patch", "card", "test"])
def test_incomplete_lane_is_flagged(tmp_path: Path, missing: str) -> None:
    mod = _load()
    lane = _make_lane(tmp_path / f"CLAUDE_v9.7.410_missing_{missing}",
                      patch=(missing != "patch"), card=(missing != "card"),
                      test=(missing != "test"))
    problems = mod.check_lane(lane)
    assert problems, f"a lane missing its {missing} must be flagged"
    assert any(missing in p or {"patch": ".patch", "card": "PATCH_CARD",
                                 "test": "test"}[missing] in p for p in problems)


def test_stream_flags_a_misfiled_nonlane(tmp_path: Path) -> None:
    """The figure_factory_effort case: an audit folder (no .patch, no card) filed under a cut stream."""
    mod = _load()
    stream = tmp_path / "stream"
    _make_lane(stream / "CLAUDE_v9.7.410_good")
    reports = stream / "some_effort"
    reports.mkdir(parents=True)
    (reports / "AUDIT.md").write_text("findings, not a patch\n", encoding="utf-8")

    problems = mod.check_stream(stream)
    assert any("some_effort" in p and "not a lane" in p for p in problems)


def test_stream_skips_underscore_parked_dirs(tmp_path: Path) -> None:
    """`_NOT_LANDED_IN_409/` and the like are explicitly parked and must not be judged as live lanes."""
    mod = _load()
    stream = tmp_path / "stream"
    _make_lane(stream / "CLAUDE_v9.7.410_good")
    parked = stream / "_NOT_LANDED"
    parked.mkdir(parents=True)
    (parked / "old.patch").write_text("--- /dev/null\n+++ b/x\n", encoding="utf-8")  # incomplete, but parked
    assert mod.check_stream(stream) == []


def test_the_real_410_stream_is_conformant() -> None:
    """Dogfood: the live Claude .410 stream in this workspace must pass its own convention.

    Skipped when run from an extracted bundle that has no sibling development/ tree.
    """
    # The stream lives under for-cut/ per the convention (development/ reorganized 2026-09-06);
    # the pre-reorg flat path is kept as a fallback for a tree that has not been reorganized yet.
    rels = [
        "for-cut/Patches for Sapote Mamey Claude (v9.7.410)",
        "Patches for Sapote Mamey Claude (v9.7.410)",
    ]
    dev = Path("/Users/researcher/Alex_Claude_New_Laptop_2026/projects/sapote-mamey/development")
    candidates = [ROOT.parent.parent / "development" / r for r in rels] + [dev / r for r in rels]
    stream = next((c for c in candidates if c.is_dir()), None)
    if stream is None:
        pytest.skip("live .410 stream not present next to this bundle")
    mod = _load()
    assert mod.check_stream(stream) == [], "the live stream violates its own convention"


def test_bad_path_returns_exit_2() -> None:
    mod = _load()
    assert mod.main(["--lane", "/nonexistent/xyz"]) == 2


import pytest as _pytest


@_pytest.mark.parametrize("name,flagged", [
    ("deep-audit-408", True),
    ("wiki-improve-408", True),
    ("CLAUDE_410_modeb_heading_regex", True),                 # NO lane exemption — bare 410 flagged
    ("CLAUDE_v9.7.410_modeb_heading_regex", False),           # the correct lane name passes
    ("CLAUDE_v9.7.410_blastp_bgc_recovery_409", True),        # a trailing bare 409 is flagged too
    ("CLAUDE_v9.7.410_blastp_bgc_recovery_v9.7.409", False),  # both references full form -> passes
    ("archive/v9.7.408", False),
    ("Patches for Sapote Mamey Claude (v9.7.410)", False),
    ("figure_factory_effort", False),
    ("round4_sweep", False),
])
def test_full_version_naming_is_enforced(name, flagged):
    """Every bare cut number is ambiguous — including inside a lane slug, which circulates
    standalone. There is no exemption. Only the full `v9.7.N` form passes."""
    from pathlib import Path as _P
    mod = _load()
    problem = mod.version_naming_problem(_P(name).name)
    assert bool(problem) is flagged, f"{name}: {problem!r}"


def test_spec_forbids_the_bare_version_form():
    text = SPEC.read_text(encoding="utf-8")
    assert "never a bare number" in text
    assert "deep-audit-408" in text  # the spec names the real offender as the worked example
    assert "NO exemption" in text  # the corrected rule (no lane-slug exemption)


def test_report_stamp_is_required(tmp_path):
    """A report must declare Base + Disposition in its first 3 lines, in the full v9.7.N form."""
    mod = _load()
    good = tmp_path / "good.md"
    good.write_text("# Audit\n\n> **Base:** v9.7.408 · **Audited:** 2026-09-05 · **Disposition:** report\n\nbody\n",
                    encoding="utf-8")
    assert mod.report_stamp_problem(good) is None

    no_stamp = tmp_path / "no_stamp.md"
    no_stamp.write_text("# Audit\n\nScope: things.\nHarness: .../v9_7_408-CODE/...\n", encoding="utf-8")
    assert mod.report_stamp_problem(no_stamp) is not None  # version buried in a path is not a stamp

    bare = tmp_path / "bare.md"
    bare.write_text("# Audit\n> **Base:** 408 · **Disposition:** report\n", encoding="utf-8")
    assert mod.report_stamp_problem(bare) is not None  # bare 408 is ambiguous

    unstated = tmp_path / "unstated.md"
    unstated.write_text("# Audit\n> **Base:** (unstated in source) · **Disposition:** report\n",
                        encoding="utf-8")
    assert mod.report_stamp_problem(unstated) is None  # honest unknown is allowed


def test_check_reports_mode(tmp_path):
    mod = _load()
    (tmp_path / "a.md").write_text("# A\n> **Base:** v9.7.409 · **Disposition:** report\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B\nno stamp\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("index, exempt\n", encoding="utf-8")
    problems = mod.check_reports(tmp_path)
    assert any("b.md" in p for p in problems)
    assert not any("a.md" in p or "README" in p for p in problems)


def test_spec_has_the_report_front_matter_rule():
    text = SPEC.read_text(encoding="utf-8")
    assert "front-matter rule" in text
    assert "first three lines" in text


def test_ambiguity_case_study_ships_and_is_dated():
    """The 'why' companion to the rule — a dated, real anti-pattern record — must ship and the spec
    must point at it."""
    case = ROOT / "docs" / "ANTIPATTERN_WORKSPACE_AMBIGUITY.md"
    assert case.is_file(), "docs/ANTIPATTERN_WORKSPACE_AMBIGUITY.md missing"
    text = case.read_text(encoding="utf-8")
    assert "September 2026" in text
    assert "figure_factory_effort" in text  # the concrete worked symptom
    assert "ANTIPATTERN_WORKSPACE_AMBIGUITY.md" in SPEC.read_text(encoding="utf-8")
