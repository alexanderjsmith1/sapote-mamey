# Sapote-Mamey figure catalog

An evaluation of every figure the pipeline emits, in three tiers: **single-strain gold** (auto-emitted
in each gold run), **cross-strain cohort — standard** (`cohort-figures` F-series), and **cross-strain
cohort — extended** (the 11-figure suite fused in at v9.7.319). Each entry: what it plots, what it's for,
and how to read it honestly. Domain-level definitions (Pfam/antiSMASH/TIGRFAM accession + catalytic
signature) are in `COHORT_FIGURE_CAPTIONS.md`; every "domain" is an HMM call and every count is a
**capacity** signal, not a product or phenotype. Read all counts against fragmentation (boundary tier):
edge/full-contig BGCs are fragment-limited and inflate apparent numbers relative to interior clusters.

---

## Tier 1 — Single-strain gold figures (per gold run)

Auto-emitted to `package/gold_figures/` (22 panels) and `package/locus_maps/` (one per BGC).

### D-series — dashboards / scatter (per-BGC relationships)
- **D01 bubble_productclass_size_length** — product class vs size vs length; bubble map of where the big
  clusters sit by class.
- **D02 bubble_rare_triggers** — rare cryptic-chemistry triggers per BGC; flags unusual chemistry.
- **D03 scatter_size_vs_domains** — BGC size vs domain count; the size/complexity relationship within one strain.
- **D04 scatter_kcb_vs_size** — KCB similarity vs size; large + KCB-dark = the notable novel-and-big quadrant.
- **D05 scatter_raw_vs_corrected** — raw vs boundary-corrected BGC count; shows the fragmentation discount.
- **D06 strip_kcb_per_strain** — KCB score strip; the novelty spread for the strain.
- **D07 scatter_rarechem_vs_bgcs** — rare-chemistry load vs BGC count.
- **D08 bubble_tailoring** — tailoring-enzyme load per BGC (decoration potential).
- **D09 bubble_regulators** — regulatory-gene load per BGC.
- **D10 scatter_bgc_by_class** — BGCs distributed by biosynthetic class.
- **D11 scatter_tta_vs_modularity** — TTA/bldA dependency vs megasynthase modularity.

### F-series — per-BGC / per-gene heatmaps
- **F01 perBGC_domain_heatmap** — BGC × domain-family presence; the strain's domain fingerprint.
- **F02 perGene_active_site_completeness** — per-gene active-site completeness; which catalytic centres look intact.
- **F03 perBGC_cctt_resistance** — CCTT triggers and resistance tier per BGC together.

### G-series — complementary summaries
- **G01 rare_chemistry_triggers**, **G02 rare_product_classes**, **G03 kcb_similarity_strength**,
  **G04 bgc_boundary_status**, **G05 bgc_size_distribution**, **G06 domain_richness**,
  **G07 tta_bldA_dependency**, **G08 megasynthase_modularity** — one-metric distributions/summaries that
  back the D/F panels.

### Locus maps (`locus_maps/BGCxxx_*_locus.png`)
Gene-arrow schematic per BGC. **Enriched version** (extended fig4) adds a per-gene domain track and
gene-specific resistance/CCTT badges; the plain map shows arrows + strand only.

---

## Tier 2 — Cross-strain cohort, standard (`cohort-figures`, F-series)

Emitted to the cohort output dir. Each PNG has a sidecar CSV of its underlying values.

- **F01 census_zscore_heatmap** — 5 gene/domain metrics × strain; cells = raw counts, colour = z-score
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
- **F11 domain_clustermap_top40** — top-40 domains clustered across strains (dendrogram both axes).
- **F12 active_site_completeness** — active-site completeness across the cohort.
- **F13 bgc_domain_pca_2d** — BGCs in domain-profile PCA space.
- **F14 bgc_pca_by_cluster** — the same PCA coloured by cluster.
- **F15 strain_ordination_2d** — strains ordinated by mean BGC domain profile (extended fig3 is the per-BGC scatter complement).

---

## Tier 3 — Cross-strain cohort, extended (11-figure suite, fused v9.7.319)

Auto-emitted by `cohort-figures` (default; `--no-extended` to skip) and regenerable standalone via
`tools/cohort_figure_prototypes.py`. Full captions incl. the domain glossary in `COHORT_FIGURE_CAPTIONS.md`.

- **fig1 census_notier** — F01 census with the assembly-tier strip removed to the caption line.
- **fig2 pks_bars** — each PKS BGC a bar, height = length (kb), stacked by gene-type coding bp; grey = non-CDS.
  Reads big multi-modular megasynthases vs short fragments at a glance.
- **fig3 size_vs_rich** — BGC length vs functional-gene richness, every BGC, coloured by strain.
- **fig4 enriched_locus** — the enriched locus map: gene arrows by function + per-gene domain track +
  gene-specific T2/T3-resistance (◇) and CCTT (★) badges; BGC-wide resistance/TTA in the title.
- **fig5 archetype** — BGC biosynthetic-class composition per strain (NRPS / PKS / hybrid / RiPP / terpene / …).
- **fig6 kcb_novelty** — BGCs per strain by KCB tier as a stacked count (dark <1 = candidate-novel; similarity, not identity).
- **fig7 cctt_triggers** — CCTT trigger family × strain, counted as BGCs carrying each.
- **fig8 boundary_profile** — interior / edge / full-contig BGCs per strain: the assembly-quality lens on every count.
- **fig9 domain_cooccur** — domain co-occurrence matrix (pooled cohort); which biosynthetic modules travel
  together. Diagonal = domain frequency. **Every domain defined in the caption glossary.**
- **fig10 resistance_map** — BGCs per strain by self-resistance tier (T1/T2 = potency tell); % in caption.
- **fig11 tta_profile** — BGCs per strain by strongest bldA/TTA dependency (T1 = likely gated/cryptic = activation candidate); % in caption.

---

## Overlap map (so the manual doesn't double-count)
Some metrics appear in more than one tier by design (a per-strain heatmap in Tier 2, a per-BGC or
count-based cut in Tier 3):
- **census** → F01 (Tier 2) = fig1 (Tier 3, no tier strip).
- **CCTT** → F05 (metric × strain heatmap) vs fig7 (BGCs carrying each).
- **resistance** → F06 (signal heatmap) vs fig10 (per-strain stacked BGC counts, potency framing).
- **strain layout** → F15 (strain ordination) vs fig3 (per-BGC size/richness scatter).
Prefer the Tier-3 cut when you want counts and the potency/novelty/gating framing; prefer Tier 2 when you
want the fine-grained family × strain matrix.

## Companion (external) — BiG-SCAPE GCF network
Not a Mamey figure: `AS_batch1_BiGSCAPE_run_guide.md` drives a BiG-SCAPE 2.0 gene-cluster-family analysis
on the 624-BGC / 11-strain set. It is the network/GCF complement — Mamey gives per-BGC architecture + KCB
anchors; BiG-SCAPE gives the cross-strain family graph. Cite them side by side, not interchangeably.

## Honest caveats to carry into any manual text
- Domain presence = **capacity**; never state a strain "produces" a compound from a figure.
- KCB / BLASTp = **similarity, not identity**; "dark" = candidate-novel, not confirmed novel.
- Resistance and TTA tiers are **source-derived mechanism calls**, not measured phenotype or expression.
- Counts are inflated by fragmentation — always read against fig8 / G04 boundary status.
- Per-BGC-count figures count a BGC once regardless of how many of its genes carry a mark.
