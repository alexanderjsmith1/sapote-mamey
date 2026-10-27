# SOP-17 — cross-strain GCF cohort with BiG-SCAPE

Read [the companion tool protocol](../LLM_COMPANION_TOOL_PROTOCOL.md) and the [GCF workflow](../BIGSCAPE_GCF_WORKFLOW.md) first.

## Purpose

Build a source-preserving, resumable family-similarity layer across antiSMASH BGC regions and emit
portable cohort tables. This SOP does not assign compound identity, production, activity, or
universal novelty, and it does not edit sealed Mamey outputs by default.

## Procedure

1. Find the current bundle, the cohort registry and the BiG-SCAPE workspace. Check for an existing
   run and handoff before you create a new one.
2. Select exact strain inputs and inventory their antiSMASH ZIP hashes, region-member counts, bytes,
   locators, and antiSMASH versions.
3. Stage region GBKs as content-addressed objects with strain-prefixed run links. Quarantine
   AppleDouble/malformed/colliding records; preserve a row for every exclusion.
4. Probe BiG-SCAPE, HMMER, Pfam, and FastTree names/versions. Hash the HMM assets.
5. Declare `cohort-only` or an approved reference-augmented design. Do not auto-download MIBiG.
6. Show the preflight: BGC/strain/reference counts, bytes, core plan, runtime/disk estimate, output
   root, and mutation/network boundaries.
7. Run the exact recorded BiG-SCAPE 2.x command at cutoffs 0.3, 0.5, and 0.7. The interactive
   policy is one core; select the runner’s core flag explicitly. The generic `mamey_run.py bigscape`
   parser defaults to four without `--cpus 1`, while `tools/bigscape_pipeline.py` defaults its
   separate `--cores` option to one. Surface two and four only as explicitly selected resource options.
8. On interruption, inspect state/log/database before retrying. Reuse cache only when the immutable
   input manifest and scientific parameters are unchanged.
9. Select the exact completed database run ID. QA count parity, integrity, families, memberships,
   distances, exclusions, and reference loading.
10. Export a locator-keyed TSV plus HTML/network/tree products, checksums, and `HANDOFF.md`.
11. Interpret families as within-run related architecture. In cohort-only mode, never emit
   KNOWN/NOVEL. In a reference run, say “MIBiG-anchored” or “unanchored in this panel.”
12. If the user separately authorizes reconciliation, add source-preserving overlays to Mode B or
   triage products and retain original hashes. Do not silently mutate canonical cards.

## Reader implementation limits

The procedure above is the required run contract, not a promise that one helper creates every
receipt. `bigscape_prep.py` writes strain-prefixed GBK copies and a strictness manifest; it
does not create content-addressed links or hash every accepted member. The pipeline’s optional
`--ingest-package` route mutates cards rather than implementing additive overlays. Resolve
these gaps through the [adapter boundary](../BIGSCAPE_GCF_WORKFLOW.md#implemented-adapters-versus-the-requested-runbook)
and retain the required source/member roster and receipts separately.

The cohort procedure above requires exact completed-run selection and count reconciliation. Some auxiliary family readers filter only by cutoff and can return 0 with empty, skipped or failed output rows. Their present behavior does not enforce all SOP gates. Read [the reader recovery guide](../../tools/BIGSCAPE_READER_RECOVERY.md), inspect per-output status tables and keep an explicit hold when the database contains unresolved/mixed run memberships. Never infer completion from the process exit status alone.

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
