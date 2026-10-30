# Prerequisites

Choose what you want to do before installing anything. Reading a saved package
needs only a browser and spreadsheet reader. Running Mamey needs Python 3.12 or
newer and the [core installation](INSTALL.md).

## Python environment

The core package installs `openpyxl`, `ijson`, `reportlab` and `PyYAML`.
Use the same environment for installation and the bundle launcher.

## Select Python extras by workflow

- `figures`: plots, gene diagrams and their GenBank parsing, including Biopython.
- `bio`: Biopython when you do not need plotting.
- `documents`: Word, PDF and image support for document workflows.
- `slides`: PowerPoint and plotting support for [strain slides](STRAIN_SLIDES.md).
- `render`: CairoSVG; install the native Cairo library too.
- `addons`: optional comparison and scanner bindings.
- `all`: the figure, document, slide, bio and render extras together; excludes
  `addons`, `test`, external programs and reference datasets.

[Install](INSTALL.md#3-add-the-features-you-need) shows the extra-selection syntax.

## External tools and data

A first extraction reads results that antiSMASH already made. It does not need
a local antiSMASH installation. Comparisons, protein searches and trees have
additional requirements listed in their guides:

- [Companion tools](COMPANION_TOOL_GUIDE.md) for programs and what each adds.
- [External assets](EXTERNAL_ASSETS_GUIDE.md) for databases.
- [BiG-SCAPE](BIGSCAPE_GCF_WORKFLOW.md) for gene-cluster families.
- [Phylogeny](PHYLO_AUTOPILOT_WORKFLOW.md) for tree inputs and software.
- [NP Atlas](NPATLAS_PROVISIONING.md) for structure data and optional RDKit.

The core PDF renderer uses ReportLab. Other rendering routes may need Cairo,
fonts or system tools; check the selected guide before installing them.

## Local collection map dependencies

Shapefile maps need `pyshp`, included in `figures`, and matching `.shp`, `.shx`,
`.dbf` and `.prj` files. The collection-site map expects geographic WGS84
coordinates and does not reproject them. Use that tool's input instructions
before supplying a basemap.

## R figure stack

Use R >= 4.3 for the [R figure workflows](R_FIGURE_WORKFLOWS.md).
Check the installed packages first:

```bash
Rscript bundle_support/install_r_figure_packages.R --check
```

`--check` reports missing packages without installing them. The core group is
required; other groups support trees, bioassay panels and extra chart styles.
The report names missing packages and the figures they affect.

<details>
<summary>Packages by figure group</summary>

| Group | Packages | What it adds | Required? |
|---|---|---|---|
| `core` | `ggplot2`, `ggtext`, `jsonlite`, `scales`, `dplyr`, `patchwork`, `ggrepel`, `svglite`, `systemfonts`, `xml2` | Every R figure. The shared minimum-text check uses `svglite`, `systemfonts` and `xml2`. | Yes |
| `trees` | `ape`, `ggtree`, `treeio`, `aplot`, `phangorn` | Phylogenetic tree figures (`phangorn`: midpoint rooting in the genome-tree renderer). `ggtree` and `treeio` come from Bioconductor and need system libraries (cairo, libuv), so this is the slowest group to install. | No |
| `bioassay` | `tidyr`, `png` | Bioassay panels. | No |
| `extras` | `ragg`, `ggchicklet`, `readxl` | PNG output for the genus-composition figures (`ragg`), and rounded bars in the BGC class-group chart (`ggchicklet`), and the readxl-based non-Streptomyces count figure (`readxl`). Without `ggchicklet`, that chart draws plain square bars with the same data, labels and colors. | No |

</details>

The installer normally attempts missing packages across all groups.
`--require trees` changes which missing packages fail the check; it does not
limit installation to tree packages. For offline setup, its `--from` option
uses the supplied package archives, including their dependencies.

## Offline and architecture-specific installation

Use the [offline install steps](INSTALL.md#offline-installation) with wheels for
this operating system, processor and Python version. Include build requirements
and the dependencies of your chosen extras. Do not copy a virtual environment
between different architectures.

For documents, the [wheelhouse preflight](INSTALL.md#optional-documents-wheelhouse-preflight)
checks whether the selected requirements resolve together. Check the actual
Word/PDF workflow after installation.

## Verify the capabilities you will use

```bash
python -m pip check
python mamey_run.py doctor
```

`pip check` finds incompatible installed dependencies. Doctor lists core checks
and missing optional features. Its [write test](INSTALL.md#doctor-scope-and-write-probe)
uses the program's `runs/` folder. Then try the small example in your chosen
guide before starting a large batch.

## Optional Barrnap

[Barrnap](BARRNAP.md) is an external rRNA annotation option. Its guide covers
setup; a first Mamey extraction does not require it.
