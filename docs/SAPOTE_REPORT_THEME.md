# Sapote-Mamey report theme

The `sapote-evidence-dossier` theme is a shared visual layer for Mode B cards,
ecological synthesis, and technical reports. It separates evidence, interpretation,
and typed uncertainty visually without changing their meaning.

Use deep navy for document identity and primary headings, teal for evidence-linked
structure, gold for decision or next-action accents, cream for metadata and holds,
and pale coral for warnings. Always pair color with a text label such as `HOLD`,
`NOT_SCORED`, or `PRESENT`.

Mode B cards should open with the exact four-part locus identity, a compact status
panel, and a short evidence summary. Sections 4, 27, 29, 45, and 46 should use
readable tables with explicit widths and repeating headers. Long interpretation
belongs in paragraphs or bullets, not dense table cells.

The theme is compatible with Markdown, DOCX, and PDF renderers. It is not a
scientific inference layer: similarity remains distinct from identity, capacity
from production, and missing evidence from biological absence.

## Semantic presentation helpers

Renderers may use `section_role()` and `section_accent()` to keep the same visual
logic across formats: identity sections use navy, evidence sections use teal,
interpretation sections use gold, and safety/hold sections use muted neutral
styling. `status_badge()` always emits a text label as well as colors, so a PDF
or DOCX remains understandable when printed or viewed by a color-blind reader.

`format_locus_identity()` is the single display helper for the required order:
strain / full node-or-contig / region / BGC alias. It rejects blank/whitespace string fields after conversion; it does not validate locus provenance, component grammar or source agreement.
Use it in headings, evidence cards, table rows, and footers; never substitute a
bare alias for visual compactness.

The recommended card layout is: identity header → evidence summary → decision /
interpretation → typed holds and next experiment → claim-safety footer. This is a
layout convention only; it must not reorder or omit the card's governed sections.

## Implementation versus layout policy

These table-width/repeating-header/layout suggestions are reader-facing policy, not universal renderer guarantees. `mamey/report_theme.py` provides renderer-neutral tokens and helpers; inclusion in this document does not prove every Markdown, DOCX or PDF path consumes them. Use the chosen exporter contract and inspect actual pages before asserting appearance or accessibility.

`section_role()` converts the input with `int()` and maps hardcoded section numbers; unknown/unconvertible sections become `safety`. This is presentation fallback, not a current50 schema validator. Do not let its colors authorize a missing section or reinterpret the active contract (`:52–74`). `status_badge()` uppercases arbitrary input, substitutes `NOT_SCORED` for falsey input, and returns neutral colors for unknown labels. It does not validate status enums or clear a HOLD (`:77–95`).

`format_locus_identity()` converts each value with `str()` before trimming (`:85–90`). Therefore `None` becomes literal `None`, and numeric values can pass; the old “raises on incomplete input” promise was broader than implementation. Reject missing/nonstring fields in the governed caller and bind strain / full node-or-contig / region / BGC alias to exact source identity before formatting. A correctly styled header is not verified evidence.

`theme_variant()` normalizes hyphens/underscores and raises for unknown names, returning copied tokens (`:98–107`). Theme variants do not change scoring, scientific approval, full-profile verification or output receipt scope. Preserve input/renderer/config/command/output hashes separately when the selected producer does not emit them. Inspect the actual rendered pages and retain their visual-review status.
