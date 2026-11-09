# Token-light Sapote document factory

The document factory removes repeated authoring boilerplate without weakening
the governed Markdown contract. One short YAML project file holds shared
audience, authority, claim footer, and output choices. Reusable Markdown body
templates hold the authored substance. The factory materializes complete
governed Markdown, validates the entire project, and then calls the same
canonical DOCX/PDF renderer used by `sapote-render`.

## Setup and the short workflow

From the bundle root, install the document extra once: `python -m pip install -e '.[documents]'`.
This adds the Word and PDF libraries. If it is missing, `build` fails. `check` does not test for it. If you prefer not to rely on the installed
`sapote-documents` script, run `python -m mamey.document_factory` from the bundle root with the same
subcommands.

```bash
# Create a starter project.
sapote-documents init my_documents

# Edit the YAML manifest and the small body templates, then check everything.
sapote-documents check my_documents/sapote-documents.yml

# Render the batch. The output folder must not already exist.
sapote-documents build my_documents/sapote-documents.yml \
  --outdir my_documents/rendered
```

What you should see: each command prints JSON. `init` and `check` print `"status": "PASS"`. `check`
also lists the document IDs and a hash for each. `build` prints `"status": "PASS"`, one entry per
DOCX and PDF it wrote, and the receipt. A failure prints `"status": "FAIL"` and exits 1.

Run `init` in a new or empty folder outside the bundle and outside any source evidence. It writes
`templates/` and the YAML manifest. If `init` stops partway, the next `init` refuses the nonempty
folder. Fix the files by hand or start in a fresh folder.

Document IDs must start with an ASCII letter or digit and contain only ASCII letters, digits, underscores or hyphens (maximum 80 characters). Choose IDs unique even when case is ignored: admission compares case sensitively, while output directory names can collide on a case-insensitive filesystem. Use a fresh `--outdir` outside source evidence. If you leave it out, `build` writes `rendered_documents` beside the project YAML.

The preflight normalizes and validates every document before the first DOCX or
PDF is published. A missing placeholder, missing asset, incomplete exact locus,
or malformed 48-section card therefore fails the project before rendering.
An image whose path would land on the normalized `<document_id>.md` file, ignoring case,
is refused with `ASSET_PATH_COLLIDES_WITH_DOCUMENT`. The asset check confirms each image
file exists; it does not check that the file is a readable image. Open the rendered output.

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

`init` writes only `templates/guide.md`. For a Mode B entry, create the card template yourself (the example below uses `templates/modeb.md`). Mode B entries must add the complete exact identity:

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
<outdir>/
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


## Check, build and failure

`check` validates the whole project in a temporary folder and prints a hash for each normalized
document. It writes nothing to your project. It does not test the Word or PDF libraries, look at
pages or verify science.

`build` renders into a private staging folder and then renames it to your `--outdir`. If `build`
fails after that rename, the output folder can still exist. Keep it as evidence, choose a new
`--outdir` and run `build` again.

The `mode_b_card` document type needs numbered `## §N` sections that match the card's own contract.
The contract comes from a header comment in the card, such as `<!-- MODE B | contract: current50_v2 -->`.
With no header comment the card is held to `full48` (sections 1 to 48). A `current50_v2` card needs sections 1 to 50.
A card whose sections do not match its contract fails `check`. Do not delete sections to satisfy this tool.
See [Mode B profiles](MODEB_PROFILE_MATRIX.md) and
[the Markdown authoring contract](SAPOTE_MARKDOWN_AUTHORING_CONTRACT.md).

The receipts record DOCX and PDF hashes, template and project hashes, and each document's normalized
Markdown hash. They do not record image hashes, so keep the image files with the handoff. Do not
change the YAML, templates or images between `check` and `build`. A saved `check` result does not
prove a later build used the same bytes.

Receipts hold absolute local paths. Exit codes are 0 for success, 1 for a caught failure and 2 for a
command-line error. Open the Word and PDF files and read the pages before you share them. A receipt
does not judge page quality.
