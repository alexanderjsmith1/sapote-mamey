# Inputs and setup

Get ready to run Mamey on one antiSMASH result ZIP. You need the program folder
and Python 3.12 or newer. If you only want to open a saved result, you need a
browser and a spreadsheet reader; go to [Read one saved package](03_READ_RESULTS.md).

## Find your files

Extract the code ZIP and open the folder containing `mamey_run.py` and
`pyproject.toml`. This is the program folder.

Keep your antiSMASH result ZIP unchanged. It contains the results that Mamey
reads, including region GenBank files and available JSON evidence. A genome
FASTA must go through antiSMASH first. [Input contents](../ANTISMASH_INPUTS_CONSUMED.md)
explains what Mamey can read when some files are missing. To practice on a public
genome, download a loose ZIP from the [public antiSMASH datasets](../PUBLIC_DATASETS.md).

A `Complete_Package.zip` is an earlier Mamey result: open it with the saved-result
guide above instead of feeding it to a new extraction.

## Set up Python

From the program folder, follow [Install](../INSTALL.md). It covers a new
Python environment, Windows activation, optional features and offline setup.
If you already installed this bundle, activate that environment and keep using it.

## Check the install

```bash
python mamey_run.py doctor
```

Read the final summary and any warnings. Missing optional tools affect their
own features; the summary says whether Mamey can run. Fix a failed core check
using [Install](../INSTALL.md#doctor-scope-and-write-probe).

## Start the run

Follow [Your first run](01_FIRST_RUN.md). The example writes to `runs/EXAMPLE/`
inside the program folder. To choose another location, use the run command's
`--outdir` option; Mamey adds the strain folder beneath it.

Keep the input ZIP with the finished `Complete_Package.zip`. Use a new output
folder for a retry so you can compare it with the earlier attempt.
