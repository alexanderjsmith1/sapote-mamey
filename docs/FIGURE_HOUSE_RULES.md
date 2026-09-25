# Figure house rules

Every figure made from this bundle meets the rules on this page. Each rule says why it exists and
what checks it. Where nothing checks it yet, check it by hand before a figure leaves your folder.

Figure routes, renderers and recipes are in [FIGURES_START_HERE.md](FIGURES_START_HERE.md). This
page is the short list of what every one of them must produce.

## Rules for every figure

| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | Save as vector SVG or PDF. If you need a raster, save lossless PNG at 300 DPI or more. Never save JPEG. | JPEG blurs tip labels, support values and thin branches until they cannot be read. | By hand. |
| 2 | The caption and methods travel with the figure. Each figure gets its own folder holding the image with a caption band under a crop line, a `_plot_only` image without the band, and a `_CAPTION.md` with the same text. | A figure that leaves its folder must still say what it shows and how it was made. | `tools/caption_band.py` writes the band and the sidecar. |
| 3 | No claim-safety wording on the page. That covers titles, legends, footers and any notes band. The claim ceiling is recorded in the render receipt instead. | The figures go into papers and talks, where that wording reads as noise. The receipt keeps the ceiling on record. | `mamey.figure_policy.FIGURE_BANNED_TEXT`, applied by `mamey/figure_save.py`, but only to figures saved through it. Most renderers call `savefig` directly and are not checked there. `tests/test_figure_draw_text_sites_v97442.py` lists the draw calls that still put this wording on a figure; the list may only shrink. Run `tools/figure_render_qc.py` on an output folder to check what was drawn. |
| 4 | A bioassay figure names its material: crude extracts, fractions, or both. Put it in the title and in the file name. Never pool crude and fraction results into one value. | A figure that hides its material cannot be compared with another, and pooling mixes two different experiments. | By hand. |
| 5 | A figure can be traced to its data. The folder holds the data table, the script, the image and the caption. A publication export carries a manifest giving each figure's source folder and the SHA-256 of the file it was made from. | A figure found months later, or pasted into slides, must lead back to exactly what drew it. | By hand. |
| 6 | Show a reference strain by its deposited name and strain designation, with the accession in brackets after it. Never label it with the accession alone. | The name is what the literature and the type-strain question use. A column of accessions cannot be read. | By hand. |
| 7 | Mark `[Type]` only when NCBI Assembly records the genome as assembly from type material. | A name that looks like a type strain is not evidence that it is one. | By hand. |
| 8 | Do not delete a figure with a known defect. Rename its image files with `_KNOWN_DEFECTIVE`, and log the rename and the reason. | Numbering and past review comments stay valid, and nobody reuses the file by accident. | By hand. |
| 9 | File each review comment in the folder of the figure it is about, with the words exactly as written. | Comments kept only in a chat are lost when that chat is compacted. | By hand. |
| 10 | Look at the rendered image before sending it. Check for clipped labels, overlapping text, empty panels and a wrong subset. | A saved file is not a checked figure. | By hand. |

### A note on rule 5

An older convention put all provenance into one file name,
`<DATA_FOLDER>__FIG_<NAME>_v<N>_<DATE>`. Current figure sets use one folder per figure, plus a
hashed manifest for any export, and none of them use the single-name form. Follow the folder
convention. A file name alone is not enough provenance, and a folder is.

## Owner study profile

These conventions belong to the bee and wasp isolate study. Apply them to its figures so a whole
figure set reads the same way. For a different study, replace them and say so in that study's
figure folder.

| Setting | Value |
|---|---|
| Pathogen axis order | Fungi first (*Candida albicans*, *Candida auris*), then the gram-negatives kept together (*E. coli*, *Acinetobacter*, *Enterobacter*, *Klebsiella oxytoca*, *Pseudomonas aeruginosa*), then MRSA last. |
| Enterobacter variant | Also make a version without *Enterobacter*, which is easy to inhibit and makes activity look higher. |
| Host groups | Honeybees (*Apis*), Bumblebees (*Bombus*), Other bees, Wasps. Keep "Other bees" as its own group. Label the axis "host group (as deposited)". |
| Isolate scope | Bee and wasp isolates only. Moss and attine isolates belong to separate studies. |
| Source and geography | Report them as deposited. Do not bin, infer or correct them. Leave out isolates with no deposited source or location, and list each one by genus, species and strain so it can be looked up. |

## When a rule and a figure disagree

Fix the figure. If the rule is wrong, change this page in the same patch and say why. Changing a
figure to get around a rule, without changing the rule, is how the two drift apart.
