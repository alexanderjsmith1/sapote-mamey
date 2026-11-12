# Portable 16S data workflow

These tools prepare candidate 16S sequences and screening evidence for tree work. They do not establish strain identity, taxonomy, gene boundaries, orientation, novelty, tree validity or a strain merge. Terms are in the [glossary](GLOSSARY.md).

The order is: admit sequences (step 1), build the 16S store (step 2), then extract from a genome and make a panel (step 3). The tree route that uses these outputs is in [PHYLOGENETICS_WORKFLOW](PHYLOGENETICS_WORKFLOW.md).

## 1. Admit sequences before alignment

Run the admission gate before MAFFT (alignment) or EPA-ng (placement). It checks a roster file against a FASTA. It does no alignment and no retrieval.

Prepare two files with the same unique tip IDs: a tab-separated roster and a FASTA. FASTA descriptions are labels only. The roster is the authority.

Required roster columns:

`tip`, `role`, `organism`, `expected_genus`, `accession`, `sequence_sha256`, `type_status`, `isolation_source`, `geography`, `sequence_evidence`, `metadata_evidence`, `biological_sample_id`, `admission`.

- `role` is `query`, `reference` or `outgroup`.
- `type_status` is `type`, `non_type` or `not_applicable` (queries only).
- `admission` must be `admitted`.
- `biological_sample_id` must be filled for query rows. It can be blank for references.
- Use the exact accession with its version. The gate checks that the field is filled, not that it is a valid versioned accession.

```bash
python tools/phylo_sequence_admission.py --roster admitted_roster.tsv \
  --fasta candidate_sequences.fasta --molecule 16S --json NEW_RECEIPT.json
```

Success: exit 0 and the receipt printed to stdout. The handled refusal and error cases below exit 2. Treat an unexpected traceback or a missing receipt as unresolved, and investigate before retrying with a fresh receipt path.

- `ADMISSION_FAIL:` the inputs were read and failed a check. The receipt carries `status` `ADMISSION_FAIL` and the reason;
- `ADMISSION_ERROR: input could not be read:` the roster or FASTA was missing, unreadable or not UTF-8. The receipt carries `status` `ADMISSION_ERROR`, and `rows` is `null` when the roster was never read. Nothing was checked;
- `ADMISSION_REFUSED:` the `--json` file already exists. No receipt is written, so give a new path each time;
- `ADMISSION_ERROR: receipt could not be written:` the receipt folder is missing or not writable. Nothing is printed to stdout.

Read the status, not the exit code alone.

The default 16S length window is 900 to 2,000 after normalization. `--min-length` and `--max-length` change it. `--molecule genome` skips the length check only. The gate rejects short fragments, cross-genus records, missing accession or evidence fields, duplicate type-species representatives, and identical query sequences from the same biological sample.

The sequence hash uses uppercase, U changed to T, and `-` and `.` removed. It differs from a raw-file SHA-256. Keep both.

Identical query sequences from the same biological sample are refused, including an identical pair alongside a third, different sequence. Exact matches across samples remain in `exact_sequence_groups` for review. A pass does not prove that samples are independent.

### Geography and isolation source

Both columns are admitted as deposited and never reworded.

- A blank value, a placeholder such as `unknown`, or an INSDC missing term such as `missing: lab stock` is not refused. The tip is admitted unchanged and listed under `figure_omissions` by full name, accession and reason `NO_DEPOSITED_GEOGRAPHY` or `NO_DEPOSITED_SOURCE`. Figures leave these tips out. A tip missing both is listed twice.
- The receipt also holds `geography_region`, a display-only grouping. It is filled only when the deposited text (or its country part before `:`) is already one of ten list values, or the country is in the table in `tools/_phylo_metadata.py`. The ten values are `US`, `Canada`, `North America (other)`, `South America`, `Europe`, `Asia`, `Africa`, `Oceania`, `Antarctica` and `Indian Ocean`. Anything else leaves it blank. `geography_region_basis` says which case applied: `LIST_VALUE`, `COUNTRY_TABLE`, `NOT_DERIVED` or `NOT_RECORDED`. The deposited text stays the record.

## 2. Build and refine the 16S store

The store is a SQLite file. Each step reads one store and writes a new one, so you keep every stage. Existing output files and symlinks are refused. The output folder must already exist.

```bash
python tools/phylo_16s_build_db.py --db output/initial.sqlite --authoritative-fasta inputs/queries.fasta
python tools/phylo_16s_fetch.py --db output/initial.sqlite --out-db output/fetched.sqlite --source pdf_candidate
python tools/phylo_16s_esearch.py --db output/fetched.sqlite --out-db output/search.sqlite --sets SET_NAME
python tools/phylo_16s_rank.py --db output/search.sqlite --out-db output/ranked.sqlite
python tools/phylo_16s_audit_merges.py --db output/ranked.sqlite --out-db output/audited.sqlite
```

Each step needs the previous output. Add a reference source to the first step with `--refseq-blastdb inputs/reference_db`; include both source options in one build to combine them. Other inputs are `--nontype-dir`, `--reference-metadata-dir`, `--pdf-hits` and `--provenance`. A source you name but that is missing is an error. To rebuild only the sets, use `--sets-only --input-db INPUT --db NEW_OUTPUT`. `fetch` handles only pending records of the source you name, so a query-only store may have none. `esearch --sets` takes a comma-separated list of set names defined in `tools/phylo_16s_esearch.py` (default `all`).

Input stores must be closed, checkpointed snapshots with no WAL or journal files. Each tool works on an in-memory copy, checks the input hash and publishes a finished store with an `operation_event` record. Large stores need enough memory for the copy and the output.

Add `--dry-run` to the build, fetch, esearch, rank and merge-audit tools to check inputs and print the plan. It does no network, BLAST or MAFFT work and writes no file. Counts that would need a remote call stay unmeasured. The defect validator below has no `--dry-run`.

Progress and plans go to stderr. Silence on stdout is not a verdict. Check the exit code and the receipt status.

### Status words

| Word | Where | Meaning |
|---|---|---|
| `PARTIAL_WITH_HOLDS` | fetch receipt | Some records were saved, some were held. The command exits nonzero. |
| `NOT_RETURNED` | fetch receipt | A requested record did not come back. The cause is unknown. |
| `NOT_MEASURED` | rank output | No saved-hit file (`--pdf-hits`) was given, so that rescue channel was not measured. |
| `SIMILARITY_SCREEN_PASS` | merge audit | Two records passed an alignment threshold. It is not an accepted merge. |
| `MERGE_ACCEPTANCE_HELD` | merge screen | No merge is accepted. This includes events with zero pairs. |
| `REVIEW_NEEDED` | validator genus report | A genus candidate needs your review. The validator can still exit 0. |

`acc_base` is the store column for an accession without its version. Local queries with no accession get an internal `LOCAL:` key there, and `acc_version` stays empty. `record_key` is the panel's separate key for such records. A `LOCAL:` key never appears as an accession in a label.

### Sequence and accession rules

- FASTA records need unique first-token IDs and ungapped IUPAC DNA. SHA-256 of the uppercase sequence binds content. Identical sequences from different sources stay separate records.
- Duplicate accessions in one source, conflicting versions, and conflicting sequences at one accession are held for you to reconcile.
- A provenance TSV needs a `strain` column. Assigning an accession also needs its exact version and a matching `sequence_sha256`. Optional columns: `organism_as_deposited`, `host`, `isolation_source`, `geo_loc_name`, `collection_date`, `lat_lon`. These are what you supply.
- Reference FASTA files are named `*_nontype_16S.fasta`. Their metadata is `*/*_nontype_meta.tsv`, keyed by exact `accession.version`, using columns `accession`, `isolation_source` and `geo`. Saved-hit TSVs use `accession`, `subject`, `subject_len`, `strain` and `pct_identity`. A missing or invalid percent identity is never turned into zero.
- `--refseq-type-material` marks a BLAST source as type material. Use it only when that is true. A culture-collection number does not establish type status.

### Remote retrieval

Fetch matches every returned record to a requested accession. An unexpected, duplicate, mismatched or truncated record holds its batch. Whole-genome records are held before download. An ESearch counts as complete only when the unique IDs returned equal the reported count. Over-limit searches are held. Search tags show that a query matched; they are not membership.

GenBank parsing needs Biopython. Without it, parsing fails with a clear message instead of silently losing the source fields. Raw GenBank files are cached by content hash in `gb_cache/` beside the input store. `--cache-dir` or `SAPOTE_16S_GB_CACHE` moves the cache; `--no-cache` writes none. Source formats: [NCBI sample record](https://www.ncbi.nlm.nih.gov/genbank/samplerecord/) and [sequence identifiers](https://www.ncbi.nlm.nih.gov/genbank/sequenceids/).

### Ranking and merge screening

Ranks and habitat tags are screens, with the observation text beside them. A title keyword can be indirect, so review a tag before using it. A missing tag does not show a negative phenotype, absent habitat or nonmembership. The ranker rebuilds its generated tags and keeps search and genome tags. The `panel_candidates` view shows `sequence_status`, `tag_scope` and `candidate_tags`.

Strain groups built from designations or collection IDs are proposals. Review them. In the merge audit, only A/C/G/T columns count toward identity, and zero comparable columns give a missing identity.

### Check a store for defects

```bash
python3 tools/phylo_16s_validate_db.py --db CLOSED_SNAPSHOT --out-dir FRESH_REPORTS
```

It runs two defect screens and writes four reports in sequence. If a report path is taken or a write fails, you can be left with some reports. Keep them, keep the snapshot, and rerun into a fresh folder. Details, output list and recovery are in [the validator and merge contracts](reference/06_CURRENT_SOURCE_SCOPE.md#16s-store-defect-validation-and-additive-merge-screening). The validator does not refuse a store with WAL or journal files, and it does not check hashes.

## 3. Extract from a genome and make a panel

```bash
python tools/phylo_16s_from_genome.py inputs/genome.fna --blastdb inputs/reference_db --out output/candidate_spans.fasta
python tools/phylo_16s_panel.py --db output/ranked.sqlite --strains QUERY_A --refs type:1x --name candidate_panel --outdir output
```

Extraction groups BLAST hits that lie within 100 nt of each other. Hits in one group must run in the same direction, or extraction holds. There is no contig-wide vote. The coordinates mark a BLAST-supported span, not a verified gene. You must establish orientation against a reference. `--best` keeps the longest span.

Duplicate genome paths or contents are refused. Tip keys hold the genome hash and the contig coordinates. A receipt records input and reference hashes, parameters, hits and the output hash. The panel metadata has `role` (query, reference or outgroup) and `taxon`, copied from the record's binomial, with `taxon_source`. A missing taxon stays empty and stops reference collapse. The panel FASTA, metadata and receipt are new files, and the receipt is written last. Treat a panel with no receipt as unfinished.

BLAST needs a path without spaces. A `TMPDIR` with a space is refused. Alias databases (`.nal`) are held; give a direct volume prefix. A tool failure or malformed result is never read as no hits.

A passing run here is not scientific acceptance. Live NCBI retrieval, real BLAST and MAFFT results and large stores need their own checks.
