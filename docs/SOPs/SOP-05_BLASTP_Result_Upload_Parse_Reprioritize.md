# SOP-05 — BLASTP Result Upload, Parse, and Reprioritization

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


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

XML2 is optional. Omit `--xml2` when no XML2 file exists; do not pass a fabricated placeholder path. Hit Table CSV can provide triage while unknown query lengths/coverage remain unknown. Use a fresh external output directory: existing filenames can be replaced. This command writes review files; it does not append to a master workbook or admit evidence into a sealed package. Those separate mutation workflows are documented in [the BLASTP protocol](../ONLINE_BLASTP_PROTOCOL.md).

## Required parser behavior

The parser must handle:

- headerless Hit Table CSV,
- query titles containing pipes,
- query titles containing semicolons,
- query titles containing colons,
- query titles containing unquoted commas,
- more than 10 hits per query,
- XML2 files with query-title metadata,
- Hit Table only,
- XML2 paired with Hit Table.

## Headerless CSV recovery rule

When a headerless NCBI Hit Table row contains commas inside the query title, the parser should treat the final stable BLASTP numeric/subject fields as the anchor fields and reconstruct the query title from the preceding fields.

## Required outputs

The implemented output set is:

- `BLASTP_hit_table_normalized.csv`: parsed hit rows;
- `BLASTP_query_summary.csv`: one selected top hit and decision per observed query;
- `BLASTP_reprioritization.csv`: the same query-level rows for sorting;
- `BLASTP_followup_summary.json`: counts and optional next-batch metadata;
- `BLASTP_FOLLOWUP_USER_GUIDE.md`: interpretation and file guide;
- `BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa`: only when both `--previous-selection` and `--panel-dir` are supplied. It can be empty when nothing qualifies.

BGC metadata can occur in query rows, but this command does not write a separately aggregated BGC summary. Queries absent from the Hit Table are not automatically censused as no-hit queries. Reconcile searched and returned query IDs against the original panel before interpreting missingness.

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

## Bug-hunt checks

1. Headerless CSV first row must not be dropped.
2. Rows with unquoted commas in query title must not shift columns.
3. Percent identity must never become 0 because of CSV shift.
4. XML2 enriches but does not replace hit-table parsing.
5. Missing XML2 must not fail triage.
6. More than 10 hits/query must be preserved.
7. Output must include next-action labels.
8. Parser must not promote BLASTP evidence to compound identity.
