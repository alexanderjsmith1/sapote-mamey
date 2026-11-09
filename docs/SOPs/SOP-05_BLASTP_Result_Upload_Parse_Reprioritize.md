# SOP-05 — BLASTP Result Upload, Parse, and Reprioritization

Run the commands below from the bundle root, the folder that holds `mamey_run.py`.


## Purpose

This SOP defines how Sapote/Mamey should ingest NCBI BLASTP results and convert them into next-action decisions.

## Inputs

Accepted inputs:

- NCBI BLASTP Hit Table CSV
- optional NCBI BLASTP Single-file XML2
- optional previous selection manifest
- optional previous FASTA panel directory

## Standard command

```bash
python mamey_run.py blastp-followup --hit-table <HitTable.csv> --xml2 <Alignment.xml> --outdir <outdir>
```

XML2 is optional. Omit `--xml2` when no XML2 file exists; do not pass a fabricated placeholder path. Hit Table CSV can provide triage while unknown query lengths/coverage remain unknown.

| Flag | Meaning | Default |
|---|---|---|
| `--hit-table` | NCBI BLASTP Hit Table CSV (required) | none |
| `--xml2` | Single-file XML2, used for hit titles and coverage | none |
| `--outdir` | Output folder (required) | none |
| `--previous-selection` | Earlier panel selection manifest CSV | none |
| `--panel-dir` | Folder of the earlier FASTA panel files. With `--previous-selection`, it lets the command write a next-batch FASTA. | none |
| `--next-proteins` | Most proteins in the next batch | 10 |
| `--target-residues` | Residue target for the next batch | 20000 |

Use a fresh external output directory: existing filenames can be replaced. This command writes review files; it does not append to a master workbook or admit evidence into a sealed package. Those separate mutation workflows are documented in [the BLASTP protocol](../ONLINE_BLASTP_PROTOCOL.md).

## What the parser accepts

The parser handles:

- headerless Hit Table CSV,
- query titles containing pipes,
- query titles containing semicolons,
- query titles containing colons,
- query titles containing unquoted commas,
- more than 10 hits per query,
- XML2 files with query-title metadata,
- Hit Table only,
- XML2 paired with Hit Table.

XML2 enrichment is a metadata join, not exact-query admission. After an exact query-title lookup fails, the fallback can match only BGC alias plus gene label and take the first matching result; it does not verify strain or query-sequence hashes. Keep input batches source-bound and independently reconcile query/result identities before using enriched titles, lengths or coverage as current-gene evidence.

## Hit Table layouts

This command accepts a Hit Table with or without a header row. A header row is read by column name. The separate `ingest-blastp` command, which loads results into a workbook, takes only the original headerless 12- or 13-column CSV and rejects a header. See [the BLASTP protocol](../ONLINE_BLASTP_PROTOCOL.md).

For a headerless row, the parser works from the end of the row:

- A row with exactly 12 fields is read as is.
- Otherwise it looks for a unique run of 10 or 11 trailing metric fields. Eleven means the % positives column is present; ten means it is not. The field before that run is the subject. Everything before the subject is the query title, rejoined with commas, so unquoted commas in a title are repaired.
- If the layout is ambiguous or does not fit, the run stops with `HIT_TABLE_LAYOUT_UNRESOLVED`. Supply a table with a header row.
- A row with fewer than 12 fields, or one whose percent identity or bit score cannot be read, is skipped. It is not stored as a zero hit.

Keep the original Hit Table beside the parsed output.

## Required outputs

The implemented output set is:

- `BLASTP_hit_table_normalized.csv`: parsed hit rows;
- `BLASTP_query_summary.csv`: one selected top hit and decision per observed query;
- `BLASTP_reprioritization.csv`: the same query-level rows for sorting;
- `BLASTP_followup_summary.json`: counts and optional next-batch metadata;
- `BLASTP_FOLLOWUP_USER_GUIDE.md`: interpretation and file guide;
- `BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa`: only when both `--previous-selection` and `--panel-dir` are supplied. It can be empty when nothing qualifies.

Rows in `BLASTP_query_summary.csv` carry these columns, among others: `query_id`, `strain`, `bgc_id`, `gene`, `top_accession`, `top_title`, `top_identity`, `top_query_coverage`, `top_evalue`, `top_bitscore`, `followup_decision`, `followup_priority` and `followup_reason`. `top_query_coverage` is alignment length divided by query length, capped at 1. The query length comes from the XML2 file when one is supplied, otherwise from an `aa=` field in the query ID (as the panel exporter writes it). When neither gives a length, the cell reads `NA`; it is never blank and never 1.0. A length read from the query ID is the header's declared value, not a check against the protein that was searched. A good run has one row per query that returned a hit, each with a decision label from the list below.

BGC metadata can occur in query rows, but this command does not write a separately aggregated BGC summary. Queries absent from the Hit Table are not automatically censused as no-hit queries. Reconcile searched and returned query IDs against the original panel before interpreting missingness. The optional next batch excludes only queries observed in the parsed hit rows, so previously submitted queries without a returned hit row can be selected again. Reconcile that FASTA against the original submission/no-hit ledger and receipts before any new submission; the previous-selection manifest alone does not establish which queries completed.

Exit status is 0 when at least one query was parsed and 1 when no query was parsed. Files may already exist after a zero-query result; their existence alone is not success.

## Decision labels

Current `classify_followup` labels are:

- `DOWNGRADE_CONFIRMED_REDUNDANT`
- `RETAIN_PROOF_RELEVANT`
- `RETAIN_CONTEXT_RELEVANT`
- `UPGRADE_WEAK_OR_PARTIAL`
- `UPGRADE_UNINFORMATIVE_TOP_HIT`
- `ISOLATE_GIANT_OR_DOMAIN_FOLLOWUP`
- `REVIEW_AMBIGUOUS`

`UPGRADE_NO_HIT` is defined for an absent hit passed to the classifier, but the current summary iterates observed hit queries. Do not assume every searched zero-hit query receives that row. These labels guide review; “confirmed redundant” does not confirm a molecule or biological phenotype.
