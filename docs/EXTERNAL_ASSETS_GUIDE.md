# Find reference data for your task

Use this page when an optional workflow needs a database, HMM file or reference
collection. Core extraction reads an antiSMASH result ZIP; it does not require every
asset listed here. Find your task in the table first.

Then see [companion files](COMPANION_FILES.md#inputs-for-the-selected-task),
[installation](INSTALL.md) and [prerequisites](PREREQUISITES.md). Reuse existing
assets in place and record their path, version and SHA-256. Before downloading,
check the source, size, terms and destination.

## Which asset for which task

| Task | Asset | Section |
|---|---|---|
| Scanner domain checks | Pfam HMM subset (`SM_HMM_DB`) | [Scanner HMMs](#scanner-hmms) |
| BiG-SCAPE | Full Pfam-A and MIBiG GBKs | [BiG-SCAPE and sequence comparisons](#big-scape-and-sequence-comparisons) |
| Local BLAST or 16S work | BLAST+ and a database | [BiG-SCAPE and sequence comparisons](#big-scape-and-sequence-comparisons) |
| Named-hit enrichment | NP Atlas reference files | [NP Atlas and literature](#np-atlas-and-literature) |
| Literature enrichment | Literature corpus | [NP Atlas and literature](#np-atlas-and-literature) |

## Check the selected paths

Run doctor from an editable program folder:

```bash
python mamey_run.py doctor
```

When at least one dataset is found, the line `External datasets provisioned` gives a count such
as `2/6` and names them. With none found, that line is absent. Each missing dataset gets its own
warning with the variable to set and where to download it. `doctor` does not print the folder
for each dataset; it does print the exclusions-file path on its governed-denominator line when
that source is bound. To see the resolved path for each dataset, run this from the bundle root:

```bash
python -c "import json; from mamey import external_data as x; print(json.dumps(x.status(), indent=2))"
```

[Install](INSTALL.md#doctor-scope-and-write-probe) explains `doctor`'s temporary write probe. Keep the existing project layout:
`Wheelhouse/` holds scanner/registry material; `wheels/` holds Python wheels.

For generic datasets, lookup tries the dataset variable, then
`MAMEY_DATA_ROOT` plus the subdirectory below, then the legacy bundle location.
A candidate needs its named probe file; an invalid override can fall through. For example, `export MAMEY_MIBIG_DIR=/data/mibig` makes the lookup use that folder if it holds the probe file. Then run the command above to see the path it resolves.

| Dataset | Variable | Subdirectory | Probe |
|---|---|---|---|
| MIBiG index | `MAMEY_MIBIG_DIR` | `mibig/` | `mibig_reference_index.bacterial.json` |
| MIBiG neighborhoods | `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | `mibig/neighborhoods/` | `PROVENANCE.md` |
| Literature | `MAMEY_LITERATURE_CORPUS` | `literature/` | `literature_corpus.jsonl` |
| NP Atlas raw source (presence check only; see below) | `MAMEY_NPATLAS_DIR` | `npatlas/` | `np_atlas.json` |
| Exclusions/governance | `MAMEY_OFFICIAL_DATA` | `OFFICIAL_DATA/` | `exclusions.json` |

If the resolved path is unexpected, check both the dataset variable and `MAMEY_DATA_ROOT`. The consumers below have additional lookup rules.

## Scanner HMMs

The scanner uses a small Pfam HMM subset. The CODE ZIP does not ship it: its `Wheelhouse/` has no `hmm/` folder. Lookup tries, in order:

1. an existing `SM_HMM_DB` path;
2. `MAMEY_HMM_DIR`;
3. `MAMEY_DATA_ROOT/hmm/`;
4. `Wheelhouse/hmm/scanner_pfam_150.hmm`, only if your bundle carries one;
5. a `scanner_pfam_150.hmm` in a discovered add-on folder;
6. `Wheelhouse/hmm/scanner_pfam.hmm`, the 35-model set, which the public bundle also omits.

In steps 2 and 3, `scanner_pfam_150.hmm` is tried before `scanner_pfam.hmm`. Its model-count hint is 148; the other file's hint is 35. Check the content and hash, not just the filename.

Set `SM_HMM_DB` to the `.hmm` file itself. A directory is refused, and lookup does not fall through to another source.
The [subset builder](447_COMPANION_RETRIEVAL_CONTROLS.md#scanner-subset-provisioning)
uses a compatible local Pfam-A file and performs no download. Without HMM evidence,
regex work can continue while the HMMER fields say `NEEDS_HMMER_DOMTBLOUT`.

## BiG-SCAPE and sequence comparisons

BiG-SCAPE needs full Pfam-A through `--pfam`, including the required pressed
indexes. The scanner subset cannot replace it. For reference anchoring, supply
selected antiSMASH-processed MIBiG GBKs with `--mibig-dir`; see the
[cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

Local homology work needs BLAST+ and the chosen database. `phylo_autopilot.py`
invokes `blastn` and `blastdbcmd` through `PATH`. `outgroup_registry.py` and
`phylo_refset.py` try `BLAST_BIN` before `PATH`; check the selected tool.
Database options depend on the command.
The [local 16S guide](LOCAL_16S_DATABASE.md) covers `SAPOTE_16S_DB`.
Keep MIBiG index data, neighborhood partitions and reference GBKs with their
release details: they serve different readers. Use the
[online BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) for remote searches.

## NP Atlas and literature

Raw `np_atlas.json` satisfies the generic NP Atlas probe. Named-hit enrichment
uses `all_actinobacteria_npatlas_ref.json` and `bacteria_nonactino_npatlas_ref.json`;
follow [NP Atlas provisioning](NPATLAS_PROVISIONING.md).

The named-hit reader (`mamey/npatlas_resolver.py`) does not use `MAMEY_DATA_ROOT`. It reads
only `MAMEY_NPATLAS_DIR` (or the legacy `SM_NPATLAS_DIR`, which warns) and its fallback folders.
So `doctor` can count NP Atlas as provisioned from `$MAMEY_DATA_ROOT/npatlas/np_atlas.json`
while the reader finds no references. Set `MAMEY_NPATLAS_DIR` to the folder that holds the two
reference files. The reader caches its index per process, so start a fresh process after you
change those files. `status()` reports `consumer_ready` for the reader's view. Other rules are in
[NP Atlas provisioning](NPATLAS_PROVISIONING.md).

The literature builder `mamey/data/literature/_corpus/pubmed_ingest.py` reads
local PubMed search-result PDF exports with `pypdf`; it does not fetch records.
Point `MAMEY_LITERATURE_CORPUS` to the resulting corpus directory. See
[external data](EXTERNAL_DATA.md#2-literature-corpus--pmids-dois-titles-abstracts).
Unavailable enrichment stays NOT MEASURED.

## Exclusions and other references

A bound source context supplies its own exclusions. Otherwise, `MAMEY_OFFICIAL_DATA` selects its folder exclusively; if unset, `MAMEY_DATA_ROOT` selects its `OFFICIAL_DATA/` subfolder exclusively. With neither set, the loader can search parent folders. A missing selected list can fall back to empty in non-strict reads or be refused in strict reads. Check the actual source and hash; see [cohort-pack binding](COHORT_PACK_INTERFACE.md#binding). A single-strain run does not need a cohort pack.

For phylogenomics, use the selected reference genomes and metadata from the
[workflow](PHYLO_AUTOPILOT_WORKFLOW.md). Binary lookup can use `MAMEY_PHYLO_BIN`,
`PHYLO_BIN`, `PLACEMENT_BIN` or explicit options. GToTree has its own data settings.
Choose the resources for that analysis rather than downloading all of GTDB.

For Python extras, follow [Install](INSTALL.md). `.[addons]` requests the
comparative/scanner stack. `.[all]` combines figures, bio, render, documents and
slides; it excludes addons and tests. The code ZIP's three packaging wheels
are not a complete offline runtime; see [companion installation](COMPANION_FILES.md#installation-and-companion-tool-boundaries).

For input formats and genome recovery, use [companion files](COMPANION_FILES.md).
