# Token-light Sapote document factory

The document factory removes repeated authoring boilerplate without weakening
the governed Markdown contract. One short YAML project file holds shared
audience, authority, claim footer, and output choices. Reusable Markdown body
templates hold the authored substance. The factory materializes complete
governed Markdown, validates the entire project, and then calls the same
canonical DOCX/PDF renderer used by `sapote-render`.

## The short workflow

```bash
# Create a starter project.
sapote-documents init my_documents

# Edit one YAML manifest and small body templates, then preflight everything.
sapote-documents check my_documents/sapote-documents.yml

# Render the complete batch. The output directory must not already exist.
sapote-documents build my_documents/sapote-documents.yml \
  --outdir my_documents/rendered
```

The preflight normalizes and validates every document before the first DOCX or
PDF is published. A missing placeholder, missing asset, incomplete exact locus,
or malformed 48-section card therefore fails the project before rendering.

## Project manifest

```yaml
schema_version: sapote-document-project-1.0
authority: PROJECT_RENDER_ONLY_NOT_SCIENTIFIC_VALIDATION
defaults:
  audience: Sapote-Mamey users
  authority: User documentation; not a biological result
  claim_safety_footer: Software guidance only; conclusions require source review.
  output_format: both
documents:
  - id: quickstart
    source: templates/guide.md
    document_type: human_guide
    title: Five-Minute Quickstart
    subtitle: Start with the manifest
    variables:
      topic: Inspect Before Interpretation
```

Mode B entries must add the complete exact identity:

```yaml
  - id: modeb_demo
    source: templates/modeb.md
    document_type: mode_b_card
    title: Synthetic Mode B Demonstration
    authority: TRUE_DRAFT_NOT_PARENT_AUDITED_NOT_SHELF_PROMOTABLE
    exact_locus:
      strain: DEMO-STRAIN
      node_or_contig: demo_contig_0001_length_80000
      region: region001
      bgc_alias: BGC001
```

The factory injects the exact-identity H1 only when the reusable body has no
H1. It never guesses or falls back to a bare alias.

## Reusable body templates

Templates are ordinary governed Markdown without YAML front matter. A strict,
non-programmable placeholder can insert an explicit scalar:

```markdown
# {{topic}}

> [LEAD] The short version
> {{lead}}
```

There are no expressions, functions, imports, loops, or filesystem access in
the template language. Every placeholder must be supplied by the project
manifest or by the exact-locus system fields. Unresolved template markup fails
closed.

## Output structure

```text
rendered/
├── DOCUMENT_FACTORY_RECEIPT.json
├── normalized/
│   └── <document_id>/<document_id>.md
└── documents/
    └── <document_id>/
        ├── <document_id>.docx
        ├── <document_id>.pdf
        └── <document_id>.render_receipt.json
```

The normalized Markdown is deliberately retained. It makes the exact authored
input reviewable, patchable, and reproducible even though authors worked from
shared templates.

## Safety and scope

- Project and asset paths must be portable, relative, and contained by the
  project root.
- Existing output directories are never overwritten.
- All documents preflight before rendering starts.
- `--format both` remains strict for each document.
- Template reuse does not authorize prose transfer between biological loci.
- The factory reduces repeated packaging text; it does not reduce the evidence
  or reasoning required for a substantive scientific card.
- Rendering integrity does not validate scientific claims or authorize release.

