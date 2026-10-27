# Figure system overview

## Current figure owner and verification scope

Choose a figure route using [Figures start here](../FIGURES_START_HERE.md), then
use the [figure catalog](../FIGURE_CATALOG.md) to compare panel meanings. If your
input is already an admitted sidecar and you need its R renderer, use
[R figure workflows](../R_FIGURE_WORKFLOWS.md). This page explains the system's
layers; the dated design account is retained below for background.

For a selected existing figure, open its actual data, manifest/receipt and caption
before deciding to regenerate it. The current default post-seal locus-map adapter
uses v8 and attempts PNG plus SVG with an exact-locus data CSV and v8 receipt.
It reports missing gene/triage inputs and per-locus skips. Its `fmt` argument is
compatibility metadata on the v8 route; the separately selected `legacy` route
is where SVG-or-PNG selection applies. Use [Locus map v8](../LOCUS_MAP_V8.md) for
that route's inputs and review requirements; neither output existence nor a
legacy redraw establishes v8 equivalence.

The print-pack manifest records whether a sidecar exists; it does not certify
lossless source coverage or reproducibility. Preserve input, source/configuration
and output hashes, and inspect the selected image at its intended size. A missing
required figure remains a deliverable hold; a skipped or failed figure is not a
measured-negative result.

Follow the current [figure house rules](../FIGURE_HOUSE_RULES.md) for page wording,
formats, approved renderers/palettes and provenance. The historical claim-safety
footer convention below is not the current style to copy: current policy keeps
operator-governance wording off the figure page. Check the actual saved output;
a policy rule is not a guarantee that every emitter already enforces it.

The cohort `soft_divider` helper is currently a no-op. Display markers and
public/private ordering do not authorize disclosure; use the actual audience and
source authority. For individual loci, retain strain / full node-or-contig /
region / BGC alias. Current source details are in
[the source-scope reference](06_CURRENT_SOURCE_SCOPE.md).

<details>
<summary>Historical v9.7.319 design account (2026-06-23)</summary>

## Cluster G: The Figure System

This cluster covers how Mamey turns its computed data into figures. The pipeline produces a large library of figures — per-strain charts during a run, post-seal re-renders, and cross-strain cohort comparisons — and they all share a common design discipline. This document explains that design and what each major figure shows. It is an overview of the figure system's logic, not a module-by-module inventory; the full module catalog lives in the Plumbing Reference.

The two standing interpretive rules apply to figures as much as to numbers: scores are routing priors, not biological proof, and KCB is similarity, not identity. Both are enforced in the figures themselves, not just the documentation — every figure carries a claim-safety footer.

---

### The five shared disciplines

Every figure module in the system obeys the same five rules. These are worth stating once because they are what make the figures trustworthy as evidence rather than decoration.

**1. Data-only PNGs with a companion CSV.** Most figures are saved as a PNG with a sidecar CSV (`<figure_name>_data.csv`) containing the exact data plotted. Anyone can open the CSV and reconstruct or re-plot the figure, verify a value, or check that nothing was smoothed or hidden. A figure with no CSV would be an unverifiable claim; a figure with its CSV is a reproducible one.

**2. Non-blocking and best-effort.** Every figure render path is wrapped so that a failure never blocks the package seal. If a figure cannot be drawn — a missing input, an absent plotting library, a malformed table — the pipeline writes a skip marker explaining why and moves on. The scientific artifacts (the manifest, the scores, the scans) are always sealed; figures are best-effort cosmetics layered on top. A render hang or crash costs a figure, never the data.

**3. The saccharide exclusion policy.** Pure-saccharide BGCs are omitted from comparative figures. Sugar biosynthesis genes are present in nearly every bacterium and would clutter every comparison without distinguishing strains. "Pure saccharide" has a precise definition: the BGC's only specialist signal is `saccharide` and it carries none of the 36 specialist classes (NRPS, PKS, RiPP, terpene, siderophore, and others). A BGC annotated as `NRPS;saccharide` is *not* pure saccharide — it plots under NRPS. This rule lives in one module (`figure_policy.py`) and every figure module imports it, so the exclusion is identical everywhere rather than re-derived inconsistently.

**4. The raw BGC count prohibition.** Raw BGC counts must never appear as a headline biological ranking. A strain with 60 raw BGCs in a fragmented assembly does not have more biosynthetic capacity than a strain with 40 in a closed genome — it may have less, with its clusters split into more fragments. Raw counts are fragmentation-sensitive and belong only in QC or context panels that explain *why* the corrected count is needed. The one figure that does plot raw counts (raw count vs contig count) carries an explicit policy annotation on the figure itself stating that it is QC-only.

**5. Claim-safety footers.** Every figure carries a footer line stating its epistemic limits. The standard footer reads roughly: "Data-only figure · scores are deterministic capacity signals, not activity measurements · KCB = similarity, not identity · capacity-level." The locus-map footer additionally notes that gene roles come from antiSMASH annotation rather than BLASTP confirmation. When a figure includes unpublished strains, the footer carries the PRIVATE release tag. The footer is not boilerplate — it is the figure stating, in its own margin, exactly what it does and does not claim.

A house-style palette ties the set together: blues lead, with greens (not orange) for the antifungal track so it never collides with the orange used for POOR assembly tiers. All rendering uses a display-free backend so figures generate identically whether or not a screen is attached.

---

### Three tiers of figures

Figures are produced at three different points in the workflow, answering three different scopes of question.

**Per-strain figures, auto-emitted during a run.** When a strain is processed with a standard brief, the pipeline automatically emits a set of reader-facing figures for that single strain. These read the normalized triage rows directly — no judgment layer, no network. They are the figures a researcher looks at first to understand one strain's biosynthetic portfolio.

**Post-seal re-renders.** After a package is sealed, a subset of figures can be regenerated from the sealed data without re-running the analysis. This matters in token-limited or resumed sessions. The locus maps, the lead bars, and the workbook-native figure set can all be re-rendered from what is stored in the package. So a figure that was skipped during the run can be produced later.

**Cross-strain cohort figures.** When more than one strain is processed, the pipeline aggregates the per-strain packages into cohort tables and produces cross-strain comparison figures automatically. These are the figures that turn a collection of isolated strains into a connected dataset — heatmaps of shared and unique capacities, cross-strain lead boards, fragmentation comparisons, and the split-cluster rescue rollup.

---

### The per-strain figures

The core per-strain set answers: what is in this strain, and what should I look at first?

**The DAPR dual-track scatter** plots every BGC as a point, with its antibacterial score on one axis and its antifungal score on the other. Boundary status colors the points; median guide lines divide the plot into quadrants; the top antibacterial and antifungal leads are labeled node-first. This single figure shows the whole strain's portfolio at once — where the leads cluster, whether the strain is antibacterial-leaning or antifungal-leaning, and which specific BGCs sit at the top of each axis.

**The antibacterial and antifungal ranking charts** are horizontal lollipop charts of the top BGCs on each axis, colored by boundary status. They answer "which BGCs are the strongest leads on this axis, and are they complete or truncated?"

**The claim-safety funnel** is the most conceptually important per-strain figure. It shows, as a four-stage funnel, how a raw BGC count becomes a genuine lead count: raw BGCs → corrected count (Interior + ½ Edge + ¼ Full-contig) → minus saccharide-only clusters → genuine lead tier (antibacterial score ≥ 70 or antifungal score ≥ 44). Each stage is a stated deterministic rule, and the figure makes the whole reduction transparent — a reader sees exactly how many clusters survived each filter and why. This is the figure that defends the strain's headline lead count against the objection "but antiSMASH found sixty clusters."

The extended per-strain set adds a class-distribution bar chart and a CCTT trigger map (which diagnostic triggers fired on which BGCs). It also adds a length histogram stacked by boundary status, an Interior/Edge/Full-contig boundary composition, and a novelty ranking. Finally, it adds a KCB anchor chart (most-cited reference compounds, labeled "similarity, not identity") and a genome atlas showing each BGC's position along the genome colored by class.

One claim-safety surface deserves specific mention: KCB compound names on figure labels are truncated to 18 characters. This is the only place compound names appear on figures, and the truncation deliberately forces brevity — a similarity signal should not be presented as a precise compound identification.

---

### Locus maps

Locus maps are gene-arrow diagrams of a single BGC (or a paired panel for a split-cluster rescue). Each gene is an arrow, scaled and oriented, colored by functional role. They are the most detailed per-BGC figure — the one that shows the actual gene content rather than a summary statistic.

Gene roles are derived from antiSMASH's functional annotations rather than the product field, so a gene with an empty product annotation still receives a role. The role palette is loaded from an external file, so new chemotype roles can be added without code changes, and unknown gene tokens fall to a default "other / hypothetical" role rather than crashing.

Two design details matter. First, locus maps can be rendered from two sources — the antiSMASH GenBank file during a run, or the sealed gene context afterward — and both paths classify genes identically, so in-run and post-seal maps match. Second, the map zooms to the gene span rather than the full contig: a BGC sitting near the end of a long contig fills the panel instead of being crushed into an illegible sliver at one edge.

---

### Cross-strain cohort figures

The cohort figures compare strains against each other. They read all the per-strain packages and produce comparative views.

**The heatmap series** is the heart of the cohort comparison. Each heatmap is a strain-by-feature grid: strains down one axis, a feature category across the other, with cell color showing the count or intensity. The series covers several feature categories — a megasynthase heatmap (the core PKS/NRPS catalytic domains: ketosynthase, acyltransferase, ketoreductase, dehydratase, condensation, adenylation, and others), a product-class heatmap, and a tailoring-enzyme heatmap (halogenases, chitinases, P450s, methyltransferases, glycosyltransferases). It also covers a CCTT trigger heatmap, a resistance-tier heatmap, NRPS A-domain and PKS AT-domain substrate consensus heatmaps, transporter and regulator family heatmaps, and a hierarchically-clustered top-domain clustermap. Public strains are ordered first, then private strains, separated by a divider line; a public-only switch drops the private strains for a shareable cut.

**The cohort class-capacity heatmap** is a strain-by-biosynthetic-class grid drawn from the master workbook, showing which classes each strain can make. It uses the same centralized exclusion set as the rest of the comparative layer so all consumers drop identical classes.

**The cross-strain RG-GMCI figures** turn the split-cluster rescue results into a comparison: how many rescue pairs each strain has, the confidence distribution, the score and identity distributions, and the boundary composition. These visualize the fragmentation-and-rescue picture across the whole cohort.

**The metadata-gated collection bundle** is a separate cross-strain layer driven by strain metadata (genus, host, isolation source, bioactivity calls, 16S similarity) rather than by BGC content. Each figure in this bundle declares which metadata fields it needs; the bundle renders only the figures whose required fields are present and writes an availability report for the rest. This layer carries its own careful bioactivity claim-safety discipline: "not tested" is kept strictly distinct from "negative" in every count, and only explicit positive tokens count as positive — the absence of a recorded activity never becomes a negative call.

**The master atlas** assembles a publication-ready, cross-strain dashboard bundle — a one-page overview, per-strain cards, cross-strain priority scatters, and boundary landscapes — with stable figure IDs so a specific figure can be referenced across revisions.

---

### What the figure system guarantees

Taken together, the figure disciplines make a specific promise. Figures are meant to be reproducible from a companion CSV and to state their limits in a footer. The system never lets fragmentation-inflated raw counts masquerade as biology, never plots ubiquitous saccharide clusters as if they distinguished strains, and never blocks the scientific seal if a figure fails to render. A figure from this system is a claim you can check, not a picture you have to trust.

---


</details>
