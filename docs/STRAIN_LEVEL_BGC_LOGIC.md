# Strain-level BGC logic reports

`tools/strain_level_bgc_logic.py` converts the definitive BGC and gene-level functional workups into readable strain reports. It does not average a strain into one biological claim. It ranks each complete-identity locus within its strain and then summarizes the strongest pathway-family hypotheses, boundary limitations, annotation-supported unmatched genes, and HIGH RG-GMCI fragment pairs.

## Inputs

- `--bgc-workup`: `ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv` from Functional Logic Workup.
- `--gene-ledger`: optional `ALL_GENE_FUNCTIONAL_EVIDENCE.tsv`; when supplied, each top-locus report includes the annotation-supported genes outside the dominant reference.
- `--package-list`: optional newline-delimited list of sealed package directories. Each package must contain exactly one `*_cds_table.csv`; this adds CDS coordinates and strand to protein tables and locus maps.
- `--out`: a new output directory.

## Product-logic score

The starting value is the standalone biological evidence score from Definitive BGC Ranker. Transparent modifiers are then applied:

- architecture corroborates reference: +8;
- architecture support present: +4;
- architecture extends weak reference: +2;
- architecture-only without a reference: +1;
- architecture unresolved and reference-dominant: -3;
- reference match with unresolved architecture: -5;
- architecture/reference conflict: -12;
- both channels unresolved: -15;
- Edge boundary: -4;
- Full-contig boundary: -8;
- Tier A: +6; Tier B supported partial architecture: +3.

Generic PKS, NRPS, polyketide, or hybrid assembly-line evidence receives additional controls:

- Full-contig generic assembly-line call: -12;
- Edge generic assembly-line call: -6;
- fewer than four dominant-reference genes: -6;
- dominant-reference hit fraction below 0.15: -4.

The final score is clamped to 0-100. These modifiers create a strain-level review order; they are not probabilities or a replacement for the definitive biological-evidence score.

## Evidence bands

- `P1_STRONG_FAMILY_HYPOTHESIS`: score at least 70 without an architecture/reference conflict or jointly unresolved channels.
- `P2_SUPPORTED_FAMILY_HYPOTHESIS`: score 50-69.99.
- `P3_PROVISIONAL_CAPACITY`: score 30-49.99.
- `P4_FRAGMENT_OR_WEAK_SIGNAL`: score below 30.

Named compounds are displayed as like-family hypotheses. Architecture-only findings remain capacity hypotheses. The report retains the complete identity `strain / full node-or-contig / region / BGC alias` for every locus.

## Outputs

- `INDEX.html`: cohort navigation across all strains.
- `PER_STRAIN/<strain>/REPORT.html`: readable strain report with the top ten review units, evidence channels, protein size/function/domain/homology tables, coordinate-based locus maps, unmatched functional genes, and all-locus table. Each admitted HIGH RG-GMCI pair is co-located in one two-locus rescue unit.
- `PER_STRAIN/<strain>/REPORT.md`: manuscript-friendly Markdown version of the same top review units and protein tables.
- `PER_STRAIN/<strain>/LOCUS_MAPS/*.svg`: one coordinate-based map per locus in the top review units. If coordinates were not supplied, the SVG is explicitly labeled as a gene-order schematic scaled by protein length.
- `CROSS_STRAIN_BGC_COMPARISON.tsv` and `.md`: architecture-led groups occurring in at least two strains, with all complete identities, strain breadth, scores, and boundary counts. Each per-strain report includes its strongest cross-strain groups.
- `ALL_BGC_STRAIN_PRODUCT_LOGIC.tsv`: complete scored locus table.
- `STRAIN_LEVEL_SUMMARY.tsv`: one row per strain.
- `STRAIN_PRODUCT_FAMILY_SUMMARY.tsv`: family hypotheses summarized within each strain.
- `RECEIPT.json`: bound input hashes and output counts.

The outputs support prioritization and manuscript review only. They do not prove an exact product, complete pathway, expression, production, activity, novelty, physical linkage, or scientific acceptance.
