# Make and review Mamey figures

Sapote–Mamey v9.7.433 · Mamey engine 1.9.167

Sapote-Mamey has several figure routes with **different input contracts**. Start with
the question you want to show, then choose a route below. A finished image is
not a validated biological interpretation: keep the plotted values, source
identity, denominator, methods, and any missingness or assembly warning with it.

## Choose the route

| You want to see | Starting input | Command or guide |
| --- | --- | --- |
| One strain's BGC inventory or locus maps | A sealed gold package | Open the Mamey Zip and inspect `package/gold_figures/` and `package/locus_maps/`; regenerate a selected set with `render-figures` below. |
| The same Mamey feature across several strains | One `<strain>/package/` per strain in a runs directory | `cohort-figures` below; [figure catalog](FIGURE_CATALOG.md) explains F, G, D and extended panels. |
| A manuscript comparison from a master workbook | A checked workbook with strain registry and BGC master sheets | Export `figure_ready/` tables, then follow a [named figure recipe](../prompts/figure_prompts/_INDEX.md). The recipes are specifications, not an automatic renderer. |
| A custom aggregate evidence-coverage bar chart | Counted metrics TSV plus an explicit cohort manifest | [Aggregate evidence guide](FIGURE_FACTORY_NEXT.md). This specialized route does not read BLASTp databases itself. |
| A tree or BiG-SCAPE gene-cluster-family panel | Bound tree/database, tips or regions, and matching metadata | [Tree figure grammar](TREE_FIGURE_GRAMMAR.md) or [BiG-SCAPE walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md). Do not derive host metadata from a strain ID. |

Use the bundle's `mamey_run.py` entry point from the extracted code root so the
local bundled engine is selected. Commands below are templates: replace each
path with your real input and choose a **new output directory** for review.

## A single Mamey package

First inspect the package's `manifest.json`, `*_1_intake.json`, existing
`gold_figures/`, and `locus_maps/`. Record the engine/bundle version,
antiSMASH source, assembly, strain, region identities, and any figure holds.
Gold runs may already contain many images; you do not need to rerun extraction
to view them.

To regenerate the standard figure set from the package:

```bash
python mamey_run.py render-figures --package /path/to/strain/package \
  --outdir /path/to/new_review/standard --figure-set standard
```

Other supported sets include `domain-level`, `locus-maps`, `cohort-class`,
and `mamey-native`. The last two require `--workbook`; check
`python mamey_run.py render-figures --help` and the workbook's actual
sheets before using them. An empty Sapote judgment sheet is not an observed
negative finding.

## Compare several Mamey packages (cross-strain comparison)

The Mamey package outputs are standardized to enable comparative figure generation across the figure suite. 

The cohort command expects a directory containing `<strain>/package/`
subdirectories. Specify the strains deliberately; do not let an unrelated
reference package enter the denominator.

```bash
python mamey_run.py cohort-figures --runs-dir /path/to/checked_runs \
  --strains STRAIN_A,STRAIN_B,STRAIN_C \
  --out /path/to/new_review/cohort --series F --no-extended
```

The standard F series contains domain, class, tailoring, resistance, and
boundary-related panels; `--series G`, `D`, or `all` changes the set.
Omit `--no-extended` to request the extended panels too. Some panels have
extra admission requirements: the separately named `F13_bgc_domain_pca_2d`
needs a hash-bound cohort manifest and an independent denominator registry;
without these, read its HOLD receipt rather than treating it as an admitted
BGC PCA. The rendered `F13_strain_ordination_2d` is a different panel and
still needs visual review. The [catalog](FIGURE_CATALOG.md)
describes what each panel counts. Verify output sidecar data and captions for
every figure you use.

Do not combine two assemblies under one strain label. Reconcile package
input hashes, locus identities and bundle versions before comparing counts.
Edge and full-contig BGCs can inflate apparent class counts relative to
interior clusters. A heatmap of predicted biosynthetic capacity does not
establish expressed chemistry or antimicrobial activity.

## Ecological synthesis needs another join

A Mamey package can have a generic source string such as a rebuild label.
For a bee/wasp, host or geography comparison, join each exact strain and
assembly to an independently checked metadata table with an explicit source
and missingness state. State which strains were included and excluded,
whether the unit is a strain or BGC, and the denominator for each group.
Keep an unknown source unknown. The figure prompt library includes an
[ecological synthesis recipe](../prompts/figure_prompts/deliverable_maps/map_hymenoptera_crossstrain.md);
it describes a proposed combination of panels, not proof that the metadata
are bound or the panels are ready for publication.

## Master-workbook and prompt figures

Only the workbook-driven prompt route requires the tidy `figure_ready/*.csv`
export:

```bash
python tools/export_figure_ready.py /path/to/master.xlsx /path/to/new_review/figure_ready
```

The exporter reads `A2_Strain_Registry` and `B1_BGC_Master`;
`A3_Run_Manifest` supplies corrected counts when present. Inspect the
exported `DATA_DICTIONARY.md`, `strain_summary.csv`,
`bgc_inventory.csv`, and the individual recipe's required columns.
Optional diagnostics or cross-strain findings files depend on workbook
sheets actually present. Do not manufacture missing fields to satisfy a
plot recipe. [Prompt usage](../prompts/figure_prompts/HOW_TO_USE.md)
explains how a human or LLM implements a named figure.

## Review before manuscript use

For each candidate figure, preserve the input paths and hashes, plotted
CSV/TSV, code and package version, caption/methods, and a visual proof at
the intended size. The caption should state the unit, group sizes,
exclusions, calculation, source of host labels, and limits of the claim.
Inspect small text and legends for overlap. Use [Figure style](FIGURE_STYLE.md)
and [preflight and methods](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md)
for the corresponding figure family. Keep visual QA, mechanical PASS, and
scientific acceptance distinct.
