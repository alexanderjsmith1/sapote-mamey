<!-- Mirror of docs/PREREQUISITES.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# PREREQUISITES — Sapote–Mamey v9.7.459

Start with [INSTALL](../docs/INSTALL.md) or the [complete walkthrough](../docs/MASTER_WALKTHROUGH.md). The package metadata in [pyproject.toml](../pyproject.toml) defines the supported Python version, core requirements and extras. Use the [README tool table](../README.md#tool-downloads-and-licenses) for upstream downloads and licenses.

## Choose the task before installing

| Your next task | Requirements and next guide |
|---|---|
| Read a saved package | A browser and a spreadsheet/table reader can open the saved outputs without Python. Start with [Read one saved package](../docs/reader/03_READ_RESULTS.md). |
| Extract a supplied antiSMASH ZIP | Configure the Python environment for that task using [Inputs and setup](../docs/reader/02_INPUTS_AND_SETUP.md), then follow [Your first extraction](../docs/reader/01_FIRST_RUN.md). Keep the input and output locations separate. |
| Add a figure, comparison or other optional result | Use the [task router](../docs/USER_TASK_ROUTER.md) to identify that workflow's inputs, Python extras, external executables and reference data. A core installation does not supply every optional capability. |

## Python environment

Use Python **3.12 or newer**, pip, and an isolated virtual environment. Confirm `import ssl` succeeds before using HTTPS downloads or online searches. Use the same interpreter for installation and `mamey_run.py`; an unrelated installed console command may resolve to another bundle.

Core installation is `python -m pip install -e .`. It declares openpyxl, ijson, reportlab and PyYAML. The engine also carries a vendored ijson fallback; that does not remove the package manager's declared dependency when installing normally.

## Select Python extras by workflow

| Extra | Use |
|---|---|
| `figures` | Matplotlib, NumPy, pandas, NetworkX, SciPy and scikit-learn for plotting and network/cluster views; DNA Features Viewer and pyCirclize for gene-arrow and atlas diagrams; Biopython for their GenBank parsing; pyshp (`shapefile`) for local Shapefile basemaps |
| `documents` | Word/PDF and image-processing support used by document workflows |
| `slides` | python-pptx, Matplotlib, NumPy and Pillow for the [Strain slides builder](../docs/STRAIN_SLIDES.md) and protein PCoA panels; PDF conversion remains a separate step |
| `bio` | Biopython-backed parsing and workflows that require Bio APIs. `figures` already includes Biopython; use `bio` alone when you do not need plotting. |
| `render` | CairoSVG support for conversion; a compatible native Cairo library is also needed |
| `addons` | Optional comparative/scanner Python bindings, including pyswrd, pyfastani, pyskani, pyhmmer and pyrodigal. These are distinct from external BLAST+, HMMER, Prodigal or DIAMOND executables and do not provision databases; follow the consuming workflow. |
| `all` | Convenience figure/document/slide/bio/render stack. It does not include the separate `addons` or `test` stacks, RDKit, external binaries or datasets. |

For example: `python -m pip install -e '.[figures,documents,bio]'`. Some parsing paths have a built-in GBK shim, but this does not imply every biological workflow works without Biopython.

## Local collection map dependencies

Local Shapefile basemaps use the `pyshp` distribution, imported as `shapefile`.
It is included in the optional `figures` extra and the `all` convenience extra.
For `tools/collection_site_map.py`, GeoJSON and no-basemap inputs do not need this
reader. Its Shapefile route requires supplied local `.shp`, `.shx`, `.dbf` and
`.prj` components with the documented geographic WGS84 coordinates; it performs
no projection conversion or basemap download. `tools/collection_map.py` always
requires local Shapefile basemaps and has its own input contract; do not assume
it performs the same CRS checks as `collection_site_map`.

Doctor only checks that a `shapefile` module can be found. Before relying on a
map route, import it and read a small Shapefile in the target environment. Offline
setup needs a compatible `pyshp` wheel in the figure dependency pool. No tested
PyShp version range is claimed.

## External tools and data

Install only the toolchain required for the selected workflow, using its upstream installation instructions and license terms. BiG-SCAPE, HMMER, BLAST/DIAMOND, genome-comparison tools, and phylogenetic tools are separate from a core pip installation. Their reference databases must also be provisioned and versioned separately. Follow [external assets](../docs/EXTERNAL_ASSETS_GUIDE.md), [BiG-SCAPE](../docs/BIGSCAPE_GCF_WORKFLOW.md), and [phylogeny](../docs/PHYLO_AUTOPILOT_WORKFLOW.md).

Do not equate a full Pfam installation with a scanner-specific HMM panel: follow the consuming command's required panel and registry. Missing external evidence remains missing; a fallback output does not prove that scan ran.

The ReportLab-based PDF path is part of core dependencies. Alternate document routes may need pandoc, TeX, fonts or other native tools. Check the selected renderer's requirements before installing a large toolchain. CairoSVG additionally requires native Cairo; a successful Python import alone is not a conversion test. If PNG conversion is unavailable, preserve the renderer's explicit status and do not claim an unproduced PNG sibling.

## R figure stack

Use R >= 4.3 for the R figure workflows. `bundle_support/install_r_figure_packages.R` reports packages in four groups. The core group is required by default; other groups support particular figure families. This is a failure policy, not a selective installer: the online installation route attempts missing packages across all groups. `--require trees` makes the trees group required as well; it does not limit installation to trees. Use `--check` first when you only want to inspect the configured environment.

| Group | Packages | What it adds | Required? |
|---|---|---|---|
| `core` | `ggplot2`, `ggtext`, `jsonlite`, `scales`, `dplyr`, `patchwork`, `ggrepel`, `svglite`, `systemfonts`, `xml2` | Every R figure. The shared minimum-text check uses `svglite`, `systemfonts` and `xml2`. | Yes |
| `trees` | `ape`, `ggtree`, `treeio`, `aplot`, `phangorn` | Phylogenetic tree figures (`phangorn`: midpoint rooting in the genome-tree renderer). `ggtree` and `treeio` come from Bioconductor and need system libraries (cairo, libuv), so this is the slowest group to install. | No |
| `bioassay` | `tidyr`, `png` | Bioassay panels. | No |
| `extras` | `ragg`, `ggchicklet`, `readxl` | PNG output for the genus-composition figures (`ragg`), and rounded bars in the BGC class-group chart (`ggchicklet`), and the readxl-based non-Streptomyces count figure (`readxl`). Without `ggchicklet`, that chart draws plain square bars with the same data, labels and colors. | No |

```bash
Rscript bundle_support/install_r_figure_packages.R --check             # inspect only; installs nothing
Rscript bundle_support/install_r_figure_packages.R                     # online install attempts all missing groups
Rscript bundle_support/install_r_figure_packages.R --require trees     # same install scope; also require trees
Rscript bundle_support/install_r_figure_packages.R --require all       # same install scope; require every group
```

What happens when something is missing:
- **A core package:** the installer exits with status 2. Fix this before drawing any R figure.
- **A package in another group:** the installer lists it as `not installed (optional)` and still succeeds. Only that group's figures are unavailable; everything else works.
- **With `--require <group>`:** a missing package in that group is listed as `MISSING`, and the installer exits with status 2.

`python mamey_run.py doctor` prints one line per group: ready, or which packages are missing, which figures that affects, and the command that fixes it.

`ggchicklet` is not on CRAN. The installer fetches its author's source archive, pinned to one commit, from `codeload.github.com`. No GitHub account or token is needed.

For an offline machine, supply the compatible package source archives and use `--from <dir>`. That route attempts every `.tar.gz` or `.zip` archive in the selected directory; `--require` still controls required groups rather than filtering those archives. Supply and review only the intended local archive set, including its dependencies. No third-party package source ships in the bundle, and source builds still need their system dependencies. A package check establishes namespace loading, not a rendered result; verify the selected figure route before scaling up.

## Offline and architecture-specific installation

Prepare a complete compatible wheelhouse for the target operating system, CPU architecture and Python ABI, including build requirements and chosen extras. Follow the complete [offline installation procedure](../docs/INSTALL.md#offline-installation) from the bundle root with the intended environment active. It includes pip configuration controls that an abbreviated install command can omit. Inspect any supplied wheel inventory rather than assuming it matches this machine. Do not rename compatibility tags, override system-Python protections, or copy a virtual environment between architectures.

For the governed six-package document profile, see the [documents wheelhouse preflight](../docs/INSTALL.md#optional-documents-wheelhouse-preflight). Read both the per-requirement rows and `joint_resolution`: aggregate `PASS` requires the requirements to resolve individually and together, plus no failed mapped import check when requested. The resolver checks fresh binary-wheel resolution without installing. Optional import checks inspect the currently installed environment, not the candidate wheels. Keep build requirements, other extras, native renderers, fonts and actual workflow outputs separate; this preflight does not establish a complete installation or a rendered deliverable.

## Verify the capabilities you will use

Run `python -m pip check` and use `python -B mamey_run.py start --no-doctor` for orientation. Before running `python mamey_run.py doctor`, read its [write-probe scope](../docs/INSTALL.md#doctor-scope-and-write-probe) and use a writable working installation. If `runs/_doctor_probe` already exists, doctor leaves it untouched and reports its write check as FAIL. Move the folder out of `runs/` (keep it; do not delete it), then run doctor again. Record missing optional items and check the chosen external tools with their own version and diagnostic commands. Verify an actual small output for the selected workflow before scaling it up.

`doctor --companions` covers the named companion registry, not every tool in the README. Barrnap, SeqKit, ITSx, BUSCO, compleasm and RDKit are not entries in that registry; check the selected owning guide and actual installation separately. RDKit is not declared by `.[all]` or another bundle extra; [NP Atlas provisioning](../docs/NPATLAS_PROVISIONING.md) separates its optional structure-rendering requirement from dataset provisioning.

Maintainers install pytest separately and use the complete configured test profile: `python -m pytest -q -p no:cacheprovider --run-slow --run-network`. See [the cut protocol](../CUT_PROTOCOL.md). Test counts change with the bundle, so use its validation receipt rather than a count copied into this guide. Skips and interrupted runs are not passes.

## Optional Barrnap

[Barrnap](../docs/BARRNAP.md) is an external rRNA annotation option in the marker/fungal guidance, not a core Mamey dependency or a universal phylogeny requirement. Check the installed version, dependencies and database/model before using a historical command. The marker planner prints a recipe; it does not run Barrnap.
