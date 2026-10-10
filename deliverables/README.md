# Deliverable requests and legacy bulk rendering

This CODE bundle ships request templates and a generic prompt library here. It does not ship the historical analyses, deep dives, workbook, `DLV_EXAMPLES.md` or `HIVE_Board.csv` previously advertised in this index. Supply and verify your own input bank/workbook; do not treat old cohort counts or named reports as current results.

Start with the [request template](DELIVERABLE_INSTRUCTION_TEMPLATE.md), [prompt library](GENERIC_PROMPT_LIBRARY.md) and [current task router](../docs/USER_TASK_ROUTER.md). For package deliverables, use the [deliverable queue contract](../docs/DELIVERABLE_QUEUE.md). For the paired PowerPoint workflow, request the **Sapote-Mamey Strain slides builder**, `tools/strain_slides.py`, described in [Strain slides](../docs/STRAIN_SLIDES.md). For current native Mode B authoring, follow the [Mode B walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md); the banked eight-section helper is a separate legacy report.

## Legacy bulk command

From the root of a disposable working copy, with explicit existing inputs:

```bash
bash tools/build_all_deliverables.sh /absolute/path/to/bank /absolute/path/to/working-workbook.xlsx
```

Source: `tools/build_all_deliverables.sh`. This writes to the fixed relative `deliverables/` directory and overwrites `build_all_deliverables_status.tsv`. It runs the Mode B deep-dive, thesis-vignette, GCF-tag and size-profile generators, then discovers **every** `*.md` below `deliverables/` except files named exactly `README.md`. Request templates, this prompt library and incoming Markdown are therefore also eligible for conversion. It has no output-root or dry-run flag. It uses `python3` from PATH and Bash `mapfile`; verify both in the intended environment. Do not invoke it on the immutable bundle merely to preview one incoming figure.

A failed generator is recorded and later phases continue. Old Markdown can therefore still be rendered. The final exit is nonzero if a required phase failed; inspect each log row, expected fresh outputs and their source bindings rather than accepting whatever files remain in the directory. A PASS establishes successful commands/rendering, not scientific acceptance, privacy clearance, exact-locus binding or visual QA. Output writes are not one all-or-nothing transaction.

## Single-file conversion

When conversion is requested, prefer a specific reviewed Markdown input and fresh destinations:

```bash
bash tools/md_to_pdf.sh /absolute/path/to/report.md /absolute/path/to/new-report.pdf
bash tools/md_to_docx.sh /absolute/path/to/report.md /absolute/path/to/new-report.docx
```

The PDF wrapper first tries `tools/render_deliverable_pdf.py` (ReportLab), then falls back to Pandoc plus XeLaTeX if the primary renderer fails. Fallback also writes preflight JSON and possibly a wide-table Markdown appendix beside the PDF. Missing fallback tools cause failure. The Word wrapper requires Pandoc. Existing destination files can be replaced; the PDF wrapper creates its parent directory, while the Word wrapper does not. These wrappers do not validate evidence or guarantee page layout. Inspect actual rendered pages before claiming visual QA. Markdown-only requests require no conversion.

See [incoming figures](incoming_figures/README.md) for a complete evidence handoff. A similarity anchor, heuristic class, absent anchor or Mode B verdict does not establish a compound, biological activity or novelty. Privacy must be tied to the actual package/profile and reviewed release scope; a filename prefix is insufficient.
