# FA6 — Mode B card exporter (`modeb-export`)

**Tag:** FEATURE (sign-off), prototype. **Non-scoring** — touches no scan, scorer, gate,
manifest, or version string. Ships one new module (`mamey/modeb_export.py`) and one test
(`tests/test_modeb_export.py`). **No `cli.py` edit** (this doc is the wiring hook).

## What it does

Turns an authored Mode B card (`§1–§30` markdown, or the `mode-b` top-lead card) into a
Word `.docx` and a PDF for hand-off outside the terminal.

- **Input:** a single Mode B card `.md` (e.g. `<pkg>/mode_b/<STRAIN>_Mode_B_Top_Leads.md`
  or an authored `<BGC>_ModeB.md`), **or** a package `mode_b/` directory (batch — every
  `*.md`, `PROVENANCE.md` excluded).
- **Output (next to the source, or under `--outdir`):**
  - `<card>.docx` — headings, the §-structure, bullets, blockquotes, and **every markdown
    table (the §4 evidence grid included) as a real Word table**.
  - `<card>.pdf` — reportlab, readable typography, a **page number on every page**, and the
    claim-safety footer on every page.
- **Claim-safety:** the card's own claim-safety language is preserved **verbatim** (it is
  ordinary markdown, never rewritten). Every page additionally carries the footer:
  `Class-level capacity hypothesis · judgment deferred · similarity not identity`.
- **Deterministic; no network.** Never mutates the source markdown.

## Renderer reuse (not a second reportlab renderer)

The PDF path **reuses the sanctioned markdown→flowables renderer**
`tools/render_deliverable_pdf.py` — its `parse()`, styles, cover, and `_footer_line()` —
loaded by file path (`tools/` is not a package). `modeb_export.export_card_pdf` adds only
the mandatory claim-safety footer + page-number `onPage` callback. No renderer is duplicated.

## Run it now (standalone, no CLI edit needed)

```bash
cd <code_tier>
# 1) produce a real card (or reuse an existing <pkg>/mode_b/*.md)
../Tools/bin/python3 mamey_run.py mode-b --package <pkg>            # writes <pkg>/mode_b/
# 2) export it
../Tools/bin/python3 -m mamey.modeb_export <pkg>/mode_b/<STRAIN>_Mode_B_Top_Leads.md
../Tools/bin/python3 -m mamey.modeb_export <pkg>/mode_b --outdir <pkg>/mode_b_export   # batch
```

`--format {docx,pdf,both}` (default `both`), `--outdir DIR`.

## Optional CLI wiring (a future cut, when promoted from prototype)

Add next to the `mode-b` parser in `mamey/cli.py::build_parser` (mirrors that block):

```python
    from .modeb_export import main as _modeb_export_main
    mx = sub.add_parser("modeb-export",
                        help="Export an authored Mode B card .md (or a mode_b/ dir) to .docx + .pdf")
    mx.add_argument("input", help="A Mode B card .md OR a package mode_b/ directory (batch)")
    mx.add_argument("--outdir", default=None)
    mx.add_argument("--format", choices=["docx", "pdf", "both"], default="both")
    mx.set_defaults(func=lambda a: _modeb_export_main(
        [a.input] + (["--outdir", a.outdir] if a.outdir else []) + ["--format", a.format]))
```

Post-seal, non-blocking style: it consumes an already-authored card and never fails a run.

## Dependencies & offline status

| Dep | Needed for | In interpreter (`Tools/bin/python3`) | In `Tools/wheelhouse` |
|-----|-----------|--------------------------------------|-----------------------|
| reportlab | PDF | yes (4.x) | yes (`reportlab-4.*.whl`) |
| pypdf | test page-count (optional) | yes | yes (`pypdf-*.whl`) |
| python-docx (+ lxml) | DOCX | yes (docx 1.2.0) | **no** |

> **reportlab version:** must satisfy the project pin `reportlab>=4.0,<5.0`
> (`pyproject.toml`, `requirements.txt`). Vendor a 4.x wheel in the interpreter and
> `Tools/wheelhouse` (`reportlab-4.*.whl`). An earlier cut of this table listed 5.0.0,
> which the `<5.0` cap excludes — do not ship a 5.x wheel against these pins.

**python-docx is installed in the interpreter but is NOT vendored in `Tools/wheelhouse`
(neither `linux_cp312_x86_64` nor `macos_arm64_cp314`).** The DOCX path therefore **degrades
gracefully**: if `docx` is unimportable, `export_card_docx` returns
`{"status": "SKIPPED_NO_DOCX", ...}` with an install hint and the PDF path is unaffected; the
test skips (never fails) the DOCX assertions. To enable offline DOCX export, add
`python-docx` + `lxml` wheels to both wheelhouse platform dirs.

## Verification (this cut)

- Real card: `mode-b --top-n 3` on `audit_runs/AS-XXX/package` →
  `AS-XXX_Mode_B_Top_Leads.md` exported → **PDF 14 pages / ~36 KB** (footer + verbatim
  claim-safety text present on the page), **DOCX ~45 KB / 9 real tables** (footer set).
- `pytest tests/test_modeb_export.py -q` → **3 passed**.
