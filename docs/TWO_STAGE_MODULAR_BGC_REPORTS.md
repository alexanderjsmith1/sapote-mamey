# Two-stage modular BGC reports

Sapote-Mamey can reuse a large prior-report corpus without pretending that old
locators, rankings, BLASTP snapshots, or interpretations are current. The
report is assembled in two stages.

## Stage 1 — preliminary assembly

Stage 1 produces a useful internal report quickly. Its primary user locator is
the exact node or contig plus antiSMASH region. A historical `BGCnnn` value is
retained only as a source-scoped alias.

The stage can include:

- exact assembly, node, region, profile and sequence identity when available;
- exact gene, protein and domain inventory;
- exact profile-call records;
- channel-separated observed BLASTP rows with explicit receipt state;
- a hash-bound V7 literature-atlas section; and
- a hash-bound preliminary Mode B section.

Prior prose is marked `PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED`. Observed BLASTP
rows remain navigation evidence until submitted query bytes and database/run
receipts are bound. Missing channels are missingness, not biological absence.

## Stage 2 — verification and promotion

Stage 2 operates module by module. It does not require the entire report to be
rewritten whenever one database, assembly, or interpretation changes.

The normal promotion sequence is:

1. bind MiBIG and KnownClusterBlast one-to-many comparator children;
2. bind ClusterBlast subjects and ordered locus topology;
3. generate an exact editable locus/domain map;
4. compare strict, relaxed and loose profiles only across an exact compatible
   assembly/version boundary;
5. classify each inherited paragraph as retain, update, supersede, remap, or
   hold; and
6. run current Mode B verification against the complete consumed-evidence
   ledger.

MiBIG/KnownClusterBlast and ClusterBlast per-gene CSVs can be declared as
`comparator_sources` in an internal program specification. The builder writes
separate child tables and `COMPARATOR_EVIDENCE_LEDGER.tsv`; it never collapses
the channels. A locus-tag match to the exact-region inventory is recorded as
`LOCUS_TAG_IN_EXACT_REGION_QUERY_BYTES_UNBOUND`, not as exact submitted-query
admission. Source coverage above 100% is preserved in the raw column but
quarantined from the usable-coverage column until its denominator and HSP
aggregation policy are resolved.

Every module retains its source hash, state, promotion gate, and next required
tool or input in `REPORT_MODULE_STATUS.tsv` and the per-locus
`report_module_status.tsv` table.

The `attach-bgc-overlays` command consumes a frozen target ledger, a
hash-and-byte-verified review manifest, locator-first scientific-analysis rows,
and paragraph dispositions. It requires the reviewed assembly and exact region
key to match the immutable base `REPORT_INDEX.tsv`, verifies every indexed base
report, and rechecks the base, target, and review snapshots immediately before
atomic publication. Source-reported comparator coverage above 100 percent is
admissible only as an explicitly quarantined, non-usable provenance value. Its
output is deliberately small and additive: one reconciliation Markdown module
per reviewed locus, a locator-first `INDEX.md`, machine-readable
`REVIEW_INDEX.tsv`, `SCIENTIFIC_OVERLAY_LEDGER.tsv`,
`PARAGRAPH_DISPOSITION.tsv`, and `MODULE_STATE_DELTA.tsv`. A proposed state
delta never edits the base report or confers acceptance, integration,
biological validation, or release authority.

## Independent states

The following states must remain independent:

- source discovered;
- exact identity bound;
- evidence observed;
- query and run receipt admitted;
- module assembled;
- module verified current;
- interpretation reviewed;
- public export approved.

Passing one state never manufactures another. Similarity is not identity, and
biosynthetic capacity is not production, activity, novelty, or physical
linkage.

## Portable software boundary

The report builder ships inside the standalone Sapote-Mamey bundle. User data
does not. External evidence is resolved through logical root configuration and
a hash-bound source manifest. Reports contain logical evidence identifiers, not
hard-coded personal workspace paths.

## Builder, overlay, and current-card gates

The L0 program is implemented by `mamey/bgc_l0_program.py`; the additive overlay is `mamey/stage2_overlay.py`. A successful program build has status `DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED`. Read the module-state counts, exact-locus bridge states and individual ledgers, not just report count. The module status table records workflow/promotion states; source hashes are retained in the source/evidence/manifest records, rather than necessarily as a column in every module-status row. A `release=PUBLIC` selection governs a software/source-resolution route and is not owner approval.

The overlay's status is `PASS_PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED`. It hashes and rechecks snapshots and records proposed deltas, but does not run current Mode B validation or prove a reviewed paragraph's scientific correctness. Retain the immutable base with the overlay and its QA/artifact manifests; resolve holds in a separately authorized review, preserving prior states. Both builders refuse an already-existing final directory and publish from staging after their documented source checks. Use a new destination for changed inputs.

For work orders requiring the current 50-section card, the explicit profile is `current50_v2`; `verify-modeb` defaults to `full48`. Declare the contract and exact consumed-evidence/package bindings rather than relying on the default or an old §1–§20 layout reference. `--require-expanded-locus` is current50-only; a `--rescue-tsv` existence admission does not grant BGC membership to a gene outside a region. Verification is a separate action with its own receipt and does not establish publication or scientific adoption.

Source owners: `mamey/bgc_l0_program.py:809–837,1004–1068,1071–1118`; `mamey/stage2_overlay.py:337–351,589–613,641–692`; `mamey/cli.py:7241–7255`.
