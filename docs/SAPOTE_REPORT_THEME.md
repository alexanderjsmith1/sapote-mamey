# Sapote-Mamey report theme

The `sapote-evidence-dossier` theme is a shared set of colors, fonts and page
settings for Mode B cards (the per-locus evidence write-ups), ecology
synthesis and technical reports. It changes how a document looks. It does not
change what the document says.

Colors have jobs. Navy is for document identity and main headings. Teal marks
evidence-linked structure. Gold marks decisions and next actions. Cream marks
metadata and holds. Pale coral marks warnings. Always pair a color with a text
label such as `HOLD`, `NOT_SCORED` or `PRESENT`, so the page reads without color.

A card opens with the exact four-part locus identity, a short status panel and
a short evidence summary. Put long interpretation in paragraphs or bullets, not
dense table cells. The recommended order is: identity header, evidence summary,
decision or interpretation, holds and next experiment, claim-safety footer.
That order is a layout habit. It never reorders or drops a governed section.

## Use the helpers

`mamey/report_theme.py` holds the tokens and helpers. They return plain values
for an exporter to use. They draw nothing. Run from the bundle root:

```python
from mamey.report_theme import (
    section_role, section_accent, status_badge,
    format_locus_identity, theme_variant,
)

section_role(4)        # 'evidence'
section_accent(4)      # 'teal'
status_badge("hold")   # {'label': 'HOLD', 'fill': 'F5F1E7', 'foreground': '243648'}
format_locus_identity("DEMO", "demo_contig_0001_length_80000", "region001", "BGC001")
# 'DEMO / demo_contig_0001_length_80000 / region001 / BGC001'
```

- `section_role()` takes a section number and returns `identity`, `evidence`,
  `interpretation` or `safety`, for presentation only. The built-in table
  (`SECTION_ROLES`) lists these sections:
  - `identity`: 1, 2, 3;
  - `evidence`: 4, 20, 29, 34, 45, 46;
  - `interpretation`: 5, 6, 7, 18, 19, 22, 33, 48;
  - `safety`: 8, 27, 35 to 44, 47.

  Every other number returns `safety` as a fallback. That includes 9 to 17, 21,
  23 to 26, 28 and 30 to 32, and any text that is not a number. A `safety`
  result can therefore mean either a listed section or an unlisted one.
- `status_badge()` upper-cases the status and returns `label`, `fill` and
  `foreground`. Empty input becomes `NOT_SCORED`. An unknown label gets the
  neutral cream fill.
- `format_locus_identity()` joins the four parts in the required order. It
  raises `ValueError` if any part is blank. Never put a bare alias in a heading
  to save space.
- `theme_variant()` returns a copy of one preset: `evidence_dossier` (the
  default), `field_notebook`, `dark_lab` or `minimal_clinical`. Hyphens and
  underscores are both accepted. An unknown name raises `ValueError`.

## Limits

- The helpers format values. They do not check that a section list is complete,
  that a status is allowed, or that the four identity parts match a source
  record. Check the identity against its source before you format it. `None`
  becomes the text `None`, so reject missing fields in your own code first.
- A color never clears a `HOLD`, adds a missing section or approves a result.
- Not every export path uses these tokens. Open the finished DOCX or PDF and
  look at it before you rely on how it appears.
