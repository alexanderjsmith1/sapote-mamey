# Sapote workflow ledger — implemented checks and remaining holds

The workflow ledger lists the eleven deliverable steps (W0 to W10) of a strain and marks each
`PASS`, `PENDING`, `BLOCKED` or `N/A`. It looks at files in the package and runs a few checks. It does
not write reports, send anything or decide that the science is accepted. The code is
`mamey/sapote_workflow.py`.

```bash
python mamey_run.py workflow --package path/to/package --ledger-out path/to/review/workflow_ledger.md
```

You get a Markdown ledger like this, one row per step. The header line counts steps that pass and
mandatory steps still open:

```text
**N/11 steps PASS · M/10 mandatory steps incomplete**

| Step | Stage | Req | Status | Receipt |
| W0 | Sealed Mamey package (validate) | M | PASS | ... |
```

Open the `Receipt` of the first non-passing step. It says what is missing. The ledger ends with the
next mandatory step and the command that completes it.

## What each step checks

| Step | Stage | What it checks | What it does not check |
|---|---|---|---|
| W0 | Sealed package | Manifest file, recorded PASS-family/boolean gate verdict and checksum-list presence | Does not rerun validation or verify current checksum values; use the actual validator separately |
| W1 | First-pass scans and triage board | Triage-board file and row count; notes scan-state presence | PASS does not require scans to exist or be complete |
| W2 | Lead boards | AB and AF lead-board file presence | No biological or complete row-content validation |
| W3 | Mode B templates emitted | At least one `mode_b_templates/*BGC*.md` file | Does not inspect template profile, coverage or content; the ledger’s §1–§48 wording is not a profile receipt |
| W4 | Mode B cards authored and verified | COMPLETE register entries or discovered authored disk cards; `--strict` verifies discovered cards via default `verify-modeb` | Authored heuristic ≥3 recognized sections and ≥200 non-whitespace characters; does not enforce every expected BGC is covered or propagate current50 selection |
| W5 | BGC guides (only if you made one) | Matching `*_Guide.md` files, no residual LAY slots | Conditional N/A when none exists; no invocation of `verify-guide` |
| W6 | Layperson, ecology and fermentation narratives | Matching layperson/ecology/fermentation filenames | Content and source binding are not verified |
| W7 | Compiled report | Selected internal or integrity-bound external compiled report, no counted placeholders | Does not run `compile-report --strict`; placeholder scan is not scientific or publication clearance |
| W8 | Deliverable suite contract | Finds a Markdown DELIVERABLE_MANIFEST and runs the suite checker on it in gold mode | Uses the first match found in the deliverables folder, then the package, then the working folder; does not pass `--artifact-root`, so artifact paths are not checked for existence |
| W9 | Judgment receipt | Package manifest is readable and lacks literal JUDGMENT_PENDING; reports optional receipt filename | A missing or unreadable manifest reads PENDING. Does not require a receipt or validate it |
| W10 | Session close | N/A once W9 has passed: closing the session is a manual step. BLOCKED while W9 has not passed | N/A counts as complete. A BLOCKED W10 counts as incomplete |

A filename match or a recorded status is weaker than checking the file itself. Obtain current Mode B
profile details from [the profile matrix](MODEB_PROFILE_MATRIX.md) and
[the user walkthrough](MODE_B_USER_WALKTHROUGH.md); bind the exact profile and complete locus
identity when invoking its verifier separately.

## Reading `--strict`

Each step has a status. `PASS` and `N/A` count as complete. `PENDING` means the step has not
passed its check. `BLOCKED` means the step before it has not passed, so the step was not checked.
`--strict` exits 1 when any mandatory step is `PENDING` or `BLOCKED`. It exits 2, with
`ERROR: package dir not found`, when the package folder does not exist.

A strict failure lists every incomplete mandatory step, including steps that are only `BLOCKED`.
A package that stops at W2 lists W3 to W10, and W10 shows up because W9 is blocked. Fix the first
non-passing step in the ledger and run it again; the later steps usually clear after it. W9 reads
only the package `manifest.json` and stays `PENDING` while it contains `JUDGMENT_PENDING`.
`tools/sapote_judgment_receipt.py` writes a separate receipt file and does not edit the manifest, so a
receipt alone does not clear W9. The two records can disagree; keep both, and treat W9 as open until
the manifest itself is reconciled by the owner's sealed route. Do not call a strain release-ready
from the exit code alone.

W8’s invoked `tools/check_deliverable_suite.py` reads numbered Markdown contract rows and gold
Section H text from the suite manifest the driver found. It does not check that each COMPLETE
artifact path exists. When that matters, run the checker separately with `--artifact-root` set to
the folder the paths are relative to, and retain its own receipt.

W4 under strict mode verifies disk candidates it discovers, not the complete expected locus roster.
Register COMPLETE and a verifier exit zero have different scopes. Missing expected loci and a
nondefault profile remain explicit holds until independently bound and checked.

## Commands and side effects

```bash
# Status check. It writes a ledger, so keep the ledger outside an immutable package.
# --ledger-out must be a new file outside the package and deliverables folders; an existing file,
# or any path inside those folders, is refused with OUTPUT_REFUSED and exit 2 before any check runs.
python mamey_run.py workflow --package path/to/package \
  --ledger-out path/to/review/workflow_ledger.md

# Also print the ledger as JSON on stdout. The Markdown ledger is still written.
python mamey_run.py workflow --package path/to/package \
  --deliverables path/to/deliverables --ledger-out path/to/review/workflow_ledger.md --json

# Release gate: exit 1 if a mandatory step is open.
python mamey_run.py workflow --package path/to/package --strict

# Run the W8 suite check yourself, on its Markdown input.
python tools/check_deliverable_suite.py --manifest path/to/DELIVERABLE_MANIFEST.md --mode gold
```

`tools/sapote_workflow.py` and `python -m mamey workflow` run the same code.

Without `--ledger-out`, the ledger goes into the package as `<strain>_SAPOTE_WORKFLOW_LEDGER.md`. No
separate JSON file is written. Without `--strict`, the command exits 0 when it finishes, even if
steps are open. A ledger write error is reported but does not by itself fail a non-strict run. Work on
a copy of the package if its bytes must stay fixed. The ledger does not authorize sealing, release or
publishing.
