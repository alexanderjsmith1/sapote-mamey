# Shrink a reference tree for drawing

A reference panel often has many near-identical reference sequences that crowd a figure. This page shows how to fold them into one labeled tip for the drawing, and how to prove the drawn tree came from your original tree. Your analysis tree, alignment and metadata are never changed.

The steps: add source labels (optional), collapse, verify, render. A fold is a display choice. It does not assign a species, an ecological group, or scientific acceptance. A receipt in this page is an integrity record, not a signature or approval.

## What you need

- One aligned nucleotide FASTA, one Newick tree, and one metadata TSV. The tip names must match exactly in all three.
- Metadata columns: `tip`, `label`, `role`, `taxon`. `role` is `query`, `reference` or `outgroup` (lowercase). A table with only a `kind` column is refused: add a `role` column.
- Take `taxon` from the source record of each reference you want to be able to fold. A blank taxon is never folded. A name or an accession pattern does not set a taxon.
- Every non-root branch needs a finite, nonnegative length.

These inputs are refused: duplicate tips or headers, malformed rows, unequal or empty sequences, symbols other than nucleotides, and a `role` that conflicts with a query-like key.

## 1. Add deposited source labels (optional)

Do this before collapsing, so the labels are part of the original metadata that the ledger records.

```bash
python tools/add_reference_source_labels.py panel_meta.tsv \
  --db frozen_reference.sqlite --out panel_with_sources.tsv
```

The database is read-only. It must be a frozen SQLite snapshot with a `record.acc_version` column, with no live journal or WAL files. Lookups use the exact versioned accession. A missing or ambiguous accession stays marked as unresolved.

Only reference labels change. The text comes from the deposited `isolation_source`, then `host`, then `geo_loc_name`. A location is prefixed `location:`. A missing field means the evidence is unavailable. It is not a negative result. The run writes a receipt beside the output.

## 2. Collapse

The files below are named `panel.aln.fasta`, `panel.nwk` and `panel_meta.tsv`.

```bash
python tools/collapse_near_identical.py panel.aln.fasta panel.nwk panel_meta.tsv \
  --max-nt 2 --min-cols 500 --out-prefix figures/panel
```

`--max-nt` and `--min-cols` are both required. A fold needs every pair in the group to differ at no more than `--max-nt` positions, counted over at least `--min-cols` columns where both sequences have A, C, G or T. The group must also be one clade of your tree, with one recorded taxon. Queries and outgroups are never folded. `--protect TIP` keeps one more tip, and you can repeat it. A protected tip that is not in the tree is refused.

Success: exit 0. The tool prints the receipt path and its SHA-256, and writes four files that must not already exist:

- `figures/panel_display.nwk`, the drawing tree.
- `figures/panel_display_meta.tsv`, with one folded row per group.
- `figures/panel_collapse_ledger.tsv`, with one row per input tip: its original metadata, representative, outcome, and the mismatch counts.
- `figures/panel_display_receipt.json`.

Copy the printed SHA-256 into your run notes. You need it in step 3.

The representative is the member with the most unambiguous bases. Distances between the tips you keep are preserved. A folded row is labeled with the taxon, member count, mismatch limit and representative. Use `--group-label representative` to keep the representative's own label instead. The ledger keeps every member either way.

`--prune-outgroup` drops the outgroup from the drawing only if the outgroups form one clade that is the sister of the rest. It never reroots. At least two tips must remain.

## 3. Verify

```bash
python tools/gate_stem_aware.py figures/panel_display.nwk \
  --metadata figures/panel_display_meta.tsv \
  --receipt figures/panel_display_receipt.json \
  --receipt-sha256 <SHA-256 printed in step 2> --parent panel.nwk
```

Exit 0 means the gate passed: the printed digest matches the receipt, every recorded hash and size matches, the display can be rebuilt byte for byte from the bound inputs, and the tree has no long or dominating branch. The output ends with a line starting `PASS`. Exit 2 means a binding or the tree check failed, for example `DISPLAY_RECEIPT_HASH_MISMATCH_OR_MISSING`. Exit 3 means a sibling tool is missing. Do not draw after exit 2 or 3.

## 4. Render

```bash
GG_DISPLAY_RECEIPT=figures/panel_display_receipt.json \
GG_DISPLAY_RECEIPT_SHA256=<SHA-256 printed in step 2> \
GG_GATE_TREE=panel.nwk GG_FIGID='Figure reference panel' GG_STRIPS=0 \
GG_METHODS="$(cat figures/reference_panel_caption.txt)" \
Rscript tools/ggtree_rect_heatmap.R figures/panel_display.nwk \
  figures/panel_display_meta.tsv figures/reference_panel QUERY_TIP
```

The three arguments are the display tree, the display metadata and the output prefix. The optional fourth is a comma-separated list of tips to highlight. Here it is `QUERY_TIP`, a query tip name from your own table. `GG_STRIPS` is the number of annotation strips: 0, 1 or 2. `GG_STRIP1_TITLE` and `GG_STRIP2_TITLE` name the columns shown. `GG_GATE_TREE` is optional when the receipt names the parent. If you give it, it must match.

The page heading "Page i of n" is off unless `GG_PAGE_TITLE=1` is set exactly. Other values leave it off.

Success: exit 0, and a line `wrote figures/reference_panel: 1 pages ... minimum 8 pt; N tips`. The folder then holds the PDF and PNG, `reference_panel.render_receipt.json` (which binds the figure to the display receipt), `.methods.txt`, `.pages.json` and `.session.txt`. With a display receipt, the renderer refuses before drawing if any output it can write already exists: the PDF, PNG, SVG, `.session.txt`, `.render_receipt.json`, `.methods.txt`, `.pages.json`, `.activity_audit.tsv`, `.annotation_audit.tsv`, or any `<prefix>_page*` file. Always open the figure.

No caption is generated for you. The renderer draws a caption only from `GG_METHODS`, and writes the same text to `.methods.txt`. Without `GG_METHODS`, no caption is drawn and `.methods.txt` reads `Methods not supplied.` Write `figures/reference_panel_caption.txt` yourself before step 4, from the receipt and ledger of step 2. Give the tip count, the pruned outgroups, the mismatch limit (`--max-nt`, `--min-cols`) and the ledger file name. Then read the drawn caption on the page.

If the final binding fails, treat the graphics as unverified. A diagnostic render keeps `gate_pass=false`. A passing gate is not scientific acceptance.

## Optional: editable copy of a finished figure

`tools/export_tree_figure_source_package.py` copies one finished display folder into a new folder, with the helper scripts, so someone else can edit the figure. It does not draw, check hashes, or interpret anything.

```bash
python tools/export_tree_figure_source_package.py inputs/rendered_panel \
  --out outputs/editable_panel_new
```

- Use a new `--out` folder. If an export fails, delete the partial folder and run it again.
- The source folder must be the output folder of `tools/placement_display.py` (see [the placement metadata figures page](PLACEMENT_METADATA_FIGURES.md) and [the placement workflow](EPA_NG_PLACEMENT_WORKFLOW.md)). Steps 1 to 4 above do not make it: step 4 names its output `figures/reference_panel`, not `*_rect02`. The folder needs one `*_display.nwk`, one matching `*_rect02` PNG and PDF pair, one `*_rect02.methods.txt`, `display_input.tsv`, `display_input.fasta`, `METHODS.md`, and one `*_display_receipt.json`. `--caption FILE` picks another caption file. `--supplement FILE` adds a file, and you can repeat it. Give each supplement a different file name.
- Run the gate on the original first. The export does not check the receipt.
- The rerender script `<stem>_rerender_captioned.sh` uses the original tree and metadata named in the receipt. Editing the `_tree.nwk` or `_metadata.tsv` copies has no effect on it.
- The copy needs R and the Python gate tools on the new machine. A changed tree, alignment or scientific metadata needs a new display and receipt.
- `MANIFEST.json` lists the folder's file hashes and a `source_dir` path from your machine. Check it before you share the copy.
