# Cohort figure captions

This page gives caption notes for the eleven extended cohort figures, `fig1` to `fig11`. Each note says what the figure counts, what the denominator is, and what the figure does not show. A caption should name the producer, the source table, the strains included and the denominator.

## Make the figures

```bash
python mamey_run.py cohort-figures --runs-dir runs --out cohort_figures
```

`--runs-dir` holds one `<ID>/package/` folder per strain from a finished run. The extended figures are on by default. `--no-extended` turns them off, and `--strains` picks a subset. The PNG files and a copy of this page land in `--out`.

Each figure reads two package files: the per-BGC inventory (`<ID>_2_inventory.csv`) and the per-gene table (`<ID>_gene_by_gene_all_bgcs.csv`). A figure that fails to draw is reported as a warning, and the other figures are still written. So a file that exists does not mean the run was complete. Compare the PNG list with the extended-figure count the command prints, and read any warning lines.

All figures count rows in the supplied tables. They do not check full locus identity.

## fig1 to fig8

- **fig1 `census_notier`**: gene and domain census per strain. Cells are raw counts, and color is the z-score within each metric. It is a count per strain, so strains with different assembly quality are not directly comparable.
- **fig2 `pks_bars`**: one bar per PKS BGC. Height is length in kb, stacked by coding base pairs per gene type, and gray is non-coding. It does not show module order or the product.
- **fig3 `size_vs_rich`**: BGC length against functional-gene richness for all BGCs, colored by strain. It does not show that bigger clusters are richer for a reason.
- **fig4 `enriched_locus`**: one locus drawn as gene arrows with a domain track and badges. The badges mark gene-specific T2 or T3 resistance-like signals and CCTT triggers. In an automatic run it draws the first strain's `BGC001`. It does not show a mechanism.
- **fig5 `archetype`**: BGC biosynthetic-class composition per strain, taken from the Products field. It shows class mix, not product.
- **fig6 `kcb_novelty`**: BGCs per strain in three groups by `KCB_score`: under 1 (red, "no KCB hit (<1)"), 1 to under 40, and 40 or more. A blank, non-numeric or non-finite score (`nan`) is not put in any of the three. It forms a fourth group, "unknown / missing score", which is drawn and written to the CSV (`missing_or_nonnumeric_score`) only when a strain has one. The percent above each bar uses all four groups as its denominator. These cut points are not the report bands in [reading your results](READING_YOUR_RESULTS.md), which use 70 and 40. The figure does not show novelty.
- **fig7 `cctt_triggers`**: CCTT cryptic-chemistry trigger family against strain. Each cell counts the BGCs that carry the trigger. It does not show that the trigger is active.
- **fig8 `boundary_profile`**: interior, edge and full-contig BGCs per strain. A blank or unrecognized `Boundary` value forms its own group, "unknown / missing", drawn and written to the CSV only when present, so every inventory row stays in the denominator. Interior means the region does not touch a contig end; it is not a measure of how complete or correct the cluster is. The figure is the assembly view of the other counts. Report the denominator with every count. Edge and full-contig status can raise the number of called regions. This figure does not show by how much.

## fig9: domain co-occurrence

A cell is the number of BGCs whose domain set contains both the row and the column domain. The diagonal is the number of BGCs that carry that domain.

- A domain label is one semicolon-separated token from the `sec_met_domains` column. The figure does not look at the underlying models, cutoffs, alignment scores or catalytic residues. A token is annotation context, not a demonstrated function.
- The input is pooled across the selected strains. Only BGCs with at least one non-blank token are counted. A repeated token inside one BGC counts once.
- By default the matrix shows the 16 most frequent tokens.
- The counts describe the table you supplied. They are not unique genes, whole-genome prevalence, physical linkage or confirmed motifs. Co-occurrence is not module movement, coupling or catalytic function.
- For the meaning of a Pfam or antiSMASH domain name, see the [glossary](GLOSSARY.md) and the Pfam entry for that accession.

## fig10: resistance-related signals

Each BGC is placed in the highest tier recorded among its genes, in the order T1, T2, T3.

- **T1**: a diagnostic self-protection candidate recorded near the cluster. Check class match and gene context before you name a mechanism.
- **T2**: a resistance-like function that is not a clear self-protection call.
- **T3**: an efflux or transport function only, such as an ABC or MFS pump. It fits export but is not a self-protection signal alone.
- **No resistance signal (scanned)**: every gene row of the BGC carries the scanned-negative tier `NULL_NO_SOURCE_DERIVED_RESISTANCE`.
- **Unknown / missing tier**: a gene row has a blank or unrecognized tier and none has T1 to T3. This is missing evidence, not a negative. It is drawn and written to the CSV only when present.

The chart and its CSV hold counts, not percentages. To report a percentage, compute 100 x (T1 + T2 BGCs) / (all BGCs with rows in this figure's per-gene input) for each strain, and state the denominator. Missing gene rows change the denominator. The figure does not show the target, activity, potency or resistance.

## fig11: TTA burden tier

A TTA codon is a leucine codon that the bldA tRNA reads in Streptomyces and some other actinomycetes. A BGC is placed in its highest recorded tier, from the count of TTA codons in its coding sequences:

| Tier | TTA codons in the BGC |
|---|---|
| T1 | 0 |
| T2 | 1 or 2 |
| T3 | 3 to 5 |
| T4 | 6 or more |

Two more bins exist. "Unknown" means no recognized tier in the per-gene table. "Not applicable" means the scan declined to give a bldA tier for a non-actinomycete.

The renderer takes the highest tier among a BGC's gene rows. Those rows repeat one BGC-wide tier, so rows that disagree need a look at the source data. The chart and CSV hold counts. To report a T4 fraction, divide T4 by all BGCs for that strain, including the unknown and not-applicable bins, and give both numbers. A TTA count can motivate a look at translational regulation. It does not show transcription, protein level, silencing or the conditions that induce a cluster.

## Before you use a figure

Look at the image. These captions do not replace a render check, and the command writes no source-hash receipt. For a figure of one locus, bind the strain, full contig or node, region and BGC alias to the source table. Record scientific adoption separately from the render.
