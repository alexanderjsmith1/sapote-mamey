# From a validated package to a table, figure and caption

Follow these steps to turn a validated package into one table, one figure and a caption you can review. You need a finished run (see [first run](reader/01_FIRST_RUN.md)). A **Mode B card** is a written interpretation of one locus, built from its gene list and supporting sources. It is optional here. Without one, use the inventory and triage tables. Terms are in the [glossary](GLOSSARY.md).

Replace `EXAMPLE` with your run label. Run commands from the program folder.

## 1. Copy the package, then check the copy

`validate` refreshes `package_status.json` in the folder it is given, so copy first and keep the original untouched. Some figure and report commands also write into the package ([which ones](POSTSEAL_READERS.md)).

```bash
cp -R runs/EXAMPLE/package ../EXAMPLE-review
shasum -a 256 runs/EXAMPLE/EXAMPLE_*_Complete_Package.zip
python mamey_run.py validate ../EXAMPLE-review --workbook-strict
```

Save the checksum with your notes. It identifies the exact input. A good validation exits 0, with status `MAMEY_COMPLETE` or a status that starts with `PASS` (see [first run](reader/01_FIRST_RUN.md#4-check-that-the-run-worked)). Then read `issue_log.md` in the package; [Read your results](READING_YOUR_RESULTS.md) explains both. Stop if validation fails.

## 2. Write the question and pick the table

Write one sentence saying what you want to learn. Name the table that answers it, such as `EXAMPLE_2_inventory.csv` (one row per region) or `EXAMPLE_4_triage_board.csv` (every region, ranked, including regions flagged as excluded from leads). Say what one row means.

Identify each locus as **strain / full node-or-contig / region / BGC alias**, copied from one source row. Keep a missing measurement separate from a zero.

## 3. Draw the figure

```bash
python mamey_run.py render-figures --package ../EXAMPLE-review \
  --outdir reviews/EXAMPLE/standard
```

Expect `top_antibacterial_leads.png`, `top_antifungal_leads.png`, `figure_manifest.csv` and `FIGURE_QA.md` in the output folder. An exit code of 0 does not prove both images exist; check the folder. Other figure sets and renderers are in the [figure guide](FIGURES_START_HERE.md).

In `FIGURE_QA.md`, each figure shows `[PASS]`, `[FAIL]` or `[SKIP]`. If no rows qualify, a figure can be skipped and `NO_FIGURES_RENDERED.md` appears.

Check the images:

```bash
python tools/figure_render_qc.py reviews/EXAMPLE/standard \
  --out reviews/EXAMPLE/standard-qa --ocr require --print-width-in 6
```

Set the width to your layout. `--ocr require` makes the run fail when text cannot be checked; it reads SVG text or macOS OCR. Use a fresh `--out` folder, because an existing one is refused. Read `RENDER_QC.md` and `RENDER_QC.tsv` in the output folder, then look at every image yourself for clipped labels, wrong units and the rows you meant to show.

## 4. Write the caption

State a value with its unit, source row and field, calculation and the figure it appears in. Write the caption from the plotted data, not from memory. Say what is plotted, the unit, how many rows, which rows were excluded and why, and the threshold. Put no interpretation on the figure itself, and keep work logs out of the caption. Say whether the figure covers all regions, a subset or one representative per group. A tree or family analysis can be plotted only after its own analysis has finished. Caption rules are in rule 2 of the [house rules](FIGURE_HOUSE_RULES.md); write the caption first as a Markdown file, then run `python tools/caption_band.py <plot.png> <caption.md> --outdir <folder>`. It writes `<name>_with_caption.png` and `.pdf` with the caption under a crop line, and a `<name>_CAPTION.md` copy beside them.

Add two to four plain sentences per finding: what was measured, how, the result, and what is unresolved. Keep every count traceable to its source rows. If two evidence channels disagree, say so before explaining it.

For Methods, use the saved commands, versions and settings of this run. If a detail is missing, mark it for recovery. Do not fill it with the current tool version.

## 5. Record the figure

Keep one index with a row for each figure:

| Field | Example |
|---|---|
| Figure | F1 |
| Question | Which regions rank highest? |
| Source table | `EXAMPLE_4_triage_board.csv` (`figure_manifest.csv` lists the figures made, not the plotted data) |
| Plotted rows | the triage-board rows you plotted, copied or filtered into your own file |
| Calculation and rows used | top 10 by score after exclusions; 10 of 31 |
| Script or settings | the `render-figures` command above, with the package checksum |
| Image and formats | `top_antibacterial_leads.png` (omitted: PDF, with reason) |
| Caption file and Methods text | `<image name>_CAPTION.md` |
| Checks passed | `FIGURE_QA.md` clean; `RENDER_QC.md` read; images viewed |
| SHA-256 | `<hash>` for each file |

If a script redraws saved tables, say so. Name any outside analysis and its environment separately.

Hash each file with `shasum -a 256 <file>`. Note which checks passed and what is still missing. List any omitted figure with the reason.

## 6. Hand it over

See the [preflight manual](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md), the [deliverable contract](DELIVERABLE_CONTRACT.md) for the files to include and [portable evidence roots](PORTABLE_EVIDENCE_WORKSPACE.md) for linking a larger project. To keep the package in a checked store, see [Keep results in a Strain Master](DATA_HOME.md).

Before sharing an archive, open it and look for private data, comments and local paths. Check public accessions and any type-material label against their deposited records.

Example request to an assistant: "Use the validated package at runs/EXAMPLE/package. Give me the selected figures with their source tables and checksums, a short finding for each, the commands and versions used, and the open questions."
