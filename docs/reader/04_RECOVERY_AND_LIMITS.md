# Recover a run

Use this page when `run` or `validate` does not end with exit code `0`, or when a
result is missing. Keep the output folder as it is while you work out what happened.
[Your first run](01_FIRST_RUN.md#4-check-that-the-run-worked) explains the exit codes.

## Find what failed

Look in three places, in this order:

1. **The terminal.** Read the last `REFUSED:` or `ERROR:` line. A refusal before any
   work (exit code `2`) names its reason there, for example an unsafe strain name.
2. **`runs/EXAMPLE/package/issue_log.md`.** It lists every issue. An issue marked
   `[BLOCKING]` makes `run` exit `1`. Issues marked `[WARN]` do not.
3. **`runs/EXAMPLE/package/run_phase_receipts.jsonl`.** It has one line per step,
   each with a `phase` and a `status`:

| Status | Meaning |
|---|---|
| `START` | The step began. A `START` with no later line for that step means the run stopped there, or is still running. |
| `END` | The step finished. |
| `ERROR` | The step raised an error. The line's `reason` field gives it. |
| `FAIL` | The step could not write its result. The line's `error` field gives the reason. |
| `TIMEOUT` | The step hit its time limit. |
| `SKIP` | The step was not run. The line's `reason` field says why, for example `--brief none`. |
| `WARN` | The step finished with a warning, for example incomplete scoring coverage. The `reason` field gives it. |

If the terminal is still busy, the run may still be going. Check that before you
start another one.

## Common causes

- **`TAXONOMY_PLACEHOLDER` or `SOURCE_PLACEHOLDER`:** the command still has the `<…>`
  text that `inspect` prints, or a bare `sp.`. Edit or delete that line. The run exits `1` and writes nothing.
- **`PACKAGE_LOCKED` or "another mamey run is writing":** another run is writing to
  the same folder, and this one exits `1`. Wait for it, or use a different `--outdir`.
- **File not found:** check the path. Put a path with spaces in quotes.
- **Python or an import fails:** activate the environment you installed into, then
  run `python mamey_run.py doctor`. [Install](../INSTALL.md) covers each missing package.
- **Workbook missing:** look for `EXAMPLE_5_workbook.xlsx` in the package and for
  a workbook issue in the log. Check that `openpyxl` is installed.
- **JSON evidence held or cut short:** the issue log names the file and the reason.
  [Missing JSON evidence](../COMMON_MISTAKES.md#kcb-riq-or-json-evidence-is-missing)
  explains the size limits.
- **`validate` fails:** it names the failing check in its JSON result. Correct the
  cause and run again. Do not edit a result file to make it pass.
- **A figure or PDF is missing or clipped:** read the renderer's warning, then use
  [figure help](../FIGURES_START_HERE.md) for that renderer.

A blank cell or a missing table can mean missing input, a skipped step or a
failure. Check its status before you read it as "no hits".

## Run again without overwriting the attempt

When you have fixed the cause, run the same `run` command as before, with the same
taxonomy and source, and add `--outdir` with a new folder. For example:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --taxonomy "Streptomyces sp." --mode gold --release PRIVATE \
  --capped-session --json-evidence off --brief none --outdir runs/retry
python mamey_run.py validate runs/retry/EXAMPLE/package --workbook-strict
```

The retry writes to `runs/retry/EXAMPLE/`, and `runs/EXAMPLE/` stays as it was.
Open the new `OPEN_ME_FIRST.html` and compare its issues with the failed attempt.

For many ZIPs, use the [batch guide](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md).
Its resume option skips inputs that already finished. It does not continue an
interrupted run.

## Ask for help

Send the following as text:
- the command you ran;
- the exit code;
- the last `ERROR:` line;
- the output of `python --version`;
- the input file name;
- the output folder.

Add the input checksum and the bundle version when you compare two runs.
[Troubleshooting](../COMMON_MISTAKES.md) covers more specific errors.

## Limits

- A passing package means the steps completed. It does not show that a cluster makes
  a compound.
- A similarity to a known cluster is not an identity.
- A "no hits" state means the search returned nothing. It is not proof of absence.
