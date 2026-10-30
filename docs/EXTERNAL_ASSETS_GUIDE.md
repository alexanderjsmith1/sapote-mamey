# Find reference data for your task

Use this page when an optional workflow needs a database, HMM file or reference
collection. You need the selected task and its input requirements. Core extraction
reads an antiSMASH result ZIP; it does not require every asset listed here.

Start with [companion files](COMPANION_FILES.md#inputs-for-the-selected-task),
[installation](INSTALL.md) and [prerequisites](PREREQUISITES.md). Reuse existing
assets in place and record their path, version and SHA-256. Before downloading,
check the source, size, terms and destination.

## Check the selected paths

Run doctor from an editable program folder:

```bash
python mamey_run.py doctor
```

Read its selected paths and missing capabilities. [Install](INSTALL.md#doctor-scope-and-write-probe)
explains its temporary write probe. Keep the existing project layout:
`Wheelhouse/` holds scanner/registry material; `wheels/` holds Python wheels.

For generic datasets, lookup tries the dataset variable, then
`MAMEY_DATA_ROOT` plus the subdirectory below, then the legacy bundle location.
A candidate needs its named probe file; an invalid override can fall through.

| Dataset | Variable | Subdirectory | Probe |
|---|---|---|---|
| MIBiG index | `MAMEY_MIBIG_DIR` | `mibig/` | `mibig_reference_index.bacterial.json` |
| MIBiG neighborhoods | `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | `mibig/neighborhoods/` | `PROVENANCE.md` |
| Literature | `MAMEY_LITERATURE_CORPUS` | `literature/` | `literature_corpus.jsonl` |
| NP Atlas raw source | `MAMEY_NPATLAS_DIR` | `npatlas/` | `np_atlas.json` |
| Exclusions/governance | `MAMEY_OFFICIAL_DATA` | `OFFICIAL_DATA/` | `exclusions.json` |

For example, point `MAMEY_MIBIG_DIR` to the folder containing its index file.
Check both that variable and `MAMEY_DATA_ROOT` if the reported path is unexpected.
The consumers below have additional lookup rules.

## Scanner HMMs

Lookup tries an existing `SM_HMM_DB` path, `MAMEY_HMM_DIR`,
`MAMEY_DATA_ROOT/hmm/`, bundle `Wheelhouse/hmm/scanner_pfam_150.hmm`, a discovered
add-on copy, then bundle `scanner_pfam.hmm`. Within configured directories,
the `_150` filename takes precedence. Its model-count hint is 148; the smaller
filename's hint is 35. Check the content and hash, not just the filename.

Set `SM_HMM_DB` to a file: its existence check also accepts directories.
The [subset builder](447_COMPANION_RETRIEVAL_CONTROLS.md#scanner-subset-provisioning)
uses a compatible local Pfam-A file and performs no download. Without HMM evidence,
regex work can continue while the HMMER fields say `NEEDS_HMMER_DOMTBLOUT`.

## BiG-SCAPE and sequence comparisons

BiG-SCAPE needs full Pfam-A through `--pfam`, including the required pressed
indexes. The scanner subset cannot replace it. For reference anchoring, supply
selected antiSMASH-processed MIBiG GBKs with `--mibig-dir`; see the
[cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

Local homology work needs BLAST+ and the chosen database. Phylogeny/outgroup
tools read `BLAST_BIN` or PATH; database options depend on the command.
The [local 16S guide](LOCAL_16S_DATABASE.md) covers `SAPOTE_16S_DB`.
Keep MIBiG index data, neighborhood partitions and reference GBKs with their
release details: they serve different readers. Use the
[online BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) for remote searches.

## NP Atlas and literature

Raw `np_atlas.json` satisfies the generic NP Atlas probe. Named-hit enrichment
uses `all_actinobacteria_npatlas_ref.json` and `bacteria_nonactino_npatlas_ref.json`;
follow [NP Atlas provisioning](NPATLAS_PROVISIONING.md).

`MAMEY_NPATLAS_DIR` prioritizes the normalized files; `SM_NPATLAS_DIR` is a
warned legacy alias. This reader does not directly use `MAMEY_DATA_ROOT/npatlas`.
It combines readable fallback files and keeps the first record per lowercased
name. Start a fresh process after changing references because the index is cached.
Check raw presence, consumer counts and unreadable files separately. Review the
release terms and the bundle's nonredistribution policy before sharing these data.

The literature builder `mamey/data/literature/_corpus/pubmed_ingest.py` reads
local PubMed search-result PDF exports with `pypdf`; it does not fetch records.
Point `MAMEY_LITERATURE_CORPUS` to the resulting corpus directory. See
[external data](EXTERNAL_DATA.md#2-literature-corpus--pmids-dois-titles-abstracts).
Unavailable enrichment stays NOT MEASURED.

## Exclusions and other references

An active source context can supply exclusions before environment lookup;
see [cohort-pack binding](COHORT_PACK_INTERFACE.md#binding). Otherwise,
`MAMEY_OFFICIAL_DATA` is exclusive. With no such variable, a set
`MAMEY_DATA_ROOT` supplies an exclusive `OFFICIAL_DATA/` candidate; with neither,
lookup walks package parents. A missing/unusable source can fail strict checks
or use an empty default in non-strict operation. Inspect the selected source
before using a cohort denominator.

For phylogenomics, use the selected reference genomes and metadata from the
[workflow](PHYLO_AUTOPILOT_WORKFLOW.md). Binary lookup can use `MAMEY_PHYLO_BIN`,
`PHYLO_BIN`, `PLACEMENT_BIN` or explicit options. GToTree has its own data settings.
Choose the resources for that analysis rather than downloading all of GTDB.

For Python extras, follow [Install](INSTALL.md). `.[addons]` requests the
comparative/scanner stack. `.[all]` combines figures, bio, render, documents and
slides; it excludes addons and tests. The code ZIP's three packaging wheels
are not a complete offline runtime; see [companion installation](COMPANION_FILES.md#installation-and-companion-tool-boundaries).

For input formats and genome recovery, use [companion files](COMPANION_FILES.md).
The [previous guide](history/EXTERNAL_ASSETS_GUIDE.md) remains in history.

<a id="acquire-only-the-assets-needed-for-the-selected-task"></a>
<a id="where-assets-belong"></a>
<a id="how-the-engine-finds-an-asset-once-it-is-present"></a>
<a id="assets"></a>
