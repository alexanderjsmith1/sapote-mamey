# Mamey v1.9.152 ChatGPT Batch Protocol

## Batch 0 — Intake smoke test

- Confirm bundle version.
- Confirm input ZIPs are antiSMASH outputs.
- Inspect for region GBKs and clusterblast/knownclusterblast/subclusterblast folders.
- Confirm or infer strain IDs.

## Batch 1 — Extraction foundation

- Parse BGC inventory.
- Compute assembly metrics and edge/fragmentation state.
- Extract KCB evidence from TXT files.
- Compute corrected BGC counts and depth-floor flags.
- Write per-strain workbook and master workbook.

## Batch 2 — Source-derived scans

- KCB sweep.
- RG-GMCI reference-guided gapped multi-contig integration (split-BGC pairing from clusterblast/knownclusterblast TXT files; mandatory for multi-contig genomes).
- FLBR / large-BGC fragmentation review.
- CCTT cryptic-class triggers.
- Chitin/CGAD and glycan/ecology readiness.
- UMED maturation-enzyme gap review.
- EFLS edge/flank/linkage readiness from available evidence.
- Resistance/self-protection scan.
- bldA/TTA scan.
- TFBS/regulation scan.

## Batch 3 — Package and validation

- Write manifest and project-memory alias.
- Write issue log and commit receipt.
- Write `gate_validation.json`.
- Write checksums.
- Create per-strain package ZIP.
- Create combined batch ZIP.

## Batch 4 — Triage/judgment handoff

- Produce ranked extraction-side triage board.
- Identify top antibacterial and antifungal leads.
- Mark `MAMEY_COMPLETE` when extraction is finished and all BGCs have depth-floor assignments. This is the normal end state of a ChatGPT extraction pass — judgment is handled by Claude/Sapote in a separate session.
- Assign judgment batches.

## Batch 5+ — Mode B and reader outputs

- Full Mode B for all BGCs required by Standard depth floor.
- In gold/archive mode, full Mode B or ledger for every BGC.
- Literature deep dives for top antibacterial and antifungal leads.
- Wet-lab detection/isolation guidance.
- Reader-facing PDFs and final ZIP when requested.

## Non-negotiables

- Do not reduce depth to fit a session; batch instead.
- Do not call extraction-only output a completed judgment run.
- Every BGC must be accounted for by locked ID.
- Every deferred item must have a reason and next batch assignment.
- Treat ChatGPT runtime limits as normal operating constraints, not workflow failure.

