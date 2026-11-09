> Historical release notes. Current release status: [RELEASE_MANIFEST](../../RELEASE_MANIFEST.md).

# Release Notes — Sapote/Mamey v9.7.142 Candidate

Status: candidate awaiting sign-off, not a signed release. Historical: this status was never updated on this page. Current release status is in [RELEASE_MANIFEST](../../RELEASE_MANIFEST.md).

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
- Full all-file pytest was not rerun during rapid cut preparation; use focused validation evidence plus sign-off before promotion.
- Historical: this page names no receipt for the focused validation. A retained sign-off packet for this candidate (SHA-256 `d80957e253ce698b6671d0673b923baae4aab8abeff6fc23dd2fe231d9c228b7`) reports a focused test run that exited 1, then a rerun that exited 0 after a test assertion was corrected. A rerun does not show the full suite passed, and the unsigned and full-suite holds above stand.
- C5/C7 remains staged as starter hardening and should be audited in candidate context.
- Live NCBI RID retrieval is not included; workflow is offline-first using user-downloaded Hit Table CSV/XML2.
