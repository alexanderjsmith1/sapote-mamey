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
strain / full node-or-contig / region / BGC alias. It raises on incomplete input.
Use it in headings, evidence cards, table rows, and footers; never substitute a
bare alias for visual compactness.

The recommended card layout is: identity header → evidence summary → decision /
interpretation → typed holds and next experiment → claim-safety footer. This is a
layout convention only; it must not reorder or omit the card's governed sections.
