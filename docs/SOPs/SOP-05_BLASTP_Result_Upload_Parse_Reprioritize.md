# SOP-05 — BLASTP Result Upload, Parse, and Reprioritization

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
python -m mamey blastp-followup --hit-table <HitTable.csv> --xml2 <Alignment.xml> --outdir <outdir>
```

XML2 should be optional. Hit Table CSV should be enough for triage.

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

Each parse should produce:

- normalized hit table,
- query-level summary,
- BGC-level summary when BGC IDs are available,
- reprioritization table,
- follow-up user guide,
- optional next FASTA batch.

## Decision labels

Recommended labels:

- `DOWNGRADE_CONFIRMED_REDUNDANT`
- `RETAIN_PROOF_RELEVANT`
- `RETAIN_CONTEXT_RELEVANT`
- `UPGRADE_UNINFORMATIVE_TOP_HIT`
- `ISOLATE_GIANT_OR_DOMAIN_FOLLOWUP`
- `RERUN_MORE_DIAGNOSTIC_PROTEIN`
- `SEND_RELATED_GENOME_TO_ANTISMASH`
- `NO_ACTION_LOW_VALUE`

## Bug-hunt checks

1. Headerless CSV first row must not be dropped.
2. Rows with unquoted commas in query title must not shift columns.
3. Percent identity must never become 0 because of CSV shift.
4. XML2 enriches but does not replace hit-table parsing.
5. Missing XML2 must not fail triage.
6. More than 10 hits/query must be preserved.
7. Output must include next-action labels.
8. Parser must not promote BLASTP evidence to compound identity.
