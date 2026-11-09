# Sapote-Mamey

Sapote-Mamey is a Python-based analysis pipeline for actinomycete genomes, developed with assistance from large language models (LLMs). It was developed using genomes from common actinomycete genera, including Streptomyces, Micromonospora and Actinomadura.

Sapote-Mamey is under continuous development and can help users run research tools and interpret their outputs. Its development has involved providing antiSMASH results (downloaded ZIP files; antiSMASH is a program that finds biosynthetic gene clusters in genomes) to LLMs and using those results to refine the analysis and reporting workflows.

The analysis pipeline primarily works to interpret antiSMASH results into a user-friendly narrative and allows integration of other bioinformatics tools and other data streams provided by the user. The LLM environment gives the user flexibility to explore the antiSMASH output and other data however they choose. This dynamic interaction allows the potential to take the analysis in any direction. 

Common applications include helping the user understand which biosynthetic gene clusters (BGCs) a genome carries, what their genes resemble, and which regions deserve a closer look. It is built around actinomycete genomes and a user's genome can be compared with reference genomes. The options to do this include downloading related reference genomes and running antiSMASH on them, and a user can ask the LLM for assistance. The user or LLM can find related genomes based on phylogeny (16S BLAST results), related genomes obtained by clusterblast and knownclusterblast matches, or searching the genus name in NCBI Nucleotide database and ranking by size to find the appropriately sized assemblies (approximately 5 to 12 Mb depending on the genus). A score is a reason to inspect a region, not a measurement of antimicrobial activity.

Sapote Mamey has two main components. Mamey is the executable BGC-analysis module: extraction, evidence checks, tables
and analysis tools. Sapote is the interpretation and writing workflow: it takes those results into gene-by-gene
[Mode B](docs/GLOSSARY.md#14-mode-b) cards and reports. A generated table or template starts that review; it does not write
the interpretation for you.

From one antiSMASH result ZIP you can examine the genes and their reference matches, deepen
uncertain calls with BLASTp (a protein similarity search), and compare strains. Optional companion workflows add BiG-SCAPE
gene-cluster families, independently predicted GECCO evidence, and phylogenetic trees to the same evidence review and figure workflow.
You do not need every optional workflow to get a useful result. Mode B cards have sections for these extra data streams. A finished card fills each section or says why the evidence is missing.

For one short route from your input file to a checked result, see
[Start with your file](docs/READER_START_HERE.md). It covers a new extraction and reading a saved results package.

For a one-page map of the program's parts, inputs, and outputs, see
[What Sapote-Mamey offers](docs/PRODUCT_MAP.md).

## Platform compatibility and equal AI contribution credit

Sapote-Mamey is designed to work across Anthropic and OpenAI platforms. Browser access through
Claude.ai and ChatGPT works well for inspecting inputs, interpreting existing evidence, and drafting
bounded reports, subject to each service's upload, runtime, network, and session limits. The desktop
applications generally provide a stronger file-centered experience. For the fullest experience, the
project recommends Claude Code or Codex in a local project environment; those agent interfaces offer
the best compatibility with bundle tools, local data, databases, long-running commands, rendered
artifacts, and validation receipts.

**Equal AI contribution credit (50/50).** The Sapote-Mamey project credits
[Anthropic](https://www.anthropic.com/) and [OpenAI](https://openai.com/) as equal contributors—50%
each—to the AI-assisted development, testing, refinement, and documentation of this bundle.
Anthropic's contribution was made through Claude and Claude Code; OpenAI's contribution was made
through ChatGPT and Codex. This credit records the project's development history. It does not imply
sponsorship, endorsement, approval, ownership, or responsibility for scientific conclusions by
either company.

## Start in ChatGPT or Claude.ai

Many Sapote-Mamey review and reporting workflows can begin in a browser without a local
installation. Paste the repository link
[github.com/alexanderjsmith1/sapote-mamey](https://github.com/alexanderjsmith1/sapote-mamey)
into a new ChatGPT or Claude.ai conversation, state the analysis you want, and attach one or more
antiSMASH result ZIPs. For phylogeny, attach the sequence input you actually have, such as 16S
(ribosomal RNA marker gene) FASTA, an assembled genome FASTA or GenBank file, and the matching sample metadata. Raw sequencing
reads first need an appropriate assembly and quality-control route.

Ask the assistant to read `AGENTS.md`, this `README.md`, and
`skills/sapote-mamey/SKILL.md` before it begins. Tell it whether you authorize inspection only or
execution of the attached data. For every individual BGC, require the complete identity in the
order **strain / full node-or-contig / region / BGC alias**, and require source-backed uncertainty
and claim ceilings. A useful opening prompt is:

> Read the Sapote-Mamey repository instructions and inspect my attached files. I authorize analysis
> of these inputs. Preserve complete BGC identities and provenance, report evidence gaps, and do not
> treat similarity as product identity or production. Use the available execution tools for supported
> workflows; if a required runtime or database is unavailable, identify the exact local step instead
> of inventing a result.

Browser interfaces differ in file-size limits, runtimes, network access, and session persistence.
They can inspect inputs, interpret existing evidence, and prepare reports when those capabilities are
available. The deterministic Mamey engine, external phylogeny programs, large databases, and long
runs may still require a local Claude Code or Codex session, or a terminal environment. Download
the generated reports and receipts; a chat response alone is not a validated or sealed Mamey package (see [sealed package](docs/GLOSSARY.md#evidence-identity-portability-and-authority-vocabulary)).

**Start with the file you have:**

- An **antiSMASH result ZIP** → [Your first extraction](docs/reader/01_FIRST_RUN.md). To have an assistant run it, use [the walkthrough request](docs/MASTER_WALKTHROUGH.md#route-a-ask-your-assistant-to-run-it).
- A **Complete_Package ZIP** from an earlier run → [Read one saved package](docs/reader/03_READ_RESULTS.md).
- A **code ZIP** → [Install](#install) below.
- No antiSMASH ZIP yet → download one from the [public antiSMASH datasets](docs/PUBLIC_DATASETS.md) on Zenodo: 1,258 public genomes run with antiSMASH 8.0.4 at loose strictness.

## What you can do

| Your question | Workflow | What you get |
|---|---|---|
| What biosynthetic regions and genes are present? | Inspect and run an antiSMASH ZIP | Region inventory, assembly/boundary context, source scans, comparator evidence, triage board, workbook, and validated package |
| What do these proteins most closely resemble? | Export translated proteins for manual BLASTp, run an online search, or import saved results | Per-gene homology evidence to compare with antiSMASH annotations, domain architecture, and reference-cluster matches |
| Is a pathway split across contigs? | Review the extraction's [RG-GMCI](docs/GLOSSARY.md#7-rg-gmci-and-the-rescue-layer) fragment-linkage evidence | Candidate links supported by reference geometry, complementary gene coverage, and contig-boundary evidence, with contradictory or insufficient evidence retained |
| Which clusters belong to related families? | Run the integrated BiG-SCAPE companion on region GBKs (GenBank files) | Run-specific gene-cluster families in SQLite and, when available, matrix and gene-comparison widgets |
| How do biosynthetic features vary across a tree? | Route 16S sequences or build a genome tree, then supply matched annotation tracks | Trees with metadata or strain-level heatmap overlays, plus the data and methods needed to reproduce them |
| What does the combined evidence suggest? | Author and verify a Mode B card | A traceable gene-by-gene interpretation incorporating available protein, domain, cluster-family, and comparative evidence |

**Optional tools:** see the [tool downloads and licenses](#tool-downloads-and-licenses) table for external programs, what each adds, and official installation links. Add only the tools needed by your selected workflow.

## Beyond extraction

Each of these is optional and runs after a first run. Each guide gives the inputs, the commands and how to check the result.

| You want to | Command | Guide |
|---|---|---|
| Compare a region's proteins with NCBI (BLASTp) | `blastp-online`, `auto-blastp`, `ingest-blastp` | [Protein search](docs/ONLINE_BLASTP_PROTOCOL.md) |
| Group regions into gene-cluster families | `bigscape` | [BiG-SCAPE walkthrough](docs/BIGSCAPE_COHORT_WALKTHROUGH.md) |
| Check a split pathway across contigs (RG-GMCI, a reference-guided fragment check) | runs inside `run` | [Fragment review](docs/GUIDE/02_Quick_Guide.md#fragmented-pathway-review), [RG-GMCI reference](docs/reference/04_RGGMCI_ClusterBlast_Utilization.md) |
| Get a second opinion from GECCO, stage regions for mass-spec review, or read a two-proof rescue | `gecco-crosscheck`, `export-metabolomics`, `two-proof-rescue` | [Class-evidence commands](docs/COMPANION_CLASS_EVIDENCE.md) |
| Place a strain in a tree, or add tracks to one | `phylo-autopilot`, `phylo-mlsa`, `phylo-run` | [Phylogenetics workflow](docs/PHYLOGENETICS_WORKFLOW.md) |
| Write reports from a sealed package | `compile-report` and other readers | [Post-seal readers](docs/POSTSEAL_READERS.md) |
| Write a gene-by-gene Mode B card | `mode-b`, `emit-modeb-template`, `verify-modeb` | [Mode B walkthrough](docs/MODE_B_USER_WALKTHROUGH.md) |
| Draw bioassay figures | Figure Factory | [Bioassay figures](docs/BIOASSAY_FIGURE_FACTORY.md) |
| Make any other figure | `render-figures` and others | [Figures](docs/FIGURES_START_HERE.md) |

`blastp-online` and `auto-blastp --submit` upload the selected protein sequences to NCBI. A
live `auto-blastp` run also needs `--confirm-public-sequence-upload`.

None of these outputs establishes a compound, its production or its activity. A match is
a similarity, and a family is membership in one run at one cutoff.

## Install

> **Build status.** This CODE archive records its validation results in the release manifest. The footer of this file carries the exact bundle and engine versions, sourced from [`pyproject.toml`](pyproject.toml). [`RELEASE_MANIFEST.md`](RELEASE_MANIFEST.md) is the authoritative status source.
>
> GitHub source users: start with `docs/PUBLIC_RELEASE_GUIDE.md` for what ships, the Pfam HMM you provision yourself, the tool's runtime network behavior, and air-gapped operation. Full step-by-step setup is in `docs/INSTALL.md`.

### Python and dependencies

You need **Python 3.12 or newer**. Run these from the extracted directory that contains
`pyproject.toml` and `mamey_run.py`. Use a writable working installation. Before
running `doctor`, read its [write-probe boundary](docs/INSTALL.md#doctor-scope-and-write-probe).
If `runs/_doctor_probe` already exists, leave it where it is. Doctor does not touch it and
reports a failed write check. Use another working installation instead. Then run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python mamey_run.py start --no-doctor
python mamey_run.py doctor
```

These are macOS/Linux commands. On Windows, activate with `.venv\Scripts\Activate.ps1` in
PowerShell. The core dependencies are declared in [pyproject.toml](pyproject.toml): `openpyxl`,
`ijson`, `reportlab`, and `PyYAML`. Always use the local launcher (`python mamey_run.py`) so you
do not run some other installed version by mistake.

Optional features have named extras:

```bash
python -m pip install -e '.[figures,documents,bio]'
```

[INSTALL](docs/INSTALL.md) has the full setup, offline installation and platform-compatible
add-ons. [PREREQUISITES](docs/PREREQUISITES.md) covers companion tools and
[EXTERNAL ASSETS](docs/EXTERNAL_ASSETS_GUIDE.md) covers data provision. antiSMASH runs
separately; you give its result ZIP to Mamey. The core Python package does not install external
databases, system tools, or the curated Pfam HMM.

## Quickstart

[Your first run](docs/reader/01_FIRST_RUN.md) is the full recipe. In short, from the
program folder:

```bash
python mamey_run.py doctor
python mamey_run.py inspect path/to/EXAMPLE.zip
```

`inspect` prints a capped `run` command for that ZIP, which is a shorter run with no PDF
brief and no gene maps. The strain name comes from the file name, here `EXAMPLE`. Edit the
command's `--taxonomy` and `--source` lines to match your records, or delete them. `run`
refuses the text in angle brackets. Run the command, then check the package:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

`run` exits `0` when the package is complete. It exits `1` on a `[BLOCKING]` issue,
and `2` when it refuses a bad command line before starting, such as an unsafe strain name.
Unedited `<Genus species>` or `<isolation source>` text is refused with exit `1`. Open
`runs/EXAMPLE/package/OPEN_ME_FIRST.html` to see the results. A passing package means
the steps completed. It does not show that any cluster makes a compound.

The [Quick Guide](docs/GUIDE/02_Quick_Guide.md) covers package review and cohort work, and the
[Mode B walkthrough](docs/MODE_B_USER_WALKTHROUGH.md) covers writing a card. `python mamey_run.py --help` lists every command.

## Tool downloads and licenses

The [Companion Tool Guide](docs/COMPANION_TOOL_GUIDE.md) describes each tool, how to use it on
its own, and how it connects to Sapote–Mamey. The table below is the download and license
reference. It is not a requirement to install everything: install Python and the core package
first, then add only the companion tools your analysis needs.

The links go to the upstream project or installation page, where downloads and full license
texts are maintained. The listed license applies to the named upstream software; dependencies
and reference databases have their own terms. Check the license shipped with the version you
install. In practice: MIT, BSD, Apache, PSF and similar permissive licenses generally require you
to keep their copyright and license notices when redistributing the software. GPL and AGPL tools
carry source and license obligations when redistributed or modified; LGPL has its own linking and
redistribution conditions. External executables and native libraries require separate setup. Python bindings
and any supplied companion wheels have their own distribution notices; inspect the actual
bundle inventory before assuming a component is supplied or absent. "Public domain" applies to the named software, not automatically to
records in a database it searches. Follow the linked upstream text for the exact version and
distribution you use.

| Tool / official download or installation page | Needed for | Upstream license |
|---|---|---|
| [Python](https://www.python.org/downloads/) | Required runtime, Python 3.12 or newer | [PSF License and bundled notices](https://docs.python.org/3/license.html) |
| [antiSMASH](https://github.com/antismash/antismash#installation) | Generate the input results; a supplied result ZIP avoids a local antiSMASH installation | AGPL-3.0-or-later |
| [NCBI BLAST+](https://www.ncbi.nlm.nih.gov/books/NBK279690/) | Local protein/nucleotide searches and 16S routing; not needed merely to export FASTA or use the web runner | [NCBI public-domain software notice](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html) |
| [BiG-SCAPE 2](https://github.com/medema-group/BiG-SCAPE) | Optional gene-cluster family analysis; the seeded launcher `tools/bigscape_seeded.py` imports its `big_scape` Python module | AGPL-3.0 |
| [GECCO](https://github.com/zellerlab/GECCO) | Optional independent BGC predictions; [integration and supplied-result guidance](docs/companion_tools.md#gecco) | GPL-3.0-or-later; model/data terms separately |
| [HMMER](https://github.com/EddyRivasLab/hmmer) | Profile searches and pressed Pfam preparation for relevant companion workflows | [BSD-3-Clause](https://github.com/EddyRivasLab/hmmer/blob/master/LICENSE) |
| [clinker](https://github.com/gamcil/clinker#installation) | Optional gene-cluster comparison views | MIT |
| [DIAMOND](https://github.com/bbuchfink/diamond) | Optional accelerated local protein comparisons | GPL-3.0 |
| [BLAST+ `tblastn`](https://blast.ncbi.nlm.nih.gov/doc/blast-help/) | Optional translated search of a region's proteins against genomes, used by `tools/region_presence_survey.py` | Public domain (US government work) |
| [GToTree](https://github.com/AstrobioMike/GToTree) | Optional genome-marker phylogeny workflow | [MIT](https://github.com/AstrobioMike/GToTree); dependencies retain their own licenses |
| [Barrnap](https://github.com/tseemann/barrnap) | Optional rRNA annotation for marker workflows; [the bundled planner prints a recipe](docs/BARRNAP.md) | GPL-3.0; reference data retain their own terms |
| [SeqKit](https://github.com/shenwei356/seqkit) | Optional FASTA/FASTQ inspection and sequence-file preparation | MIT |
| [Prodigal](https://github.com/hyattpd/Prodigal) | Gene prediction where required by the selected genome workflow | GPL-3.0 |
| [MUSCLE](https://github.com/rcedgar/muscle) | Alignment in workflows configured for MUSCLE | [GPL-3.0 for the current upstream distribution](https://github.com/rcedgar/muscle/blob/main/LICENSE); verify the required CLI version |
| [MAFFT](https://mafft.cbrc.jp/alignment/software/index.html) | Alignment for the placement workflow | BSD for the core distribution; bundled extensions have separate terms |
| [trimAl](https://github.com/inab/trimal) | Alignment trimming in configured phylogenomic workflows | GPL-3.0 |
| [IQ-TREE 2](https://github.com/iqtree/iqtree2) | Maximum-likelihood genome-marker trees | GPL-2.0 |
| [FastTree](https://github.com/morgannprice/fasttree) | Tree inference when called by the selected companion | GPL-3.0 in the current upstream repository; check older distributions separately |
| [RAxML-NG](https://github.com/amkozlov/raxml-ng) | Reference backbone inference for placement | AGPL-3.0 |
| [EPA-ng](https://github.com/pierrebarbera/epa-ng) | Placement of query sequences on a reference tree | AGPL-3.0 |
| [gappa](https://github.com/lczech/gappa) | Phylogenetic placement processing | GPL-3.0 |
| [FastANI](https://github.com/ParBLiSS/FastANI) | Optional genome ANI comparisons | Apache-2.0 |
| [skani](https://github.com/bluenote-1577/skani) / [pyskani](https://github.com/althonos/pyskani) | Optional genome ANI and aligned-fraction comparisons; the in-process comparison uses the Python binding, not a required skani executable | MIT for both projects; vendored dependencies retain their own terms |
| [Pandoc](https://pandoc.org/installing.html) | Optional `md_to_docx.sh` Word route and alternate Markdown-to-PDF fallback; primary ReportLab rendering does not require it | [GPL, see upstream COPYING](https://github.com/jgm/pandoc/blob/main/COPYING.md); PDF engines separately licensed |
| [Cairo](https://cairographics.org/download/) | Native graphics library needed by the optional CairoSVG route; installing the Python extra alone may not supply it | [LGPL-2.1 or MPL-1.1](https://cairographics.org/), at the user's option; dependencies separately licensed |
| [librsvg / rsvg-convert](https://gnome.pages.gitlab.gnome.org/librsvg/devel-docs/product.html) | Alternative SVG-to-PDF/PNG converter for compiled reports when the preceding CairoSVG route is unavailable | See the selected upstream release's COPYING notices; verify distribution terms |
| [Inkscape](https://inkscape.org/release/) | Another SVG-to-PDF/PNG fallback for compiled reports; install only if selecting this conversion route | [Upstream COPYING](https://gitlab.com/inkscape/inkscape/-/blob/master/COPYING); retain selected-release and dependency notices |
| [R](https://www.r-project.org/) | Optional R plotting scripts | [GPL-2 or GPL-3](https://www.r-project.org/Licenses/) |
| [ITSx](https://microbiology.se/software/itsx/) | Optional fungal ITS identification/extraction in the [fungal workflow](docs/PHYLO_FUNGAL_WORKFLOW.md) | See `license.txt` in the upstream download; dependencies separately licensed |
| [BUSCO](https://busco.ezlab.org/) | Optional genome completeness and single-copy marker assessment in the fungal workflow | MIT software; BUSCO datasets have separate CC-BY-ND-4.0 terms |
| [compleasm](https://github.com/huangnengCSU/compleasm) | Optional genome completeness assessment in workflows selected for compleasm; retain its own run/model receipt | Apache-2.0; dependencies/data separately licensed |
| [NCBI Datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/) | Optional reference-genome and metadata retrieval for [genome-tree workflows](docs/GTOTREE_WORKFLOW.md); supplied local references can avoid downloading | See upstream software notices; retrieved records retain their source terms |
| [ggplot2](https://ggplot2.tidyverse.org/) | R plotting | MIT |
| [RDKit](https://github.com/rdkit/rdkit) | Optional rendering of a characterized reference structure in the [NP Atlas workflow](docs/NPATLAS_PROVISIONING.md); provisioning does not require it | BSD-3-Clause; dependencies separately licensed |
| [ggtree](https://bioconductor.org/packages/release/bioc/html/ggtree.html) | R tree visualization | Artistic-2.0 |
| [patchwork](https://patchwork.data-imaginist.com/) | R composite layouts | MIT |
| [svglite](https://svglite.r-lib.org/) | SVG output for R renderers using ggplot2's SVG device | GPL-2.0-or-later |
| Other R packages loaded by the shipped R scripts: ggrepel (non-overlapping labels), ggtext, ape, treeio, aplot, dplyr, tidyr, jsonlite, scales (axis and label formatting), readxl (reads the non-Streptomyces count inputs), ragg (PNG output), png (reads a rendered PNG to center bioassay panels), and ggchicklet (optional; rounded bars in the class-group figure, plain bars without it; not on CRAN, so the installer fetches its author's source archive from codeload.github.com, pinned to one commit) | `bundle_support/install_r_figure_packages.R` installs these together with the packages above; [Rscript](https://www.r-project.org/) runs every R renderer | ggrepel GPL-3; ggtext GPL-2; ape GPL-2 or GPL-3; treeio and aplot Artistic-2.0; dplyr, tidyr, jsonlite and ggchicklet MIT; ragg MIT; png GPL-2 or GPL-3 (from each package's installed DESCRIPTION) |
| [Poppler utilities](https://poppler.freedesktop.org/) (`pdftotext`, `pdfinfo`, `pdffonts`, `pdfimages`) | Checking compiled report PDFs: text, fonts, images and page counts | See upstream COPYING |
| `qlmanage` (macOS Quick Look, built in) | PNG preview of protein-space grid pages, rendered from the checked PDF; skipped when absent (the PDF and SVG are still written) | Part of macOS |
| [Google Chrome or Chromium](https://www.chromium.org/getting-involved/download-chromium/), headless | Printing HTML locus reading pages, clinker views and class heatmaps to PDF or PNG | See upstream terms for the browser you install |
| [wkhtmltopdf](https://wkhtmltopdf.org/) | One optional HTML-to-PDF fallback for briefs and chat exports | See upstream |
| [Graphviz](https://graphviz.org/download/) (`dot`) | Drawing workflow and cause-map diagrams | See upstream |
| [IQ-TREE 3](https://iqtree.github.io/) (`iqtree3`) | Recognized alongside IQ-TREE 2 for genome-marker trees | See upstream |
| [CheckM2](https://github.com/chklovski/CheckM2) | Optional genome completeness and contamination checks in planned tree runs and clade decontamination | See upstream |
| [DeepBGC](https://github.com/Merck/deepbgc) | Optional companion BGC caller, not run by the core workflow; its Pfam random-forest activity interface is declared only and is not operational | MIT (installed package metadata) |
| [BiG-SLiCE](https://github.com/medema-group/bigslice) | Optional queries against a BiG-SLiCE database (`tools/bigslice_query.py`) | See upstream |
| [cblaster](https://github.com/gamcil/cblaster) | Optional homologous gene-cluster search, registered as a companion tool | See upstream |
| [RiPPER](https://github.com/streptomyces/ripper) | Optional, experimental RiPP (ribosomally synthesized and post-translationally modified peptide) discovery adapter (`tools/ripper_*`); nothing runs without explicit opt-in | See upstream |
| [TriMap](https://github.com/eamid/trimap) | Optional alternative embedding for protein-space figures | Apache-2.0 (installed package metadata) |
| [SPAdes](https://github.com/ablab/spades) | Not run by the bundle; contig names in SPAdes style (`NODE_…_length_…`) are parsed from assemblies made upstream | See upstream |
| [Swift](https://www.swift.org/install/) (`swiftc`, macOS) | Optional on-device text recognition in `tools/figure_render_qc.py` | Apache-2.0 for the Swift toolchain; see upstream |
| [curl](https://curl.se/) | Web requests in the BLASTp crawl tools and the NCBI 16S search helper | curl license (MIT-style) |
| [pyGenomeViz](https://github.com/moshi4/pyGenomeViz) | Optional scriptable BGC locus figures (SVG/PDF), registered as a companion tool | See upstream |
| [GTDB-Tk](https://github.com/Ecogenomics/GTDBTk) | On request only: genome taxonomy against GTDB; needs the ~100 GB GTDB reference database and network access to fetch it | See upstream |
| [CORASON](https://github.com/nselem/corason) | Optional query-centered conserved-gene-core locus comparison; the registry pins a reviewed source and never installs or runs it | See upstream |
| [NPLinker](https://nplinker.github.io/nplinker/latest/) | Optional linking of genome-side families with your own MS observations; links need separate review | See upstream |
| [PRISM](https://prism.adapsyn.com/) | Optional class-level genome interpretation through its web service; no product prediction is adopted | See upstream terms |
| [GNPS / MASST](https://ccms-ucsd.github.io/GNPSDocumentation/toolindex/) | Optional MS/MS networking and similarity that you run; Mamey submits nothing | See upstream terms |
| [SIRIUS / CANOPUS](https://v6.docs.sirius-ms.io/) | Optional compound-class annotation of your MS/MS data; genome hypotheses are not CANOPUS predictions | See upstream terms |

Python libraries the optional workflows import, and the extra that installs each (licenses are listed in
[Third-Party Licenses](docs/THIRD_PARTY_LICENSES.md)):

| Extra | Libraries |
|---|---|
| `figures` | matplotlib, numpy, pandas, scipy, scikit-learn (imported as `sklearn`; t-SNE companion layout), networkx, pyshp, dna-features-viewer, pycirclize, Biopython |
| `documents` | python-docx, lxml, pypdf, Pillow, markdown |
| `slides` | python-pptx, matplotlib, numpy, Pillow |
| `render` | CairoSVG, with its tinycss2 dependency (the PDF preparer also uses tinycss2 to check CSS `url()` references in SVG figures; without it, an SVG with CSS urls is refused with `PDF_SVG_CSS_PARSER_UNAVAILABLE`) |
| `addons` | pyrodigal, pyfastani, pyswrd, pyhmmer, pyskani and the other `pyproject.toml` add-ons |
| `test` | pytest, build, pdfplumber, psutil |
| not in any extra; install only if wanted | pypdfium2 (PDF page images for interactive-figure bridges), certifi (extra TLS certificates for reference-metadata lookups in `tools/resolve_reference_metadata.py`), diamond4py (in-process DIAMOND alignment), RDKit (structure drawing, above) |

Core Python dependencies install with `python -m pip install -e .`:
[openpyxl](https://pypi.org/project/openpyxl/) (MIT),
[ijson](https://pypi.org/project/ijson/) (BSD-3-Clause for current upstream; the vendored copy retains its own notice),
[ReportLab](https://pypi.org/project/reportlab/) (BSD), and
[PyYAML](https://pypi.org/project/PyYAML/) (MIT).
The optional Python figures and documents packages install through the extras above; their
license inventory is in [Third-Party Licenses](docs/THIRD_PARTY_LICENSES.md). This table covers
direct workflow tools, not every transitive library their package managers install.

### External reference datasets

The repository ships small, versioned lookup tables and positive-control extracts used by the
engine. It does not ship the full Pfam, MIBiG, UniProt/Swiss-Prot, nr, ClusteredNR, RefSeq, or
16S collections. Record the exact dataset release, download date and file hashes you used. A data
license governs reuse; a scientific citation documents which resource informed the work. Do both
when the resource asks for attribution.

| Resource | Used for | What the terms mean for this workflow |
|---|---|---|
| [Pfam](https://pfam-docs.readthedocs.io/en/latest/pfam.html) | Protein-domain HMMs; obtain the release and press it with HMMER | [CC0 1.0](https://www.ebi.ac.uk/interpro/about/license/): the downloadable Pfam data can be reused without a legal attribution requirement. Cite Pfam/InterPro as scientific practice and retain the release identity. |
| [MIBiG](https://mibig.secondarymetabolites.org/) | Experimentally supported reference biosynthetic clusters and their metadata | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): attribution is required. Cite MIBiG, link the license when redistributing adapted content, and identify changes. |
| [UniProt / Swiss-Prot](https://www.uniprot.org/help/downloads) | Reviewed protein-reference evidence | [CC BY 4.0](https://www.uniprot.org/help/license/) applies to copyrightable database content: attribution is required. UniProt also notes that patents or other third-party rights may apply to some records. |
| [NCBI BLAST databases](https://www.ncbi.nlm.nih.gov/books/NBK62345/) | nr, ClusteredNR, RefSeq protein, and 16S reference searches | [BLAST software is public domain](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html). Treat database content separately: retain the exact database name/date and record-level source identifiers, cite the contributing resources, and review the notices supplied with the selected database. |

### Online services

Some optional workflows contact these services. The core extraction runs offline. Sending sequences to a
public service discloses them to that service. The BLASTp submission commands refuse to upload without `--confirm-public-sequence-upload`.

| Service | Used for | Notes |
|---|---|---|
| [antiSMASH web server](https://antismash.secondarymetabolites.org/) | Producing the antiSMASH result ZIP that Mamey reads; links in package reports | Submitted by the user; Mamey does not upload genomes |
| [MIBiG downloads](https://dl.secondarymetabolites.org/) | Fetching MIBiG reference records (`tools/fetch_mibig_reference.py`) | Record the MIBiG release used |
| [NCBI BLAST web service](https://blast.ncbi.nlm.nih.gov/) | `blastp-online`, `auto-blastp` and the BLASTp crawl tools (nr, ClusteredNR) | Uploads selected protein sequences; requires `--confirm-public-sequence-upload` |
| [EMBL-EBI BLAST service](https://www.ebi.ac.uk/Tools/sss/ncbiblast/) | Fallback BLASTp route (`mamey/blastp_ebi.py`) when NCBI is unreachable; one job per protein | Uploads selected protein sequences |
| [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) (`eutils.ncbi.nlm.nih.gov`) | Sequence and metadata lookups for references, 16S searches and alignment helpers | Follow NCBI's usage policy and rate limits |
| [NCBI Datasets](https://www.ncbi.nlm.nih.gov/datasets/) | Reference-genome and metadata retrieval (CLI listed above) | Retrieved records keep their source terms |
| [NP Atlas](https://www.npatlas.org/) | Optional natural-product reference records (see the NP Atlas workflow) | Record the release used |
| [TYGS](https://tygs.dsmz.de/) (DSMZ) | Type-strain genome comparisons; the bundle reads TYGS result tables you download | Submitted by the user |
| [BacDive](https://bacdive.dsmz.de/) (DSMZ) | Strain metadata looked up by culture-collection number | Used for display metadata only |
| [GTDB](https://gtdb.ecogenomic.org/) | Taxonomy and marker references for genome trees (via GToTree) | Record the GTDB release used |

Keep database versions and hashes with the analysis. Installing the Python package does not
download these databases or install the external binaries. Run
`python mamey_run.py doctor --companions` to check the analysis machine, and use the
[installation guide](docs/INSTALL.md) for the bundle setup.

## Repository layout

- `mamey/` — the deterministic engine (extraction, gating, figures; vendored `ijson` under `_vendor/`).
- `tools/` — release, audit, and authoring utilities.
- `bundle_support/` — add-on installer, registry inventories, and reusable templates.
- `debugging_modules/` — audit and debugging protocols.
- `docs/` — the operating contracts (Mode B, deliverables, claim-safety) and reference material; start at `docs/BUNDLE_CAPABILITIES.md`.
- `skills/sapote-mamey/` — the detailed operating discipline referenced by the shared assistant contract.
- `tests/` — the regression suite (`python -m pytest`).

## Using with an AI assistant

[AGENTS.md](AGENTS.md) is the portable operating contract for coding assistants. For an authorized execution task, `python mamey_run.py start` reports the loaded version and workflow. For inspection or document review, read the files and bind the source without installing or running the reviewed code. `CLAUDE.md` is a byte-identical copy of AGENTS.md for assistants that look
for that filename; it defines no separate startup path, and other assistants are not assumed to
find it. Point ChatGPT, Gemini, or any other assistant at `AGENTS.md`, or supply it through that
product's instruction mechanism. `skills/sapote-mamey/SKILL.md` holds the detailed Mode B and
audit disciplines.

## Citation-Compact Provenance and Citation Status

Sapote-Mamey uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the producing check reported structural success. Citation-compact QA checks its encoded citation-coverage and caveat rules; it does not validate every package artifact or verify primary literature. Read the named producer’s receipt and run package validation separately.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another literature session — a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope.

## Data availability

Before you share data, check the exact tier's inventory, the release manifest and the disclosure
decisions. A CODE candidate's filename, a strain prefix, or a local test pass does not establish
public-release authority. Keep private or unpublished material out of public artifacts and
preserve source attribution.

## Scientific integrity

Report the exact metric and evidence scope: sequence identity is an alignment measurement, while KnownClusterBlast (KCB) scores and reference matches do not establish compound identity. A BGC prediction alone does not demonstrate production or activity; stronger attribution requires experimental evidence specifically linked to that locus. The linter, package claim-safety gate and Mode B structure gate provide scoped heuristic checks, not universal enforcement or scientific certification. Retain findings and source review for each claim.

## Citation

If you use Sapote-Mamey, please cite it (see `CITATION.cff`) and antiSMASH 8.0 (Blin et al.). BGC detection depends on antiSMASH; interpretation depends on this pipeline.

## License

Code is released under the MIT License (`LICENSE`), © 2026 Alexander J. Smith. Documentation is covered by `LICENSE-DOCS.txt`. Bundled third-party code and its licenses are listed in `docs/THIRD_PARTY_LICENSES.md`.

## Practical help

- [Find the right document](docs/DOCUMENTATION_MAP.md)
- [Troubleshooting](docs/COMMON_MISTAKES.md)
- [Files, storage and handoff](docs/FILES_STORAGE_AND_HANDOFF.md)

## Choose a task by name

Use [Choose a task](docs/USER_TASK_ROUTER.md) to turn your request into a named workflow, required inputs, owning guide and reviewable outputs. Assistants can use its [JSON routes](docs/USER_TASK_ROUTER.json), under the scope and source rules in [AGENTS.md](AGENTS.md).

---
*Current bundle: sapote-mamey-v9.7.464 / engine 1.9.180 · build 20261108v97464a · release profile: CODE (see RELEASE_MANIFEST.md)*
