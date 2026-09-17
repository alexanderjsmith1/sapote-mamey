# What Sapote-Mamey offers

Sapote-Mamey has a **core analysis** and optional follow-up workflows. You can
start with one antiSMASH result ZIP or hundreds, inspect BGCs, and receive a validated
evidence package for each microbial isolate without running every optional analysis. Add protein searches,
cross-strain comparisons, trees, or figures when they help answer a specific
question. 

The option exists to detect contamination and remove contaminating data from the analysis. This is best achieved by removing the contaminating sequences from the assembly fasta and running the "cleaned" assembly through antiSMASH.  

**Mamey** is the executable, deterministic half of Sapote Mamey analysis: Mamey extracts and checks evidence, records provenance, and produces tables, workbooks, packages, and selected figures. No LLM or artificial intelligence is able to participate in the Mamey run, and the output of Mamey is a sealed zip package that LLMs are strictly forbidden from modifying. The Mamey "engine" is python-based and versioned, such that the Mamey zip outputs are versioned and comparable across genomes when the same engine is used. Updates to the larger Sapote Mamey bundle can occur and the Mamey packages remain current when the Mamey engine does not change. This strict boundary between deterministic outputs and LLM-enhanced Sapote outputs helps to keep the outputs grounded in hard truth and completely independent of LLM models. 

**Sapote** is the governed interpretation workflow. This is LLM-guided and while much of the modules and processes are python bases, the LLM model does participate and assists integrating multiple streams of information. This allows a researcher to direct the attention of the LLM to specific BGCs and scientific questions while under strict operating rules to help create a consistent and non-fabricated output. The primary BGC-based deliverable is the "Mode B card" which is a 50 section document that has a strict template and gates preventing poorly constructed cards from passing. It may be wishful thinking of the developers to believe that this can occur with much consistancy, but exemple mode B cards for each BGC class are available to help steer the LLM toward success. The production of mode B cards is token-expensive, and so the user can use the flexibility to their advantage by requesting various depths of analysis for specific BGCs. Deep analysis can be restricted to PKS-containing BGCs, or attention directed towards resistance genes, specific types of RiPPs, etc. 

The Sapote Mamey analysis pipeline is set up to run BLASTp against the clustered_nr and nr NCBI databases in an automated, background task. The Mamey engine automatically produces fasta files for each BGC in batches that are sized appropriately for BLASTp queries (10 proteins per query, except large proteins are separated and retained as individual fasta files to be submitted as single proteins). The BLASTp can then be ordered to be run under the LLMs direction, which requires tokens during the setup phase but runs in the background once set up and established. The FASTA file can also be run manually by the user through the NCBI web interface and other means. With dozens of genomes, a bottleneck situation arises and the user may request the LLM to batch and prioritize proteins into FASTA files to suit their needs (specific BGC classes, specific isolates, specific genes). High BLASTp submission rates lead to throttling and error messages from NCBI rather than results, so a recommended run is 6 or 8 runners with maxinflight=4, this prevents a situation of oversubmisison through the internal NCBI interface. This current Sapote Mamey bundle can submit and retrieve approximately 1000 protein sequences on a rolling 24/7 basis when fully working. A graphical display of cumulative BLASTp retrieval can be displayed simply by requesting the LLM to "plot BLASTp". 

```text
antiSMASH result ZIP
  └─ inspect → Mamey run → validate → evidence package + workbook
                                  ├─ protein search/import → gene-level matches
                                  ├─ BiG-SCAPE → cluster-family comparisons
                                  ├─ Mode B → reviewed BGC interpretation
                                  └─ figures → locus and cohort displays

full genome assembly or 16S sequence
  └─ optional MLSA / EPA-ng / GToTree → tree + metadata-linked figures
```

## Pick the part you need

| You want to know… | Start with | What it produces | Guide |
|---|---|---|---|
| Which BGCs and genes are present? | One antiSMASH result ZIP; `inspect`, then `run` and `validate` | Per-strain inventory, gene and boundary evidence, triage board, workbook, manifest and issues | [Your first analysis](MASTER_WALKTHROUGH.md) |
| What proteins do the genes resemble? | An existing package and its region sequences; manual/online BLASTp or saved hit tables | Separate, provenance-bound per-gene matches for each search database | [Protein search](GUIDE/02_Quick_Guide.md#protein-search-and-result-import) |
| Does a pathway span fragmented contigs? | The package's region, boundary and reference-linkage evidence | Candidate fragment links and explicit contradictory or missing evidence | [Fragment review](GUIDE/02_Quick_Guide.md#fragmented-pathway-review) |
| Which BGCs cluster across strains? | Region GBKs plus an external BiG-SCAPE 2.x installation and Pfam data | Run-specific gene-cluster families and comparison files | [BiG-SCAPE cohort workflow](BIGSCAPE_COHORT_WALKTHROUGH.md) |
| How should one BGC be interpreted? | The exact region and admitted gene/domain/reference evidence | A human-reviewed Mode B card, with claims and holds tied to their sources | [Mode B authoring](MODEB_FULL50_CONTRACT_USAGE.md) |
| Where do 16S sequences or genomes sit on a tree? | 16S or full assembly sequences, a declared reference panel, and external tools | EPA-ng placement, optional five-locus MLSA screening, or GToTree core-genome analysis | [Phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md) |
| How do I show results? | A validated package or a tree with matching metadata | Locus maps, comparison figures, tree displays and selected overlays | [Figures start here](FIGURES_START_HERE.md) |

The package is the common handoff between these parts. Its `manifest.json`
records the input and available outputs. Read [your results](READING_YOUR_RESULTS.md)
before asking for deeper interpretation or rerunning a workflow.

## What is inside the bundle, and what you supply

- **Bundled:** the Python program, extraction rules, templates, validators,
  documented workflows, and some reference indices and seed sequences.
- **Your data:** antiSMASH results, genome or 16S sequences, strain and
  sample metadata, saved BLASTp results, and any assay observations you want
  to connect to figures.
- **External companions when selected:** BLAST+ or online BLAST services,
  BiG-SCAPE with its Pfam database, Prodigal/MUSCLE/IQ-TREE for MLSA,
  EPA-ng tools for 16S placement, and GToTree/IQ-TREE for core-genome trees.
  The core Mamey run does not install or run all of these.

For a genome tree, a full assembly FASTA may be inside your antiSMASH ZIP.
Check the ZIP first; clipped region GBKs do not substitute for a whole genome.
The optional `phylo-mlsa` command offers a plan and a five-locus screen from a
ZIP that contains a full assembly. The separate 16S extraction tool uses a
local BLASTn reference database to find candidate rRNA spans in an assembly;
it does not certify gene boundaries. See [phylogenetics](PHYLOGENETICS_WORKFLOW.md)
for when to use each route.

## How the tree tools fit together

The **Tree Catalog** is for declaring and rendering several views of an
already completed placement analysis. It can make different reference-density
and metadata displays, but it does not find all tree files on your computer,
choose the authoritative tree, or infer a new one. Use the
[Tree Catalog guide](TREE_CATALOG.md) after the underlying tree, sequences,
reference roster and metadata have been reviewed.

## Where to begin

1. **New antiSMASH ZIP:** use [Your first analysis](MASTER_WALKTHROUGH.md).
2. **Existing Complete Package:** use [Read your results](READING_YOUR_RESULTS.md).
3. **Working with an assistant:** use [Working with Sapote-Mamey and an assistant](ASSISTANT_USER_GUIDE.md).

For a compact command reference, use the [Quick Guide](GUIDE/02_Quick_Guide.md).
For setup and optional companions, use [Install](INSTALL.md) and
[Prerequisites](PREREQUISITES.md). The [current document index](../CURRENT_DOCS_INDEX.md)
points to specialist documentation. The release manifest states the status of
the exact build you have; a successful software check does not substitute for
scientific review.
