# Figure Factory preflight and methods

Use the [aggregate rendering guide](../docs/FIGURE_FACTORY_NEXT.md) for the current configuration,
commands and output files. This page explains what to verify before using a figure. Different
renderers have different input and refusal contracts; the name Figure Factory does not make them
interchangeable.

## Choose the renderer

| Surface | Inputs and behavior |
|---|---|
| Aggregate Figure Factory Next | v2 configuration, aggregate-metrics TSV and cohort manifest, exact input hashes, separate evidence channels; emits SVG/PNG, TSV/CSV, exclusions, methods and receipt. |
| Phylogeny Figure Factory | A supported `figure_kind` routes the same CLI to the phylogeny renderer; tree, identity and annotation requirements depend on that kind. |
| Package/cohort and domain figures | Read their command-specific package or table inputs; optional data or plotting dependencies can produce a documented skip. |
| Repair specifications | Describe intended changes and unresolved bindings. A specification or registry entry is not evidence that a renderer or input exists. |

Run commands from the extracted bundle root through `python mamey_run.py`.
Automatic run/cohort output requires a discoverable configuration; see the rendering guide for
search order and the automatic output-directory replacement policy. Manual aggregate rendering
requires a new output directory.

## Before rendering

1. State the figure question, measurement and observation unit.
2. Bind source locators, hashes, input schemas and the exact run/package receipt.
3. For individual loci use `strain / full node-or-contig / region / BGC alias`; preserve the
   sequence identity for any protein or domain join.
4. Declare the fitted or aggregated population and excluded, missing and observed-zero rows.
5. Keep evidence channels and comparator roles distinguishable in both data and labels.
6. Inspect the renderer's actual missingness and denominator checks. Do not replace a missing
   observation with zero to make a plot render.
7. Choose the final physical size and verify readable labels, legends and unclipped bounds.
8. Keep plotted data, methods and the render receipt beside the artwork.

## Aggregate renderer details

The v2 cohort manifest distinguishes STUDY, REFERENCE, EXTERNAL_BENCHMARK and OUTGROUP roles.
External benchmarks and outgroups are default-off; explicitly selected default-off assembly rows
are separate sensitivity rows. This is a current v2 capability, replacing the older v1 description.

An empty eligible set is refused. An all-zero numerator set can be a valid observed result;
this renderer does not implement a universal all-zero refusal. Assess missingness and the
scientific question before deciding whether such a figure is useful.

Record the denominator key, channel, inclusion/exclusion rules and transformation in the methods.
For ordinations also state features, centering/scaling, missing-value handling, fitted subset,
explained variance and loadings. These belong in an adjacent methods record, not boilerplate on
the scientific canvas. Preserve data-specific caveats that materially affect interpretation.

## Outputs and restyling

The aggregate renderer exports matching `figure_factory_next_data.tsv` and
`figure_factory_next_data.csv`. The shipped `tools/figure_factory_next_ggplot.R` renders the CSV
with ggplot2; use the invocation in the aggregate guide. Tree and other figure families have their
own sidecars and R tools. Verify each family's actual output rather than assuming one universal CSV.

The [deliverable menu](../docs/DELIVERABLE_MENU.md) remains a generated capability index.
[Repair specifications and binding records](../docs/figure_factory/README.md) are development material.
A successful render receipt records mechanical checks; interpretation still depends on the inputs.
