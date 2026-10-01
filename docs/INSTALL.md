# Install Sapote Mamey

This guide sets up the bundle you received. Start from the [README](../README.md) if you have
not read it. The [release manifest](../RELEASE_MANIFEST.md) gives the version, tier and status;
an unsealed candidate is not a signed public release. External data and some integration-test
fixtures are provisioned separately.

For the full analysis sequence, see [the Master Walkthrough](MASTER_WALKTHROUGH.md).

## 1. Open the bundle root

Extract the ZIP to a writable directory and go into the directory that contains
`pyproject.toml` and `mamey_run.py`. The archive filename is not necessarily its top-level
directory name, so look. Keep the original ZIP unchanged and use a separate output directory
for analyses.

## 2. Create a Python environment

You need **Python 3.12 or newer**. These commands use a macOS/Linux shell:

```bash
python3 --version
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell. If your `python3` is too
old, point `venv` at an installed Python 3.12-or-newer interpreter. Use an isolated environment
like this one rather than overriding protection on a system-managed Python.

The editable install reads the core requirements from [pyproject.toml](../pyproject.toml):
`openpyxl`, `ijson`, `reportlab`, and `PyYAML`. Always run the local launcher
(`python mamey_run.py`) from this bundle, even if a `mamey` console command is installed
somewhere else.

## 3. Add the features you need

```bash
# Plotting, document export, and Biopython support
python -m pip install -e '.[figures,documents,bio]'
```

The `figures`, `documents`, and `bio` extras can be installed one at a time; `.[all]` is the
combined convenience extra. Some workflows also need system tools or reference datasets. Follow
[PREREQUISITES](PREREQUISITES.md) and the [external assets guide](EXTERNAL_ASSETS_GUIDE.md), then
check the diagnostics of the command you want to use. If HMM evidence or another evidence
channel is unavailable, it stays recorded as missing; a fallback does not count as that scan
having run.

**Offline install.** First obtain a complete, compatible wheelhouse: build requirements,
dependencies, and any extras you want. Then, from the bundle root:

```bash
python -m pip install --no-index --find-links /path/to/wheels -e .
```

If you have the separate Sapote add-on archive, follow its inventory and platform requirements.
Its optional installer is `bash bundle_support/install_sapote_addons.sh`; still check the core
installation afterwards. A Linux x86_64 `cp312` wheel is not a macOS arm64 wheel, and a wheel for
one Python ABI does not work on another. Do not rename wheel tags to make them look compatible.

## 4. Confirm the local version and environment

```bash
python mamey_run.py start
python mamey_run.py doctor
python tools/sync_version.py --check
```

Read the diagnostics, including which optional capabilities are missing. `doctor` checks the
environment; it is not an analysis or a release approval.

## 5. Inspect and run an input

Mamey takes an antiSMASH result ZIP; it does not run antiSMASH itself. Inspect the ZIP, bind its
metadata, then follow the [Quick Guide](GUIDE/02_Quick_Guide.md) for the extraction command,
validation and handoff. Supply only the taxonomy and isolation source you actually know; if you
do not know them, say so rather than inventing them.

## 6. Optional: developer tests

You do not need the test suite to read a result package. For code changes, install pytest in the
environment and run the tests relevant to the change:

```bash
python -m pip install pytest
python -m pytest -q path/to/relevant_test.py
```

Replace the path with the real test file. The full release profile adds `--run-slow` and
`--run-network`, which enable the slow and network partitions; use them only when that work and
network access are intended. They are not first-run setup steps, and external inputs may still
be required. Gated skips can remain for optional dependencies and external fixtures; a skip is
not a passed check, and an interrupted suite is incomplete. Release validation follows the
[cut protocol](../CUT_PROTOCOL.md) and must keep the exact commands, counts and unresolved holds.

## Workspace and output locations

`mamey.workspace_root.workspace_root()` resolves `SAPOTE_WORKSPACE_ROOT`, then `SAPOTE_ROOT`,
then the current working directory. There is no required personal workspace path. Set a root
only when a workflow needs it, and use each command's explicit input and output options. This
helper does not change every command's output directory.

## Reader package homes and assembly authority

Built-in package homes match case-insensitively. Archive and excluded home names and nested directories do not compete with active built-in homes.
Set `MAMEY_PACKAGE_HOMES` to additional root-relative or absolute glob patterns, separated by the platform path separator.
For example, `MAMEY_PACKAGE_HOMES="results/packages"` adds a local results home. Clear the resolver cache after new packages arrive.

An optional owner table at `OFFICIAL_DATA/ASSEMBLY_AUTHORITY.tsv`, or `SAPOTE_ASSEMBLY_AUTHORITY`, admits current packages.
Required columns are `strain`, `authoritative_contigs`, `authoritative_genome_bp`, `clean_package`, and `clean_antismash_zip`.
Paths may be root-relative or absolute; a nominated package must match the strain and both assembly metrics.
Optional `antismash_flavor` binds the clean antiSMASH ZIP for a flavor-specific request.
An invalid configured table fails closed. A nominated package that is missing or mismatched is not replaced by an older raw package.
Without a nominated package, owner-matched candidates prefer parsed engine version, then bundle version and path.
Without an owner row, the legacy highest-bundle-version order remains. This orders only discovered ZIPs;
use a nominated package or configured home for results outside built-in homes.
Metrics are not sequence-hash proof. Populate and review the table before relying on it for assembly custody.
The resolver never creates or changes the table, and reports authority status and searched homes in its descriptor.
