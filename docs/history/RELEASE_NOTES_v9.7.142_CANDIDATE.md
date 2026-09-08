# Release Notes — Sapote/Mamey v9.7.142 Candidate

Status: candidate for Claude sign-off, not signed release until reviewed.

Main additions:

- Iterative NCBI BLASTP FASTA batching for BGC evidence.
- BLASTP follow-up parser for Hit Table CSV and optional XML2.
- Headerless CSV and comma-bearing query-title hardening.
- Durable BLASTP evidence store preserving raw NCBI files, parsed per-round tables, cumulative tables, manifests, and checksums.
- Single-region public accession intake rule for KY089035-style antiSMASH ZIPs.
- C5/C7 starter hardening from REV2.
- SOP library and SOP-derived bug-hunt matrix.

Known caveats for sign-off:

- This is a candidate packet, not a signed final release.
- Full all-file pytest was not rerun during rapid cut preparation; use focused validation evidence plus Claude sign-off before promotion.
- C5/C7 remains staged as starter hardening and should be audited in candidate context.
- Live NCBI RID retrieval is not included; workflow is offline-first using user-downloaded Hit Table CSV/XML2.
