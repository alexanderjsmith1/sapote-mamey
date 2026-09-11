# Deliverable map: Per-strain Gene-by-Gene BGC Analysis

Maps library figures to a **single-strain gene-by-gene deep-dive** (the AS-XXX-style 30+pp deliverable).
Audience: natural-products specialist. Goal: situate ONE strain, then go deep on its leads. Set `<SID>` once.
All figures inherit `FIGURE_CONVENTIONS.md` (no arrows on data points).

| # | Library figure | Data source (filter sid == <SID>) | Caption (suggested) | Overlay (downstream) |
|---|---|---|---|---|
| 1 | `fig_per_strain_cohort_context_panel` | strain_summary + class_by_strain + bgc_inventory | Where <SID> sits in the cohort: corrected-BGC rank, shared/unique classes, KCB-dark count. | Drop beside a colony photo on the title slide. |
| 2 | `fig_per_strain_class_donut` | bgc_class_long (sid==<SID>) | Product-class composition of <SID> (class-level calls). | — |
| 3 | `fig_per_strain_bgc_ranking` | bgc_inventory (sid==<SID>, top 10 by length) | Largest candidate BGCs in <SID>; colour = edge status. | Box the flagship megacluster; add its name. |
| 4 | `fig_edge_status_composition` | bgc_inventory (single-strain bar) | Completeness profile: Interior/Edge/Full-contig fractions for <SID>. | — |

**Note:** the gene-by-gene prose still carries the per-BGC architecture; these figures are the framing/context
panels. Every BGC mention in the surrounding text must carry its `(contig · region)` locator (Contract §4).

## Per-BGC page layout (co-location — required)

When compiling the deep-dive, **each BGC is one page-unit; its locus map and its §1–§48 Mode B analysis go on the same page** (Contract §A2.5). Do **not** emit one locus map per page with the analysis pushed overleaf — that wastes ~half of every page and was the prior failure mode. Per BGC, top → bottom:

1. **Locus map** (top ~45% of the page) — gene-arrow panel for this BGC.
2. **Predicted class line** (one line under the map): `BGC_ID (contig · regionXXX) · predicted class: <class> · boundary: <…> · KCB: <similarity>` — claim-safe.
3. **Mode B card** (~55%, below) — §1–§48 for this BGC.

Spill to a second page only if a single BGC's Mode B card overflows (map + §1–§4 stay together; §5–§8 continues with a "cont." marker). Full spec + worked example: `docs/PER_BGC_PAGE_LAYOUT_SPEC.md`.
