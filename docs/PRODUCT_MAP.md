# What Sapote-Mamey offers

Sapote-Mamey combines a Python extraction engine, package readers, and governed interpretation workflows. Begin with the exact antiSMASH result ZIP, inspect its identity and contents, and review the resulting package's receipts and actual files. Optional searches, comparisons, trees and figures have separate inputs, dependencies and status.

**Mamey** extracts evidence and records provenance. A successful extraction is not a finished biological interpretation. Compare packages using input hashes, build/source identity, engine version, options and receipt scope; an unchanged engine number alone does not establish currentness or comparability. An assistant may help operate authorized commands and read outputs, but must preserve source evidence and disclose assumptions and holds. Some post-seal authoring commands write additive package artifacts and refresh an integrity receipt (`mamey/cli.py:8550–8569`); a sibling reader output such as widgets has a different write boundary.

**Sapote** is the governed interpretation layer. Mode B cards use a selected contract: the default full48 profile and opt-in current50_v2 profile have different sections and requirements. Template or software gate success does not establish scientific acceptance. See the [profile matrix](MODEB_PROFILE_MATRIX.md) and preserve the complete strain / full node-or-contig / region / BGC alias identity whenever interpreting an individual locus.

Saved protein-search evidence can support follow-up when query identity, database/channel, provenance and admission states are bound. Automated external searches require the relevant authorization, local controls and service availability. No fixed runner count, daily throughput or unattended completion is guaranteed by this bundle. Use [the online BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) and [retrieval controls](447_COMPANION_RETRIEVAL_CONTROLS.md) before selecting that optional route; a planned or submitted query is not a fetched, admitted result.

Contamination flags are review evidence. Assembly exclusions or reprocessing require a separately documented decision and input identity; retain the original evidence and bind any replacement run to its own input hash. See [the deliverable contract](DELIVERABLE_CONTRACT.md) for extraction and interpretation boundaries.

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
| How should one BGC be interpreted? | The exact region and admitted gene/domain/reference evidence | A profile-bound Mode B card for human review, with claims and holds tied to their sources | [Mode B profiles](MODEB_PROFILE_MATRIX.md) |
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

See [artifact maps and menu limits](ARTIFACT_MAP_LIMITS.md) when choosing a deliverable by name or checking whether it exists.

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
