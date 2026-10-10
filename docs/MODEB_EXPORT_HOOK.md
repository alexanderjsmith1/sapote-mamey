# Mode B card export: current command and verification boundary

`modeb-export` is a shipped .447 command, not a future CLI-wiring prototype. It converts Markdown into DOCX/PDF with a selected report theme; it does not author the card or verify its complete selected Mode B profile.

```text
python mamey_run.py modeb-export <card.md> --outdir <new-export-folder> --format both --theme evidence_dossier
```

Use the selected compatible interpreter from the bundle root. Input may also be a directory: batch discovery reads sorted top-level `*.md`, excluding only `PROVENANCE.md`. It does not distinguish a completed card from a template, routing document, or other Markdown by filename. Select the intended saved card explicitly or curate a bound input directory.

## Verification before export

Verify the exact saved Markdown under its work-order contract with its package-scoped alias and complete strain / full node-or-contig / region / BGC alias binding. `verify-modeb` defaults to `full48`; use `--contract current50_v2` where required. Inspect errors, warnings, roster/coverage flags and consumed-source bindings separately. Passing a formatting export cannot supply these checks or owner acceptance.

The exporter calls `lint_card` and retains only `CLAIM_SAFETY` findings for its refusal gate. It does not call the full authored verifier, retain all other linter findings, validate current50 structure, or bind package context. `REFUSED_CLAIM_SAFETY` means no new requested exports are written through that orchestration call. Fix the source and review the actual evidence instead of treating the claim-safety footer as validation. Direct low-level DOCX/PDF render functions do not perform this orchestration gate.

The standalone module exposes `--force` for an explicitly reviewed phrase; the bundle `mamey_run.py modeb-export` parser does not expose or forward that option. Such an override does not convert a finding into scientific acceptance.

## Outputs, dependencies, and exit status

Themes: `evidence_dossier` (default), `field_notebook`, `dark_lab`, `minimal_clinical`. DOCX uses python-docx; PDF uses reportlab through the packaged `mamey.markdown_pdf` renderer. It no longer imports `tools/render_deliverable_pdf.py`. Reportlab is a core declared dependency (`>=4.0,<5.0`); python-docx/lxml are in the `documents` extra. Package declarations do not prove the selected interpreter or offline wheelhouse contains those modules; inspect dependency status for that environment.

Each requested format reports `WRITTEN`, a typed skip, or refusal. Default `--format both` requires **both** outputs written and returns 1 if either is skipped. PDF-only skipped returns 1. DOCX-only `SKIPPED_NO_DOCX` can return 0: always inspect the per-format status and file. Missing single input returns 2; an empty batch returns 1. Other read/render failures can propagate as exceptions and leave earlier batch outputs.

Artifacts use the source stem. Existing export files are replaced via `.tmp` siblings; there is no no-clobber output guard or atomic DOCX+PDF pair transaction. Use a fresh export folder and preserve prior artifacts. A failure or refusal does not remove a preexisting export in a reused directory. The PDF prints the claim ceiling on each page; the explicit page-number callback skips the cover page.

## Binding and review

Export results provide path, bytes, theme and engine; no source/artifact hash receipt or saved verifier receipt is emitted. Retain the exact Markdown hash, package/source hashes, verifier invocation/receipt, theme, dependency versions and output hashes in a separate run record. Embedded assets are separate inputs and need their own binding. Inspect actual rendered pages at intended size before claiming visual QA. Use actual output and visual-review receipts for current page counts and layout.

Source owners: `mamey/cli.py:7032–7042`; `mamey/modeb_export.py:245–263,338–368,371–443,449–545`; `mamey/authored_verify.py:68–109,591–680`; `pyproject.toml:13,33`.
