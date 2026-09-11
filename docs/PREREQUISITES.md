# PREREQUISITES — Sapote–Mamey v9.7.428

Start with [INSTALL](INSTALL.md) or the [complete walkthrough](MASTER_WALKTHROUGH.md). The package metadata in [pyproject.toml](../pyproject.toml) defines the supported Python version, core requirements and extras. Use the [README tool table](../README.md#tool-downloads-and-licenses) for upstream downloads and licenses.

## Python environment

Use Python **3.12 or newer**, pip, and an isolated virtual environment. Confirm `import ssl` succeeds before using HTTPS downloads or online searches. Use the same interpreter for installation and `mamey_run.py`; an unrelated installed console command may resolve to another bundle.

Core installation is `python -m pip install -e .`. It declares openpyxl, ijson, reportlab and PyYAML. The engine also carries a vendored ijson fallback; that does not remove the package manager's declared dependency when installing normally. Do not assume packages are preinstalled because a previous assistant environment included them.

## Select Python extras by workflow

| Extra | Use |
|---|---|
| `figures` | Matplotlib, NumPy, pandas, NetworkX and SciPy for plotting and network/cluster views |
| `documents` | Word/PDF and image-processing support used by document workflows |
| `bio` | Biopython-backed parsing and workflows that require Bio APIs |
| `render` | CairoSVG support for conversion; a compatible native Cairo library is also needed |
| `all` | The combined convenience extra; external binaries and datasets remain separate |

For example: `python -m pip install -e '.[figures,documents,bio]'`. Some parsing paths have a built-in GBK shim, but this does not imply every biological workflow works without Biopython.

## External tools and data

Install only the toolchain required for the selected workflow, using its upstream installation instructions and license terms. BiG-SCAPE, HMMER, BLAST/DIAMOND, genome-comparison tools, and phylogenetic tools are separate from a core pip installation. Their reference databases must also be provisioned and versioned separately. Follow [external assets](EXTERNAL_ASSETS_GUIDE.md), [BiG-SCAPE](BIGSCAPE_GCF_WORKFLOW.md), and [phylogeny](PHYLO_AUTOPILOT_WORKFLOW.md).

Do not equate a full Pfam installation with a scanner-specific HMM panel: follow the consuming command's required panel and registry. Missing external evidence remains missing; a fallback output does not prove that scan ran.

The ReportLab-based PDF path is part of core dependencies. Alternate document routes may need pandoc, TeX, fonts or other native tools. Check the selected renderer's requirements before installing a large toolchain. CairoSVG additionally requires native Cairo; a successful Python import alone is not a conversion test. If PNG conversion is unavailable, preserve the renderer's explicit status and do not claim an unproduced PNG sibling.

## Offline and architecture-specific installation

Prepare a complete compatible wheelhouse for the target operating system, CPU architecture and Python ABI, including build requirements and chosen extras. Then use `python -m pip install --no-index --find-links /path/to/wheels -e .` from the bundle root. Inspect any supplied wheel inventory rather than assuming it matches this machine. Do not rename compatibility tags, override system-Python protections, or copy a virtual environment between architectures.

## Verify the capabilities you will use

Run `python -m pip check`, `python mamey_run.py start`, and `python mamey_run.py doctor`. Record missing optional items and check the chosen external tools with their own version and diagnostic commands. Verify an actual small output for the selected workflow before scaling it up.

Maintainers install pytest separately and use the complete configured test profile: `python -m pytest -q --run-slow --run-network`. See [the cut protocol](../CUT_PROTOCOL.md). Test counts change with the bundle, so use its validation receipt rather than a count copied into this guide. Skips and interrupted runs are not passes.
