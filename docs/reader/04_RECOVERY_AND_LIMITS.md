# Recover a run

Use this page when `run` or `validate` ends with an exit code other than `0`, or when a
result is missing. Leave the output folder as it is while you find out what happened.
[Your first run](01_FIRST_RUN.md#4-check-that-the-run-worked) explains the exit codes.

## Find what failed

Look in three places, in this order.

**1. The terminal.** Read the last `REFUSED:` or `ERROR:` line. A command refused before
any work started (exit code `2`) gives its reason there, for example an unsafe strain name.

**2. `runs/EXAMPLE/package/issue_log.md`.** One issue per line, each starting with `- `.

- A line whose text starts with `[BLOCKING]` makes `run` exit `1`.
- Other lines are warnings, for example
  `- OVER_MERGE_CANDIDATES: 1 region(s) hold 2 or more protoclusters ...`. They do not change
  the exit code, but read them: an optional step can fail without a blocking line.
- `- No blocking issues recorded.` is the summary line when there is nothing to report.

The terminal prints the same warnings with an `[ISSUE]` tag.

**3. `runs/EXAMPLE/package/run_phase_receipts.jsonl`.** One line per step event, each with a
`phase` and a `status`. The run writes these as it goes, so a crash can leave the last one
missing. The detail fields differ from step to step.

| Status | Meaning |
|---|---|
| `START` | The step began. If no later line follows, the step was still running, was interrupted, or failed before it could write its result. Check whether the process is still running. |
| `END` | The step finished. |
| `ERROR` | The step raised an error. The `reason` field gives it. |
| `FAIL` | The step could not write its result. The `error` field gives the reason. |
| `TIMEOUT` | The step hit its time limit. |
| `SKIP` | The step did not run. The `reason` field says why, for example `--brief none`. |
| `WARN` | The step finished with a warning, for example incomplete scoring coverage. It may carry `reason`, `events` or `n`. |

If the terminal is still busy, the run may still be going. Check before you start another.

## Common causes

- **`TAXONOMY_PLACEHOLDER` or `SOURCE_PLACEHOLDER`:** the command still has the `<…>` text
  that `inspect` prints, or a bare `sp.`. Edit or delete that line. The run exits `1` and
  writes nothing.
- **`PACKAGE_LOCKED` or "another mamey run is writing":** another run is writing to the same
  folder, and this one exits `1`. The package folder may already exist. Wait for the other
  run, or use a different `--outdir`.
- **File not found:** check the path. Put a path with spaces in quotes.
- **Python or an import fails:** activate the environment you installed into, then run
  `python mamey_run.py doctor`. [Install](../INSTALL.md) covers each missing package.
- **Workbook missing:** look for `EXAMPLE_5_workbook.xlsx` in the package and for a workbook
  line in the issue log. Check that `openpyxl` is installed.
- **JSON evidence missing or cut short:** look in the issue log for `JSON_EVIDENCE_SKIPPED`
  and other JSON lines. [JSON evidence modes](#json-evidence-modes) below explains them.
- **`validate` fails:** its JSON result names the failing check. Fix the cause and run it
  again. Do not edit a result file to make it pass.
- **A figure or PDF is missing or clipped:** read the renderer's warning, then use
  [figure help](../FIGURES_START_HERE.md) for that renderer.

A blank cell or a missing table can mean missing input, a skipped step or a failure. Check
which before you read it as "no hits".

## Status values

`run` prints a `status` for each strain, and `package_status.json` keeps it as
`terminal_status`. `validate` prints its own `status`. They answer different questions.
[Read one saved package](03_READ_RESULTS.md#check-what-finished) shows where each is stored.

| Value | Printed by | Meaning |
|---|---|---|
| `MAMEY_COMPLETE` | `run`, `validate` | The run finished and the checks passed. From `validate`, it also means written cards do not yet cover every region. |
| `MAMEY_COMPLETE_WITH_ISSUES` | `run` | The run exits `0` and recorded issues. Read `issue_log.md` and the phase receipts. |
| `PASS` | `validate` | The checks passed and written cards cover every region. |
| `FAIL` | `validate` | A check failed. The JSON result names it, and `validate` exits `1`. |
| `VALIDATION_FAIL` | `run` | The run's own validation failed. `run` exits `1`. |
| `MAMEY_FAILED` | `run` | The run stopped without a package, for example because the input is not an antiSMASH ZIP. `run` exits `1`. |
| `TAXONOMY_PLACEHOLDER`, `SOURCE_PLACEHOLDER` | `run` | Metadata was refused before anything was written. `run` exits `1`. |
| `PACKAGE_LOCKED` | `run` | Another run holds the package lock. `run` exits `1`. |

`package_status.json` also has a `package_status` field for the recovery state:

| Value | Meaning |
|---|---|
| `MAMEY_COMPLETE` | A normal run, including one that recorded issues. |
| `RECOVERY_VALIDATED` | The package holds a validated-recovery marker file. It was recovered, not run straight through. |
| `RECOVERY_NEEDED` | The package holds a recovery-needed marker, or another file with "recovery" in its name. Recover it or review it by hand. |
| `PARTIAL_FAILED` | The newest validation failed, or the recorded status is not a recognized success. A failed fresh validation wins over every other value. |

`JUDGMENT_PENDING` in `gate_validation.json` means written cards do not cover every region.
Some cards may still exist; check the package before you start writing.

## JSON evidence modes

`run --json-evidence` sets how the main JSON reader handles antiSMASH's result JSON:

| Mode | What the main reader does |
|---|---|
| `bounded` | The default. Streams the JSON and keeps the KnownClusterBlast, region-to-region and RiQ parts. With the `ijson` streaming parser it skips a JSON file over 250,000,000 bytes. Without `ijson` it falls back to `off`. |
| `off` | Does not run. `--capped-session` forces this mode. |
| `full` | Loads the whole JSON. It refuses a JSON file over 80,000,000 bytes uncompressed. Memory use can be much larger than the file. |

In every mode, a separate step reads the JSON for the KnownClusterBlast percent and TIGRFAM
hits. The KnownClusterBlast text files are read when the ZIP has them. So a capped run
can still carry JSON-derived values. That separate step can be held or fail, which leaves
those values blank; its status is recorded in the package. RiQ scores come only from the
main reader, so they stay blank in `off` mode.

## Run again without overwriting the attempt

When you have fixed the cause, run the same `run` command again. Keep every input and
metadata option as it was, including `--taxonomy` and `--source`, and add `--outdir` with a
new folder. Put your own values in place of the angle-bracket text:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --taxonomy "<taxonomy you used before>" --source "<source you used before>" \
  --mode gold --release PRIVATE \
  --capped-session --json-evidence off --brief none --outdir runs/retry
python mamey_run.py validate runs/retry/EXAMPLE/package --workbook-strict
```

Leave out `--source` only if the first run left it out. `run` refuses text left in angle
brackets.

The retry writes to `runs/retry/EXAMPLE/`, and `runs/EXAMPLE/` stays as it was. Open the new
`OPEN_ME_FIRST.html`, or the new `issue_log.md` if the page is missing, and compare its issues
with the failed attempt. A separate output folder also keeps the earlier `HANDBACK.json`.

For many ZIPs, use the [batch guide](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md). Its resume
option skips an input only when the input bytes, code, options and package all match the
saved receipt. It does not continue an interrupted run.

## Ask for help

Send these as text:
- the command you ran;
- the exit code;
- the last `ERROR:` line;
- the output of `python --version`;
- the input file name;
- the output folder.

When you compare two runs, add the input checksum and the bundle version.
[Troubleshooting](../COMMON_MISTAKES.md) covers more specific errors.

## Limits

- A pass means the software checks passed. It does not show that every BGC was found or
  that any biological reading is right.
- A similarity to a known cluster is not an identity.
- A no-hit result describes one named search and its recorded state. It does not show that
  similar sequences are absent.
