# Sapote Markdown authoring contract

This prototype uses one constrained Markdown dialect for user guides, scientific
analysis reports, and Mode B cards. The same parsed document model drives DOCX
and PDF output. The renderer changes presentation, never scientific meaning.

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

Mode B cards additionally require:

```yaml
exact_locus:
  strain: DEMO-STRAIN
  node_or_contig: demo_contig_0001_length_80000
  region: region001
  bgc_alias: BGC001
```

The H1 must contain the complete identity in this order:
`strain / full node-or-contig / region / BGC alias`. A Mode B card must contain
exactly one ordered `## §1` through `## §48` sequence.

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
PDF repeat the header row across pages.

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

- The parser validates structure and binding; it does not validate a biological
  conclusion.
- Mode B is a governed post-extraction judgment workflow, not part of Mamey's
  deterministic fact-generation layer.
- Missing or unbound evidence remains a typed workflow gap, not biological
  absence.
- Similarity is not identity, and biosynthetic capacity is not production.
- Avoid decorative slogans in page furniture. Footers must state the document's
  actual claim ceiling.

## Strict export behavior

```bash
python -m mamey.document_export document.md --format both --outdir rendered
```

`--format both` checks all dependencies first, renders to temporary files, and
publishes neither final artifact unless both DOCX and PDF were written. Use
`--format docx` or `--format pdf` when a single output is intended.

