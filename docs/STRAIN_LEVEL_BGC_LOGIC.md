# Strain-level BGC logic reports

`tools/strain_level_bgc_logic.py` converts the source-bound BGC and gene-level functional workups into readable strain reports. It does not average a strain into one biological claim. It ranks each complete-identity locus within its strain and then summarizes the strongest pathway-family hypotheses, boundary limitations, annotation-supported unmatched genes, and HIGH RG-GMCI fragment pairs.

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

## Source binding and acceptance limits

The source command accepts an existing output directory and overwrites fixed paths; the `--out` description above is the recommended safe use, not an enforced refusal. `PASS` records mechanical report completion and does not independently verify upstream functional/reference/RG-GMCI admission. An empty workup can fail at `rows[0]` after comparison outputs were written; an old receipt in a reused output directory is not a receipt for that failed attempt. Missing or malformed numeric inputs can become default numeric values in the scoring helper. Review input completeness and preserve missingness; do not interpret a displayed score as an independently measured biological result.

The coordinate adapter joins on `(strain, BGC alias, locus tag)` and takes the last duplicate key. It carries contig/region fields but does not compare them to the ledger's full locus identity during this join. Supply only the exact package/version selected for the workup, reject duplicate coordinate keys, and independently check every matched contig/region. The receipt hashes the package-list text, not the referenced CDS tables. Bind each coordinate table hash separately.

HIGH pair grouping uses the input confidence text beginning with `HIGH` and a present partner identity in the same strain table. It does not require a reciprocal partner call or validate an RG-GMCI receipt. The top-ten limit is ten **review units**, so pairs can make more than ten loci visible; lower-ranked HIGH pairs are not all included there. Verify pair provenance and retain unrepresented pairs in the all-locus/summary census.

Dense SVGs can suppress `other` labels without a shown/total suppression counter. These maps are not automatically compliant with the [locus-map review contract](LOCUS_MAP_REVIEW_CONTRACT.md). The SVG may be a gene-order schematic when any coordinates are missing; this is not evidence of genomic spacing or linkage. Keep the full protein table, verify the expected gene roster and label visibility, and inspect final reader-size maps before acceptance.

Use a fresh output folder, separately record input-package and emitted artifact hashes, and diagnose a failed build before reusing any receipt. Source owners: `tools/strain_level_bgc_logic.py:58–62,133–169,178–192,198–229,268–307,375–377`.

The cross-strain Markdown currently prints “42 package-backed AS strains” literally. It is not calculated from the input roster. Reconcile and correct that denominator in a separately bound reviewed copy, retaining the actual distinct strain/locus census. Source: `tools/strain_level_bgc_logic.py:323,327`.
