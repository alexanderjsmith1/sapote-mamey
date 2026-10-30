# Choose a companion tool

Find the tool for your next analysis and its download link. Start with a question
and the input files listed by that workflow. A first Mamey extraction needs only
the [core installation](INSTALL.md); add other tools when you need their results.

Genome assembly and antiSMASH run upstream. Protein searches, cluster comparisons
and trees add evidence later. R libraries draw selected results. The descriptions
below explain where each tool fits; [run contracts](COMPANION_RUN_CONTRACTS.md)
give the detailed input and write rules.

Use the [download table](#tool-downloads-and-licenses) for project sites and licenses.
Record the installed version and selected database release with a run.

## Choose a stage

### Python — the runtime for Mamey

Runs Mamey and its Python libraries. Use the environment installed for this bundle and launch from the program folder. [Install](INSTALL.md) covers setup.

### Galaxy — an upstream workflow service or local platform

Runs upstream analysis workflows through a hosted or local Galaxy installation. Download the completed analysis files and their parameters before starting Mamey.

### SPAdes — genome assembly upstream of this program

Assembles sequencing reads into contigs. Run antiSMASH on the assembly, then give Mamey the full antiSMASH result ZIP. Save the assembly and assembly settings for later comparisons.

### antiSMASH — produces the annotated input archive

Finds candidate biosynthetic regions and annotates genes. Mamey reads its result archive rather than running antiSMASH itself. Download the full archive, including JSON, logs and text comparisons; see [input contents](ANTISMASH_INPUTS_CONSUMED.md).

### NCBI web BLASTp — remote protein similarity search

Searches protein sequences against a remote NCBI database. You can import saved results with the [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md). Live submission sends the selected sequences outside your computer; review the query list first.

### NCBI BLAST+ — the local search programs

Runs BLAST searches locally against a selected database. Supply the database files as well as the program. Save raw alignments, database version and query-to-locus mapping when importing results.

### EMBL-EBI Job Dispatcher — a separate remote protein-search channel

Offers remote protein searches through EMBL-EBI. Keep its results labeled with their database and search channel when importing them; the [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) covers supported formats.

### DIAMOND — accelerated protein comparisons

Accelerates protein comparisons. Pairwise comparison selects DIAMOND when available through `diamond4py` or a command-line executable. Check the row backend and log for the aligner used. [Pairwise comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md) explains inputs and coverage.

### HMMER — profile-based protein-domain search

Searches sequences with profile hidden Markov models, including Pfam profiles. Install the model library separately and record the model release and search thresholds.

### pyhmmer — access to HMMER operations from Python

Exposes HMMER operations to Python. The selected scanner needs a working Python library and its model files. Use the scanner-specific guide to choose those inputs.

### BiG-SCAPE — gene-cluster family analysis

Groups selected biosynthetic regions into gene-cluster families. Supply region GenBank files and the required Pfam data; [the cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md) covers staging, clustering and reading the families.

### clinker — gene-cluster comparison pictures

Draws gene-cluster comparisons with protein-similarity links. Supply the selected GenBank records and keep each label mapped to its complete locus identity. The comparison picture helps inspect gene order and shared genes.

### GToTree — coordinates a genome-marker phylogeny workflow

Coordinates marker identification and alignment across a genome panel. [The GToTree workflow](GTOTREE_WORKFLOW.md) separates panel preparation, tree planning and execution. Choose the genomes and marker model before running it.

### Prodigal — predicts protein-coding genes

Predicts protein-coding genes for workflows that need translated proteins from genome sequences. Preserve the prediction settings and identifiers linking proteins to their source genomes.

### MAFFT — aligns sequences or adds queries to an alignment

Aligns sequences or adds queries to an existing alignment. The chosen tree or placement workflow determines the mode and reference alignment. Inspect alignment coverage before building a tree.

### MUSCLE — another multiple-sequence alignment tool

Builds multiple-sequence alignments. Some genome-marker routes use it as a companion; follow the selected workflow rather than substituting it for another aligner.

### trimAl — selects alignment columns for downstream analysis

Selects alignment columns before tree inference. Save both original and trimmed alignments, along with the trimming settings, so the retained sites can be checked.

### IQ-TREE — maximum-likelihood tree inference

Infers maximum-likelihood trees from alignments. Record the selected model, support method, seed and thread count with the tree. The [GToTree guide](GTOTREE_WORKFLOW.md) provides the supported genome-tree route.

### FastTree — approximate maximum-likelihood tree inference

Builds approximate maximum-likelihood trees. Some companion workflows use it for rapid tree construction; keep the method identified when comparing those trees with other inferences.

### RAxML-NG — reference-tree inference

Infers reference trees used by supported phylogenetic workflows. Keep the alignment, model, tree and tip roster together so later placement uses the matching reference set.

### EPA-ng — places queries onto a fixed reference tree

Places aligned query sequences onto an existing reference tree. It needs the matching reference alignment, tree and model; use the [phylogeny workflow](PHYLO_AUTOPILOT_WORKFLOW.md) to select a supported route.

### gappa — processes phylogenetic placements

Summarizes and processes phylogenetic placement files. Keep the original placement output and query mapping with the summaries used in a figure.

### FastANI — whole-genome nucleotide similarity

Compares whole-genome nucleotide similarity from genome FASTAs. Read alignment fraction together with ANI and confirm that both FASTAs are the intended assemblies.

### skani / pyskani — another genome-similarity route

Provides another genome-similarity backend. Follow the selected comparison route and record which backend actually ran; thresholds and output fields belong to that method.

### R — the optional statistical and plotting environment

Runs the optional R analysis and plotting scripts. [R figure workflows](R_FIGURE_WORKFLOWS.md) lists supported plots and [Prerequisites](PREREQUISITES.md) lists package groups.

### ggplot2 — constructs R figures from data and mappings

Builds R plots from tables and aesthetic mappings. Use the bundle renderer and theme for the selected figure, and keep the plotted table with the output.

### ggtree — displays trees with matched annotations

Displays phylogenetic trees with tip annotations and tracks. Match the annotation rows to the tree tips and check missing taxa, ordering and legend scales.

### patchwork — arranges multiple R plot panels

Arranges R plot panels into a combined figure. Inspect the complete layout at its intended reading size, including labels and legends.

### svglite — writes SVG graphics from R

Exports R figures as SVG. Keep the source data and rendering script with the export; fonts and layout should be checked in the final viewer.

## Reference databases are a separate choice

Pfam supplies protein-family models. MIBiG supplies curated cluster references.
UniProt/Swiss-Prot, nr, ClusteredNR and RefSeq offer different protein collections.
A local 16S workflow needs its selected reference sequences and taxon roster.
Install the dataset required by your workflow as well as the tool that reads it.

## Before using a companion

Identify the question, input files, database, output folder and expected result.
Check whether the command runs an analysis or prepares/imports files. Save the
command, versions, input hashes and output log with the result.

<a id="hand-a-selected-question-to-a-companion-tool"></a>

## Prepare the inputs

For protein and domain searches, provide query sequences with their source
identities. For a region, use **strain / full node-or-contig / region / BGC alias**;
for a gene, also keep its locus tag. Save coverage and search status beside scores.

For cluster comparisons, select the region GenBank files and preserve their
labels. For trees or ANI, choose the genome/sequence panel, references and any
outgroup. Keep the alignment and tree settings with the output. For figures,
provide the intended table, units and missing-value meanings, then inspect the
finished plot.

## Tool downloads and licenses

[PyYAML](https://pyyaml.org/) reads the bundle's YAML configuration and is a core dependency.

| Tool / official download or installation page | Needed for | Upstream license |
|---|---|---|
| [Python](https://www.python.org/downloads/) | Required runtime, Python 3.12 or newer | [PSF License and bundled notices](https://docs.python.org/3/license.html) |
| [antiSMASH](https://github.com/antismash/antismash#installation) | Generate the input results; a supplied result ZIP avoids a local antiSMASH installation | AGPL-3.0-or-later |
| [NCBI BLAST+](https://www.ncbi.nlm.nih.gov/books/NBK279690/) | Local protein/nucleotide searches and 16S routing | [NCBI public-domain software notice](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html) |
| [BiG-SCAPE 2](https://github.com/medema-group/BiG-SCAPE) | Optional gene-cluster family analysis; the seeded launcher `tools/bigscape_seeded.py` imports its `big_scape` Python module | AGPL-3.0 |
| [GECCO](https://github.com/zellerlab/GECCO) | Optional independent BGC predictions; [integration and supplied-result guidance](companion_tools.md#gecco) | GPL-3.0-or-later; model/data terms separately |
| [HMMER](https://github.com/EddyRivasLab/hmmer) | Profile searches and pressed Pfam preparation for relevant companion workflows | [BSD-3-Clause](https://github.com/EddyRivasLab/hmmer/blob/master/LICENSE) |
| [clinker](https://github.com/gamcil/clinker#installation) | Optional gene-cluster comparison views | MIT |
| [DIAMOND](https://github.com/bbuchfink/diamond) | Optional accelerated local protein comparisons | GPL-3.0 |
| [BLAST+ `tblastn`](https://blast.ncbi.nlm.nih.gov/doc/blast-help/) | Optional translated search of a region's proteins against genomes, used by `tools/region_presence_survey.py` | Public domain (US government work) |
| [GToTree](https://github.com/AstrobioMike/GToTree) | Optional genome-marker phylogeny workflow | [MIT](https://github.com/AstrobioMike/GToTree); dependencies keep their own licenses |
| [Barrnap](https://github.com/tseemann/barrnap) | Optional rRNA annotation for marker workflows; [the bundled planner prints a recipe](BARRNAP.md) | GPL-3.0; reference data keep their own terms |
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
| [skani](https://github.com/bluenote-1577/skani) / [pyskani](https://github.com/althonos/pyskani) | Optional genome ANI and aligned-fraction comparisons; the in-process comparison uses the Python binding, not a required skani executable | MIT for both projects; vendored dependencies keep their own terms |
| [Pandoc](https://pandoc.org/installing.html) | Optional `md_to_docx.sh` Word route and alternate Markdown-to-PDF fallback | [GPL, see upstream COPYING](https://github.com/jgm/pandoc/blob/main/COPYING.md); PDF engines separately licensed |
| [Cairo](https://cairographics.org/download/) | Native graphics library needed by the optional CairoSVG route; installing the Python extra alone may not supply it | [LGPL-2.1 or MPL-1.1](https://cairographics.org/), at the user's option; dependencies separately licensed |
| [librsvg / rsvg-convert](https://gnome.pages.gitlab.gnome.org/librsvg/devel-docs/product.html) | Alternative SVG-to-PDF/PNG converter for compiled reports when the preceding CairoSVG route is unavailable | See the selected upstream release's COPYING notices; verify distribution terms |
| [Inkscape](https://inkscape.org/release/) | Another SVG-to-PDF/PNG fallback for compiled reports; install only if selecting this conversion route | [Upstream COPYING](https://gitlab.com/inkscape/inkscape/-/blob/master/COPYING); keep selected-release and dependency notices |
| [R](https://www.r-project.org/) | Optional R plotting scripts | [GPL-2 or GPL-3](https://www.r-project.org/Licenses/) |
| [ITSx](https://microbiology.se/software/itsx/) | Optional fungal ITS identification/extraction in the [fungal workflow](PHYLO_FUNGAL_WORKFLOW.md) | See `license.txt` in the upstream download; dependencies separately licensed |
| [BUSCO](https://busco.ezlab.org/) | Optional genome completeness and single-copy marker assessment in the fungal workflow | MIT software; BUSCO datasets have separate CC-BY-ND-4.0 terms |
| [compleasm](https://github.com/huangnengCSU/compleasm) | Optional genome completeness assessment in workflows selected for compleasm; keep its own run/model receipt | Apache-2.0; dependencies/data separately licensed |
| [NCBI Datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/) | Optional reference-genome and metadata retrieval for [genome-tree workflows](GTOTREE_WORKFLOW.md); supplied local references can avoid downloading | See upstream software notices; retrieved records keep their source terms |
| [ggplot2](https://ggplot2.tidyverse.org/) | R plotting | MIT |
| [RDKit](https://github.com/rdkit/rdkit) | Optional rendering of a characterized reference structure in the [NP Atlas workflow](NPATLAS_PROVISIONING.md); provisioning does not require it | BSD-3-Clause; dependencies separately licensed |
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
[Third-Party Licenses](THIRD_PARTY_LICENSES.md)):

| Extra | Libraries |
|---|---|
| `figures` | matplotlib, numpy, pandas, scipy, scikit-learn (imported as `sklearn`; t-SNE companion layout), networkx, pyshp, dna-features-viewer, pycirclize, Biopython |
| `documents` | python-docx, lxml, pypdf, Pillow, markdown |
| `slides` | python-pptx, matplotlib, numpy, Pillow |
| `render` | CairoSVG |
| `addons` | pyrodigal, pyfastani, pyswrd, pyhmmer, pyskani and the other `pyproject.toml` add-ons |
| `test` | pytest, build, pdfplumber, psutil |
| not in any extra; install only if wanted | pypdfium2 (PDF page images for interactive-figure bridges), certifi (extra TLS certificates for reference-metadata lookups in `tools/resolve_reference_metadata.py`), diamond4py (in-process DIAMOND alignment), RDKit (structure drawing, above) |

Core Python dependencies install with `python -m pip install -e .`:
[openpyxl](https://pypi.org/project/openpyxl/) (MIT),
[ijson](https://pypi.org/project/ijson/) (BSD-3-Clause for current upstream; the vendored copy retains its own notice),
[ReportLab](https://pypi.org/project/reportlab/) (BSD), and
[PyYAML](https://pypi.org/project/PyYAML/) (MIT).
The optional Python figures and documents packages install through the extras above; their
license inventory is in [Third-Party Licenses](THIRD_PARTY_LICENSES.md). This table covers direct workflow tools.

### External reference datasets

The repository ships small, versioned lookup tables and positive-control extracts used by the
engine. It does not ship the full Pfam, MIBiG, UniProt/Swiss-Prot, nr, ClusteredNR, RefSeq, or
16S collections. Record the exact dataset release, download date and file hashes you used. A data
license governs reuse; a scientific citation documents which resource informed the work. Do both
when the resource asks for attribution.

| Resource | Used for | What the terms mean for this workflow |
|---|---|---|
| [Pfam](https://pfam-docs.readthedocs.io/en/latest/pfam.html) | Protein-domain HMMs; obtain the release and press it with HMMER | [CC0 1.0](https://www.ebi.ac.uk/interpro/about/license/): the downloadable Pfam data can be reused without a legal attribution requirement. Cite Pfam/InterPro as scientific practice and keep the release identity. |
| [MIBiG](https://mibig.secondarymetabolites.org/) | Experimentally supported reference biosynthetic clusters and their metadata | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): attribution is required. Cite MIBiG, link the license when redistributing adapted content, and identify changes. |
| [UniProt / Swiss-Prot](https://www.uniprot.org/help/downloads) | Reviewed protein-reference evidence | [CC BY 4.0](https://www.uniprot.org/help/license/) applies to copyrightable database content: attribution is required. UniProt also notes that patents or other third-party rights may apply to some records. |
| [NCBI BLAST databases](https://www.ncbi.nlm.nih.gov/books/NBK62345/) | nr, ClusteredNR, RefSeq protein, and 16S reference searches | [BLAST software is public domain](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html). Treat database content separately: keep the exact database name/date and record-level source identifiers, cite the contributing resources, and review the notices supplied with the selected database. |

### Online services

Some optional workflows contact these services. The core extraction runs offline. Sending sequences to a
public service discloses them to that service. The BLASTp submission commands refuse to upload without `--confirm-public-sequence-upload`.

| Service | Used for | Notes |
|---|---|---|
| [antiSMASH web server](https://antismash.secondarymetabolites.org/) | Producing the antiSMASH result ZIP that Mamey reads; links in package reports | Submitted by the user |
| [MIBiG downloads](https://dl.secondarymetabolites.org/) | Fetching MIBiG reference records (`tools/fetch_mibig_reference.py`) | Record the MIBiG release used |
| [NCBI BLAST web service](https://blast.ncbi.nlm.nih.gov/) | `blastp-online`, `auto-blastp` and the BLASTp crawl tools (nr, ClusteredNR) | Uploads selected protein sequences; requires `--confirm-public-sequence-upload` |
| [EMBL-EBI BLAST service](https://www.ebi.ac.uk/Tools/sss/ncbiblast/) | Fallback BLASTp route (`mamey/blastp_ebi.py`) when NCBI is unreachable; one job per protein | Uploads selected protein sequences |
| [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) (`eutils.ncbi.nlm.nih.gov`) | Sequence and metadata lookups for references, 16S searches and alignment helpers | Follow NCBI's usage policy and rate limits |
| [NCBI Datasets](https://www.ncbi.nlm.nih.gov/datasets/) | Reference-genome and metadata retrieval (CLI listed above) | Retrieved records keep their source terms |
| [NP Atlas](https://www.npatlas.org/) | Optional natural-product reference records (see the NP Atlas workflow) | Record the release used |
| [TYGS](https://tygs.dsmz.de/) (DSMZ) | Type-strain genome comparisons; the bundle reads TYGS result tables you download | Submitted by the user |
| [BacDive](https://bacdive.dsmz.de/) (DSMZ) | Strain metadata looked up by culture-collection number | Used for display metadata only |
| [GTDB](https://gtdb.ecogenomic.org/) | Taxonomy and marker references for genome trees (via GToTree) | Record the GTDB release used |

Keep database versions and hashes with the analysis.  Run
`python mamey_run.py doctor --companions` to check the analysis machine, and use the
[installation guide](INSTALL.md) for the bundle setup.
