# Start with your file

Pick the row that matches the file you have, then follow that one guide.

| You have | Read next | What you will have at the end |
|---|---|---|
| The program's code ZIP, not yet set up | [Inputs and setup](reader/02_INPUTS_AND_SETUP.md) | A working install and three folders: program, input, output. No results yet. |
| A result ZIP from antiSMASH (a separate program that finds gene clusters in a genome), with this program set up | [Your first extraction](reader/01_FIRST_RUN.md) | An evidence package, a workbook and a validation result. |
| A saved `*Complete_Package.zip`, or its unzipped folder | [Read one saved package](reader/03_READ_RESULTS.md) | A short review note. Nothing is rerun. |
| A run that failed or stopped | [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md) | What failed, what was kept, and one next step. |

A genome FASTA or raw reads are not an antiSMASH result. Run antiSMASH first; this program does not. A file's name does not tell you which kind of ZIP it is, so open it and look. Keep every original archive and its SHA-256.

## What the program does and does not tell you

Mamey pulls evidence out of antiSMASH results and organizes it. Sapote helps you interpret and write it up. Neither one proves that a compound is made, what its structure is, or that it is active. A score ranks what to look at first. A reference match shows similarity, not identity.

## Before you run anything

- The program folder is the one holding both `mamey_run.py` and `pyproject.toml`. You need Python 3.12 or newer.
- Set up once and reuse that environment. You do not need to reinstall when you switch guides.
- Put outputs in a new folder, away from the program and the input.
- Some commands write inside the program folder even when you give an output folder. `doctor` writes a short-lived test file under `runs/_doctor_probe/`. `validate` can update a package's `package_status.json`. To keep a saved package untouched, validate a copy.

The examples use a macOS or Linux shell. [Inputs and setup](reader/02_INPUTS_AND_SETUP.md) links the Windows and offline instructions.

## How to tell whether it worked

Ask four separate questions:

1. Did the command finish? Check the exit status and the run log.
2. Did the package pass its checks? Check the `validate` result and the issue log.
3. Which evidence channels actually ran? Check each channel's receipt.
4. Has anyone authored and reviewed an interpretation? A finished extraction is not one.

An empty cell does not say why it is empty. "Not run", "failed", "missing" and "ran, found nothing" are different results; the receipts tell them apart. [Read one saved package](reader/03_READ_RESULTS.md) shows how.

When you name a single biosynthetic gene cluster (BGC), copy **strain / full node-or-contig / region / BGC alias** from one source record. If any part is missing or conflicting, hold it rather than guessing.

## Keep the handoff together

Keep the input and software versions, the exact commands, the logs, the validation output, the output paths and any open issues. Keep the package folder together. A chat answer is not the package.

When one question is done, pick the next task in the [task router](USER_TASK_ROUTER.md). For more detail, see the [first-analysis walkthrough](MASTER_WALKTHROUGH.md), the [result-reading reference](READING_YOUR_RESULTS.md) and the [troubleshooting guide](COMMON_MISTAKES.md).
