# Recover a run without losing its evidence

Use this page when a [first extraction](01_FIRST_RUN.md) stops or an
[existing result](03_READ_RESULTS.md) looks incomplete. Keep the attempt
and diagnose the affected step before deciding whether more execution is needed.
Opening a saved result in a new conversation does not require another run.

## Keep a useful record

Retain the exact command, input filename and SHA-256, bundle/build, Python
interpreter/version, output location, exit code and error text. Keep the original
ZIP, logs, manifest, issue log and available receipts; an early failure may have
produced only a terminal error. Check identifiers and local paths before sharing.

If the run may still be going, check the terminal or the process list before
calling it stopped or finished. A quiet terminal, an old progress line or a lock
file does not tell you its state. If you cannot check, record the state as
**unconfirmed**.

## Match the symptom to one next step

| Symptom | Check and next step |
|---|---|
| **Path not found or an old link fails** | Confirm which file is needed: code, antiSMASH input (the result ZIP from the program that finds gene clusters) or saved package. Check the actual path and quote spaces. Keep a moved package’s folder structure together; verify the source hash before substituting a relocated file. See [file and transfer recovery](../COMMON_MISTAKES.md#package-fails-after-transfer-or-files-seem-missing). |
| **Dependency absent or wrong Python** | Confirm the selected interpreter and bundle folder. Follow [installation](../INSTALL.md) for Python 3.12+ and only the selected feature’s dependencies. Record the unavailable feature; do not install everything or switch methods to hide the failure. |
| **JSON evidence is held or truncated** | Read the issue log, affected members and parse/visibility receipt. Preserve the requested and effective settings. Decide whether the missing evidence affects the question before proposing a separately scoped attempt. See [evidence availability](../COMMON_MISTAKES.md#missing-kcb-riq-or-json-evidence). |
| **Workbook is missing** | Look for the actual `[strain]_5_workbook.xlsx` and the workbook warning; check the selected environment’s `openpyxl`. CSVs may remain readable, but do not substitute them for a required workbook. Use the [workbook diagnosis](../COMMON_MISTAKES.md#workbook-missing-incompatible-or-changed-after-validation). |
| **Validation fails** | Preserve the captured result and identify the failing gate, file or checksum. Stop the affected interpretation and diagnose that failure. Do not edit a status to PASS or [reseal](../GLOSSARY.md#evidence-identity-portability-and-authority-vocabulary) unexplained changes. See [validation scope](../COMMON_MISTAKES.md#a-validation-or-seal-command-returns-zero). |
| **Run was interrupted or appears stalled** | Check the terminal or process list and the latest phase record first. Retain partial outputs and logs. Do not start a competing writer, remove a lock or assume arbitrary checkpoint recovery. Follow [interruption guidance](../COMMON_MISTAKES.md#run-appears-stalled-or-was-interrupted). |
| **PDF text or tables are clipped** | Compare the pages with the underlying tables/full text and keep the render warning. Treat the PDF as needing presentation repair. Keep the documented renderer route; report its blocker instead of substituting a different method. See [PDF diagnosis](../COMMON_MISTAKES.md#pdf-missing-clipped-or-confusing). |

A bounded JSON limit is not the same problem as clipped display text. Neither
an omitted value on a page nor a blank evidence cell establishes biological
absence. Keep unavailable, unrun, failed, truncated and evaluated-no-hit states
distinct.

## Before a new check or replacement attempt

Read saved validation receipts first. Ordinary `validate` can refresh
`package_status.json`; use an identified review copy if the original must remain
unchanged. When a workbook is required, the walkthrough’s
[`--workbook-strict` check](../MASTER_WALKTHROUGH.md#5-validate-and-read-what-finished)
makes its absence a failure rather than a skip. Read `WORKBOOK_CONTENT` alongside
the main result.

A phase START without an observed END/ERROR leaves that phase unresolved; receipt
writes can also fail. A phase END does not establish the whole run’s completion.
The batch harness’s `--resume` can skip a matching completed attempt; it does not
continue every partial extraction. Preserve the previous attempt and establish
its state before choosing a fresh destination or a documented recovery route.
See [resume binding](../COMMON_MISTAKES.md#batch-resume-refuses-an-existing-package).

## What a recovery result can support

- A resolved path or discoverable dependency does not prove successful execution.
- A zero exit or package-check pass does not prove complete evidence or authored interpretation.
- A [Mode B](../GLOSSARY.md#14-mode-b) template is a scaffold; finished work still needs its selected
  [profile and review](../MODEB_PROFILE_MATRIX.md).
- A readable or repaired PDF does not supply scientific acceptance or release authority.

For an individual locus, retain **strain / full node-or-contig / region / BGC alias**
(BGC: biosynthetic gene cluster) from one source record. Leave missing or conflicting identity on hold.

Write down what you saw, which files you checked, the failure that remains and
the one next step you plan. Note what you did not do. A software fix is not
scientific acceptance.
