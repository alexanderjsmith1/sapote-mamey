# ChatGPT surrogate gate — v9.7.141

## Actual coverage, exit and write limits

The command exists, but inspect its current declared steps and saved per-step results rather than assuming
this v9.7.141 subset list describes every current check. `tools/run_chatgpt_surrogate_gate.py:104,:150`
filters nonexistent declared paths; `:127–137` labels missing-module failures ENV-SKIP. Overall status
(`:165`) rejects FAIL/TIMEOUT but permits ENV-SKIP-only or PASS+ENV-SKIP summaries to be PASS. Such a summary
is partial/unverified coverage, not proof every proposed step survived. Doctor can be skipped by its flag.
The old approximate timing ratio and historic partitioned-suite story are not current runtime measurements.

Logs/summary/CSV/report use fixed destinations and replace prior files (`:98–101,:178–203`), and py_compile
can create caches (`:146`). Within an authorized check, retain exact source/input/step scope, omitted/skipped
files, actual return codes, logs and timestamps; select the one candidate output deliberately. This command
executes its configured checks; bind their inputs, resource scope and outputs before running it.

For actual release criteria, use [release records](RELEASE_RECORDS_GUIDE.md) and the source-bound cut owner;
current full-suite flags/structured external receipt requirements are separate. An advisory surrogate,
old test count, ENV-SKIP or historical PASS cannot waive those gates. No scientific result, real smoke run,
rendered QA, owner acceptance or release approval follows from this guide or summary status.

<!-- Historical source text follows. -->

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


Purpose: provide a fast, high-signal gate for ChatGPT/Claude review loops when the complete partitioned pytest suite is too slow for every iteration.

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
- Python compilation of the main v9.7.141 ChatGPT/recovery/receipt tools
- Bash syntax for the deliverable fail-closed script
- A curated pytest subset covering:
  - release identity and bootstrap freshness
  - ChatGPT smoke-first and oversized-batch guards
  - heartbeat/finalization behavior
  - receipt, recovery-status, and timing parity
  - registry parity and workbook populated-sheet gate

## Why it exists

The v9.7.141c evidence showed the full collected suite can pass by partitions, but it takes roughly tens of minutes in the ChatGPT tool environment. The surrogate gate gives reviewers a fast preflight that should finish in about 1/10th of that time or less.

## Interpretation

PASS means the candidate survived the fast ChatGPT operational-reliability gate. It does **not** mean:

- full partitioned pytest was re-run;
- real genome smoke runs were re-run;
- C5 production deliverables rendered on a full cohort;
- C7 public workbook generation ran on a real banked cohort.

Use this gate for quick patch turns. Use the full partitioned pytest and real smoke tests for release sign-off.
