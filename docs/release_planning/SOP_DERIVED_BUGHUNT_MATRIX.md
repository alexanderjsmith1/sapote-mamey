# SOP-Derived Bug Hunt Matrix — v9.7.142

## Historical expectations, current source binding

This matrix and [its CSV](SOP_DERIVED_BUGHUNT_MATRIX.csv) preserve v9.7.142 planning expectations and
REV3/REV4/REV5 status claims. They are not fresh tests or release receipts. The actual current panel and
follow-up parser owners are mamey/bgc_blastp_panel.py and mamey/blastp_followup.py, exposed by mamey/cli.py.
Parameterize a current reproducer from those parsers: the panel defaults to 2 representatives/BGC,
20 proteins/file, 30 first-pass proteins, 85,000 residues and a 2,500-aa giant threshold; these differ
from historical example/threshold wording in the CSV. Record selected values and actual input hashes.
Preparing FASTA does not submit an online search. Supplied Hit Table CSV/optional XML2 ingestion is a
separate input path; observed rows, metric fields and failures must be checked against actual saved inputs.

Current claim-safety and privacy/release gates have their own owners and scope. An old 'fixed' cell,
placeholder scan, matrix BLOCKER label or surrogate summary is not independent science, source binding,
whole-test-suite coverage or release approval. Use [current scoped entry](START_HERE_FOR_OTHER_CHATS.md)
and [release record guide](../RELEASE_RECORDS_GUIDE.md). Keep planned reproductions NOT_TESTED until they
run within the actual task; do not infer permission from historical test-input labels.

## Retained bug-hunt priorities

This matrix converts SOP expectations into pre-cut bug-hunt checks.

## Top blockers to attack first

1. BLASTP Hit Table parser must not corrupt percent identity when query titles contain commas.
2. Public-facing outputs must not leak private AS/SID labels.
3. BLASTP/KCB evidence must not be promoted to compound identity.
4. C5 deliverables must not emit placeholders as if real.
5. Single-region public accession inputs must not be framed as failed full-genome runs.

See `SOP_DERIVED_BUGHUNT_MATRIX.csv` for the full table.
