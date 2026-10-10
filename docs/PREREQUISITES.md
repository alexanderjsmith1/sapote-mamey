# PREREQUISITES — Sapote–Mamey v9.7.449

Start with [INSTALL](INSTALL.md) or the [complete walkthrough](MASTER_WALKTHROUGH.md). The package metadata in [pyproject.toml](../pyproject.toml) defines the supported Python version, core requirements and extras. Use the [README tool table](../README.md#tool-downloads-and-licenses) for upstream downloads and licenses.

## Python environment

Use Python **3.12 or newer**, pip, and an isolated virtual environment. Confirm `import ssl` succeeds before using HTTPS downloads or online searches. Use the same interpreter for installation and `mamey_run.py`; an unrelated installed console command may resolve to another bundle.

Core installation is `python -m pip install -e .`. It declares openpyxl, ijson, reportlab and PyYAML. The engine also carries a vendored ijson fallback; that does not remove the package manager's declared dependency when installing normally. Do not assume packages are preinstalled because a previous assistant environment included them.

## Select Python extras by workflow

| Extra | Use |
|---|---|
| `figures` | Matplotlib, NumPy, pandas, NetworkX and SciPy for plotting and network/cluster views |
| `documents` | Word/PDF and image-processing support used by document workflows |
| `slides` | python-pptx, Matplotlib, NumPy and Pillow for the [Strain slides builder](STRAIN_SLIDES.md) and protein PCoA panels; PDF conversion remains a separate step |
| `bio` | Biopython-backed parsing and workflows that require Bio APIs |
| `render` | CairoSVG support for conversion; a compatible native Cairo library is also needed |
| `addons` | Optional comparative/scanner Python bindings, including pyswrd, pyfastani, pyskani, pyhmmer and pyrodigal. These are distinct from external BLAST+, HMMER, Prodigal or DIAMOND executables and do not provision databases; follow the consuming workflow. |
| `all` | Convenience figure/document/slide/bio/render stack. It does not include the separate `addons` stack, RDKit, external binaries or datasets. |

For example: `python -m pip install -e '.[figures,documents,bio]'`. Some parsing paths have a built-in GBK shim, but this does not imply every biological workflow works without Biopython.

## External tools and data

Install only the toolchain required for the selected workflow, using its upstream installation instructions and license terms. BiG-SCAPE, HMMER, BLAST/DIAMOND, genome-comparison tools, and phylogenetic tools are separate from a core pip installation. Their reference databases must also be provisioned and versioned separately. Follow [external assets](EXTERNAL_ASSETS_GUIDE.md), [BiG-SCAPE](BIGSCAPE_GCF_WORKFLOW.md), and [phylogeny](PHYLO_AUTOPILOT_WORKFLOW.md).

Do not equate a full Pfam installation with a scanner-specific HMM panel: follow the consuming command's required panel and registry. Missing external evidence remains missing; a fallback output does not prove that scan ran.

The ReportLab-based PDF path is part of core dependencies. Alternate document routes may need pandoc, TeX, fonts or other native tools. Check the selected renderer's requirements before installing a large toolchain. CairoSVG additionally requires native Cairo; a successful Python import alone is not a conversion test. If PNG conversion is unavailable, preserve the renderer's explicit status and do not claim an unproduced PNG sibling.

## R figure stack

Use R >= 4.3 for the R figure workflows. The base installer checks `ggplot2`, `dplyr`, `tidyr`, `scales`, `patchwork`, `ape`, `ggrepel` (CRAN) and `ggtree`, `treeio` (Bioconductor). Install that base set with `Rscript bundle_support/install_r_figure_packages.R`; `--check` reports readiness for its listed packages without installing.

Renderer-specific prerequisites extend that list: **`svglite`** supplies the SVG device used by the figure workflows, and **`aplot`** is explicitly loaded by `tools/ggtree_rect_heatmap.R`. Provision them and their dependencies in the same R library used by the renderer. They may arrive transitively, but the base installer's successful check does not explicitly check them. Before choosing those renderers, check:

```bash
Rscript -e 'p <- c("svglite", "aplot"); ok <- vapply(p, requireNamespace, logical(1), quietly=TRUE); print(ok); if (!all(ok)) quit(status=2)'
```

This namespace check establishes package availability only; verify a small actual SVG/rectangular output for the selected renderer before scaling up. For an offline machine, download the package source archives yourself and run `--from <dir>`; no third-party package source ships in the bundle, and source builds still need their system dependencies. Missing packages produce a nonzero exit. `python mamey_run.py doctor` reports
whether `Rscript` is found; a missing package surfaces as an R error at render time, never as a figure.

## Offline and architecture-specific installation

Prepare a complete compatible wheelhouse for the target operating system, CPU architecture and Python ABI, including build requirements and chosen extras. Then use `python -m pip install --no-index --find-links /path/to/wheels -e .` from the bundle root. Inspect any supplied wheel inventory rather than assuming it matches this machine. Do not rename compatibility tags, override system-Python protections, or copy a virtual environment between architectures.

For the governed six-package document profile, see the [documents wheelhouse preflight](INSTALL.md#optional-documents-wheelhouse-preflight). Its separate per-requirement pip dry runs and optional mapped import checks are narrower than a complete fresh-environment installation. Keep build/extras/native-renderer requirements and actual selected workflow output checks separate; a receipt `PASS` is not a complete compatible-wheel inventory, an executed install or a rendered deliverable.

## Verify the capabilities you will use

Run `python -m pip check`, `python mamey_run.py start`, and `python mamey_run.py doctor`. Record missing optional items and check the chosen external tools with their own version and diagnostic commands. Verify an actual small output for the selected workflow before scaling it up.

`doctor --companions` covers the named companion registry, not every tool in the README. Barrnap, SeqKit, ITSx, BUSCO, compleasm and RDKit are not entries in that registry; check the selected owning guide and actual installation separately. RDKit is not declared by `.[all]` or another bundle extra; [NP Atlas provisioning](NPATLAS_PROVISIONING.md) separates its optional structure-rendering requirement from dataset provisioning.

Maintainers install pytest separately and use the complete configured test profile: `python -m pytest -q -p no:cacheprovider --run-slow --run-network`. See [the cut protocol](../CUT_PROTOCOL.md). Test counts change with the bundle, so use its validation receipt rather than a count copied into this guide. Skips and interrupted runs are not passes.

## Optional Barrnap

[Barrnap](BARRNAP.md) is an external rRNA annotation option in the marker/fungal guidance, not a core Mamey dependency or a universal phylogeny requirement. Check the installed version, dependencies and database/model before using a historical command. The marker planner prints a recipe; it does not run Barrnap.

Before `doctor`, review its [write-probe scope](INSTALL.md#doctor-scope-and-write-probe). Keep `runs/_doctor_probe` absent in the chosen editable installation; an existing probe file can be overwritten and removed. Its bundle-local write check does not validate every future output destination.
