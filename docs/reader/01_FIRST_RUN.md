# Your first run

This is the one first-run recipe. Other pages link here rather than repeat it.

You need one antiSMASH result ZIP. antiSMASH is a separate program that finds
biosynthetic gene clusters (BGCs) in a genome. Mamey reads its results and builds a
package: a folder of tables, a workbook and an issue log for that strain.

- Setup not done yet? Start with [Inputs and setup](02_INPUTS_AND_SETUP.md).
- No ZIP of your own? Download one from the [public antiSMASH datasets](../PUBLIC_DATASETS.md).
- Already have a `Complete_Package.zip`? Go to [Read one saved package](03_READ_RESULTS.md).

Open a terminal in the program folder, the one that holds `mamey_run.py`, and activate the
Python environment you installed into ([Install](../INSTALL.md#2-create-a-python-environment)).
If `python` is not found, the environment is not active.
In the commands below, replace `EXAMPLE` with your strain name and
`~/Downloads/EXAMPLE.zip` with the path to your ZIP. Put a path with spaces in quotes.

## 1. Check the install

```bash
python mamey_run.py doctor
```

The last line tells you whether to go on:

| Last line starts with | Meaning |
|---|---|
| `DOCTOR: ALL CLEAR` | Go on. |
| `DOCTOR: PASS with N warning(s) — optional items only` | Go on. The warnings name optional tools you can add later. |
| `DOCTOR: PASS with N warning(s) — missing core dependency` | Install the package it names, then run `doctor` again. |
| `DOCTOR: N blocking issue(s)` | Stop. Fix the lines marked ❌. [Install](../INSTALL.md) covers each one. |

## 2. Look inside the ZIP

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

`inspect` counts the region files Mamey will read, one BGC per file. It says whether
the ZIP holds antiSMASH's JSON file and its KnownClusterBlast text files. Those are
antiSMASH's comparisons with known clusters. It then prints a `run` command for this ZIP.

The printed `--strain` comes from the ZIP file name. `EXAMPLE.zip` gives `EXAMPLE`.
Change it if you want another name, and use the same name in the paths below.

Some antiSMASH exports hold whole records instead of region files. Then `inspect`
prints a `Whole records` line. A record is admitted only when it has exactly one region
feature with its own region number, and it becomes one BGC with that number. Any other
record is held, and the line lists the hold codes.

If it says the ZIP does NOT look like an antiSMASH output, no region file or whole record
could be admitted. With no hold codes, it is probably a genome download: run antiSMASH on
it first. With hold codes, the records are antiSMASH output whose region identity is unclear:
export the full antiSMASH results again, with the region files.

## 3. Run the command that `inspect` printed

Copy the printed command, then edit two lines before you run it:

- `--taxonomy "<Genus species>"`: put the species from your record, for example
  `--taxonomy "Streptomyces sp."`. If you have no record, delete the line. The run
  then records "not verified".
- `--source "<isolation source>"`: copy the isolation source exactly as it was
  deposited, for example the GenBank `isolation_source`. If you have no record,
  delete the line.

If you leave the text in angle brackets, `run` refuses with `TAXONOMY_PLACEHOLDER` or
`SOURCE_PLACEHOLDER` and exits `1`. A bare `sp.` is refused the same way. Use a genus,
for example `Streptomyces sp.`, or `not verified`.

The printed command looks like this:

```bash
python mamey_run.py run \
    --strain EXAMPLE \
    --input-zip ~/Downloads/EXAMPLE.zip \
    --taxonomy "Streptomyces sp." \
    --mode gold \
    --release PRIVATE \
    --capped-session \
    --json-evidence off \
    --brief none
```

What the flags do:
- `--mode gold`: the analysis mode. Use it; `standard` is deprecated.
- `--release PRIVATE`: keeps the package private.
- `--capped-session`: cuts the work so the run finishes in a short session. It
  requires the workbook. It turns off the written brief (a PDF summary), the reading of
  antiSMASH's JSON file, and the automatic gene maps. You can render maps and figures later from the finished package.

A run writes everything to `runs/EXAMPLE/`. A large genome can take a while.

## 4. Check that the run worked

When `run` finishes, it prints a results block and a `DELIVERABLES` list, then exits:

| Exit code | Meaning |
|---|---|
| `0` | Finished. The status is `MAMEY_COMPLETE`, or `MAMEY_COMPLETE_WITH_ISSUES` with warnings only. |
| `1` | Not usable. Causes: a `[BLOCKING]` issue, a placeholder refusal (`TAXONOMY_PLACEHOLDER`, `SOURCE_PLACEHOLDER`), another run writing the same folder (`PACKAGE_LOCKED`), or a run that stopped with an error. The last `ERROR:` or `REFUSED:` line names it. Go to [Recovery](04_RECOVERY_AND_LIMITS.md). |
| `2` | Refused before the run started, for a bad command line. Examples are an unsafe strain name, a strain name that is a database accession, or an output folder inside the program's code folders such as `mamey/` or `docs/`. A `REFUSED:` or `ERROR:` line says why. Fix the command and run it again. |

To see the exit code, run `echo $?` straight after the command. On Windows
PowerShell, use `echo $LASTEXITCODE`. The commands on this page break lines with `\`,
which PowerShell does not accept. In PowerShell, put each command on one line, or end
each line with a backtick (`` ` ``) instead.

Then validate the package:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

It prints a JSON result and then a `WORKBOOK_CONTENT` block. With exit code `0`, the
package is complete. The `status` is then `MAMEY_COMPLETE` for a fresh run, or starts
with `PASS`. `MAMEY_COMPLETE` means the extraction is done and no written cards exist yet.
Exit code `1` with `FAIL` means a check failed. The result names the check.
`--workbook-strict` also fails the check when the workbook is missing or invalid.

A passing check means the package is complete. It does not mean any cluster makes a
compound.

## 5. Open the results

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html` in a browser. It shows the strain,
taxonomy, source, run status and validation status. It also lists the issues and links:
- the triage board (`EXAMPLE_4_triage_board.csv`), with every BGC ranked;
- the workbook (`EXAMPLE_5_workbook.xlsx`);
- the issue log (`issue_log.md`).

[Read one saved package](03_READ_RESULTS.md) walks through them.

The run also writes a sealed copy in `runs/EXAMPLE/`. Its name ends in
`_Complete_Package.zip` and includes the program version and the antiSMASH detection
setting, in the form `EXAMPLE_SapoteMamey_v<version>_engine<engine>_<setting>_Complete_Package.zip`.
The `DELIVERABLES` list prints its full path. Keep and share this ZIP. Keep it with the original antiSMASH ZIP.

## If something fails

Keep the output folder and the last error, and go to
[Recovery and limits](04_RECOVERY_AND_LIMITS.md).

## What next

To go from the triage board to a written card or a figure, use
[Choose a task](../USER_TASK_ROUTER.md).
