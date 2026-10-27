# Install Sapote Mamey

This guide sets up the bundle you received. Start from the [README](../README.md) if you have
not read it. The [release manifest](../RELEASE_MANIFEST.md) gives the version, tier and status;
an unsealed candidate is not a signed public release. External data and some integration-test
fixtures are provisioned separately.

For a first extraction, complete steps 1–5 below with the selected antiSMASH result ZIP.
Choose optional dependencies in step 3 only for the task you plan to run. If you are
installing without internet access, use [the offline instructions](#offline-installation)
instead of the online pip commands. Check [what ships and what to supply](COMPANION_FILES.md#what-is-supplied)
before requesting another archive.

After setup, continue with [Your first extraction](reader/01_FIRST_RUN.md).

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

This step is optional. If your selected task uses only the core installation,
continue at step 4. The example below adds plotting, document export and Biopython
support; choose only the extras that your task needs.

```bash
# Optional example: plotting, document export, and Biopython support
python -m pip install -e '.[figures,documents,bio]'
```

The `figures`, `documents`, and `bio` extras can be installed one at a time. The `.[all]`
convenience extra combines `figures`, `bio`, `render`, `documents`, and `slides`; it does not
include `addons` or `test`. `figures` includes `dna-features-viewer` for gene-arrow
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

## 4. Confirm the local version and environment

Run `doctor` only in an editable working installation after checking its
[reserved write-probe path](#doctor-scope-and-write-probe). Do not run it in preserved
code evidence. If `runs/_doctor_probe` already exists, move that folder out of `runs/`
(keep it; do not delete it) before you run doctor.

```bash
python -B mamey_run.py start --no-doctor
python mamey_run.py doctor
python tools/sync_version.py --check
```

Read the diagnostics, including which optional capabilities are missing. `doctor` checks the
environment; it is not an analysis or a release approval.

## Doctor scope and write probe

`doctor` reports selected dependency names, executable discovery, dataset status and bundle-file presence. The Python check requires 3.12 or newer, matching `pyproject.toml`. Module discoverability and executable discovery do not prove a workflow produces valid output. Placement/R companion discovery requires regular executable files, but does not establish their version, architecture or valid output. Missing optional items and warnings remain relevant even when the command returns success. Verify the specific tool/data/renderer route you need rather than treating a “ready” line as end-to-end proof.

This command performs a write test beneath the bundle directory, using `runs/_doctor_probe/probe.txt`; `start` also runs it unless `--no-doctor` is supplied. It is not a purely read-only environment check. An occupied or symlink probe path is refused without touching its contents; a symlink `runs/` is also refused. Probe directory and file creation are exclusive. Cleanup removes only paths created by that invocation whose filesystem identity still matches, including a newly created `runs/` only when empty. A pre-existing `runs/` is preserved. Use an authorized editable working installation rather than preserved code evidence. The test checks the bundle's `runs/` location, not an arbitrary destination supplied to a later workflow.

For orientation, `python -B mamey_run.py start --no-doctor` skips the doctor probe and disables launcher cache writes on a cache-free tree. Untrusted/source-drift bytecode is refused without removal; valid bound caches may still be read. Normal bytecode-enabled mode can write the provenance marker or purge unbound caches, and explicit `--purge-bytecode` remains mutating. These controls do not suppress writes by doctor or other handlers. Verify integrated startup/import effects before describing an invocation as fully read-only; the launcher boundary alone is insufficient.

Keep the original bundle and source evidence intact. If the write check fails because `runs/_doctor_probe` already exists, doctor still runs its other checks. Keep its diagnostic text, look inside the folder, then move it out of `runs/` (keep it; do not delete it) and run doctor again. The reserved probe is created exclusively, with cleanup limited to paths created by that invocation; concurrent adversarial filesystem mutation is not a supported execution model.

Sources: `mamey/cli.py` (`doctor_command`, `_start_command`, `_placement_and_r_companion_status`) and `mamey_run.py` (`_refuse_foreign_bytecode`); the current installation/runtime requirement remains authoritative.

## 5. Inspect and run an input

Mamey takes an antiSMASH result ZIP; it does not run antiSMASH itself. Keep the environment
you just set up and continue with [Your first extraction](reader/01_FIRST_RUN.md). It covers
input inspection, extraction, validation and opening the results. To have an assistant run it
instead, use [the walkthrough request](MASTER_WALKTHROUGH.md#route-a-ask-your-assistant-to-run-it).
Supply only the taxonomy and isolation source you actually know; leave unknown metadata explicit.

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

## Offline installation

Create and activate the Python 3.12-or-newer environment from step 2, skipping its
online pip command. Obtain a complete, compatible wheelhouse containing build
requirements, dependencies and any selected extras. Run the following from the
bundle root with that environment active:

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

For an offline extras install, select the desired extras in the command above, for
example `-e '.[figures]'`, and supply their complete compatible wheel set, including
transitive dependencies. A Linux x86_64 `cp312` wheel is not a macOS arm64 wheel,
and a wheel for one Python ABI does not work on another. Do not rename wheel tags.

If you received a separate Sapote add-on archive, inspect its inventory and platform
requirements, then follow [the companion installer instructions](COMPANION_FILES.md#installation-and-companion-tool-boundaries).
That route pools wheels from multiple search roots, attempts the figure/analysis
group on a best-effort basis, and reports optional imports separately. A successful
core check does not establish that figure libraries installed or a renderer ran.
The normal route is offline; `--online` permits the documented missing-wheel fallback.

### Optional documents wheelhouse preflight

`tools/audit_documents_wheelhouse.py` checks the bundled `sapote_addons/profiles/documents.txt` against one selected wheel directory. That governed profile lists python-docx, lxml, PyYAML, reportlab, pypdf and Pillow; it does not cover every extra, build requirement, native renderer, font or external dataset. This lowercase dependency wheelhouse is distinct from the uppercase `Wheelhouse/` scanner/registry area.

From the bundle root, with the intended environment active and separately provisioned compatible wheels:

```bash
python tools/audit_documents_wheelhouse.py --wheelhouse ../document_wheels \
  --output ../review_output/documents_wheelhouse_new.json
```

Read the report before installing:

1. Confirm the interpreter: the default is the current Python; `--python` selects
   another interpreter by path.
2. Read both the per-requirement rows and `joint_resolution`. Aggregate `PASS`
   requires every direct resolution and the complete profile to resolve together,
   plus no failed mapped import check when requested. Passing individual rows alone
   does not establish a compatible complete profile.
3. Keep the reviewed wheel inventory and the actual selected-install result.
   This audit does not install dependencies or test a workflow. Each resolution uses
   the selected interpreter's pip with `--dry-run --ignore-installed --no-index
   --only-binary=:all:`; installed packages cannot satisfy it. The report schema is
   `sapote-documents-wheelhouse-audit-1.1`.

Use the governed version-bound profile for this offline check. Custom `--profile` files and direct API requirements accept distribution names with optional version clauses only. URLs, direct references, local paths, markers, extras and requirement-file directives are refused before resolution; this grammar is deliberately narrower than PEP 508. Full-line comments and whitespace-separated inline comments are supported. The resolver is invoked with `--isolated` and `PIP_CONFIG_FILE` set to the platform null device. Review wheel metadata independently: neither these pip controls nor the assigned `NO_INDEX_LOCAL_BINARY_WHEELS_ONLY` label establishes an operating-system network sandbox.

After an independently authorized offline install, `--check-imports` additionally checks imports in the selected interpreter for the six mapped distribution names. These checks inspect the currently installed environment, not the prospective wheel installation; they do not verify candidate wheel versions or renderer behavior. A custom unmapped distribution receives `NOT_MAPPED`, which does not fail the overall report; inspect every row rather than treating aggregate `PASS` as full import coverage. No PDF, Word or image is rendered by this helper.

The optional `--output` creates missing parent directories and directly replaces the selected JSON file, including on an audit failure. It does not guard source/output overlap or publish atomically; select a new receipt outside the profile, interpreter and wheel inputs. Without `--output`, JSON is printed to stdout. Normal aggregate `PASS` returns zero and `FAIL` returns one; a receipt-write failure can instead raise without the normal stdout result and leave a partial file. Preserve original inputs and partial receipts; retry to a new path after correcting the problem. The report records requirement strings, selected paths and short resolver/import tails, but no wheel/profile/interpreter content hashes or full dependency plan. Retain those evidence bindings separately. Source: `tools/audit_documents_wheelhouse.py` (`validate_requirement`, `audit_requirements` and `main`).

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
