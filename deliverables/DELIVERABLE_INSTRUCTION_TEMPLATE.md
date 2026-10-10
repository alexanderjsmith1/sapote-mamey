# Source-bound deliverable request template

Fill every relevant field. Unknown inputs or authority remain explicit holds; this template does not authorize fetching, rescanning, mutation, external messaging or publication.

## Request

- Deliverable ID and version: `<id / version>`
- Owner and intended reader: `<owner / human, LLM or both>`
- Goal and exact output format: `<question / Markdown, table, figure, deck, etc.>`
- Builder: `<named shipped workflow, owning source path and declared command>`
- Input package/bank/workbook: `<absolute paths, schema/version, SHA-256, cohort membership and provenance>`
- Individual locus: `<strain / full node-or-contig / region / BGC alias>`; keep all four fields even when a display alias is used.
- Selection and denominator: `<explicit roster/filter; count convention; inclusion/exclusion and missingness>`
- Output destination: `<fresh absolute path; filename/version; expected artifacts>`
- Mutation scope: `<which working files may change, backups and concurrency assumptions>`
- Privacy/release scope: `<actual profile and authorized audience; unresolved policy means held>`

## Method and evidence

Verify input existence and source bindings first. Do not assume `merged_cohort` is populated or current. Use the [task router](../docs/USER_TASK_ROUTER.md) and the tool's declared parser; tools do not share a universal `--banked-dir ... --out` interface. Specify the working directory and environment. Prefer fresh destinations and working workbook copies where a command rewrites sheets.

Separate deterministic extraction/rendering from bounded interpretation. For every claim or number, record input file/hash, field/row, denominator and transformation. For each individual locus, preserve the complete four-part identity. A KCB/MIBiG match is a similarity anchor; lack of an anchor is unresolved reference coverage, not proof of novelty. Predictions and workflow CONFIRM/status labels do not establish a product, activity or experimental confirmation. Only supplied, typed, strain-bound assay metadata may support assay wording; otherwise use `NOT_SUPPLIED` or the source's explicit missing state. Never impute an assay target or inactivity.

If using an adjusted count such as Interior + 0.5 × Edge + 0.25 × Full-contig, name it as that workflow's weighting convention, show raw counts and explain the denominator. Do not present a heuristic as a validated census. Colours may distinguish source/status categories, with a literal legend; avoid assigning biological confidence from colour alone.

## Acceptance and hand-back

- [ ] Requested roster, complete identities, hashes and schema/version recorded.
- [ ] Declared command and dependencies checked; actual run receipt distinguished from source-only review.
- [ ] Expected output files exist, are current, readable and individually hash-bound.
- [ ] Tables/figures match source rows and declared denominator; missing and held states remain visible.
- [ ] Evidence limits, privacy scope and unresolved code/data issues stated.
- [ ] Requested formats verified; rendered pages inspected if visual QA is claimed.
- [ ] Completion is limited to the accepted deliverable and does not imply whole-suite or scientific adoption.

Return output paths, evidence/check receipt, unresolved holds and one bounded next action. Update a tracking board only if the actual board is supplied, its row is bound and the user authorized the update. This CODE bundle contains no `HIVE_Board.csv`; do not fabricate a DONE receipt.

The [manifest/checker guide](../docs/DELIVERABLE_MANIFEST_TEMPLATE.md) explains why the legacy suite checker cannot replace file, hash, identity or content checks. Use the [incoming figure handoff](incoming_figures/README.md) when incorporating artwork from another workflow.
