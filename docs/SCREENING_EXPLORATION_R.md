# Screening exploration figures (R)

This optional R tool draws exploratory figures from screening results and biosynthetic-annotation
summaries. You prepare the input CSV files. The tool draws one view for each file it finds. It does
not choose strains, admit evidence or interpret results. Those steps happen before you run it.

It is not a `mamey_run.py` command and does not run after a package is sealed.

## Before you start
- R with the packages `ggplot2` and `patchwork`. To install the figure packages, run
  `Rscript bundle_support/install_r_figure_packages.R`. The tool itself installs nothing and makes
  no network calls.
- A folder with one or more of the CSV files listed under **Input tables**.
- A new, empty output folder.

## Try it with a small example
Make a folder `overlap_inputs` that holds one file, `overlap.csv`:

```csv
category,count,total
Both targets,3,10
Candida only,4,10
Neither,3,10
```

These numbers are invented. Run:

```sh
Rscript tools/render_screening_exploration.R overlap_inputs new_figures
```

You should see `1 figures created, each as PNG, PDF and caption text`. `new_figures` should
hold `01_screening_overlap.png`, `01_screening_overlap.pdf`, `01_screening_overlap_caption.txt`
and `R_SESSION.txt`. A missing file, or an R error message, means the run failed. With no
supported input file, the tool stops with an error.

## What the tool writes
- Each supported input file produces one view as a PNG and a PDF, plus a separate caption
  `_caption.txt`. The PNG has no caption text on it.
- Concentration data produces two views per dataset: the full range, and a `_zoom` view that only
  crops the display. Organisms appear as facets. With `--score-0-100`, each dataset produces one
  `_scored` view instead, and `concentration_scored_data.csv` holds the raw and scored values.
- `R_SESSION.txt` records the R and package versions. It is written last, so it can be missing
  after a failure.
- An existing figure name stops the run unless you add `--overwrite`.

The tool writes files one after another. A failure can leave earlier files behind. Use a fresh
output folder, and treat a folder from a failed run as incomplete.

## Input tables
Every input is a UTF-8 CSV file with a header row. Count fields are not negative; inhibition values can be. Resolve missing values
before you render. A file you leave out means that view is not requested. It does not mean the
biology is absent.

| File | Columns | Rules |
|---|---|---|
| `overlap.csv` | `category,count,total` | Mutually exclusive categories sum to one shared total. Make sure the total is above zero. |
| `host_calls.csv` | `host,organism,positive,tested,not_tested,percent` | `percent` is positive divided by tested, times 100. Tested must be above zero. |
| `concentration_observations.csv` | `dataset,organism,concentration_ug_ml,inhibition_pct,assay_plate,fraction_plate,source_well` | One row per record at each of 15, 30, 60 and 120 µg/mL. Do not treat separate records as biological replicates. This table is for fractions. Do not put crude extracts in it. |
| `wider_inventory.csv` | `organism,format_label,records` | Labels are `384 well tagged`, `96 well tagged` or `Format untagged`. Counts can include controls. The figure labels them as source records, not strain counts. |
| `modeb_machinery.csv` | `strain,family,loci_with_annotation,loci_in_snapshot,percent_loci` | One row per strain and family. Count each region once per family. |
| `selected_class_profiles.csv` | `strain,class,regions,total_regions,Candida,MRSA` | Calls are `positive` or `negative`. Class labels can overlap. The targets are fixed as Candida and MRSA. |
| `render_context.csv` (optional) | `key,value` | Keys `collection_label`, `architecture_label` and `package_label` set the subtitles. `assay_format` (for example `384-well`) adds the format to the concentration subtitle. `admission_statement` is your own statement of the source admission (for example, which crude extracts and identity conflicts were removed); the concentration captions quote it as stated. Without it, the captions say the renderer did not check the admission. |

Terms: a *dataset* is one set of concentration records. A *fraction plate* is the plate that holds
the fractions tested. The *assay plate* is the plate the assay ran on.

## Checks the tool does and does not do
The tool checks that numbers are finite, that count fields (counts, totals, positives, tested,
records) are not negative, that shapes match, and that a strain/family or strain/class cell is not
repeated. Inhibition values only have to be finite; negative values stay in the full-range view.
For concentration data it refuses a record that lacks any of the four concentrations. It does not
check:
- whether the source rows were properly admitted, for example that crude extracts and identity
  conflicts were removed, or the assay format. The figure states these only when you put them in
  `render_context.csv`, and then only as your statement;
- that counts are whole numbers;
- that one strain has the same denominator or the same Candida and MRSA calls in every class row;
- that the fixed words in a title (for example "more than two targets") match your data.

Check those yourself before you send a figure. Keep a source receipt with the source paths, input
hashes, row identities, exclusions and assay conditions. A successful render is not scientific
acceptance. The tool produces no potency estimate, replicate count, significance test or
gene-to-activity claim.

## Concentration views and scoring
The full-range view keeps negative values and values above 100 percent. The `_zoom` view only
changes the window. Every record still counts in the boxplots.

Add `--score-0-100` only if your assay convention calls for it. Values below 0 become 0 and values
above 100 become 100, and the boxplots are recalculated from the scores. This changes the data, so
say so in the caption and the receipt. The raw values stay in the input file.

## Package a final figure
A preview is not a finished figure. A finished figure needs its caption, plotted data, source
receipt, R code, package versions and instructions to reproduce it. `tools/package_screening_figure.py`
bundles these and refuses a missing or empty part. For the overlap view:

```sh
python tools/package_screening_figure.py --figure-dir new_figures --figure-stem 01_screening_overlap --data-dir overlap_inputs --caption new_figures/01_screening_overlap_caption.txt --receipt receipt.json --renderer tools/render_screening_exploration.R --session-info new_figures/R_SESSION.txt --out standalone/overlap
```

- `--data-dir` must hold only the tables for this figure. The packager copies every top-level CSV.
- `receipt.json` is your own source receipt (see above). The packager only checks that it is valid
  JSON. It does not check what it says. An empty `{}` is not a source record.
- For a scored figure, add `--score-0-100`.
- Success writes the packet folder and a ZIP. They hold the figure, data, caption, receipt,
  `render.R`, `reproduce.R`, the shared theme, instructions, the session record and checksums.
  An existing destination is refused.

To check the packet, extract the ZIP and run `Rscript <extracted packet>/reproduce.R`. It writes
`reproduced/` beside the packet and does not read your original paths. Packaging does not run the
reproduction. A packet that has not been reproduced is not yet shown to be portable.

## Where this fits
Use the bioassay figure factory for governed material, target, time point and dose summaries. Use
the registered R renderers for tidy, matrix and strain inputs. The input files here are not the
figure-ready tables from those routes. Do not pass those tables in without mapping the columns.
See [R figure workflows](R_FIGURE_WORKFLOWS.md) and [Figures start here](FIGURES_START_HERE.md).

The tool reuses `tools/sapote_figure_theme.R`. PNGs are 300 dpi at the saved size. That does not
show the text is 8 pt or larger at a journal column width. Check that against the
[figure style rule](FIGURE_STYLE.md).

Method background: [Assay Guidance Manual](https://www.ncbi.nlm.nih.gov/books/NBK83783/) and
[antiSMASH ClusterBlast documentation](https://docs.antismash.secondarymetabolites.org/modules/clusterblast/).
