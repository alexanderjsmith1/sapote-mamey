# Token-light Sapote document factory

The document factory removes repeated authoring boilerplate without weakening
the governed Markdown contract. One short YAML project file holds shared
audience, authority, claim footer, and output choices. Reusable Markdown body
templates hold the authored substance. The factory materializes complete
governed Markdown, validates the entire project, and then calls the same
canonical DOCX/PDF renderer used by `sapote-render`.

## Setup and the short workflow

From the bound bundle root, install its document extra in the selected engine virtual environment when needed: `python -m pip install -e '.[documents]'`. The console scripts are installed entry points; they resolve to that environment's package. To pin source without depending on those entry points, use `python -m mamey.document_factory` from the selected bundle root with the same subcommands. Do not run installation merely to inspect this guide.

```bash
# Create a starter project.
sapote-documents init my_documents

# Edit one YAML manifest and small body templates, then preflight everything.
sapote-documents check my_documents/sapote-documents.yml

# Render the complete batch. The output directory must not already exist.
sapote-documents build my_documents/sapote-documents.yml \
  --outdir my_documents/rendered
```

Run `init` in a new or empty authoring directory outside the installed bundle/source evidence. It writes `templates/`, the YAML manifest and the guide body sequentially. A failed initialization can leave a nonempty partial project that the next `init` refuses. Preserve those files, then repair the authoring project explicitly or initialize a fresh directory; `init` is not a resume command.

Document IDs must start with an ASCII letter or digit and contain only ASCII letters, digits, underscores or hyphens (maximum 80 characters). Choose IDs unique even when case is ignored: admission compares case sensitively, while output directory names can collide on a case-insensitive filesystem. Use an explicit fresh `--outdir` outside source evidence. If omitted, build uses `rendered_documents` beside the project YAML, rather than the example's `rendered` directory.

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
H1. It never guesses or falls back to a bare alias. Supply all four components as explicit nonempty strings copied from the bound source identity. The factory converts values to strings; YAML null can become the literal `None`. The Markdown validator checks `region`/`BGC` syntax and a small list of generic node labels, but does not verify strain or full node identity against source evidence. A validation PASS therefore does not establish a correctly bound locus or reject every missing-value spelling.

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

Variables merge in this order: default variables, document-entry variables, then system fields. `document_id`, `title`, `audience`, `authority` and `claim_safety_footer` always use the planned metadata; Mode B identity components and `exact_locus` then override variables with those names. Changing a same-named variable does not change its metadata/system field. Variable values must be scalars other than null; nested mappings/lists are refused. Other metadata has string coercion rather than the same scalar admission, so use explicit strings and inspect the normalized front matter.

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

- Template source paths must be portable, relative and contained by the project root. Image assets are resolved relative to their template source directory and must remain inside that directory. A project-contained sibling asset referenced with `../` can therefore still be refused.
- Existing output directories are never overwritten.
- All documents preflight before rendering starts.
- Choose `output_format: both`, `docx` or `pdf` in a document entry or defaults. The factory CLI has no `--format` argument; that flag belongs to `sapote-render`. `both` renders both temporary artifacts before publishing a document.
- Template reuse does not authorize prose transfer between biological loci.
- The factory reduces repeated packaging text; it does not reduce the evidence
  or reasoning required for a substantive scientific card.
- Rendering integrity does not validate scientific claims or authorize release.


## Preflight, failure and profile limits

`check` normalizes the whole project in a temporary directory and returns validation status and normalized hashes. It does not publish the normalized Markdown, exercise DOCX/PDF renderer dependencies, inspect pages or verify scientific claims.

`build` normalizes every document, renders into a private staging directory beside the selected output, then renames that directory to the requested destination. It repairs render-receipt paths and writes `DOCUMENT_FACTORY_RECEIPT.json` after that rename. If a later receipt repair, hash/read or receipt write fails, the command can return failure while the published output directory remains. Inspect the directory and receipts before retrying; the next build refuses an existing destination. Preserve it as partial evidence and choose a fresh destination for a corrected retry.

The factory's `mode_b_card` validator currently requires numbered sections 1–48. This is a renderer schema constraint, not automatic support for native Mode B `current50_v2` cards. Use the selected native profile's emitter and verifier for authorship, and choose a compatible export path without deleting required sections merely to satisfy a different renderer schema. See [Mode B profiles](MODEB_PROFILE_MATRIX.md) and [the Markdown authoring contract](SAPOTE_MARKDOWN_AUTHORING_CONTRACT.md).

The factory receipt records DOCX/PDF hashes and template/project hashes; each document's render receipt also records its normalized Markdown input hash and canonical model hash. Referenced images are copied into each document's normalized directory, but these receipts do not enumerate image-byte hashes. Keep image sources and their separately recorded hashes with the handoff. Keep the YAML, templates and assets unchanged throughout check/build: the factory hashes YAML/templates after rendering rather than checking a frozen consumed-byte snapshot. A saved `check` result is not freshness evidence for a later build.

Receipts contain absolute local paths; retain the relative project/output layout and update any handoff locator mapping explicitly when moving a project. The command prints its result JSON on stdout and exits 0 on success; caught command failures print `status: FAIL` on stdout and exit 1, while argument-parser errors exit 2. Save stdout and exit status when recording a run. No receipt establishes rendered-page quality or owner acceptance. Inspect requested outputs and pages separately before claiming they are usable for readers.
