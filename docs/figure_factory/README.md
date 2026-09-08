# Figure Factory — working folder index

Figure Factory is a first-class, expected deliverable, not an optional hand-run tool. It is invoked as
the integrated Mamey subcommand `python mamey_run.py figure-factory --config <json>` and auto-emitted
in the run/cohort flow; `python tools/figure_factory_next.py --config <json>` is the advanced/manual
path (same `build()`, identical artifacts). Read these first for the deliverable contract:

- `docs/FIGURE_FACTORY_NEXT.md` — portable contract, integrated invocation, emitted artifacts, and the
  R / ggplot2 + ggtree export companion.
- `wiki/Figure-Factory-Preflight-and-Methods-Manual.md` — preflight order, typed refusal surface,
  caption/methods contracts, and the claim ceiling.
- `docs/OPTIONAL_FIGURE_FACTORY_TOOLS.md` — optional theme/component preview galleries, distinct from
  the integrated deliverable.

## What lives in this folder

- `PROGRESS_DASHBOARD_PATTERN.md` — the reusable progress-dashboard visual grammar (matched trailing
  windows, cumulative + interval panels, shared Figure Factory receipt). Descriptive operational
  telemetry only; it validates no scientific result.
- `REPAIR_SPEC_Q-*.md` — per-figure repair specifications (identity, data source, denominator, and
  layout corrections for individual figures).
- `binding_status/Q*_BINDING_STATUS.md` — binding-status ledgers recording whether each repaired
  figure's identity and source tables are currently bound.

## Data sidecars and R export

Every figure ships its exact plotted data beside the image so it can be reproduced or restyled without
re-running the pipeline: the Figure Factory Next renderer writes `figure_factory_next_data.tsv`, and
the wider figure set carries a tidy `_data.csv` (via `tools/export_figure_ready.py`). R templates
(`tools/ggtree_placement.R` and the `sapote_ggplot2.R` / `sapote_ggtree.R` set from the R-export
sibling lanes) render publication artwork from those sidecars. A figure whose numbers cannot be
recovered from its sidecar is not integration-ready.

## Retired

The legacy "Diner Menu" (`docs/DELIVERABLE_MENU.md`) is retired and is not the authoritative
deliverable spec. The authoritative deliverable set is the Mamey CLI subcommand surface
(`python mamey_run.py --help`, `docs/COMMAND_CATALOG.generated.md`), in which Figure Factory now
appears as the `figure-factory` integrated deliverable.

A Figure Factory `PASS` is rendering, reconciliation, and policy QA for the recorded inputs. It is not
biological validation, Mode B acceptance, owner approval, integration, release approval, or publication
approval.
