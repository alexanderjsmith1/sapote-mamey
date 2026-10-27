# ChatGPT surrogate gate — v9.7.141

## Actual coverage, exit and write limits

The gate skips declared paths that do not exist and marks missing-module failures ENV-SKIP. A summary
of PASS plus ENV-SKIP still reports PASS, so read the per-step results. Doctor can be skipped by its flag.

Logs, summary, CSV and report go to fixed paths and replace earlier files; py_compile can create
caches. Within an authorized check, retain exact source/input/step scope, omitted/skipped
files, actual return codes, logs and timestamps; select the one candidate output deliberately. This command
executes its configured checks; bind their inputs, resource scope and outputs before running it.

For actual release criteria, use [release records](RELEASE_RECORDS_GUIDE.md) and the source-bound cut owner;
current full-suite flags/structured external receipt requirements are separate. An advisory surrogate,
old test count, ENV-SKIP or historical PASS cannot waive those gates. No scientific result, real smoke run,
rendered QA, owner acceptance or release approval follows from this guide or summary status.

Run these commands from the bundle root.


Purpose: provide a fast, high-signal gate for quick review loops when the complete partitioned pytest suite is too slow for every iteration.

This gate is intentionally **not** a replacement for the full partitioned pytest suite before signing. It is a surrogate for rapid patch-review cycling.

## Command

```bash
python tools/run_chatgpt_surrogate_gate.py
```

Default output directory:

```text
validation/chatgpt_surrogate_gate/
```

## What it covers

- `python mamey_run.py doctor`
- Python compilation of the main recovery and receipt tools
- Bash syntax for the deliverable fail-closed script
- A curated pytest subset covering:
  - release identity and bootstrap freshness
  - ChatGPT smoke-first and oversized-batch guards
  - heartbeat/finalization behavior
  - receipt, recovery-status, and timing parity
  - registry parity and workbook populated-sheet gate

## Why it exists

The full suite passes by partitions but takes tens of minutes. This gate aims to finish in a tenth of that.

## Interpretation

PASS means the candidate survived the fast operational-reliability gate. It does **not** mean:

- full partitioned pytest was re-run;
- real genome smoke runs were re-run;
- C5 production deliverables rendered on a full cohort;
- C7 public workbook generation ran on a real banked cohort.

Use this gate for quick patch turns. Use the full partitioned pytest and real smoke tests for release sign-off.
