# Sapote Markdown authoring contract

This page defines one constrained Markdown dialect for user guides, scientific
analysis reports, and Mode B cards. The same parsed document model drives DOCX
and PDF output. Both formats consume the same parsed model; presentation still needs actual rendered-page review, and parser acceptance does not establish scientific meaning or visual correctness.

## Required front matter

```yaml
---
schema_version: sapote-markdown-1.0
document_type: human_guide       # human_guide | analysis_report | mode_b_card
title: A short, descriptive title
subtitle: Optional explanatory subtitle
audience: New users
authority: User documentation; not a biological result
render_profile: human_guide      # human_guide | scientific_report | mode_b_card
claim_safety_footer: Specific short claim ceiling, at most 190 characters
source_manifest: manifest.json   # optional but recommended
---
```

Each field is text. A blank value or YAML `null` counts as missing, so a
missing title, audience, authority or claim-safety footer is refused. Whole
numbers are read as text. Other YAML values, such as `true`, a date, a list or a
mapping, are refused with `META_FIELD_TYPE_INVALID`. The same rule applies to the
four `exact_locus` fields.

Mode B cards additionally require:

```yaml
exact_locus:
  strain: DEMO-STRAIN
  node_or_contig: demo_contig_0001_length_80000
  region: region001
  bgc_alias: BGC001
```

The H1 must contain the complete identity in this order:
`strain / full node-or-contig / region / BGC alias`. A Mode B card must contain exactly one ordered `## §1` through `## §N` sequence.
The section list comes from the contract the card declares in its header
comment, for example `<!-- MODE B contract: current50_v2 -->`. With no
declaration the card is checked against the 48-section contract (§1 to §48).
A card that declares `current50_v2` is checked for §1 to §50 and renders the
same way. A card that declares two different contracts is refused. See the
[Mode B profile matrix](MODEB_PROFILE_MATRIX.md) for the profiles. This
renderer checks structure only; it does not verify the card's content. Do not
delete required sections to force it to accept a card.

## Stable Markdown subset

Supported structures are H1–H4 headings, paragraphs, ordered and unordered
lists, simple bold/italic/code inline spans, horizontal rules, governed
callouts, tables, figures, and explicit page breaks. Raw HTML is rejected.

### Callouts

```markdown
> [LEAD] What the reader should know first
> One or more lines of authored content.
```

Allowed labels are `LEAD`, `NOTE`, `CAUTION`, `HOLD`, `CLAIM CEILING`, and
`DECISION`. They render as accessible tinted blocks, not as fake tables.

### Tables

Every table has a stable ID and declared layout:

```markdown
<!-- sapote:table id=lead_summary layout=portrait repeat_header=true widths=2,4,3 -->
| Lead | Interpretation | Limitation |
|---|---|---|
| Example | Class-level capacity hypothesis | Production untested |
```

Tables wider than six columns must use `layout=landscape` or
`layout=companion`. Widths are relative weights, one per column. Both DOCX and
PDF repeat the header row across pages when `repeat_header=true`. `layout=companion` is an accepted layout label; this renderer does not automatically export a separate companion table/data file.

### Figures, trees, and captions

```markdown
<!-- sapote:figure id=phylogeny_1 layout=full -->
![Maximum-likelihood tree of a governed protein family](assets/tree.png)
**Caption:** Branch labels identify the synthetic demonstration sequences.
**Methods:** Demonstration tree; no biological inference.
**Source:** Fixture generated locally by build_fixture_images.py.
```

The path must be relative and contained by the Markdown directory. Alt text,
caption, methods, and source are mandatory. A phylogenetic tree is therefore a
normal governed figure: the renderer does not guess its method, rooting,
support metric, or biological interpretation.

### Page breaks

```markdown
<!-- sapote:page-break -->
```

Use page breaks sparingly. Landscape transitions are automatic for declared
wide tables.

## Claim and content boundaries

- The parser validates declared identity/header agreement, structural fields and portable figure assets. `source_manifest` is retained metadata; its manifest bytes and locus membership are not independently verified. It does not validate a biological conclusion.
- Mode B is a governed post-extraction judgment workflow, not part of Mamey's
  deterministic fact-generation layer.
- Missing or unbound evidence remains a typed workflow gap, not biological
  absence.
- Similarity is not identity, and biosynthetic capacity is not production.
- Avoid decorative slogans in page furniture. Footers must state the document's
  actual claim ceiling.

## A complete small document

Save this as `document.md`. It is a valid `human_guide`.

```markdown
---
schema_version: sapote-markdown-1.0
document_type: human_guide
title: Five-Minute Quickstart
audience: New users
authority: User documentation; not a biological result
render_profile: human_guide
claim_safety_footer: Software guidance only; scientific conclusions require source review.
---

# Start here

> [LEAD] The short version
> Replace this sentence with the reader's most important takeaway.

## First steps

1. Add the source-derived facts.
2. State the decision or next action.
3. Preserve the relevant claim ceiling.
```

## Render it

```bash
sapote-render document.md --format both --outdir rendered
```

`sapote-render` is the installed script. `python -m mamey.document_export` takes the same arguments
and runs from the bundle root without the install. Both need the `documents` extra
(`python -m pip install -e '.[documents]'`). To write many documents from templates, use the
[document factory](TOKEN_LIGHT_DOCUMENT_FACTORY.md).

`--format both` checks the libraries first, renders both files to temporary names, then moves them
into place. It writes the DOCX, the PDF and a render receipt to the output folder. If the output
folder already holds files with the same names, they are overwritten. If rendering fails partway, run
it again into a new folder. Use `--format docx` or `--format pdf` for one file. Without `--outdir`
the output goes beside the Markdown file.

The receipt records the hashes of the input, the parsed model and the outputs. It does not check the
science or the page layout. Open the files and read the pages before you share them.
