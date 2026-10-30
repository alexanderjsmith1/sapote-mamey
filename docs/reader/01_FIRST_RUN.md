# Your first run

You need one antiSMASH result ZIP. antiSMASH is a separate program that finds biosynthetic
gene clusters in a genome. Mamey reads its results and builds an evidence package.

- Setup not done yet? Start with [Inputs and setup](02_INPUTS_AND_SETUP.md).
- No ZIP of your own? Download a loose ZIP from the [public antiSMASH datasets](../PUBLIC_DATASETS.md).
- Have a `Complete_Package.zip` from an earlier run? Go to [Read one saved package](03_READ_RESULTS.md).
- Want an assistant to do it? Use [the walkthrough request](../MASTER_WALKTHROUGH.md#route-a-ask-your-assistant-to-run-it).

## Run it

Open a terminal in the program folder, the one with `mamey_run.py`. Replace `EXAMPLE` with
your strain name and the path with your ZIP.

```bash
python mamey_run.py doctor
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip
python mamey_run.py validate runs/EXAMPLE/package
```

- `doctor` checks the install.
- `inspect` lists what is in the ZIP and prints a suggested `run` command.
- `run` does the extraction and writes everything to `runs/EXAMPLE/`. A large genome takes a while.
- `validate` checks the finished package.

On Windows, activate Python as the [install guide](../INSTALL.md#2-create-a-python-environment)
shows. The commands are the same.

## Add what you know about the strain

If you have a record of the species or the isolation source, add them to `run`:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --taxonomy 'Streptomyces sp.' --source 'leaf-cutter ant cuticle'
```

Copy the source exactly as it was deposited, for example the GenBank `isolation_source`.
Leave a flag out when you have no record for it.

## Look at the results

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html` in a browser. It links to the region list,
the workbook and the issue log. [Read one saved package](03_READ_RESULTS.md) walks through them.

The run also writes a `*_Complete_Package.zip` in `runs/EXAMPLE/`. Keep it with the original ZIP.

## If something fails

Keep the folder and the error message, and see [Recovery and limits](04_RECOVERY_AND_LIMITS.md).
To try again, add `--outdir` with a new folder so the failed attempt stays as it was.

## What next

To go from the region list to a written card or a figure, use [Choose a task](../USER_TASK_ROUTER.md).
