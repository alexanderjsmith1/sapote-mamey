# Reusable progress-dashboard pattern

This Figure Factory pattern adopts the useful visual grammar of the supplied BLASTp throughput chart without embedding BLASTp, personal paths, filesystem discovery, or a particular work queue in the renderer.

The generic input is a sequence of `ProgressEvent(series, completed_at, units)` records. `units` must be the actual completed work quantity, not a proxy such as file, panel, batch, or directory count unless that proxy is genuinely the governed unit. Invalid, negative, missing, infinite, future, or timezone-incompatible values fail closed rather than becoming zero.

The visual contract is:

- matched trailing-window columns;
- cumulative completed units in the larger upper panel;
- interval throughput in the smaller lower panel;
- stable color identity across windows and scales;
- one shared legend below the plots, carrying every window total;
- dynamic bottom reservation plus a programmatic legend-overlap and tick-collision check;
- PNG/SVG/CSV outputs and the shared Figure Factory receipt.

Domain adapters remain separate. Candidate future adapters could summarize Figure Factory render completion, package-audit records, governed evidence ingestion, Mode B section completion, or phylogenetic workflow stages such as admitted sequences or completed placements. Each adapter must define its completion timestamp, actual unit, denominator, missingness policy, and authority ceiling; this renderer does not infer any of them.

The pattern is descriptive operational telemetry. It does not validate scientific results, establish release readiness, or authorize publication.

## Current callable and binding limits

The implementation is `mamey.interactive_figures.progress_dashboard.render_progress_dashboard`; this guide describes an API, not a generic event-ingestion CLI. Required keyword arguments are `now`, `windows_hours`, `title`, `unit_label`, `out_stem`, `package_dir`, and `provenance`; `bin_hours` defaults to 1 and must divide 24. Windows must be unique finite positive values; events need a nonblank series, finite nonnegative units, compatible aware/naive timestamps, and completion no later than `now`. All timestamps may be naive if `now` is naive, so the adapter must document its timezone and normalize it consistently.

Keep the output stem inside the bound package root and choose a fresh stem. The CSV and receipt are written with ordinary replace-capable file operations. The final status is `CANDIDATE_RENDERED`; it binds the emitted data/artwork, not an independently verified source event log or completion authority. Record the source event-log hash, extraction version, unit definition, roster, timestamp policy, and deduplication rule separately. The generic renderer does not deduplicate repeated event records: duplicate completion events increase totals. A domain adapter must resolve event identity before rendering.

Source owner: `mamey/interactive_figures/progress_dashboard.py:40–53,81–109,119–133,166–195`.
