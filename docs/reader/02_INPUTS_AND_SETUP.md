# Inputs and setup

Get ready to run Mamey on one antiSMASH result ZIP. You need the program folder
and Python 3.12 or newer. To only open a saved result, you need a browser and a
spreadsheet reader; go to [Read one saved package](03_READ_RESULTS.md).

## What goes in

| Input | What it is | What to do |
|---|---|---|
| Code ZIP | The program. | Extract it. Open the folder that holds `mamey_run.py` and `pyproject.toml`. This is the program folder. |
| antiSMASH result ZIP | antiSMASH's output for one genome. It holds one GenBank file per region and, usually, a JSON file and KnownClusterBlast text files. | Keep it unchanged. Mamey reads it and never edits it. |
| Genome FASTA | A raw sequence. | Not an input. Run antiSMASH on it first; the [antiSMASH web submission guide](../ANTISMASH_WEB_SUBMISSION_SOP.md) gives the settings. |
| `Complete_Package.zip` | A saved Mamey result. | Not an input to `run`. Open it with [Read one saved package](03_READ_RESULTS.md). |

[Input contents](../ANTISMASH_INPUTS_CONSUMED.md) explains what Mamey can read when
some files are missing.

## Practice on a public genome

Download a loose ZIP from the [public antiSMASH datasets](../PUBLIC_DATASETS.md).
File names in that set often start with an accession, the database number for the
genome.

Choose your own short strain name for `--strain`, such as `ABC-12`. Do not use the
accession. When the archive names an organism, `run` refuses an accession as the
strain name and exits 2. To use the accession anyway, add `--allow-accession-strain-id`.

## Set up Python

From the program folder, follow [Install](../INSTALL.md). It covers a new Python
environment, Windows activation, optional features and offline setup. If you
already installed this bundle, activate that environment and keep using it.

## Check the install

```bash
python mamey_run.py doctor
```

The last line says whether to go on. Missing optional tools affect only their own
features. [Your first run](01_FIRST_RUN.md#1-check-the-install) lists each ending and what
it means. To fix a failed core check, see [Install](../INSTALL.md#doctor-scope-and-write-probe).

## Start the run

Follow [Your first run](01_FIRST_RUN.md). It writes to `runs/EXAMPLE/` inside the
program folder. To choose another location, add `--outdir <folder>` to the `run`
command; Mamey adds the strain folder beneath it.

For a retry, use a new output folder so you can compare it with the earlier attempt.
Keep the input ZIP with the finished `Complete_Package.zip`.
