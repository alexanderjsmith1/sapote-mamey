# Your first run

This page takes one antiSMASH result ZIP through to a checked result. Other pages link here
instead of repeating these steps.

antiSMASH is a separate program that finds biosynthetic gene clusters (BGCs) in a genome.
Mamey reads antiSMASH's result ZIP and builds a **package**: a folder of tables, a workbook
and an issue log for one strain.

- Setup not done yet? Start with [Inputs and setup](02_INPUTS_AND_SETUP.md).
- No ZIP of your own? Download one from the [public antiSMASH datasets](../PUBLIC_DATASETS.md),
  or practice on the bundled example `examples/test_data/smoke_antismash_small.zip`.
- Already have a `Complete_Package.zip`? Go to [Read one saved package](03_READ_RESULTS.md).

## Before you start

1. Open a terminal in the program folder, the one that holds `mamey_run.py`.
2. Activate the Python environment you installed into
   ([Install, step 2](../INSTALL.md#2-create-a-python-environment)).
   Check that `python --version` runs before you go on.
3. In the commands below, replace `EXAMPLE` with your strain name and
   `~/Downloads/EXAMPLE.zip` with the path to your ZIP. Put a path that has spaces in quotes.

The commands break long lines with `\`. Windows PowerShell does not accept that. In
PowerShell, put each command on one line, or end each line with a backtick (`` ` ``).

## 1. Check the install

```bash
python mamey_run.py doctor
```

Read the last line:

| Last line starts with | What to do |
|---|---|
| `DOCTOR: ALL CLEAR` | Go on. |
| `DOCTOR: PASS with N warning(s) — optional items only` | Go on. The warnings name optional tools and data you can add later. |
| `DOCTOR: PASS with N warning(s) — missing core dependency` | Install the package it names, then run `doctor` again. |
| `DOCTOR: N blocking issue(s)` | Stop. Fix the lines marked ❌. [Install](../INSTALL.md) covers each one. |

`doctor` tests that it can write by creating `runs/_doctor_probe/` for a moment. If that
folder already exists, it leaves it alone and reports a failed write check. Do not delete
the folder to make the check pass. [Doctor scope](../INSTALL.md#doctor-scope-and-write-probe)
explains what to do instead.

## 2. Look inside the ZIP

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

`inspect` reads the ZIP without changing it. It reports:

- **GBK region files:** how many region files the ZIP holds. Mamey reads one BGC from each.
- **JSON evidence:** whether antiSMASH's JSON file is in the ZIP.
- **KCB TXT files:** how many KnownClusterBlast text files it holds. These are antiSMASH's
  comparisons with known clusters. If the count is above zero, an `Other ClusterBlast TXT`
  line counts the ClusterBlast and SubClusterBlast files.
- **A `run` command** for this ZIP, then the `validate` command to use afterward.

The printed `--strain` is usually the ZIP file name: `EXAMPLE.zip` gives `EXAMPLE`. If
`inspect` has to change it, for example because the name is longer than 64 characters,
it prints a `Strain name:` line that says why. You can pick another name. Use the same
name in every later command.

Some antiSMASH exports hold whole records instead of region files. `inspect` then prints a
`Whole records` line. A record is used only when it has exactly one region with its own
number. Any other record is held, and the line gives the hold codes.

If `inspect` says the ZIP does **not** look like antiSMASH output, it found no region files
and no usable whole records. The ZIP may be a raw genome download or an incomplete archive.
Check where it came from before you run antiSMASH again.

`inspect` checks the file's shape. It does not show that the run will succeed, or that
the ZIP covers the whole genome.

## 3. Run the command that `inspect` printed

The printed command has two lines for you to fill in:

```bash
python mamey_run.py run \
    --strain EXAMPLE \
    --input-zip ~/Downloads/EXAMPLE.zip \
    --taxonomy "<Genus species>" \
    --source "<isolation source>" \
    --mode gold \
    --release PRIVATE \
    --capped-session \
    --json-evidence off \
    --brief none
```

Edit those two lines:

- `--taxonomy`: the most specific name your records support, for example
  `--taxonomy "Streptomyces sp."`. If you have no record, delete the line. The run then
  records the taxonomy as not verified.
- `--source`: the isolation source exactly as it was deposited, for example the GenBank
  `isolation_source` field. If you have no record, delete the line.

If you leave the angle-bracket text in place, `run` stops with `TAXONOMY_PLACEHOLDER` or
`SOURCE_PLACEHOLDER`, writes nothing and exits with code 1. Any source written in angle
brackets is refused. A bare `sp.` is refused as a taxonomy.

With a taxonomy and no source record, the edited command is:

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

What the other flags do:

- `--mode gold`: the analysis mode. It is the only one; `standard` is deprecated.
- `--release PRIVATE`: labels the run private. The label does not control who can read the
  files; manage access to them yourself.
- `--capped-session`: a lighter run for a session with a time limit. It cannot promise to
  finish before the limit. It requires the workbook, turns off the brief and the main JSON
  reader, and turns off automatic gene maps unless you set a map option yourself.
  You can render maps and figures later from the finished package.

Even with `--json-evidence off`, a separate step still tries to read the JSON for the
KnownClusterBlast percent and TIGRFAM hits. If those values are missing, check that
step's status in the package. [JSON evidence modes](04_RECOVERY_AND_LIMITS.md#json-evidence-modes)
explains the settings.

**Without the cap.** Delete the `--capped-session`, `--json-evidence off` and `--brief none`
lines. The run then reads JSON evidence within a time budget, writes the standard brief and
draws gene maps. It takes longer.

A large genome can take a while. The run writes into `runs/EXAMPLE/`.

## 4. Check that the run worked

When the run ends, it prints a `DELIVERABLES` block. The block names the sealed ZIP and
its status.

```text
DELIVERABLES — hand these sealed package zip(s) to the user:
  → runs/EXAMPLE/EXAMPLE_SapoteMamey_v<version>_engine<engine>_<setting>_Complete_Package.zip  (… KB, MAMEY_COMPLETE_WITH_ISSUES)
```

Check the exit code with `echo $?` straight after the command. In PowerShell, use
`echo $LASTEXITCODE`.

| Exit code | Meaning |
|---|---|
| `0` | The run finished. Its status is `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES`. Read the issue log either way. |
| `1` | The run did not produce a usable result. The last `ERROR:` or `REFUSED:` line says why: a `[BLOCKING]` issue, a placeholder refusal, another run writing the same folder (`PACKAGE_LOCKED`), or a crash. Go to [Recovery](04_RECOVERY_AND_LIMITS.md). |
| `2` | The command was refused before the run started. Examples: an unsafe strain name, a strain name that is a database accession, or an output folder inside the program's code folders such as `mamey/` or `docs/`. Fix the command and run it again. |

`MAMEY_COMPLETE_WITH_ISSUES` with exit code 0 does not mean every step worked. An optional
step can record an error or skip an output and the run still exits 0. The issue log and
`run_phase_receipts.jsonl` in the package show which steps had problems.

Then validate the package. `inspect` printed this command too:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

It prints a JSON result, then a `WORKBOOK_CONTENT` block.

- **Exit code 0:** the checks passed. The overall `status` is `MAMEY_COMPLETE` for a fresh
  run, or `PASS` once written cards cover every region.
- **Exit code 1 with `FAIL`:** a check failed, and the result names it. With
  `--workbook-strict`, a missing or invalid workbook also fails.

[Status values](04_RECOVERY_AND_LIMITS.md#status-values) lists every status.

`validate` updates `package_status.json` inside the package. To keep the package exactly
as the run wrote it, validate a copy.

A pass means the software checks passed. It does not prove that every BGC was found or
that any biological reading is right. Review the issue log, missing evidence and holds
yourself.

## 5. Open the results

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html` in a browser. It shows the strain, taxonomy,
source, run status and validation status, lists the issues, and links to:

- the triage board, `EXAMPLE_4_triage_board.csv`;
- the workbook, `EXAMPLE_5_workbook.xlsx`;
- the issue log, `issue_log.md`.

If `OPEN_ME_FIRST.html` is missing, open `issue_log.md` first.
[Read one saved package](03_READ_RESULTS.md) walks through every file.

The triage board lists the BGCs the run scored. Before you rely on a count, compare it with
the region count from `inspect` and with the holds in the issue log.

## Keep the sealed ZIP

The `*_Complete_Package.zip` in `runs/EXAMPLE/` is the result to keep and share. Keep it
with the original antiSMASH ZIP, and keep both unchanged.

The run also writes `runs/HANDBACK.json`, a pointer to the newest sealed ZIP. A later run
with the same output folder replaces that pointer, so do not rely on it to find older
results. Give each run its own output folder.

## If something fails

Keep the output folder and the last error message, and go to
[Recovery and limits](04_RECOVERY_AND_LIMITS.md).

## What next

To go from the triage board to a written card or a figure, use
[Choose a task](../USER_TASK_ROUTER.md).
