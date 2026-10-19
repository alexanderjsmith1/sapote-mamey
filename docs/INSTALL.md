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
combined convenience extra. `figures` includes `dna-features-viewer` for gene-arrow
diagrams, `pycirclize` for the native atlas route, and Biopython for those routes' GenBank
parsing. The `bio` extra remains a compatible way to request Biopython without plotting.
The two plotting libraries currently have no declared version interval; this is an optional
dependency declaration, not a tested compatibility range or a record of versions used.
Some workflows also need system tools or reference datasets. Follow
[PREREQUISITES](PREREQUISITES.md) and the [external assets guide](EXTERNAL_ASSETS_GUIDE.md), then
check the diagnostics of the command you want to use. If HMM evidence or another evidence
channel is unavailable, it stays recorded as missing; a fallback does not count as that scan
having run.

Local Shapefile basemaps use the `pyshp` distribution, imported as `shapefile`.
It is included in the optional `figures` extra and the `all` convenience extra.
For `tools/collection_site_map.py`, GeoJSON and no-basemap inputs do not need this
reader. Its Shapefile route requires supplied local `.shp`, `.shx`, `.dbf` and
`.prj` components with the documented geographic WGS84 coordinates; it performs
no projection conversion or basemap download. `tools/collection_map.py` always
requires local Shapefile basemaps and has its own input contract; do not assume
it performs the same CRS checks as `collection_site_map`.

Doctor reports only module-spec discovery through `find_spec`; a discoverable
`shapefile` module is not a verified import, parsed Shapefile or rendered map.
Offline setup needs a compatible `pyshp` wheel in the selected figure dependency
pool. No tested PyShp version interval is currently claimed. Verify an actual
import and a small Shapefile read/write case in the intended environment before
claiming that route is ready. A best-effort optional installer or successful core
installation does not establish map readiness.

For the [Strain slides builder](STRAIN_SLIDES.md), install its separate optional extra from this bundle root:

```bash
python -m pip install -e '.[slides]'
```

It adds the PowerPoint/plotting dependencies, not a PDF converter or reference datasets. The package's distribution name is `mamey`; `.[slides]` selects the extra from this local source and avoids assuming a different package named `sapote-mamey`.

**Offline install.** First obtain a complete, compatible wheelhouse: build requirements,
dependencies, and any extras you want. Then, from the bundle root:

This Bash subshell clears inherited pip settings before the core-only editable
install, so build-dependency children inherit the controlled configuration too:

```bash
(
  while IFS= read -r pip_env_name; do
    case "$pip_env_name" in PIP_*) unset -v "$pip_env_name" ;; esac
  done < <(compgen -e)
  export PIP_CONFIG_FILE=/dev/null
  python -m pip --isolated install --no-index --find-links /path/to/wheels -e .
)
```

For the bootstrap's test-dependency and all-extras attempt, use the same selected
active environment with `PYTHON="$(command -v python)" bash bootstrap.sh --wheels
/path/to/wheels`. Read its `ALL_EXTRAS` or `CORE_ONLY` result: a successful core
fallback does not admit all extras. Both routes require complete compatible
build/transitive wheels. Direct URL metadata and arbitrary backend network use
need separate review; pip configuration controls are not an OS network sandbox.

If you have the separate Sapote add-on archive, follow its inventory and platform requirements.
Its optional installer is `bash bundle_support/install_sapote_addons.sh`; still check the core
installation afterwards. That installer requests its figure/analysis group on a best-effort
basis and reports optional imports separately; a successful core check does not prove that
all figure libraries installed or a renderer ran. It uses an offline wheel pool by default;
`--online` explicitly permits the documented missing-wheel fallback. For an offline extras
install, select the desired extras in the command above, for example `-e '.[figures]'`,
and supply the complete compatible wheel set including transitive dependencies. A Linux x86_64 `cp312` wheel is not a macOS arm64 wheel, and a wheel for
one Python ABI does not work on another. Do not rename wheel tags to make them look compatible.

### Optional documents wheelhouse preflight

`tools/audit_documents_wheelhouse.py` checks the bundled `sapote_addons/profiles/documents.txt` against one selected wheel directory. That governed profile lists python-docx, lxml, PyYAML, reportlab, pypdf and Pillow; it does not cover every extra, build requirement, native renderer, font or external dataset. This lowercase dependency wheelhouse is distinct from the uppercase `Wheelhouse/` scanner/registry area.

From the bundle root, with the intended environment active and separately provisioned compatible wheels:

```bash
python tools/audit_documents_wheelhouse.py --wheelhouse ../document_wheels \
  --output ../review_output/documents_wheelhouse_new.json
```

The default target is the current Python; `--python` selects another interpreter by path. The audit invokes that interpreter's pip for each direct requirement and once for the complete profile together. Every resolution uses `--dry-run --ignore-installed --no-index --only-binary=:all:`, so already installed packages cannot satisfy these resolver checks. It does not install dependencies. The report uses schema `sapote-documents-wheelhouse-audit-1.1` and records `joint_resolution` separately from the per-requirement rows. Aggregate `PASS` requires all direct resolutions and the joint resolution to succeed, plus no failed mapped import check when requested. A per-row pass alone does not establish a compatible complete profile. Even joint success is a resolver result, not an installation or workflow test; retain an independently reviewed wheel inventory and actual selected-install result before describing an environment as usable.

Use the governed version-bound profile for this offline check. Custom `--profile` files and direct API requirements accept distribution names with optional version clauses only. URLs, direct references, local paths, markers, extras and requirement-file directives are refused before resolution; this grammar is deliberately narrower than PEP 508. Full-line comments and whitespace-separated inline comments are supported. The resolver is invoked with `--isolated` and `PIP_CONFIG_FILE` set to the platform null device. Review wheel metadata independently: neither these pip controls nor the assigned `NO_INDEX_LOCAL_BINARY_WHEELS_ONLY` label establishes an operating-system network sandbox.

After an independently authorized offline install, `--check-imports` additionally checks imports in the selected interpreter for the six mapped distribution names. These checks inspect the currently installed environment, not the prospective wheel installation; they do not verify candidate wheel versions or renderer behavior. A custom unmapped distribution receives `NOT_MAPPED`, which does not fail the overall report; inspect every row rather than treating aggregate `PASS` as full import coverage. No PDF, Word or image is rendered by this helper.

The optional `--output` creates missing parent directories and directly replaces the selected JSON file, including on an audit failure. It does not guard source/output overlap or publish atomically; select a new receipt outside the profile, interpreter and wheel inputs. Without `--output`, JSON is printed to stdout. Normal aggregate `PASS` returns zero and `FAIL` returns one; a receipt-write failure can instead raise without the normal stdout result and leave a partial file. Preserve original inputs and partial receipts; retry to a new path after correcting the problem. The report records requirement strings, selected paths and short resolver/import tails, but no wheel/profile/interpreter content hashes or full dependency plan. Retain those evidence bindings separately. Source: `tools/audit_documents_wheelhouse.py` (`validate_requirement`, `audit_requirements` and `main`).

## 4. Confirm the local version and environment

Run `doctor` only in an editable working installation after checking its
[reserved write-probe path](#doctor-scope-and-write-probe). Do not run that probe
against preserved code evidence or an occupied `runs/_doctor_probe` path.

```bash
python -B mamey_run.py start --no-doctor
python mamey_run.py doctor
python tools/sync_version.py --check
```

Read the diagnostics, including which optional capabilities are missing. `doctor` checks the
environment; it is not an analysis or a release approval.

## Doctor scope and write probe

`doctor` reports selected dependency names, executable discovery, dataset status and bundle-file presence. The Python check requires 3.12 or newer, matching `pyproject.toml`. Module discoverability and executable discovery do not prove a workflow produces valid output. Placement/R companion discovery requires regular executable files, but does not establish their version, architecture or valid output. Missing optional items and warnings remain relevant even when the command returns success. Verify the specific tool/data/renderer route you need rather than treating a “ready” line as end-to-end admission.

This command performs a write test beneath the bundle directory, using `runs/_doctor_probe/probe.txt`; `start` also runs it unless `--no-doctor` is supplied. It is not a purely read-only environment check. An occupied or symlink probe path is refused without touching its contents; a symlink `runs/` is also refused. Probe directory and file creation are exclusive. Cleanup removes only paths created by that invocation whose filesystem identity still matches, including a newly created `runs/` only when empty. A pre-existing `runs/` is preserved. Use an authorized editable working installation rather than preserved code evidence. The test checks the bundle's `runs/` location, not an arbitrary destination supplied to a later workflow.

For orientation, `python -B mamey_run.py start --no-doctor` skips the doctor probe and disables launcher cache writes on a cache-free tree. Untrusted/source-drift bytecode is refused without removal; valid bound caches may still be read. Normal bytecode-enabled mode can write the provenance marker or purge unbound caches, and explicit `--purge-bytecode` remains mutating. These controls do not suppress writes by doctor or other handlers. Verify integrated startup/import effects before describing an invocation as fully read-only; the launcher boundary alone is insufficient.

Keep the original bundle and source evidence intact. After a failed write probe, preserve its diagnostic text and inspect any residual probe path before retrying; do not remove a pre-existing directory merely to make the check pass. The reserved probe is created exclusively, with cleanup limited to paths created by that invocation; concurrent adversarial filesystem mutation is not a supported execution model.

Sources: `mamey/cli.py` (`doctor_command`, `_start_command`, `_placement_and_r_companion_status`) and `mamey_run.py` (`_refuse_foreign_bytecode`); the current installation/runtime requirement remains authoritative.

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
