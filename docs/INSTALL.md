# Install Sapote Mamey

Set up Mamey to read an antiSMASH result ZIP. You need Python 3.12 or newer,
the extracted program and internet access for the normal install.
For a computer without internet access, use [offline installation](#offline-installation).

## 1. Open the bundle root

Extract the code ZIP into a writable folder. Open a terminal in the folder
containing `mamey_run.py` and `pyproject.toml`.

## 2. Create a Python environment

On macOS or Linux:

```bash
python3 --version
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Check that the first line reports Python 3.12 or newer before continuing.
If it reports an older version, install a supported Python and reopen the terminal.
The environment keeps Mamey's packages separate from your other Python programs.

On Windows, use PowerShell. Create the environment with `python -m venv .venv`,
then activate it with `.venv\Scripts\Activate.ps1` before the pip command.

When you return to this folder, activate `.venv` again before running Mamey.
Start each Mamey command with `python mamey_run.py` followed by its task,
such as `doctor` below.

## 3. Add the features you need

The core install includes workbook and ReportLab PDF support. For plots and
GenBank tools, add the figures extra:

```bash
python -m pip install -e '.[figures]'
```

Other extras are `addons` for optional comparison and scanner libraries,
`documents` for Word workflows, `slides` for PowerPoint, `bio` for Biopython
without plotting, and `render` for CairoSVG conversion.
Install an extra with the same syntax, replacing `figures` with its name.
[Prerequisites](PREREQUISITES.md) covers external programs and datasets.

## 4. Confirm the local version and environment

```bash
python mamey_run.py doctor
```

Read the final summary. It says whether the core checks passed and lists missing
optional capabilities. You can start a core extraction while optional tools are absent.

### Doctor scope and write probe

Doctor briefly creates `runs/_doctor_probe/probe.txt` in the program folder.
If that folder already exists, doctor leaves it alone and reports a failed write
check. Keep it intact; use another working installation if you cannot safely move
it, then run doctor again.

The startup command also runs doctor. To see only the version and workflow,
use `python mamey_run.py start --no-doctor`.

## 5. Inspect and run an input

Continue with [Your first run](reader/01_FIRST_RUN.md), using the same environment.
It shows how to inspect the ZIP, extract it and open the results.

## Offline installation

You need a wheel folder matching this computer's operating system, processor
and Python version. Include the core dependencies, build requirements and any
extras you plan to install; the code ZIP alone is not a complete wheel collection.

Create and activate `.venv` as above. Place the compatible wheels in a folder
named `wheels` beside the program folder. In a macOS/Linux shell:

```bash
(
  unset PIP_INDEX_URL PIP_EXTRA_INDEX_URL PIP_FIND_LINKS
  export PIP_CONFIG_FILE=/dev/null
  python -m pip --isolated install --no-index --find-links ../wheels -e .
)
```

`--no-index` uses the local wheel folder instead of a package index; `--isolated`
ignores user pip configuration. If pip reports a missing distribution, add its
compatible wheel to that folder and retry. Do not rename wheel compatibility tags.

### Optional documents wheelhouse preflight

For offline Word/PDF setup, `tools/audit_documents_wheelhouse.py` can check a
wheel directory against `sapote_addons/profiles/documents.txt` before installation.
Its report includes individual requirements and `joint_resolution`; both must
pass together. Optional import checks examine the installed environment, rather
than the prospective wheels. See [Prerequisites](PREREQUISITES.md).

## Workspace and output locations

A first run writes to `runs/EXAMPLE/`. Set `--outdir` on `run` to choose a different
parent folder; the strain folder is added beneath it.

For a project shared across tools, see [Project data home](PROJECT_DATA_HOME.md).
That guide explains workspace settings, which do not replace each command's
output options.

## Reader package homes and assembly authority

Use [Project catalog](PROJECT_CATALOG.md) to find and register saved packages.
The [data-home guide](DATA_HOME.md) explains how to select the right assembly
when several results exist for one strain.

## 6. Optional: developer tests

Tests are for code changes. Follow the [cut protocol](../CUT_PROTOCOL.md) for
release checks; they are not an installation step for a first analysis.
