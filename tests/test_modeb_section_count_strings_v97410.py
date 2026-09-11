#!/usr/bin/env python3
"""TEST for CLAUDE_410 — Mode B section-count string drift (§30/§20/§8 -> §48).

Purpose
-------
The single canonical Mode B contract
(`mamey/data/mode_b/modeb_full30_corrective_contract.json`,
schema `modeb_corrective_full48_v1`) defines 48 sections, and the template
emitter (`mamey/modeb_template_emitter.py`) emits §1-§48. Before this lane,
help-text / docstrings / error + status strings across the CODE still described
the *finished / canonical* contract, template, skeleton or card as "§1-§30"
(and, in `mode_b_receipt.py`, an even older "§1-§8"). This test pins the
correction: no CODE string may describe the finished contract as §1-30 / §1-20
/ §1-8 anymore.

Scope guard (what this test deliberately does NOT flag)
-------------------------------------------------------
Some §1-§30 / §1-§20 references are correct and must survive, so this test does
NOT do a blanket grep. It checks the SPECIFIC phrasings the lane changed. The
intentional survivors are:
  * historical / legacy / retired narratives (e.g. "historical §1-§10 scaffold",
    "retired §1-§10+§11-§20 (20-section) contract", the wrong-conclusion story
    in modeb_structure_gate.py);
  * section-ordering LOGIC windows ("§1-§20 must appear in numeric order",
    "§21-§30 keep their historical any-order allowance", the §1-§30 tolerant/WARN
    bands) and section-number logic (§16/§30 anchors, the (8,9,11,19,30) tuple);
  * the deliberate prose-first "Full Mode B" §1-§20 facade/view
    (mamey/validators/modeb_full20.py, build_full20_skeleton, report_mode.py,
    session_resume.py, seal_package.py);
  * the contract JSON *filename* `modeb_full30_corrective_contract.json` and the
    `full30`/`full20` identifiers (structural, not renamed by this lane).

Run against a PATCHED bundle tree:
    python test_modeb_section_count_strings_v97410.py [<bundle_root>]
Default bundle_root is the pristine .408 bundle path; pass the patched tree to
verify. Exit 0 = all assertions pass, 1 = drift still present.
"""
import sys
from pathlib import Path

# The tree this file lives in — tests/<this file> -> bundle root. Previously a hardcoded absolute
# path to the .408 bundle, which meant that running this checker from inside a .409 tree silently
# audited the WRONG tree and reported failures that had nothing to do with the tree under test.
DEFAULT_ROOT = Path(__file__).resolve().parents[1]

# (relative path, forbidden stale substring) — must be ABSENT after the patch.
FORBIDDEN = [
    ("mamey/cli.py", "ERROR-severity §1–§30 contract violations"),
    ("mamey/cli.py", "the §1-§30 authoring scaffold"),
    ("mamey/cli.py", "canonical §1–§30 Mode B template skeleton"),
    ("mamey/cli.py", "Emit a canonical §1–§30 Mode B card template"),
    ("mamey/mode_b_receipt.py", "§1-§8 Mode B cards"),
    ("mamey/mode_b_receipt.py", "full §1-§8 markdown"),
    ("mamey/mode_b_receipt.py", "§1–§30 contract"),
    ("mamey/mode_b_receipt.py", "§1–§30 structure gate"),
    ("mamey/mode_b_receipt.py", "§1–§30 Mode B card templates"),
    ("mamey/mode_b_receipt.py", "§1–§30 contract satisfied"),
    ("mamey/modeb_cards.py", "the full §1-§30 authoring scaffold"),
    ("mamey/modeb_subsections.py", "for the §1–§30 Mode B card"),
    ("mamey/sapote_workflow.py", "§1–§30 skeletons emitted"),
    ("mamey/sapote_workflow.py", "Mode B §1–§30 templates emitted"),
    ("mamey/mode_b_quality_gate.py", "§1–§30 substance"),
    ("mamey/modeb_interp_gate.py", "§1-§30 structure"),
    ("mamey/authored_verify.py", "§1–§30 structure."),
    ("mamey/authored_verify.py", "current §1–§30 wording"),
    ("mamey/modeb_round.py", "all §1–§30 headings present"),
    ("mamey/modeb_round.py", "valid §1–§30 SCAFFOLD"),
    ("mamey/modeb_structure_gate.py", "rather than the current §1–§30 contract"),
    ("mamey/modeb_structure_gate.py", "section headings against §1–§30 with conditional"),
    ("mamey/modeb_structure_gate.py", "the §1–§30 canonical"),
    ("mamey/modeb_structure_gate.py", "canonical §1–§30 contract"),
    ("mamey/modeb_structure_gate.py", "No §1–§30 section headings detected"),
    ("mamey/modeb_structure_gate.py", "superseded by the §1–§30 contract"),
    ("mamey/modeb_structure_gate.py", "in the §1–§30 contract; treated as informational"),
    ("mamey/modeb_structure_gate.py", "PASS (§1–§30 contract satisfied)"),
    ("mamey/mode_b/evidence_ledgers.py", "the §1–§30 contract enforced by"),
    ("mamey/validators/modeb_full20.py", "is the §1–§30 enforcer"),
    ("mamey/validators/modeb_full20.py", "canonical §1–§30 contract"),
]

# (relative path, expected §48 substring) — must be PRESENT after the patch.
EXPECTED = [
    ("mamey/cli.py", "Emit a canonical §1–§48 Mode B card template"),
    ("mamey/mode_b_receipt.py", "§1-§48 Mode B cards"),
    ("mamey/mode_b_receipt.py", "PASS (§1–§48 contract satisfied)"),
    ("mamey/modeb_structure_gate.py", "the §1–§48 canonical"),
    ("mamey/modeb_structure_gate.py", "PASS (§1–§48 contract satisfied)"),
    ("mamey/modeb_structure_gate.py", "in the §1–§48 contract; treated as informational"),
    ("mamey/validators/modeb_full20.py", "is the §1–§48 enforcer"),
    ("mamey/sapote_workflow.py", "§1–§48 skeletons emitted"),
]

# Intentional survivors — must STILL be present (proves the test isn't over-broad).
SURVIVORS = [
    ("mamey/modeb_structure_gate.py", "modeb_full30_corrective_contract.json"),
    ("mamey/modeb_structure_gate.py", "§1–§20 must appear in numeric order"),
    ("mamey/validators/modeb_full20.py", "§1–§20 facade"),
    ("mamey/mode_b_quality_gate.py", "retired §1–§10+§11–§20 (20-section) contract"),
]


def collect_failures(root: Path) -> list[str]:
    """Every stale/missing/removed string finding for `root`. Empty list = clean."""
    fails: list[str] = []
    for rel, needle in FORBIDDEN:
        text = (root / rel).read_text(encoding="utf-8")
        if needle in text:
            fails.append(f"STALE STILL PRESENT: {rel}: {needle!r}")
    for rel, needle in EXPECTED:
        text = (root / rel).read_text(encoding="utf-8")
        if needle not in text:
            fails.append(f"EXPECTED §48 STRING MISSING: {rel}: {needle!r}")
    for rel, needle in SURVIVORS:
        text = (root / rel).read_text(encoding="utf-8")
        if needle not in text:
            fails.append(f"INTENTIONAL SURVIVOR REMOVED: {rel}: {needle!r}")

    return fails


def test_no_finished_contract_string_is_stale() -> None:
    """pytest entry point.

    This file is named `test_*.py`, so pytest collects it — but it previously contained only a
    `main()` behind an `if __name__ == "__main__"` guard, so collection found ZERO tests and the
    file passed silently while checking nothing. That is strictly worse than not shipping it.
    """
    fails = collect_failures(DEFAULT_ROOT)
    assert not fails, "\n".join([f"{len(fails)} finding(s) against {DEFAULT_ROOT}"] + fails)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROOT
    fails = collect_failures(root)
    if fails:
        print(f"FAIL ({len(fails)}) against {root}")
        for f in fails:
            print("  -", f)
        return 1
    print(f"PASS: no finished-contract string says §1-30/§1-20/§1-8; "
          f"§48 forms present; survivors intact. ({root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
