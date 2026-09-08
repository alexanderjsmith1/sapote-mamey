#!/usr/bin/env python3
"""VERIFY-BEFORE-ASSERT / REASONING-ORDER CONTRACT — UserPromptSubmit hook.

the Developer or User's standing instruction (2026-08-18): "First think, then think more, then consider whether
you might be wrong, review alternative scenarios in which you are wrong, reconcile, then present
your best guess along with alternatives if they are strong possibilities." And: "start thinking
more before telling me incorrect information."

Why this exists: a recurring, expensive failure pattern across sessions is confidently asserting
a fact, count, or existence-negative that a single disk check would have refuted — e.g. telling
the Developer or User to re-run 36 antiSMASH jobs whose outputs already existed on disk, quoting "301 type strains"
that were mostly duplicate files, or calling a run "void" on an over-strong premise. Each wastes
the Developer or User's time and erodes trust. This contract makes the reasoning ORDER explicit and mandatory
before any factual claim, count, existence-negative, or recommendation is presented.

Design notes:
  * Fires on every prompt, matching the house pattern of the existing UserPromptSubmit context
    hooks (STANDING RESPONSE CONTRACT, RECOMMENDATION CONTRACT, SAPOTE-MAMEY VERSION GUARD).
  * Emits additionalContext only. Never blocks, never edits, never touches a file.
  * Fails OPEN: any error exits 0 with no output, so a bug here can never wedge a prompt.
"""
import sys

CONTRACT = (
    "VERIFY-BEFORE-ASSERT CONTRACT (reason in order before stating any fact, count, "
    "existence-negative, or recommendation). Follow this order every time: "
    "(1) THINK — state the claim you are about to make. "
    "(2) THINK MORE — is it OBSERVED (you checked the actual file/data THIS turn) or only "
    "inferred, remembered, or echoed from a peer/summary? Name the specific evidence (path, "
    "number, receipt). "
    "(3) CONSIDER YOU ARE WRONG — enumerate concrete ways it could be false: stale or "
    "older-engine data; inflated or duplicated counts (copies, cross-folder repeats); an "
    "existence-negative you never checked against disk ('no such file' without a find); wrong "
    "scope or denominator; a number that is your own earlier echo; mixed or mislabeled provenance. "
    "(4) REVIEW ALTERNATIVES — actually check the strongest wrong-scenarios against disk/data "
    "before presenting; a claim is not ready until its most likely failure mode has been tested. "
    "(5) RECONCILE — reduce the claim to exactly what the evidence supports; attach explicit "
    "uncertainty (a range, 'at least N', 'distinct-by-content', 'unverified'). "
    "(6) PRESENT — best guess with its confidence, plus any strong alternative readings; mark "
    "observed-vs-told; never hand over a bare confident number you did not verify this turn. "
    "This does NOT mean run heavy compute for every claim — it means do the CHEAP check (a find, a "
    "count, opening the file) that would catch the error, and when you cannot verify, say so plainly "
    "instead of asserting. Prefer 'let me check' over a wrong answer. Claim-safety still holds: "
    "class-level hypotheses, judgment deferred."
)


def main() -> int:
    try:
        sys.stdin.read()  # drain the hook payload; content is not needed
    except Exception:
        pass
    try:
        import json
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": CONTRACT,
            }
        }))
    except Exception:
        return 0  # fail open — never wedge a prompt
    return 0


if __name__ == "__main__":
    sys.exit(main())
