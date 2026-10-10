# Screening exploration extension register

The bundle contracts remain the default. This register distinguishes implemented candidate extensions from workspace work and future proposals.

| Addition | Existing bundle route | Disposition |
|---|---|---|
| Qualitative overlap and host-call summaries | Tidy/matrix renderers | Candidate custom input contracts; no replacement of registered schemas |
| Four-dose fraction distribution boxplots | Bioassay observation factory | Candidate descriptive display; does not perform canonical observation admission |
| Explicit 0–100 inhibition scores | Canonical factory retains unbounded measurements | Candidate opt-in transformation; raw retained, summaries recomputed |
| Archive format coverage | Project plan inventory | Candidate record-count display; not strain or replicate counts |
| Mode B machinery prevalence | Matrix renderer and governed cohort inputs | Candidate snapshot display; exact-locus source tables required, current cohort acceptance separate |
| Class profiles next to qualitative calls | Strain/tidy renderers | Candidate juxtaposition; no gene-to-activity inference |
| Standalone caption/data/R ZIP packager | Figure reproducibility contract | Candidate implementation of a required handoff; includes unchanged shared R theme |
| 100 ideas and searchable file gallery | Existing figure catalog and file atlas | Workspace navigation artifact; not implemented in bundled software |
| Source-specific workbook/SQLite preparation | Existing observation and figure-ready admission | Workspace adapters only; generic mapping profiles remain a proposal |

The last two rows are documented proposals, not portable implementations. Their source-specific scripts and private scientific data do not enter this patch. Future implementation must use configurable discovery roots, explicit schema mappings, source hashes and governed admission; catalog presence cannot select evidence authority.

This candidate supersedes the earlier screening-exploration patch. Apply one cumulative patch to the bound baseline, never both. It adds four implementation/document files plus tests and this register; it does not change versions, existing observation semantics, or release status.

## Current candidate validation boundary

`tools/render_screening_exploration.R` consumes specified CSV filenames, applies per-view checks, and makes displays; it does not perform source discovery or canonical scientific admission. Each available view is optional, and a caption/PNG/PDF set is written sequentially. Existing output checks and opt-in overwrite are renderer behavior, not an all-output transaction. The `--score-0-100` transform clips display values; raw values and scope/missingness must remain traceable. Do not call clipped values canonical assay measurements.

`tools/package_screening_figure.py:12–62` checks companion paths/nonempty file size and parses receipt JSON, then copies **all** input-directory CSVs plus supplied figures/scripts/caption/receipt/session text into a new packet and ZIP. It does not validate image/PDF contents, receipt schema, claimed input hashes, caption-to-figure agreement or R-session authenticity. An empty JSON object can satisfy the JSON parse check; packaging success is not figure validity, evidence admission, reproduction success or scientific adoption. Package only a reviewed minimal input directory; record reason/estimated size before any separately authorized data/artifact copy, and preserve sources in place.

The packet's `MANIFEST.json` binds copied bytes but not its own bytes or the final ZIP; publication is sequential and can leave a partial directory after error. It does not render/test `reproduce.R` itself. Keep an external packet/manifest/ZIP hash inventory and actual reproduction/visual-review status. The shared R theme is retained as supplied content, not independent evidence that all figures meet house rules. Record actual packaging, reproduction and visual-review results separately.

“Candidate supersedes” above describes patch lineage only; it does not mean the current package has been adopted, released, scientifically accepted or verified across private sources. Use [the current screening guide](SCREENING_EXPLORATION_R.md) for the producer's source-scoped limits. Workspace galleries, ideas and source-specific adapters remain proposals/navigation until independently governed. Complete locus identities are required when a source table names a BGC; no juxtaposed assay display establishes locus causality.
