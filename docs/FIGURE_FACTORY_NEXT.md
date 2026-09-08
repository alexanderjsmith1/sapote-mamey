# Figure Factory Next portable contract

## Integrated deliverable

Figure Factory is a first-class, expected deliverable, not an optional hand-run tool. In the
integrated flow it is invoked as a Mamey subcommand and auto-emitted alongside the other cohort
outputs:

```bash
python mamey_run.py figure-factory --config project/figure_factory_next.json
```

The `figure-factory` subcommand imports `mamey/figure_factory_next.py` and runs after the package
seal and cohort assembly, so an aggregate evidence-coverage figure is produced as part of the normal
run/cohort deliverable set rather than only when a user remembers to launch a separate script. The
integrated subcommand and its auto-emit wiring are delivered by the companion CLI/cohort wiring lanes;
this document is the deliverable-facing contract they render against.

The direct driver `python tools/figure_factory_next.py --config <json>` remains available as the
advanced/manual path — identical renderer, same `build()` behaviour and identical artifacts — for
one-off renders, debugging, and configuration development outside the run/cohort flow.

Both entry points call the same `build()`; nothing below changes between the integrated subcommand and
the manual tool. The renderer is a portable-policy candidate: a `PASS` is rendering and policy QA for
the recorded inputs, not scientific acceptance, integration, or release (see the claim ceiling below).

## Portable contract

Figure Factory Next v2 renders aggregate evidence coverage from two exact, content-addressed inputs:
an aggregate-metrics TSV and an authoritative cohort manifest. It does not discover developer
workspaces, infer roles from identifiers, or hardcode a private identity.

The metrics columns are `identity`, `channel`, `metric`, `numerator`, `denominator`, and
`denominator_key`. The manifest columns are `identity`, `role`, `include_by_default`, `genus`,
`cohort`, `assembly_state`, and `assembly_reason`. Every identity must occur in both files exactly.

Roles are `STUDY`, `REFERENCE`, `EXTERNAL_BENCHMARK`, or `OUTGROUP`. External benchmarks and
outgroups must be default-off. Assembly states are `PASS`, `FLAG`, `DEFAULT_OFF`, or `UNRESOLVED`.
A selected default-off identity is rendered only as a separately labelled sensitivity row and never
enters the study denominator. Within-genus grouping is the default; optional genera require explicit
declaration and selection.

Example configuration:

```json
{
  "schema_version": "sapote.figure-factory-next.v2",
  "external_data_root": "/configured/data/root",
  "output_dir": "outputs/figure_factory_next",
  "title": "Evidence readiness by channel",
  "figure_question": "How much of each declared evidence channel is observed?",
  "source_release": "project-release-receipt",
  "software_versions": "renderer version receipt",
  "inputs": [
    {
      "role": "aggregate_metrics",
      "logical_locator": "admitted/figure_metrics.tsv",
      "sha256": "<64 lowercase hex characters>"
    },
    {
      "role": "cohort_manifest",
      "logical_locator": "admitted/cohort_manifest.tsv",
      "sha256": "<64 lowercase hex characters>"
    }
  ],
  "comparison": {
    "default_genera": ["Genus alpha"],
    "optional_genera": ["Genus beta"],
    "selected_optional_genera": [],
    "selected_optional_identities": []
  },
  "owner_notes": []
}
```

Run through the integrated subcommand, or the manual driver for advanced use:

```bash
python mamey_run.py figure-factory --config project/figure_factory_next.json   # integrated deliverable
python tools/figure_factory_next.py --config project/figure_factory_next.json  # advanced/manual path
```

The renderer transactionally emits live-text SVG and native 300-DPI PNG artwork for both 3.5-inch
single-column and 7.2-inch double-column profiles into the configured `output_dir`, together with the
exact plotted data (`figure_factory_next_data.tsv`), the audit-only exclusion table
(`figure_factory_next_exclusions.tsv`), a dynamic caption/method record (`.json` and `.md`), separate
owner-notes metadata (`figure_factory_next_owner_notes.json`), and a hash receipt
(`figure_factory_next_receipt.json`). Solid accessible cohort colors are the default. Open diamonds
mark included assembly flags; an `x` marks a deliberately selected default-off assembly sensitivity
row. The output directory must not pre-exist; the renderer stages to a temp directory and atomically
replaces the target so a partial render is never left on disk.

## R / ggplot2 + ggtree export companion

Every Sapote-Mamey figure ships with the exact plotted data beside its image, so any figure is
restyleable in R without re-running the pipeline. The plotted-data sidecar is authoritative: for the
Figure Factory Next renderer it is `figure_factory_next_data.tsv`, and across the wider figure set each
figure carries a tidy `_data.csv` (produced through `tools/export_figure_ready.py`, whose tidy
`figure_ready/*.csv` are named for ggplot2 consumption). A figure whose numbers cannot be recovered
from its data sidecar is not integration-ready.

R templates render publication artwork from those sidecars: `tools/ggtree_placement.R` places a
phylogeny, and the companion `sapote_ggplot2.R` / `sapote_ggtree.R` template set (one function per
figure type plus a shared `theme_sapote()`) is delivered by the R-export sibling lanes, so a reviewer
can reproduce or restyle any figure in ggplot2/ggtree from the shipped `_data.csv` alone. The phylogeny
factory (`mamey/phylogeny_figure_factory.py`) emits a ggtree-ready tree plus its overlay table for the
same reason. See the R-export/ggtree sibling lanes for the template set and the tidy-`_data.csv`
coverage guarantee.

## Legacy Diner Menu retired

The legacy "Diner Menu" (`docs/DELIVERABLE_MENU.md`, an early pre-consolidation figure-generation
attempt) is retired: it is not the authoritative deliverable spec. The authoritative deliverable set is
the Mamey CLI subcommand surface (`python mamey_run.py --help`,
`docs/COMMAND_CATALOG.generated.md`), in which Figure Factory now appears as the `figure-factory`
integrated deliverable. Any still-useful figure item from the old menu is folded into this integrated
Figure Factory contract and the R-export companion above; do not treat the Diner Menu as current.

The renderer refuses schema v1, changed hashes, root escapes, invalid denominators, unknown cohort
colors, missing study rows, layout collisions/overflow, undersized text, and publication-inadequate
raster output. Owner notes and governance prose never appear on the scientific canvas or caption.

This is candidate engineering, not product selection, scientific acceptance, integration, release,
or evidence that a later compiled PDF has passed its separate embedding legibility gate.
