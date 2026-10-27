# ChatGPT-safe large-strain regression — v9.7.141

Retired in v9.7.458 and kept as a record. Settings and commands may be out of date. Current guide: [AGENTS.md](../../../AGENTS.md).

> **SUPERSEDED (v9.7.409) — the run recipe below no longer runs as written.** `--mode smoke` was
> removed at v9.7.161 (`mamey run` accepts only `{standard,gold}`; `smoke` now hard-errors with
> `invalid choice`), and `--chatgpt-safe` was renamed `--capped-session` (the old flag still works
> as a deprecated alias). Current first run: `python -m mamey run --mode gold --capped-session
> --json-evidence off`. The "smoke-first" narrative below is kept for provenance; read it as
> "capped-session first," and there is no separate smoke depth to deepen from — gold is the only mode.

## Why this exists

a private large-strain test case exposed a ChatGPT-specific workflow failure: an assistant attempted a first-pass
`gold --chatgpt-safe` run before re-reading `AGENTS.md`. The run began cleanly,
then exceeded the tool-session wall-clock cap during later quiet work. After the instruction
file was read, the correct smoke-first workflow completed in about 69 seconds in the external
smoke report.

This is not primarily a biosynthetic-scoring defect. It is an operational reliability defect
for ChatGPT-style capped tool sessions.

## Historical contract and current source limits

This retained workflow is document content, not authorization to run checks or process inputs. The private run and its approximately 69-second timing have not been reproduced here. Select the current user-authorized operation and source/profile; retain actual inputs, logs, return codes and output hashes before treating a run as evidence.

1. Read the selected bundle’s canonical `AGENTS.md` and current user instructions. The duplicate filename in the original step was an error, not a separate optional instruction file.
2. Emit the required read-proof phrase and live version/build line.
3. First run must be:

```bash
python -m mamey doctor
python -m mamey inspect <antiSMASH.zip>
python -m mamey run --mode gold --capped-session --json-evidence off ...
python -m mamey validate <package>
```

4. `--capped-session` (canonical; `--chatgpt-safe` is its deprecated alias) forces `--brief none` +
   `--json-evidence off` + `--require-workbook`. It also changes automatic locus maps to `off` (an explicitly selected map setting is retained), defaults ZIP compression to `stored` only when `MAMEY_ZIP_COMPRESSION` is unset, and defaults missing heartbeat settings to 20 seconds (`mamey/cli.py`). These settings reduce selected costs; they do not guarantee completion within a tool-session cap. The old `--chatgpt-followup` is a legacy no-op since v9.7.161.
5. Quiet phases must emit heartbeats/receipts so the user can tell progress from a hang.
6. Timing and receipt telemetry must agree.

## Regression checks

- `tests/test_chatgpt_safe_first_run_guard.py`
- `tests/test_v97141_phase_receipt_and_status.py`
- `tests/test_validate_timing_receipt_parity.py`
- Real private large-strain smoke run after applying the patch

## Open validation

A real private large-strain smoke re-run should confirm:

- source_scans START and END receipts
- rggmci START and END receipts
- package_addons START and END or ERROR receipt
- package_status preserves terminal status and issue count
- validator remains PASS
- timing-vs-receipt parity validator PASS
