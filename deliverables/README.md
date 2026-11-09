# Deliverable requests and report conversion

This folder holds request templates and a generic prompt library. It does not hold
finished reports or a workbook. Bring your own inputs.

To turn a Markdown report into a PDF or Word file, go to "Convert one report" below.

## Where to start

- To ask for a deliverable, fill in the [request template](DELIVERABLE_INSTRUCTION_TEMPLATE.md)
  and pick from the [prompt library](GENERIC_PROMPT_LIBRARY.md).
- To find the right command for a task, use the [task router](../docs/USER_TASK_ROUTER.md).
- For deliverables built from a package, use the [deliverable queue](../docs/DELIVERABLE_QUEUE.md).
- For slides, use [Strain slides](../docs/STRAIN_SLIDES.md).
- For Mode B cards (the written, evidence-backed card for one cluster), use the
  [Mode B walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md).
- For figures you bring in, see [incoming figures](incoming_figures/README.md).

## Convert one report

You need a reviewed Markdown file and Python 3.12 or newer. The Word route also needs
Pandoc. From the program folder:

```bash
bash tools/md_to_pdf.sh /absolute/path/to/report.md /absolute/path/to/new-report.pdf
bash tools/md_to_docx.sh /absolute/path/to/report.md /absolute/path/to/new-report.docx
```

The PDF script has two routes, and each has its own success ending. Check that the
exit status is `0`:
- ReportLab route: `wrote <path> (colorful reportlab)`.
- Pandoc and XeLaTeX fallback: `wrote <path> (pandoc+xelatex fallback)`, then
  `preflight QA: <path>.render_preflight.json`. This is also a success.

The Word script prints `wrote <path>`. It also needs a new path: an existing `.docx` is refused
with `REFUSED` and exit `2` unless you run `bash tools/md_to_docx.sh --replace IN.md OUT.docx`. Even
then only a regular file is replaced, and never the input. Open the file and look at every page. The
scripts do not check the science, privacy or layout.

The PDF script uses ReportLab first. If that fails, it tries Pandoc with XeLaTeX. If
a fallback tool is missing it prints `PDF_TOOLCHAIN_UNAVAILABLE` and exits `2`. The
fallback, when it succeeds, also writes three files beside the PDF: `<name>.render_preflight.json`,
`<name>.wide_tables_appendix.md` and `<name>.resource_bindings.json`. Read the
preflight file and the appendix when the fallback ran.

The PDF must be a new path. Before either route runs, the script checks the PDF and
all three sidecar names. If any of them already exists, or one of them is the input,
it prints `REFUSED` and exits `2` without writing anything. Pick a new PDF name, or
move the earlier files yourself. The PDF script creates the output folder. The Word
script does not.

## Build the older bulk set

`tools/build_all_deliverables.sh` is an older script that builds a fixed set of reports
from a folder of per-strain results (its "bank", read by `--banked-dir` in each
generator) and a workbook:

```bash
bash tools/build_all_deliverables.sh /absolute/path/to/bank /absolute/path/to/working-workbook.xlsx
```

Use it only in a throwaway copy of the program folder. It writes into this
`deliverables/` folder, replaces `build_all_deliverables_status.tsv`, and converts
every `.md` file below `deliverables/` except `README.md`, including the templates.
It has no dry-run option.

It needs Bash 4 or newer. The macOS system Bash is 3.2, and the script stops at its
`mapfile` line after the generators have run. Install a newer Bash (`brew install bash`)
and run the script with it. Check `bash --version` first.

When a step fails, the script records it and carries on. The last exit is nonzero if
a required step failed. Read each row of the status file, and check that the output
files are new. A `PASS` row means the command ran, nothing more.

A similarity match, a heuristic class or a missing match does not show that a
compound exists, that it is active or that it is new. Set the privacy level from the
package and profile you used, not from a file name
([privacy and evidence](../docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md)).
