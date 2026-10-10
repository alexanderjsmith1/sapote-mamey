# Sapote workflow ledger — implemented checks and remaining holds

The workflow driver is `mamey/sapote_workflow.py`; `tools/sapote_workflow.py` is a thin shim,
and `python -m mamey workflow` calls the same implementation. It inspects selected artifacts and
runs a small number of subprocess gates. It does not author reports, transmit handoffs or grant
scientific acceptance. Apply it only within the selected authorized workflow.

## Actual step checks

| Step | Implemented evidence | Limit |
|---|---|---|
| W0 | Manifest file, recorded PASS-family/boolean gate verdict and checksum-list presence | Does not rerun validation or verify current checksum values; use the actual validator separately |
| W1 | Triage-board file and row count; notes scan-state presence | PASS does not require scans to exist or be complete |
| W2 | AB and AF lead-board file presence | No biological or complete row-content validation |
| W3 | At least one `mode_b_templates/*BGC*.md` file | Does not inspect template profile, coverage or content; the ledger’s §1–§48 wording is not a profile receipt |
| W4 | COMPLETE register entries or discovered authored disk cards; `--strict` verifies discovered cards via default `verify-modeb` | Authored heuristic ≥3 recognized sections and ≥200 non-whitespace characters; does not enforce every expected BGC is covered or propagate current50 selection |
| W5 | Matching `*_Guide.md` files, no residual LAY slots | Conditional N/A when none exists; no invocation of `verify-guide` |
| W6 | Matching layperson/ecology/fermentation filenames | Content and source binding are not verified |
| W7 | Selected internal or integrity-bound external compiled report, no counted placeholders | Does not run `compile-report --strict`; placeholder scan is not scientific or publication clearance |
| W8 | Finds a Markdown DELIVERABLE_MANIFEST, then launches suite checker | Source bug: passes package `manifest.json`, not the discovered Markdown suite manifest |
| W9 | Package manifest lacks literal JUDGMENT_PENDING; reports optional receipt filename | Does not require a receipt or validate it; an unreadable manifest becomes an empty object |
| W10 | Always N/A: session close is behavioral | Source bug: W10 is marked mandatory, so it is always in mandatory_incomplete |

These are implemented software checks, not the complete desired deliverable contract. A filename
match or recorded status is weaker than current artifact verification. Obtain current Mode B
profile details from [the profile matrix](MODEB_PROFILE_MATRIX.md) and
[the user walkthrough](MODE_B_USER_WALKTHROUGH.md); bind the exact profile and complete locus
identity when invoking its verifier separately.

## Current source holds

`--strict` currently cannot produce an all-mandatory-PASS result: W10 returns N/A while the
incomplete calculation requires every mandatory step to be PASS. Do not interpret this terminal
failure alone as a scientific defect, and do not bypass it or declare release readiness. Preserve
the ledger’s actual step evidence and report the implementation hold for owner review.

W8’s invoked `tools/check_deliverable_suite.py` reads numbered Markdown contract rows and gold
Section H text. The driver locates that document but supplies the JSON package manifest instead.
Run the suite checker separately on the actually filled suite manifest when that check is within
the authorized task; retain its own receipt. A discovered Markdown filename is not evidence that
its content was checked by W8.

W4 under strict mode verifies disk candidates it discovers, not the complete expected locus roster.
Register COMPLETE and a verifier exit zero have different scopes. Missing expected loci and a
nondefault profile remain explicit holds until independently bound and checked.

## Commands and side effects

```bash
# A status inspection writes a ledger; keep the ledger outside an immutable package.
python tools/sapote_workflow.py --package path/to/package \
  --ledger-out path/to/review/workflow_ledger.md

# JSON is printed to stdout; a Markdown ledger is still written.
python tools/sapote_workflow.py --package path/to/package \
  --deliverables path/to/deliverables --ledger-out path/to/review/workflow_ledger.md --json

# Separate suite check on its actual Markdown input.
python tools/check_deliverable_suite.py --manifest path/to/DELIVERABLE_MANIFEST.md --mode gold
```

Without `--ledger-out`, the driver writes `<strain>_SAPOTE_WORKFLOW_LEDGER.md` inside the package.
It does not emit a separate JSON ledger file automatically. Subprocess checks can add their own
receipts; consult their owners and preserve a working copy when input bytes must remain fixed.
Ledger write errors are reported but do not independently make a non-strict process fail. Non-strict
exit zero reports driver completion, not every step PASS. No command here is authority to author,
seal, release, publish or send messages.

Report the selected operation, exact paths/hashes, implemented checks, unresolved holds and one
useful bounded next action. Historical exactly-eight-path hints in the driver do not override the
user’s conversational preferences or authorization.
