# Your first Sapote-Mamey analysis

Turn one antiSMASH result ZIP into a region list, workbook and saved package.
You need that ZIP and a working Python installation. A saved Mamey
`Complete_Package.zip` can be [opened directly](reader/03_READ_RESULTS.md).

## Route A: ask your assistant to run it

Give your assistant the program folder and your antiSMASH result ZIP. You can
use this request, replacing `EXAMPLE` with your strain:

> Read AGENTS.md, inspect my EXAMPLE antiSMASH ZIP, run Mamey and validate the
> package. Show me where to open the workbook and explain any warnings.
> Keep the original input and use a new output folder.

If the assistant cannot run Python or access the files, use the terminal route
below on a computer with them.

## Route B: run the commands yourself

### 1. Find your three locations

The program folder contains `mamey_run.py`. Keep the input ZIP unchanged.
The first-run example writes results to `runs/EXAMPLE/` inside the program folder.

### 2. Set up the environment once

Follow [Install](INSTALL.md), then activate that environment whenever you return.
You can open HTML and workbook results without keeping Python running.

### 3. Inspect the ZIP

Open a terminal in the program folder. Replace the input path with yours:

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

You should see the antiSMASH version, region-file count and available evidence
files. Check that this is the input you meant to use.

### 4. Run one strain

Follow [Your first run](reader/01_FIRST_RUN.md) for the extraction command and
optional strain metadata. That page is the single first-run recipe.

### 5. Validate and read what finished

When the run finishes, check its package. Replace `EXAMPLE` with your strain:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
python mamey_run.py explain runs/EXAMPLE/package
python mamey_run.py list-bgcs runs/EXAMPLE/package
```

The strict flag makes a missing or invalid workbook fail validation. Read both
the main result and `WORKBOOK_CONTENT`. `explain` describes the package;
`list-bgcs` prints its ranked regions. It hides excluded rows by default;
add `--include-dropped` when you want those rows too.

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html`, then use
[Read one saved package](reader/03_READ_RESULTS.md) to explore the workbook and warnings.
Keep the `Complete_Package.zip` beside the original input ZIP.

## When something goes wrong

Keep the command and last error. Follow [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md)
before starting another attempt.

## Reopen or move a result

Extract the Complete_Package ZIP and open its `OPEN_ME_FIRST.html`. Keep the
folder together so links work. You do not need another extraction to read it
on a different computer.

## Optional follow-up work

Pick the question you want to answer in [Choose a task](USER_TASK_ROUTER.md):
read saved protein evidence, make a figure, compare strains or write a Mode B card.
Each guide lists the additional inputs it needs.
