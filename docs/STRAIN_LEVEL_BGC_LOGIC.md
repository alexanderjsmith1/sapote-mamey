# Strain-level BGC logic reports

`tools/strain_level_bgc_logic.py` turns the BGC workup and gene ledger into one readable report per strain. It ranks each biosynthetic gene cluster (BGC) within its strain. It then summarizes the strongest pathway-family hypotheses, boundary limits, annotated genes with no dominant-reference subject in the workup ledger, and high-confidence RG-GMCI fragment pairs. It does not average a strain into one biological claim. Terms such as KCB, RG-GMCI, Tier and Edge are in the [glossary](GLOSSARY.md) and [Reading your results](READING_YOUR_RESULTS.md).

## Where the inputs come from

This is the last of three tools. Run them in this order:

1. `tools/definitive_bgc_ranker.py` ranks every BGC. See the [ranker guide](DEFINITIVE_BGC_RANKER.md). It writes `ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv`.
2. `tools/bgc_functional_logic_workup.py` explains each rank at gene level. See the [workup guide](BGC_FUNCTIONAL_LOGIC_WORKUP.md). It writes `ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv` and `ALL_GENE_FUNCTIONAL_EVIDENCE.tsv`.
3. This tool reads those two files.

## Run it

```bash
python3 tools/strain_level_bgc_logic.py \
  --bgc-workup /path/to/functional_logic_workup/ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv \
  --gene-ledger /path/to/functional_logic_workup/ALL_GENE_FUNCTIONAL_EVIDENCE.tsv \
  --package-list /path/to/exact_package_paths.txt \
  --out /path/to/strain_level_reports
```

- `--bgc-workup` and `--out` are required.
- `--gene-ledger` is optional. With it, each top-locus report lists the annotated genes outside the dominant reference.
- `--package-list` is optional. It is a text file with one sealed package folder per line. Each package must hold exactly one `*_cds_table.csv`. With it, the protein tables and locus maps carry CDS coordinates and strand.
- `--out` must not exist yet. An existing folder, even an empty one, is refused before anything is written.

You should see `INDEX.html`, a `PER_STRAIN` folder and the other files under Outputs, and `RECEIPT.json` with `"status": "PASS"`. `PASS` means the report files were written. It does not check the upstream evidence. If the command stops with a Python error after creating the folder, the folder holds partial files, no `RECEIPT.json`, and a `RUN_FAILED.json` with status `FAILED_PARTIAL_OUTPUT_NOT_VALID` and the error. Keep that folder for diagnosis and rerun into a new folder.

## Product-logic score

The starting value is the standalone biological evidence score from the [ranker](DEFINITIVE_BGC_RANKER.md). "Architecture" means the domain-architecture class call made without looking at KCB results. "Reference" means the dominant MIBiG reference match. Transparent modifiers are then applied:

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
- fewer than four dominant-reference genes: -6, only when `reference_evidence_state` is `REFERENCE_EVALUATED`;
- dominant-reference hit fraction below 0.15: -4, only in that evaluated state with a positive CDS denominator.

A missing/nonpositive denominator leaves the emitted fraction unavailable (`None` internally), not zero. An unevaluated reference channel records its state instead of these sparse-reference penalties. Preserve that state separately from the score; no-reference availability and an evaluated sparse comparison are different evidence.

The final score is clamped to 0-100. These modifiers create a strain-level review order; they are not probabilities or a replacement for the definitive biological-evidence score.

## Evidence bands

- `P1_STRONG_FAMILY_HYPOTHESIS`: score at least 70 without an architecture/reference conflict or jointly unresolved channels.
- `P2_SUPPORTED_FAMILY_HYPOTHESIS`: score 50-69.99.
- `P3_PROVISIONAL_CAPACITY`: score 30-49.99.
- `P4_FRAGMENT_OR_WEAK_SIGNAL`: score below 30.

Named compounds are displayed as like-family hypotheses. Architecture-only findings remain capacity hypotheses. The report retains the complete identity `strain / full node-or-contig / region / BGC alias` for every locus.

## Outputs

- `INDEX.html`: cohort navigation across all strains.
- `PER_STRAIN/<strain>/REPORT.html`: readable strain report with the top ten review units, evidence channels, protein size/function/domain/homology tables, coordinate-based locus maps, unmatched functional genes, and all-locus table. The unmatched-gene list shows at most 20 genes per locus, in ledger row order; when there are more, its heading reads `showing 20 of N` and a note points to the all-proteins table and the input gene ledger, which carry every gene. Each admitted HIGH RG-GMCI pair is co-located in one two-locus rescue unit.
- `PER_STRAIN/<strain>/REPORT.md`: manuscript-friendly Markdown version of the same top review units and protein tables.
- `PER_STRAIN/<strain>/LOCUS_MAPS/*.svg`: one coordinate-based map per locus in the top review units. If coordinates were not supplied, the SVG is explicitly labeled as a gene-order schematic scaled by protein length.
- `CROSS_STRAIN_BGC_COMPARISON.tsv` and `.md`: architecture-led groups occurring in at least two strains, with all complete identities, strain breadth, scores, and boundary counts. Each per-strain report includes its strongest cross-strain groups.
- `ALL_BGC_STRAIN_PRODUCT_LOGIC.tsv`: every input column, plus `strain`, `potential_product_family_hypothesis`, `strain_product_logic_score_0_100`, `strain_product_evidence_band`, `fragment_genericity_flag`, `dominant_reference_hit_fraction`, `strain_logic_reference_evidence_state`, `strain_product_rank` and `claim_ceiling`.
- `STRAIN_LEVEL_SUMMARY.tsv`: one row per strain.
- `STRAIN_PRODUCT_FAMILY_SUMMARY.tsv`: family hypotheses summarized within each strain.
- `RECEIPT.json`: bound input hashes and output counts.

The outputs support prioritization and manuscript review only. They do not prove an exact product, complete pathway, expression, production, activity, novelty, physical linkage, or scientific acceptance.

## Safe use

- Use a new output folder for every run. An existing `--out` folder is refused.
- The homology column shows the subject, identity and coverage from the gene ledger. A blank subject reads `homology state not recorded`. When the ledger's `dominant_reference_gene_match` is `NO`, it reads that no dominant-reference subject was recorded in the workup ledger. Neither is a completed no-hit search. A blank identity or coverage reads `not recorded`.
- Give it only the package set that made the workup. The coordinate join takes the last row for a repeated (strain, alias, locus tag) key and does not compare contig or region. Check every matched contig and region yourself.
- Record the SHA-256 of each CDS table. The receipt hashes the package-list text, not the tables it names.
- An empty workup file fails after some comparison outputs are written.
- Missing or malformed numbers in the input can become defaults in the score. Check input completeness. A displayed score is a review order, not a measurement.
- The top ten is ten review units. A two-locus rescue unit shows two loci, so more than ten loci can appear. Lower-ranked HIGH pairs are still in the all-locus table and the summaries.
- Dense SVG maps can hide `other` labels without a count. If any coordinate is missing, the SVG is a gene-order schematic, and its spacing is not genomic distance. Keep the full protein table, check the gene roster, and look at each map at reading size. The [locus-map review contract](LOCUS_MAP_REVIEW_CONTRACT.md) sets the bar for a final figure.

The cross-strain Markdown counts the strains in your input. The index page title says "AS strain" whatever your strain names are.
