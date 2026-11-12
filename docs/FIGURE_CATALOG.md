# Sapote-Mamey figure catalog

Use this catalog to choose among package and cohort panels and understand their
counting units. For the command and required inputs, start with
[Figures start here](FIGURES_START_HERE.md). Read the single-strain section for
one package, the standard cohort section for strain comparisons, and the extended
section for its alternative count-based views. The overlap map below helps choose
between related panels.

Panel names here may differ a little from the files a run writes. Match the entry to the real
file name, its sidecar data and its receipt. A panel with a HOLD (F11 and F13 below) writes a
HOLD JSON file instead of artwork. The error handler attempts to write `GOLD_FIGURES_SKIPPED.md` when the whole gold-figure step raises an error. If written, it holds that error, not a list of panels; the note itself can fail to write.
Terms such as KCB, CCTT, TTA and A-domain are defined in the [glossary](GLOSSARY.md).

For domain-level definitions, see [cohort figure captions](COHORT_FIGURE_CAPTIONS.md).
Counts summarize annotation support, not measured products or phenotypes. Read region counts
together with boundary status. Edge and full-contig calls are limited by the assembly. G04 and
extended fig8 show that context.

---

## Tier 1 — Single-strain gold figures (per gold run)

A gold run (the full analysis mode) tries these figures and writes them to `package/gold_figures/`.
The number of panels depends on which input fields the run admitted. To see what was made,
compare the files in `gold_figures/` with this catalog, and read the run's console line
`Gold figures: N figure(s)`. If the step raised an error, inspect `gold_figures/GOLD_FIGURES_SKIPPED.md` when present, the phase receipt and logs. The note can be absent if its write fails or if the step returns zero figures without raising. Locus maps are made for the top-ranked loci, not for
every BGC.

### D-series — dashboards / scatter (per-BGC relationships)
- **D01 bubble_productclass_size_length** — product class vs size vs length; bubble map of where the big
  clusters sit by class.
- **D02 bubble_rare_triggers** — rare cryptic-chemistry triggers per BGC; flags unusual chemistry.
- **D03 scatter_size_vs_domains** — BGC size vs domain count; the size/complexity relationship within one strain.
- **D04 scatter_kcb_vs_size** — KCB similarity vs size; large size plus low loaded KCB similarity; neither establishes novelty.
- **D05 scatter_raw_vs_corrected** — raw vs boundary-corrected BGC count; shows the fragmentation discount.
- **D06 strip_kcb_per_strain** — KCB score strip; the loaded similarity-score distribution.
- **D07 scatter_rarechem_vs_bgcs** — rare-chemistry load vs BGC count.
- **D08 bubble_tailoring** — tailoring-enzyme load per BGC (decoration potential).
- **D09 bubble_regulators** — regulatory-gene load per BGC.
- **D10 scatter_bgc_by_class** — BGCs distributed by biosynthetic class.
- **D11 scatter_tta_vs_modularity** — TTA codon burden vs megasynthase modularity; a count does not establish bldA dependence.

### F-series — per-BGC / per-gene heatmaps
- **F01 perBGC_domain_heatmap** — per-BGC counts of eight catalytic domain classes (PKS_KS, PKS_AT, PKS_KR, PKS_DH, NRPS_C, NRPS_A, NRPS_T_PCP, TE_release), shown on a log color scale labeled `domain count`. It draws at most 40 BGCs, those with the most of these domains, so it is not the whole inventory. A zero count is an empty cell. The plotted values are in the `..._<strain>_perBGC_domain_heatmap_data.csv` sidecar beside the image.
- **F02 perGene_active_site_completeness** — per-gene active-site completeness; which catalytic centers look intact.
- **F03 perBGC_cctt_resistance** — CCTT triggers and resistance tier per BGC together.

### G-series — complementary summaries
- **G01 rare_chemistry_triggers**, **G02 rare_product_classes**, **G03 kcb_similarity_strength**,
  **G04 bgc_boundary_status**, **G05 bgc_size_distribution**, **G06 domain_richness**,
  **G07 tta_bldA_dependency** (TTA burden; dependence unverified), **G08 megasynthase_modularity** — one-metric distributions/summaries that
  back the D/F panels.

### Locus maps (`locus_maps/BGCxxx_*_locus.png`)
Gene-arrow schematic per BGC. **Enriched version** (extended fig4) adds a per-gene domain track and
gene-specific resistance/CCTT badges; the plain map shows arrows + strand only.

---

## Tier 2 — Cross-strain cohort, standard (`cohort-figures`, F-series)

Emitted to the cohort output dir. Each PNG has a sidecar CSV of its underlying values.

- **F01 census_zscore_heatmap** — 5 gene/domain metrics × strain; cells = raw counts, color = z-score
  within metric. The cohort's headline census. (Extended fig1 is this with the tier strip moved to caption.)
- **F02 megasynthase_heatmap** — megasynthase (large PKS/NRPS) content × strain.
- **F03 product_class_heatmap** — biosynthetic product class × strain.
- **F04 tailoring_enzyme_heatmap** — tailoring-enzyme families × strain (halogenases, methyltransferases, etc.).
- **F05 cctt_trigger_heatmap** — CCTT cryptic-chemistry triggers × strain (extended fig7 is the BGC-count version).
- **F06 resistance_tier_heatmap** — resistance-tier signal × strain (extended fig10 is the per-strain stacked count).
- **F07 adomain_substrate_heatmap** — NRPS A-domain predicted substrates × strain.
- **F08 AT_extender_heatmap** — PKS AT extender-unit selection × strain.
- **F09 transporter_family_heatmap** — transporter families × strain (export / resistance).
- **F10 regulator_TF_heatmap** — regulator / transcription-factor families × strain.
- **F11 active_site_completeness** — active-site completeness across the cohort. The separately named `F11_domain_clustermap_top40` is held until domain-token source classes and overlap semantics are bound; a HOLD JSON is emitted instead of its artwork.
- **F12 bgc_pca_by_cluster** — BGCs colored by architecture cluster.
- **F13 strain_ordination_2d** — strains ordinated by mean BGC domain profile. Check the rendered layout for label, legend and axis collisions. The separately named `F13_bgc_domain_pca_2d` needs a hash-bound cohort manifest and independent denominator registry; absent these, its HOLD JSON is the result, not a figure.

When you cite a panel, use the file name the run wrote. Do not treat a HOLD file as artwork.

F10 shows selected raw domain tokens from the domain hits table. It is not a regulator caller.
One counted observation is one retained domain-hit occurrence assigned to a BGC overlap. Its
caption names the displayed tokens and the upstream antiSMASH annotation types (`aSDomain`,
`PFAM_domain`). Whole-record GBKs are preferred, and region copies are excluded when whole-record
files exist. Friendly family labels are display names, not validated function calls.
`LysR_substrate` is a substrate-binding domain and does not alone show a LysR regulator.

F11 `F11_domain_clustermap_top40` holds because the domain hits table does not record whether a
token is a Pfam, aSDomain, motif or TIGRFAM record. It cannot be called "the 40 most abundant Pfam
domains". The HOLD JSON states what is missing.

---

## Tier 3 — Cross-strain cohort, extended (11 figures)

`cohort-figures` writes these by default. Add `--no-extended` to skip them. You can also rebuild
them with `tools/cohort_figure_prototypes.py`. Full captions incl. the domain glossary in `COHORT_FIGURE_CAPTIONS.md`.

- **fig1 census_notier** — F01 census with the assembly-tier strip removed to the caption line.
- **fig2 pks_bars** — each PKS BGC a bar, height = length (kb), stacked by gene-type coding bp; gray = non-CDS.
  Reads big multi-modular megasynthases vs short fragments at a glance.
- **fig3 size_vs_rich** — BGC length vs functional-gene richness, every BGC, colored by strain.
- **fig4 enriched_locus** — the enriched locus map: gene arrows by function + per-gene domain track +
  gene-specific T2/T3-resistance (◇) and CCTT (★) badges; BGC-wide resistance/TTA in the title.
- **fig5 archetype** — BGC biosynthetic-class composition per strain (NRPS / PKS / hybrid / RiPP / terpene / …).
- **fig6 kcb_novelty** — BGCs per strain by KCB tier as a stacked count (low loaded KCB similarity; global novelty remains unresolved).
- **fig7 cctt_triggers** — CCTT trigger family × strain, counted as BGCs carrying each.
- **fig8 boundary_profile** — interior / edge / full-contig BGCs per strain: the assembly-quality lens on every count.
- **fig9 domain_cooccur** — domain co-occurrence matrix (pooled cohort); which retained domain tokens co-occur within the counted input units; this is not physical transfer or pathway coupling. Diagonal = domain frequency. **Every domain defined in the caption glossary.**
- **fig10 resistance_map** — BGCs per strain by source-derived resistance-related tier; counts only.
  The annotation does not measure compound potency or confirm self-protection.
- **fig11 tta_profile** — BGCs per strain by TTA burden tier (T1 = zero; T4 = six or more);
  counts only, with explicit unknown and not-applicable bins. Expression is unmeasured.

---

## Overlap map (so the manual doesn't double-count)

Choose the view by what you need to compare. A family-by-strain heatmap and a
stacked count of BGCs answer different questions, even when both concern the same
annotation. These are alternative views, not independent evidence to add together:
- **census** → F01 (Tier 2) = fig1 (Tier 3, no tier strip).
- **CCTT** → F05 (metric × strain heatmap) vs fig7 (BGCs carrying each).
- **resistance** → F06 (signal heatmap) vs fig10 (per-strain stacked BGC counts).
- **strain layout** → F13 strain ordination vs fig3 (per-BGC size/richness scatter).
Prefer the Tier-3 cut when you want counts by source-derived tier; prefer Tier 2 when you
want the fine-grained family × strain matrix.

## BiG-SCAPE supporting figures

The bundle ships [strain-centric GCF and clinker consumers](BIGSCAPE_FIGURES.md). They are separate from the figures above. Each has its own run, cutoff and source list, and its own states for attempts that did not finish.

## Limits that apply to every panel
- A displayed domain token records annotation support. It does not show a complete domain, capacity
  or a product. Never write that a strain "produces" a compound from a figure.
- KCB and BLASTp results show similarity, not identity. No named match does not mean the BGC is
  new. "Dark" means dark in the loaded search scope.
- Resistance and TTA tiers are calls from the annotation. They are not measured phenotype or
  expression.
- Check each panel's counting unit and grouping key. For fig9, repeated tokens in one BGC group
  count once.

## What a run actually wrote
Single-strain gold figures are made on a best-effort basis. A skipped figure does not stop the
package from being sealed or validated. Look in the run folder:

- `gold_figures/GOLD_FIGURES_SKIPPED.md` is attempted when the gold-figure step raises an error; if present, it holds that error. Its absence does not prove that figures were produced.
- The files present in `gold_figures/` show which panels were written; a panel without input data is simply absent.
- `RUNS_DIR_NOTE.md` and the logs list other notes and errors.
- The sidecar CSV beside each PNG holds the plotted values.

Cohort figures are a separate command. If the extended set fails, `cohort-figures` warns, skips it
and can still succeed. Reusing an output folder can leave old figures in the count, so use a fresh
folder.

F11 and F13 holds are results of their own. See [F13 input and status](F13_BGC_DOMAIN_PCA.md). The
compile report makes locus maps for the top five triage targets. It then collects every image
under the package, so one figure saved as PNG and SVG counts as two files. That count is not the
number of admitted panels.

Source: `mamey/cli.py`, `mamey/cohort_figures.py`, `mamey/compile_report.py`, `mamey/locus_map_v8.py`.
