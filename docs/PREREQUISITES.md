# PREREQUISITES — Sapote–Mamey v9.7.455

Start with [INSTALL](INSTALL.md) or the [complete walkthrough](MASTER_WALKTHROUGH.md). The package metadata in [pyproject.toml](../pyproject.toml) defines the supported Python version, core requirements and extras. Use the [README tool table](../README.md#tool-downloads-and-licenses) for upstream downloads and licenses.

## Python environment

Use Python **3.12 or newer**, pip, and an isolated virtual environment. Confirm `import ssl` succeeds before using HTTPS downloads or online searches. Use the same interpreter for installation and `mamey_run.py`; an unrelated installed console command may resolve to another bundle.

Core installation is `python -m pip install -e .`. It declares openpyxl, ijson, reportlab and PyYAML. The engine also carries a vendored ijson fallback; that does not remove the package manager's declared dependency when installing normally. Do not assume packages are preinstalled because a previous assistant environment included them.

## Select Python extras by workflow

| Extra | Use |
|---|---|
| `figures` | Matplotlib, NumPy, pandas, NetworkX and SciPy for plotting and network/cluster views; pyshp (`shapefile`) for local Shapefile basemaps |
| `documents` | Word/PDF and image-processing support used by document workflows |
| `slides` | python-pptx, Matplotlib, NumPy and Pillow for the [Strain slides builder](STRAIN_SLIDES.md) and protein PCoA panels; PDF conversion remains a separate step |
| `bio` | Biopython-backed parsing and workflows that require Bio APIs |
| `render` | CairoSVG support for conversion; a compatible native Cairo library is also needed |
| `addons` | Optional comparative/scanner Python bindings, including pyswrd, pyfastani, pyskani, pyhmmer and pyrodigal. These are distinct from external BLAST+, HMMER, Prodigal or DIAMOND executables and do not provision databases; follow the consuming workflow. |
| `all` | Convenience figure/document/slide/bio/render stack. It does not include the separate `addons` stack, RDKit, external binaries or datasets. |

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

Doctor reports only module-spec discovery through `find_spec`; a discoverable
`shapefile` module is not a verified import, parsed Shapefile or rendered map.
Offline setup needs a compatible `pyshp` wheel in the selected figure dependency
pool. No tested PyShp version interval is currently claimed. Verify an actual
import and a small Shapefile read/write case in the intended environment before
claiming that route is ready. A best-effort optional installer or successful core
installation does not establish map readiness.

## External tools and data

Install only the toolchain required for the selected workflow, using its upstream installation instructions and license terms. BiG-SCAPE, HMMER, BLAST/DIAMOND, genome-comparison tools, and phylogenetic tools are separate from a core pip installation. Their reference databases must also be provisioned and versioned separately. Follow [external assets](EXTERNAL_ASSETS_GUIDE.md), [BiG-SCAPE](BIGSCAPE_GCF_WORKFLOW.md), and [phylogeny](PHYLO_AUTOPILOT_WORKFLOW.md).

Do not equate a full Pfam installation with a scanner-specific HMM panel: follow the consuming command's required panel and registry. Missing external evidence remains missing; a fallback output does not prove that scan ran.

The ReportLab-based PDF path is part of core dependencies. Alternate document routes may need pandoc, TeX, fonts or other native tools. Check the selected renderer's requirements before installing a large toolchain. CairoSVG additionally requires native Cairo; a successful Python import alone is not a conversion test. If PNG conversion is unavailable, preserve the renderer's explicit status and do not claim an unproduced PNG sibling.

## R figure stack

Use R >= 4.3 for the R figure workflows. One script installs the R packages: `bundle_support/install_r_figure_packages.R`. The packages come in four groups. Only the core group is required. Each other group adds one family of figures, and you can skip it if you do not draw those figures.

| Group | Packages | What it adds | Required? |
|---|---|---|---|
| `core` | `ggplot2`, `ggtext`, `jsonlite`, `scales`, `dplyr`, `patchwork`, `ggrepel`, `svglite`, `systemfonts`, `xml2` | Every R figure. The shared minimum-text check uses `svglite`, `systemfonts` and `xml2`. | Yes |
| `trees` | `ape`, `ggtree`, `treeio`, `aplot` | Phylogenetic tree figures. `ggtree` and `treeio` come from Bioconductor and need system libraries (cairo, libuv), so this is the slowest group to install. | No |
| `bioassay` | `tidyr`, `png` | Bioassay panels. | No |
| `extras` | `ragg`, `ggchicklet` | PNG output for the genus-composition figures (`ragg`), and rounded bars in the BGC class-group chart (`ggchicklet`). Without `ggchicklet`, that chart draws plain square bars with the same data, labels and colors. | No |

```bash
Rscript bundle_support/install_r_figure_packages.R                     # core required; tries every other group
Rscript bundle_support/install_r_figure_packages.R --require trees     # also fail if a tree package is missing
Rscript bundle_support/install_r_figure_packages.R --require all       # every group required (what GitHub CI uses)
Rscript bundle_support/install_r_figure_packages.R --check             # report only; installs nothing
```

What happens when something is missing:
- **A core package:** the installer exits with status 2. Fix this before drawing any R figure.
- **A package in another group:** the installer lists it as `not installed (optional)` and still succeeds. Only that group's figures are unavailable; everything else works.
- **With `--require <group>`:** a missing package in that group is listed as `MISSING`, and the installer exits with status 2.

`python mamey_run.py doctor` prints one line per group: ready, or which packages are missing, which figures that affects, and the command that fixes it.

`ggchicklet` is not on CRAN. The installer fetches its author's source archive, pinned to one commit, from `codeload.github.com`. No GitHub account or token is needed.

For an offline machine, download the package source archives yourself and run `--from <dir>`. No third-party package source ships in the bundle, and source builds still need their system dependencies. A package check shows only that the package loads; render a small figure of the type you need before scaling up.

## Offline and architecture-specific installation

Prepare a complete compatible wheelhouse for the target operating system, CPU architecture and Python ABI, including build requirements and chosen extras. Then use `python -m pip install --no-index --find-links /path/to/wheels -e .` from the bundle root. Inspect any supplied wheel inventory rather than assuming it matches this machine. Do not rename compatibility tags, override system-Python protections, or copy a virtual environment between architectures.

For the governed six-package document profile, see the [documents wheelhouse preflight](INSTALL.md#optional-documents-wheelhouse-preflight). Its separate per-requirement pip dry runs and optional mapped import checks are narrower than a complete fresh-environment installation. Keep build/extras/native-renderer requirements and actual selected workflow output checks separate; a receipt `PASS` is not a complete compatible-wheel inventory, an executed install or a rendered deliverable.

## Verify the capabilities you will use

Run `python -m pip check`, `python mamey_run.py start`, and `python mamey_run.py doctor`. Record missing optional items and check the chosen external tools with their own version and diagnostic commands. Verify an actual small output for the selected workflow before scaling it up.

`doctor --companions` covers the named companion registry, not every tool in the README. Barrnap, SeqKit, ITSx, BUSCO, compleasm and RDKit are not entries in that registry; check the selected owning guide and actual installation separately. RDKit is not declared by `.[all]` or another bundle extra; [NP Atlas provisioning](NPATLAS_PROVISIONING.md) separates its optional structure-rendering requirement from dataset provisioning.

Maintainers install pytest separately and use the complete configured test profile: `python -m pytest -q -p no:cacheprovider --run-slow --run-network`. See [the cut protocol](../CUT_PROTOCOL.md). Test counts change with the bundle, so use its validation receipt rather than a count copied into this guide. Skips and interrupted runs are not passes.

## Optional Barrnap

[Barrnap](BARRNAP.md) is an external rRNA annotation option in the marker/fungal guidance, not a core Mamey dependency or a universal phylogeny requirement. Check the installed version, dependencies and database/model before using a historical command. The marker planner prints a recipe; it does not run Barrnap.

Before `doctor`, review its [write-probe scope](INSTALL.md#doctor-scope-and-write-probe). Keep `runs/_doctor_probe` absent in the chosen editable installation; the diagnostic refuses an occupied probe location and preserves it. Its bundle-local write check does not validate every future output destination.
