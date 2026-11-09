# Figure house rules

Every figure you send for review must meet the rules on this page. To find the renderer and the
command for a figure type, start at [Make and review Mamey figures](FIGURES_START_HERE.md). This
page says what the finished figure must look like and how to check it.

Two tools check a figure folder:
- `python tools/figure_house_rules.py check <figure_folder>` checks the folder layout, the caption
  file and the text in any SVG. Add `--bioassay` for a bioassay figure. It exits 1 on an error, and
  a missing `_plot_only` image is only a warning.
- `python tools/figure_render_qc.py <output_folder> --print-width-in <inches>` checks the drawn
  text for banned wording, the image, and the files each figure needs. With `--print-width-in`, it
  also reports the smallest text size at that print width, read from the figure's PDF or SVG.
  Without it, text size is `NOT_CHECKED`. A raster-only figure, or a companion whose text cannot
  be read, gets the warning "text size not measurable", not a pass. The tool does not judge
  layout: clipping, overlaps and a legend over data need a person.

Rules marked "By hand" have no tool. Check them yourself before you send the figure.

## Rules for every figure

| # | Rule | Why | Checked by |
|---|---|---|---|
| 1 | Save as vector SVG or PDF. If you need a raster, save lossless PNG at 300 DPI or more. Never save JPEG. | JPEG blurs tip labels, support values and thin branches until they cannot be read. | By hand. Open the PNG's properties and check its DPI and pixel size at the print width you intend. |
| 2 | Each figure gets its own folder. It holds the plot image `<name>_plot_only.png`, the captioned copy `<name>_with_caption.png`, and `<name>_CAPTION.md` with the caption and methods. | A figure that leaves its folder must still say what it shows and how it was made. | Save the renderer's own image as `<name>_plot_only.png`. Then run `tools/caption_band.py` on that image and the caption file (`python tools/caption_band.py <name>_plot_only.png <name>_CAPTION.md`). It writes the captioned PNG and PDF beside them. `tools/figure_house_rules.py` warns when a file is missing. |
| 3 | No claim-safety wording on the figure: not in titles, legends, footers or a notes band. Put it in the caption, and keep the claim limit in the render receipt. | The figures go into papers and talks, where that wording reads as noise. | `mamey.figure_policy.FIGURE_BANNED_TEXT`, applied by `mamey/figure_save.py` to figures saved through it, and by `tools/caption_band.py` to the caption band. `tools/figure_house_rules.py` applies it to SVG text. For other figures, `tools/figure_render_qc.py` reads what was drawn. |
| 4 | A bioassay figure names its material: crude extracts, fractions, or both. Put it in the title and in the file name. Never pool crude and fraction results into one value. | A figure that hides its material cannot be compared with another, and pooling mixes two experiments. | `tools/figure_house_rules.py` with `--bioassay` checks the file name. Check the title by hand. |
| 5 | A figure can be traced to its data. The folder holds the data table, the script, the image and the caption. A publication export carries a manifest that gives each figure's source folder and the SHA-256 of the file it was made from. | A figure found months later, or pasted into slides, must lead back to exactly what drew it. | By hand. |
| 6 | Show a reference strain by its deposited name and strain designation, with the accession in brackets after it. Never label it with the accession alone. | The name is what the literature uses. A column of accessions cannot be read. | By hand. |
| 7 | Mark `[Type]` only when NCBI Assembly records the genome as assembly from type material. | A name that looks like a type strain is not evidence that it is one. | By hand. |
| 8 | Do not delete a figure with a known defect. Add `_KNOWN_DEFECTIVE` to its image file names, and write the old name, the new name and the reason in the folder's review notes. If a manifest or receipt names the file, record the rename there too, so the link still resolves. | Numbering and past review comments stay valid, and nobody reuses the file by accident. | By hand. |
| 9 | File each review comment in the folder of the figure it is about, with the words exactly as written. | Comments kept anywhere else get lost. | By hand. |
| 10 | Look at the rendered image before you send it. Check for clipped labels, overlapping text, empty panels and a wrong subset of samples. | A saved file is not a checked figure. | By hand for clipping, overlap, empty panels and the subset. `tools/figure_render_qc.py` with `--print-width-in <inches>` reports small text only when it can read the text from a PDF or SVG; read its `NOT_CHECKED` and "not measurable" lines too. |
| 11 | Label points on an ordination page (PCoA, TriMap) with names, never with numbers. On the plot, use the short italic species name. In the caption key, give the rule-6 form: deposited name, strain designation and the accession in brackets. How many points get a label depends on fit and placement. | A number sends the reader to a key and hides the name the literature uses. | By hand. |
| 12 | Draw a figure only through a sealed bundle route: a renderer shipped in this bundle, or a change the bundle maintainer has signed off. Before drawing, write a short rule check: each row of this page, the gate in [FIGURE_STYLE.md](FIGURE_STYLE.md), the page for that figure type, and the tool you will use. A setting that is not in the bundle docs goes to the maintainer as a proposal, never as a shipped default. | Figures drawn with hand-set labels or private scripts reached review and had to be withdrawn. | By hand. |

R figures: the R save helper `sapote_save_pair()` in `tools/sapote_figure_theme.R` writes SVG and
PNG, but it does not stop you overwriting an older file and writes no receipt. Use a fresh output
folder, and run `tools/figure_render_qc.py` on it. See [R figure workflows](R_FIGURE_WORKFLOWS.md).

## Owner study profile

These settings belong to the bee and wasp isolate study. Apply them to its figures so that a whole
figure set reads the same way. For a different study, replace them and say so in that study's
figure folder. `tools/figure_house_rules.py` holds the pathogen order and the host groups as data;
`python tools/figure_house_rules.py pathogen-order` prints the order.

| Setting | Value |
|---|---|
| Pathogen axis order | Fungi first (*Candida albicans*, *Candida auris*), then the gram-negatives together (*E. coli*, *Acinetobacter*, *Enterobacter*, *Klebsiella oxytoca*, *Pseudomonas aeruginosa*), then MRSA last. |
| Version without *Enterobacter* | Make it only when the study owner asks for it, and keep the full version beside it. Name the omitted target and the new denominator in the caption. `pathogen-order --drop-enterobacter` prints that order. |
| Host groups | Honeybees (*Apis*), Bumblebees (*Bombus*), Other bees, Wasps. Keep "Other bees" as its own group. Label the axis "host group (as deposited)". |
| Isolate scope | Bee and wasp isolates only. |
| Source and geography | Report them as deposited. Do not group, infer or correct them. Leave out isolates with no deposited source or location, and list each one by genus, species and strain in the caption so it can be looked up. |

## When a rule and a figure disagree

Fix the figure. If the rule is wrong, change this page in the same change and say why. A figure
changed to get around a rule, with the rule left as it is, is how the two drift apart.
