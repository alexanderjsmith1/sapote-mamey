# Recover a run

Use this page when a run stops or a result is missing. You need the command you
ran, its final error and the output folder. Keep that folder while you diagnose
the problem.

## Find the failed step

Read the last error in the terminal and `issue_log.md`, if the run created it.
If the terminal is still busy, check the process before starting another run.
In `run_phase_receipts.jsonl`, `TIMEOUT`, `FAIL` and `SKIP` name different outcomes;
a lone `START` needs a process check.

- **File not found:** check the path and put paths with spaces in quotes.
- **Python or an import fails:** activate the environment you used to install
  this bundle. [Install](../INSTALL.md) covers Python and missing dependencies.
- **Workbook missing:** look for `AS-40_5_workbook.xlsx` and the workbook warning.
  Check that `openpyxl` is installed in the active environment.
- **JSON held or truncated:** read the affected file and reason in the issue log.
  [Missing JSON evidence](../COMMON_MISTAKES.md#missing-kcb-riq-or-json-evidence)
  explains the size limits and settings.
- **Validation fails:** read the named file or check in the error. Keep the
  original package while you correct the cause; do not edit a result to `PASS`.
- **A figure or PDF is missing or clipped:** check the renderer warning and the
  underlying data. Follow [figure help](../FIGURES_START_HERE.md) for that renderer.

A blank result can mean missing input, a skipped step or a failure; check the
recorded status before treating it as a search with no hits.

## Try again without overwriting the attempt

Once you have corrected the cause, run the same command with `--outdir` pointing
to a new folder. For example, the first-run command becomes:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip --outdir runs/retry
```

Replace the strain and input path with yours. This writes to
`runs/retry/EXAMPLE/`, leaving `runs/EXAMPLE/` in place.

Check the new result:

```bash
python mamey_run.py validate runs/retry/EXAMPLE/package --workbook-strict
```

The strict flag checks the workbook as well as the package. Open the new
`OPEN_ME_FIRST.html` and compare the reported warnings with the failed attempt.

For a batch, use the [batch recovery guide](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md);
its resume option skips matching finished inputs rather than continuing every
interrupted extraction.

## Ask for help

Include the command, Python version, input filename, output folder and last
error as text. Add the input checksum and bundle version when comparing runs.
The [troubleshooting guide](../COMMON_MISTAKES.md) covers more specific errors.
