# SOP-17 — cross-strain GCF cohort with BiG-SCAPE

**Status:** active SOP. `docs/LLM_COMPANION_TOOL_PROTOCOL.md` and
`docs/BIGSCAPE_GCF_WORKFLOW.md` bind this procedure.

## Purpose

Build a source-preserving, resumable family-similarity layer across antiSMASH BGC regions and emit
portable cohort tables. This SOP does not assign compound identity, production, activity, or
universal novelty, and it does not edit sealed Mamey outputs by default.

## Procedure

1. Resolve the current bundle, cohort registry, and BiG-SCAPE workspace. Read `CURRENT_RUN.txt` and
   verify an existing handoff before creating a run.
2. Select exact strain inputs and inventory their antiSMASH ZIP hashes, region-member counts, bytes,
   locators, and antiSMASH versions.
3. Stage region GBKs as content-addressed objects with strain-prefixed run links. Quarantine
   AppleDouble/malformed/colliding records; preserve a row for every exclusion.
4. Probe BiG-SCAPE, HMMER, Pfam, and FastTree names/versions. Hash the HMM assets.
5. Declare `cohort-only` or an approved reference-augmented design. Do not auto-download MIBiG.
6. Show the preflight: BGC/strain/reference counts, bytes, core plan, runtime/disk estimate, output
   root, and mutation/network boundaries.
7. Run the exact recorded BiG-SCAPE 2.x command at cutoffs 0.3, 0.5, and 0.7. Default one core;
   surface two and four as user options.
8. On interruption, inspect state/log/database before retrying. Reuse cache only when the immutable
   input manifest and scientific parameters are unchanged.
9. Select the exact completed database run ID. QA count parity, integrity, families, memberships,
   distances, exclusions, and reference loading.
10. Export a locator-keyed TSV plus HTML/network/tree products, checksums, and `HANDOFF.md`.
11. Interpret families as within-run related architecture. In cohort-only mode, never emit
   KNOWN/NOVEL. In a reference run, say “MIBiG-anchored” or “unanchored in this panel.”
12. If the user separately authorizes reconciliation, add source-preserving overlays to Mode B or
   triage products and retain original hashes. Do not silently mutate canonical cards.

## Portable join key

Use `(source_run_id, cutoff, strain, bgc_id, contig·region)` for memberships. Retain the local
database `family.id` for display/audit only. Never join separate runs or databases by `family.id` or
viewer `FAM_#####` labels.

## Required receipts

- immutable run manifest and state history;
- source/member/input-view checksums and exclusion ledger;
- exact tool versions, Pfam hash, command, cores, and logs;
- exact completed run ID and SQLite integrity result;
- input/database/export count reconciliation;
- cutoff-specific family and membership denominators;
- portable GCF TSV, output manifest, QA report, and handoff;
- claim ceiling and reference-panel statement.

## Stop conditions

Stop at `HOLD` rather than improvising when the HMM assets are inconsistent, region/member counts do
not reconcile, locators collide, the requested run would exceed the approved resources, references
require an unapproved download, no exact completed run can be identified, or canonical mutation has
not been authorized.
