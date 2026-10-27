# External Assets Guide — what Sapote-Mamey can use, and how to get it

Choose assets for the task you intend to run. Core extraction reads supplied antiSMASH
results in a configured Python environment; optional comparison, scanning and phylogeny
stages need their own inputs, dependencies and reference data.

The previous text is in [the historical guide](history/EXTERNAL_ASSETS_GUIDE.md).

First choose your task in [companion files](COMPANION_FILES.md#inputs-for-the-selected-task).
Use [installation](INSTALL.md) for Python dependencies and [prerequisites](PREREQUISITES.md)
for system tools. Then use this guide to bind the reference assets that task needs.
Core extraction does not require you to provision every asset listed here.

## Acquire only the assets needed for the selected task

Check the permitted project inventory first and reuse existing assets in place. Preserve
their source path, version and SHA-256. Before acquiring anything, identify its source,
size, terms and destination. Keep missing evidence recorded as unavailable rather than
as a measured zero.

## Where assets belong

Preserve the existing project layout. `MAMEY_DATA_ROOT` can hold the registered dataset
subdirectories below, but individual consumers have exceptions. Uppercase `Wheelhouse/`
contains scanner and registry material; lowercase `wheels/` contains Python installation
archives. Neither name establishes that the required assets are present.

## How the engine finds an asset once it is present

For generic datasets, `mamey/external_data.py` checks the dataset-specific variable,
then `MAMEY_DATA_ROOT/<subdirectory>`, then its legacy bundle location. A candidate must
contain the named probe; an invalid generic override can fall through.

If a dataset appears missing, compare the selected directory with the probe in the
table. For example, `MAMEY_MIBIG_DIR` must point to the directory containing
`mibig_reference_index.bacterial.json`. If the reported path is unexpected, inspect
both the dataset-specific variable and `MAMEY_DATA_ROOT` before changing files.

| Dataset | Variable | Shared-root subdirectory | Generic probe |
|---|---|---|---|
| MIBiG index | `MAMEY_MIBIG_DIR` | `mibig/` | `mibig_reference_index.bacterial.json` |
| MIBiG neighborhoods | `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | `mibig/neighborhoods/` | `PROVENANCE.md` |
| Literature | `MAMEY_LITERATURE_CORPUS` | `literature/` | `literature_corpus.jsonl` |
| NP Atlas raw source | `MAMEY_NPATLAS_DIR` | `npatlas/` | `np_atlas.json` |
| Governance | `MAMEY_OFFICIAL_DATA` | `OFFICIAL_DATA/` | `exclusions.json` |

Scanner HMMs, normalized NP Atlas references and governed exclusions have the
consumer-specific rules below. Generic presence does not establish consumer readiness.

For environment diagnostics, read the
[doctor write-probe boundary](INSTALL.md#doctor-scope-and-write-probe) before running
`python mamey_run.py doctor` in an editable working installation. Review the selected
paths and reported states; discovery alone does not validate a workflow.

## Assets

### antiSMASH results

Supply the result ZIP for the selected strain. Mamey reads the results rather than
running antiSMASH or requiring its installed databases. Follow the
[Quick Guide](GUIDE/02_Quick_Guide.md) for intake and validation.

For downstream genome FASTA recovery, see
[companion files](COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip).

### Scanner Pfam subset

The scanner recognizes `scanner_pfam_150.hmm` and `scanner_pfam.hmm`; their resolver
model-count hints are 148 and 35. Resolution order is:

1. Existing `SM_HMM_DB` path.
2. `MAMEY_HMM_DIR`.
3. `MAMEY_DATA_ROOT/hmm/`.
4. Bundle-local `Wheelhouse/hmm/scanner_pfam_150.hmm`.
5. Discovered add-on `scanner_pfam_150.hmm`.
6. Bundle-local `Wheelhouse/hmm/scanner_pfam.hmm`.

Within operator directories, the 148 filename takes precedence. Set `SM_HMM_DB` to
an actual HMM file: that explicit branch checks existence only and can mistakenly
select a directory. Retain the selected path, tier and content hash; filenames and
model-count hints do not validate HMM content.

For local subset construction and its receipt, use the
[scanner provisioning contract](447_COMPANION_RETRIEVAL_CONTROLS.md#scanner-subset-provisioning).
The builder uses a compatible local Pfam-A source and performs no download.
Without scanner HMM evidence, regex processing may continue while HMMER fields remain
`NEEDS_HMMER_DOMTBLOUT`; this does not establish that an HMM scan ran.

### Full Pfam-A and BiG-SCAPE

Full Pfam-A is a separate, stage-specific input. Supply the selected file through
`--pfam` for the BiG-SCAPE workflow; the scanner subset is not a replacement.
Pin the source release and hashes, including required pressed indexes. For reference
anchoring, supply the selected antiSMASH-processed MIBiG GBKs with `--mibig-dir`.
See the [BiG-SCAPE cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

### BLAST and reference comparisons

Local homology work needs the selected BLAST+ executables and a suitable database.
The phylogeny/outgroup tools read `BLAST_BIN` or discover executables on `PATH`;
database paths remain command-specific. Use
[the local 16S database guide](LOCAL_16S_DATABASE.md) for the `SAPOTE_16S_DB` route.

MIBiG index data, neighborhood partitions and reference GBKs serve different consumers.
Bind the files required by the chosen command and retain their release provenance.
For independent online protein searches, follow
[the online BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md).

### NP Atlas, literature corpus and OFFICIAL_DATA

**NP Atlas.** Raw `np_atlas.json` satisfies the generic presence probe. Named-compound
enrichment instead reads `all_actinobacteria_npatlas_ref.json` and
`bacteria_nonactino_npatlas_ref.json`. Follow
[NP Atlas provisioning](NPATLAS_PROVISIONING.md) for normalized schemas and receipts.

`MAMEY_NPATLAS_DIR` prioritizes the normalized reference directory;
`SM_NPATLAS_DIR` is a warned legacy alias. The consumer does not directly use
`MAMEY_DATA_ROOT/npatlas`. It also searches fallback locations and combines readable
files, retaining the first record per lowercased name. The override is not exclusive.
Start a fresh process after changing references because the index is cached.
Review the reported raw presence, consumer files/counts and unreadable files separately.
These references enrich named similarity hits; they do not identify a strain's product.
Review the acquired release's terms and the bundle's nonredistribution policy.

**Literature.** `mamey/data/literature/_corpus/pubmed_ingest.py` builds a corpus from
authorized local PubMed search-result PDF exports using `pypdf`; it does not fetch
PubMed records. Set `MAMEY_LITERATURE_CORPUS` to the resulting corpus directory.
See [external data](EXTERNAL_DATA.md#2-literature-corpus--pmids-dois-titles-abstracts).
Unavailable enrichment remains NOT MEASURED.

**OFFICIAL_DATA.** An active source context can supply governance before environment
lookup; see [cohort-pack binding](COHORT_PACK_INTERFACE.md#binding). Without that
context, the exclusions consumer treats `MAMEY_OFFICIAL_DATA` as exclusive.
Otherwise, a set `MAMEY_DATA_ROOT` supplies an exclusive `OFFICIAL_DATA/` candidate;
with neither set, it walks package parents. A missing or unusable binding can fail
strict checks or use the empty default in non-strict operation. Inspect the actual
governance source and diagnostics before using a denominator. Generic provisioning
status alone does not establish the adopted exclusion set.

### Phylogenomics and comparator genomes

Use the selected workflow's reference genomes, metadata and external tools.
[Phylogeny autopilot](PHYLO_AUTOPILOT_WORKFLOW.md) documents that route.
Binary lookup can use `MAMEY_PHYLO_BIN`, `PHYLO_BIN`, `PLACEMENT_BIN` or explicit
command options; GToTree has its own data configuration. A tree task does not
automatically require downloading every GTDB resource.

### Python dependencies

Use the extras declared in the local `pyproject.toml` and follow
[installation](INSTALL.md). `.[addons]` requests the comparative/scanner stack.
`.[all]` combines figures, bio, render, documents and slides; it excludes addons
and test dependencies. The supplied ZIP's three packaging wheels do not form a
complete offline runtime. See [companion installation](COMPANION_FILES.md#installation-and-companion-tool-boundaries).
