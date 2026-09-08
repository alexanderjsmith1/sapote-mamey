# SOP-Derived Bug Hunt Matrix — v9.7.142

This matrix converts SOP expectations into pre-cut bug-hunt checks.

## Top blockers to attack first

1. BLASTP Hit Table parser must not corrupt percent identity when query titles contain commas.
2. Public-facing outputs must not leak private AS/SID labels.
3. BLASTP/KCB evidence must not be promoted to compound identity.
4. C5 deliverables must not emit placeholders as if real.
5. Single-region public accession inputs must not be framed as failed full-genome runs.

See `SOP_DERIVED_BUGHUNT_MATRIX.csv` for the full table.
