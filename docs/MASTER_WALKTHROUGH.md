# Your first Sapote-Mamey analysis

Turn one antiSMASH result ZIP into a package: tables, a workbook and an issue log
for one strain. You need that ZIP and a working Python installation. A saved
`Complete_Package.zip` is read by extracting it; see
[Read one saved package](reader/03_READ_RESULTS.md). Terms are in the [glossary](GLOSSARY.md).

You are done when `validate runs/EXAMPLE/package --workbook-strict` exits 0 and
reports `MAMEY_COMPLETE`. Both routes below end there.

## Route A: ask your assistant to run it

Give your assistant the program folder and your antiSMASH result ZIP. Use this
request, replacing `EXAMPLE` with your strain name:

> Read AGENTS.md, inspect my EXAMPLE antiSMASH ZIP, run Mamey and validate the
> package. Show me where to open the workbook and explain any warnings.
> Keep the original input and use a new output folder.

Check the answer yourself. The assistant should show the `validate` output and its
exit code `0`. If it cannot run Python or reach the files, use route B on a
computer that can.

## Route B: run the commands yourself

You work with three locations:

1. The program folder, which holds `mamey_run.py`.
2. The input ZIP, which you never edit.
3. The output folder, `runs/EXAMPLE/` inside the program folder.

Follow [Your first run](reader/01_FIRST_RUN.md). It covers install checks,
`inspect`, the `run` command, the exit codes and `validate`. Setup is in
[Install](INSTALL.md). Come back here for the optional commands below.

### Look at the finished package

```bash
python mamey_run.py explain runs/EXAMPLE/package
python mamey_run.py list-bgcs runs/EXAMPLE/package
```

`explain` describes the package. `list-bgcs` prints its ranked regions. It hides
excluded rows; add `--include-dropped` to see them.

Then open `runs/EXAMPLE/package/OPEN_ME_FIRST.html` and use
[Read one saved package](reader/03_READ_RESULTS.md) to explore the workbook and warnings.
Keep the `Complete_Package.zip` beside the original input ZIP.

## If it fails

`run` exits 1 or 2, or `validate` prints `FAIL`. Keep the command and the last
error, and follow [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md) before another attempt.

## Move a result

Extract the `Complete_Package.zip` and open `package/OPEN_ME_FIRST.html`. Keep the
extracted folder together so links work. Reading it on another computer needs no
Python and no new run. To copy files safely, see [Save and move a result](FILES_STORAGE_AND_HANDOFF.md).

## What next

Pick a question in [Choose a task](USER_TASK_ROUTER.md): read saved protein
evidence, make a figure, compare strains, or write a Mode B card (a written
evidence review of one region). Each guide lists the extra inputs it needs.
