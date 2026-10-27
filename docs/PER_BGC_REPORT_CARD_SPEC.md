# Make a quick per-BGC overview

Use `report-card` when you want an automatic Markdown overview from package CSVs, with slots for authored interpretation. For a full authored Mode B card, follow the [card walkthrough](MODE_B_USER_WALKTHROUGH.md) instead. This page describes the shipped command; older designs are historical.

## 1. Generate the overview

```text
python mamey_run.py report-card --package <bound-package> --bgc <package-scoped-alias> --out <new-markdown-path>
```

Run with the selected compatible interpreter from the bundle root containing `mamey_run.py`. Omitting `--bgc` selects all triage rows; omitting `--out` emits Markdown to the console. The lookup alias is scoped to the bound package. Always preserve full strain / full node-or-contig / region / BGC alias in the reviewed report and source crosswalk. The command does not validate those components as a complete identity gate.

Read the output by layer:

| Layer | What to read or complete |
|---|---|
| L0 | Overview, heuristic badges and suggested actions; check their scope before using them. |
| L1 | Package-predicted polymer/SMILES; retain unknown positions and structure uncertainty. |
| L2 | Annotation/comparator context and authoring slots to fill from admitted evidence. |
| L3 | Provenance and unresolved-evidence context to review and complete. |

Successful command completion does not mean all layers are authored or verified.

## 2. Confirm the selected card before authoring

After generation, check that the requested card is present. The command can return 0 with zero cards when the requested alias is not found. Existing output Markdown is overwritten; parent directories are created. A rescue-provider problem yields an unresolved warning rather than evidence of no rescue. Use a fresh output path, inspect the selected-card count and each warning, and verify expected regions/modules against the source roster.

## 3. Reconcile the input rows

The consumer reads the package's triage, predicted-polymers and NRPS prediction CSVs. Strain selection can fall back to the package directory name when expected CSV naming is absent; engine version is read from the package manifest with explicit fallbacks. It has no input/hash/output receipt or freshness admission. Independently bind package identity, input hashes, engine/workflow version and output hash.

Polymer lookup uses contig plus normalized region number and keeps the longest polymer when duplicates share that key. Module lookup uses the `ctg<N>_` locus prefix from a `NODE_<N>` contig; it does **not** restrict modules to the exact antiSMASH region. Multiple regions on the same node can therefore borrow each other's module rows. Public accession contigs without that node pattern receive no modules through this adapter. Reconcile every included module against the exact-region gene roster before accepting the card; do not interpret missing modules as absent biology. A code-owner fix should join explicit exact-region membership rather than a contig prefix.

## 4. Author within the evidence

Novelty, activity and tractability labels are legacy heuristic routing fields. They do not establish chemical novelty, product identity, phenotype, or experimental feasibility. KCB similarity is a comparator channel; lack of a strong match is measured database/context missingness, not a global novelty result. Source AB/AF priors are not measured extract bioactivity and cannot be assigned to an individual BGC. Generated actions are suggestions, not approved scientific decisions.

Mass calculation is optional RDKit processing of the supplied wildcard-free SMILES. Missing, wildcard, unparsable or unavailable-RDKit states remain pending/error states. The command does not repair unknown polymer positions from prediction tables. A calculated formula/mass describes the supplied candidate structure; it does not identify a detected molecule, establish a pathway product, or bind assay evidence. Keep assembly truncation and structure uncertainty explicit.

The cross-channel join key is exact source-scoped locus/gene/sequence identity and appropriate receipts, not an unverified predicted structure. Molecular comparisons and assay/LC-MS observations require their own identifiers and evidence, with no automatic transfer of compound, activity, or causality claims.

## 5. Save for review or continue to a full card

Keep the original automatic overview and a separately bound reviewed revision, with source paths/hashes, output hash and unresolved warnings. Successful generation does not replace evidence verification or scientific-owner review.

For current Mode B work, `verify-modeb` offers `full48` (default) and `current50_v2`; choose the actual work-order contract explicitly. The old §1–§20 description is not the current verification profile. See [two-stage modular reports](TWO_STAGE_MODULAR_BGC_REPORTS.md) and the separate page-layout contract for rendering requirements. No legacy badge, source-artwork file, or zero exit grants scientific acceptance or release.
