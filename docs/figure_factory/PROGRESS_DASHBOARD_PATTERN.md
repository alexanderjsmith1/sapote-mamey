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
