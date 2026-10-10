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

For the [Strain slides builder](STRAIN_SLIDES.md), install its separate optional extra from this bundle root:

```bash
python -m pip install -e '.[slides]'
```

It adds the PowerPoint/plotting dependencies, not a PDF converter or reference datasets. The package's distribution name is `mamey`; `.[slides]` selects the extra from this local source and avoids assuming a different package named `sapote-mamey`.

**Offline install.** First obtain a complete, compatible wheelhouse: build requirements,
dependencies, and any extras you want. Then, from the bundle root:

```bash
python -m pip install --no-index --find-links /path/to/wheels -e .
```

If you have the separate Sapote add-on archive, follow its inventory and platform requirements.
Its optional installer is `bash bundle_support/install_sapote_addons.sh`; still check the core
installation afterwards. A Linux x86_64 `cp312` wheel is not a macOS arm64 wheel, and a wheel for
one Python ABI does not work on another. Do not rename wheel tags to make them look compatible.

### Optional documents wheelhouse preflight

`tools/audit_documents_wheelhouse.py` checks the bundled `sapote_addons/profiles/documents.txt` against one selected wheel directory. That governed profile lists python-docx, lxml, PyYAML, reportlab, pypdf and Pillow; it does not cover every extra, build requirement, native renderer, font or external dataset. This lowercase dependency wheelhouse is distinct from the uppercase `Wheelhouse/` scanner/registry area.

From the bundle root, with the intended environment active and separately provisioned compatible wheels:

```bash
python tools/audit_documents_wheelhouse.py --wheelhouse ../document_wheels \
  --output ../review_output/documents_wheelhouse_new.json
```

The default target is the current Python; `--python` selects another interpreter by path. The audit invokes that interpreter's pip once per direct requirement with dry-run, no-index and binary-only flags. It does not install the dependencies. Each row reports that separate resolver return code, not a verified joint installation or complete wheel inventory. Already installed packages can satisfy a resolver check; there is no `--ignore-installed` in this command. A per-row `PASS` therefore does not prove a matching wheel is present in the chosen directory or that the complete profile and its transitive dependencies can be installed together into a fresh environment. Retain an independently reviewed compatible wheel inventory and complete selected-install result before describing an environment as usable.

Use the governed version-bound profile for this offline check. Custom `--profile` files are only lightly parsed; URL/direct-reference requirements can be forwarded to pip despite `--no-index`, and `#` fragments are stripped as comments. The report's assigned `NO_INDEX_LOCAL_BINARY_WHEELS_ONLY` label is not an independent network-containment check. Do not use unreviewed remote/direct-reference requirements in an offline task.

After an independently authorized offline install, `--check-imports` additionally checks imports in the selected interpreter for the six mapped distribution names. These checks do not verify installed versions or renderer behavior. A custom unmapped distribution receives `NOT_MAPPED`, which does not fail the overall report; inspect every row rather than treating aggregate `PASS` as full import coverage. No PDF, Word or image is rendered by this helper.

The optional `--output` creates missing parent directories and directly replaces the selected JSON file, including on an audit failure. It does not guard source/output overlap or publish atomically; select a new receipt outside the profile, interpreter and wheel inputs. Without `--output`, JSON is printed to stdout. Normal aggregate `PASS` returns zero and `FAIL` returns one; a receipt-write failure can instead raise without the normal stdout result and leave a partial file. Preserve original inputs and partial receipts; retry to a new path after correcting the problem. The report records requirement strings, selected paths and short resolver/import tails, but no wheel/profile/interpreter content hashes or full dependency plan. Retain those evidence bindings separately. Source: `tools/audit_documents_wheelhouse.py:24–175`.

## 4. Confirm the local version and environment

Run `doctor` only in an editable working installation after checking its
[reserved write-probe path](#doctor-scope-and-write-probe). Do not run that probe
against preserved code evidence or an occupied `runs/_doctor_probe` path.

```bash
python mamey_run.py start
python mamey_run.py doctor
python tools/sync_version.py --check
```

Read the diagnostics, including which optional capabilities are missing. `doctor` checks the
environment; it is not an analysis or a release approval.

## Doctor scope and write probe

`doctor` reports selected dependency names, executable discovery, dataset status and bundle-file presence. Finding a module does not prove it imports or that its workflow produces valid output. Its Python diagnostic uses an older threshold than the current installation requirement; follow the selected bundle's declared Python minimum. Missing optional items and warnings remain relevant even when the command returns success. Verify the specific tool/data/renderer route you need rather than treating a “ready” line as end-to-end admission.

This command performs a write test beneath the bundle directory, using `runs/_doctor_probe/probe.txt`. It is not a purely read-only environment check. Before running it, confirm that `runs/_doctor_probe` does not already exist. A pre-existing `probe.txt` can be overwritten and deleted, and an emptied probe directory can be removed. If that reserved path exists or the bundle is preserved evidence/read-only, keep it untouched and choose an authorized editable working installation for diagnostics. The test checks the bundle's `runs/` location, not an arbitrary destination supplied to a later workflow.

Keep the original bundle and source evidence intact. After a failed write probe, preserve its diagnostic text and inspect any residual probe path before retrying; do not remove a pre-existing directory merely to make the check pass. The source-owner repair is a uniquely allocated temporary probe with cleanup limited to files created by that invocation.

Sources: `mamey/cli.py:4744–4865`; the current installation/runtime requirement remains authoritative.

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

`mamey.workspace_root.workspace_root()` uses `SAPOTE_WORKSPACE_ROOT` first, then
`SAPOTE_ROOT`. Without either override, it searches the current directory and its
ancestors for the nearest directory containing `miniconda3/`, `blast_dbs/` or
`Tools/databases/`; only when no marker exists does it keep the current directory.
Marker presence does not establish project or evidence identity. Set an explicit
workspace when choosing a particular project, and use each command’s input/output
options. This helper does not change every command’s output directory.

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
