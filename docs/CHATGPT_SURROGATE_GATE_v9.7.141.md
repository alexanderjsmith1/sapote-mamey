# ChatGPT surrogate gate — v9.7.141

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

- `python -m mamey doctor`
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
