# Install Sapote Mamey

Start from the [README](../README.md). This guide covers setup for the bundle you received.
Check its [release manifest](../RELEASE_MANIFEST.md) for version, tier, and status;
an unsealed candidate is not a signed public release. External data and some integration-test
fixtures are provisioned separately.

For the full analysis sequence, see [the Master Walkthrough](MASTER_WALKTHROUGH.md).

## 1. Open the bundle root

Extract the ZIP to a writable directory and enter the directory containing `pyproject.toml`
and `mamey_run.py`. Keep the original ZIP unchanged. Use a separate output directory for analyses.
Do not assume the archive filename is also its top-level directory name.

## 2. Create a Python environment

The package requires **Python 3.12 or newer**. These commands use a macOS/Linux shell:

```bash
python3 --version
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell. If your `python3` is too
old, select an installed Python 3.12-or-newer interpreter when creating the environment.
Use an isolated environment rather than overriding protection on a system-managed Python.

The editable install reads the core requirements from [pyproject.toml](../pyproject.toml):
`openpyxl`, `ijson`, `reportlab`, and `PyYAML`. Run the local launcher from this bundle even if
a `mamey` console command is already installed elsewhere.

## 3. Add the features you need

```bash
# Plotting, document export, and Biopython support
python -m pip install -e '.[figures,documents,bio]'
```

The `figures`, `documents`, and `bio` extras can also be installed individually; `.[all]` is
the combined convenience extra. Some workflows additionally require system tools or reference
datasets. Follow [PREREQUISITES](PREREQUISITES.md) and the
[external assets guide](EXTERNAL_ASSETS_GUIDE.md), then check the selected command's diagnostics.
Missing HMM evidence or another unavailable evidence channel must remain an explicit missing
state; a fallback does not establish that the unavailable scan ran.

For an offline installation, first obtain a complete compatible wheelhouse, including build
requirements, dependencies, and any selected extras. From the bundle root:

```bash
python -m pip install --no-index --find-links /path/to/wheels -e .
```

If you have the separate Sapote add-on archive, follow its inventory and platform requirements.
Its optional installer is `bash bundle_support/install_sapote_addons.sh`; it does not replace
checking the core installation. A Linux x86_64 `cp312` wheel is not a macOS arm64 wheel, and it
is not suitable for a different Python ABI. Do not rename wheel tags to make them appear compatible.

## 4. Confirm the local version and environment

```bash
python mamey_run.py start
python mamey_run.py doctor
python tools/sync_version.py --check
```

Read the diagnostics, including missing optional capabilities. A doctor result is an environment
check, not an analysis or a release approval.

## 5. Inspect and run an input

Mamey consumes an antiSMASH result ZIP; it does not run antiSMASH itself. Inspect the ZIP, bind
its metadata, then follow the [Quick Guide](GUIDE/02_Quick_Guide.md) for the extraction command,
validation, and handoff. Supply only known taxonomy and isolation-source metadata; preserve
uncertainty explicitly instead of inventing it.

## 6. Run the relevant tests

Install pytest separately in the same environment, then run:

```bash
python -m pip install pytest
python -m pytest -q --run-slow --run-network
```

The full profile above enables the slow/network partitions. Gated skips can remain for optional dependencies and
external fixtures. A skip is not a passed check. The explicit `--run-slow` and `--run-network`
flags enable their partitions; external inputs may still be required. Release validation follows
the [cut protocol](../CUT_PROTOCOL.md) and must retain exact commands, counts, and unresolved
holds. An interrupted suite is incomplete.

## Workspace and output locations

`mamey.workspace_root.workspace_root()` resolves `SAPOTE_WORKSPACE_ROOT`, then `SAPOTE_ROOT`,
then the current working directory. There is no required personal workspace path. Set a root
only when a workflow needs it, and use each command's explicit input and output options.
Do not assume this helper changes every command's output directory.
