# Deep BGC Report to Thesis Handoff Quick Start

This guide explains how to turn governed, user-supplied locus evidence into a readable deep report, an experimental decision tree, and a compact thesis handoff. The tools package evidence; they do not identify a compound, prove expression or activity, or turn workspace files into bundled product data.

## Quick start

1. Place a neutral locus JSON and optional evidence TSV under a caller-chosen input root.
2. Build the report with `tools/build_deep_bgc_report.py`.
3. Review `REPORT_RECEIPT.json` and resolve any identity, boundary, or gene-slice hold.
4. Add the safe relative receipt locator to a leads TSV and run `tools/build_activity_decision_trees.py`.
5. Add selected reports, maps, receipts, explicit gaps, and claim ceilings to a handoff index TSV.
6. Run `tools/build_thesis_handoff.py` and verify the receipt reports `zip_crc: PASS`.

The module references provide the exact commands: [deep report](../modules/DEEP_BGC_REPORT.md), [activity decisions](../modules/ACTIVITY_DECISION_TREES.md), and [thesis handoff](../modules/THESIS_HANDOFF.md).

## Exact identity

Every locus is named in this order:

`strain / full node-or-contig / region / BGC alias`

For example: `SYNTHETIC-001 / contig_demo_0001_complete / region001 / BGC007`.

The alias is secondary. Two rows that share `BGC007` are not the same locus unless strain, full node or contig, and region also agree. The tools refuse partial identity and do not infer missing fields from filenames.

## Evidence channels

The canonical gene roster defines the admitted slice. Evidence rows may describe domains, gene roles, or reference-comparator observations, but each row must bind to the complete identity and a canonical gene. If the locus record supplies a protein SHA-256, the evidence row must carry the same hash.

Keep channel meanings separate. A domain supports a possible biochemical role. A reference match helps navigate family-level hypotheses. A chemical feature is a measured signal. An activity assay is phenotype evidence. None substitutes for the others, and a missing channel is a workflow gap rather than a verified absence.

## Overmerge and gene-slice examples

An antiSMASH region may contain a coherent matched component plus unrelated flanking genes. In that case, retain the whole-region fraction, such as `12/24`, and separately report a defensible local component, such as `10/11`, with contiguity, gene order, and core completeness. Mark the boundary as `OVERMERGED_SUSPECTED`. This preserves the boundary problem without automatically weakening the coherent component or resolving product identity.

A gene-slice mismatch is different. If `canonical_gene_count` says 11 but the JSON contains 10 genes, or evidence names `gene_012` outside the admitted roster, the builder stops before creating output. Correct the upstream slice or evidence binding; do not enlarge the roster merely to make the error disappear.

## Reading the deep report

Start with the claim ceiling and boundary status. Then read the locus map and gene table for coherent core architecture, gene order, tailoring context, transport, and regulation. Treat comparator components as navigation evidence. A convincing family-level hypothesis requires coherent core biosynthetic architecture plus supporting context, not one isolated match.

## Using the metabolomics and activity decision tree

The generated sequence is deliberately conservative:

1. Establish expression under a defined condition.
2. Establish genetic linkage with a perturbation or orthogonal genotype.
3. Establish a reproducible chemical feature with blanks and replicates.
4. Establish activity with counterscreens, dose response, and matrix controls.
5. Advance only the narrowest claim supported across the available channels.

Record a failed or unrun gate as evidence required. Do not turn absence of a test into a biological negative.

## Building the thesis handoff

Use a caller-selected `--input-root`. In the handoff TSV, point to reports, maps, receipts, and optional activity trees using relative paths beneath that root. Supply an explicit gaps statement and claim ceiling for every complete locus identity. The packager copies only listed artifacts, writes an index and gap ledger, hashes each member, builds a deterministic ZIP, and performs a CRC check.

The handoff is compact evidence for writing and review. It is not a Sapote-Mamey release, an integration receipt, or owner acceptance.

## Browser assistant workflow

A browser assistant may help inspect a rendered report or navigate user-authorized evidence, but it should work from the generated index and receipts. Confirm the complete locus identity before opening a source, keep the configured input root visible, and record any downloaded or exported source as a new governed input with its own provenance. Never paste a private workspace path into bundled documentation or teach the program to discover a particular personal folder.

## Troubleshooting

- `missing ... exact-locus identity`: provide all four identity components; do not substitute the alias.
- `evidence exact identity mismatch`: correct the row whose strain, full node or contig, region, or alias differs.
- `gene-slice mismatch`: reconcile the declared count with the canonical gene list.
- `outside canonical gene slice`: bind the evidence to an admitted gene or correct the upstream slice.
- `protein hash mismatch`: locate the correct sequence-derived evidence; do not overwrite the hash.
- `artifact locator escapes configured root`: replace the absolute or parent-traversal path with a relative locator beneath `--input-root`.
- `report receipt exact identity mismatch`: rebuild or select the receipt for the same complete locus.
- Existing output directory: choose a fresh handoff directory so earlier evidence is not silently overwritten.

## Glossary

- **BGC**: biosynthetic gene cluster.
- **Canonical gene slice**: the explicit gene roster admitted for this report.
- **Claim ceiling**: the strongest statement currently allowed by the evidence.
- **Comparator**: a reference used to navigate a family-level hypothesis, not to assert product identity.
- **Exact identity**: strain, full node or contig, region, and BGC alias in that order.
- **Evidence channel**: a distinct source type such as domains, reference comparisons, metabolomics, genetics, or activity.
- **Overmerge**: a predicted region that likely joins a coherent component with unrelated flanking sequence.
- **Receipt**: a machine-readable record binding inputs, outputs, identities, and hashes.
