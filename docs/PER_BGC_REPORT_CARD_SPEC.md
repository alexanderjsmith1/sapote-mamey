# Per-BGC L0–L3 report-card contract

This documents the shipped `report-card` command in the .447 bundle. It is an automatic Markdown overview from package CSVs, with authored L2/L3 slots. It does not replace the full Mode B card, evidence verification, or scientific-owner review. The old .196-era design text and proposed integrations are superseded here as current usage instructions.

## Command and outputs

```text
python mamey_run.py report-card --package <bound-package> --bgc <package-scoped-alias> --out <new-markdown-path>
```

Run with the selected compatible interpreter from the bundle root containing `mamey_run.py`. Omitting `--bgc` selects all triage rows; omitting `--out` emits Markdown to the console. The lookup alias is scoped to the bound package. Always preserve full strain / full node-or-contig / region / BGC alias in the reviewed report and source crosswalk. The command does not validate those components as a complete identity gate.

Layers are L0 overview with heuristic badges/action text, L1 package-predicted polymer/SMILES, L2 annotation/comparator context and authoring, and L3 provenance and unresolved-evidence context. Successful command completion is not evidence that all layers are authored or verified.

## Exact current input behavior

The consumer reads the package's triage, predicted-polymers and NRPS prediction CSVs. Strain selection can fall back to the package directory name when expected CSV naming is absent; engine version is read from the package manifest with explicit fallbacks. It has no input/hash/output receipt or freshness admission. Independently bind package identity, input hashes, engine/workflow version and output hash.

Polymer lookup uses contig plus normalized region number and keeps the longest polymer when duplicates share that key. Module lookup uses the `ctg<N>_` locus prefix from a `NODE_<N>` contig; it does **not** restrict modules to the exact antiSMASH region. Multiple regions on the same node can therefore borrow each other's module rows. Public accession contigs without that node pattern receive no modules through this adapter. Reconcile every included module against the exact-region gene roster before accepting the card; do not interpret missing modules as absent biology. A code-owner fix should join explicit exact-region membership rather than a contig prefix.

## Badge and molecule interpretation

Novelty, activity and tractability labels are legacy heuristic routing fields. They do not establish chemical novelty, product identity, phenotype, or experimental feasibility. KCB similarity is a comparator channel; lack of a strong match is measured database/context missingness, not a global novelty result. Source AB/AF priors are not measured extract bioactivity and cannot be assigned to an individual BGC. Generated actions are suggestions, not approved scientific decisions.

Mass calculation is optional RDKit processing of the supplied wildcard-free SMILES. Missing, wildcard, unparsable or unavailable-RDKit states remain pending/error states. The command does not repair unknown polymer positions from prediction tables. A calculated formula/mass describes the supplied candidate structure; it does not identify a detected molecule, establish a pathway product, or bind assay evidence. Keep assembly truncation and structure uncertainty explicit.

The cross-channel join key is exact source-scoped locus/gene/sequence identity and appropriate receipts, not an unverified predicted structure. Molecular comparisons and assay/LC-MS observations require their own identifiers and evidence, with no automatic transfer of compound, activity, or causality claims.

## Completion and recovery

The command can return 0 with zero cards when the requested alias is not found. Existing output Markdown is overwritten; parent directories are created. A rescue-provider problem yields an unresolved warning rather than evidence of no rescue. Use a fresh output path, inspect the selected-card count and each warning, and verify expected regions/modules against the source roster. Keep the original automatic card and a separately bound reviewed revision.

For current Mode B work, `verify-modeb` offers `full48` (default) and `current50_v2`; choose the actual work-order contract explicitly. The old §1–§20 description is not the current verification profile. See [two-stage modular reports](TWO_STAGE_MODULAR_BGC_REPORTS.md) and the separate page-layout contract for rendering requirements. No legacy badge, source-artwork file, or zero exit grants scientific acceptance or release.

Source owners: `mamey/cli.py:7241–7255,7725–7735`; `mamey/report_card.py:46–62,90–159,176–181,272–340,348–395`.
