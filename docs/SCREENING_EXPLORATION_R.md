# Screening exploration with ggplot2

This optional renderer turns admitted CSV tables into exploratory screening and biosynthetic-annotation figures. It does not select source databases, resolve cohort identities, assign activities to genes, or modify a sealed analysis package. Use a separate output directory.

Requirements: R with ggplot2 and patchwork. The standard R PDF device creates vector PDFs without Cairo or X11. PNGs use the installed R bitmap device. No network calls or package installation occur.

```sh
Rscript tools/render_screening_exploration.R path/to/admitted_tables path/to/new_figures
```

Existing figure names are refused unless `--overwrite` is supplied explicitly. Each available supported table triggers its figure. A concentration table can contain multiple source-labelled populations; each receives separate full-range and zoomed PNG/PDF pairs. No supported tables is an error.

## Output and validation limits

The renderer writes each caption, PNG and PDF sequentially. A later table validation, device error or existing-file refusal can leave earlier outputs behind; the directory is not an atomic figure set. `R_SESSION.txt` is written at the end and may be absent after failure. Use a fresh output directory, retain the error and mark partial outputs incomplete. Review the actual companion files rather than using the printed “figure pairs” count, which currently includes caption paths in its calculation. `--overwrite` permits replacement and is not a recovery verifier.

Its arithmetic checks do not validate upstream source admission. Counts are checked as finite/nonnegative numbers rather than necessarily integer counts. Overlap checks do not reject a shared total of zero; ensure a positive denominator yourself. The code checks unique strain/family or strain/class cells but does not enforce one shared per-strain denominator or consistent Candida/MRSA calls across that strain's class rows. Retain exact-row provenance and resolve conflicting denominators/calls before rendering. No printed title is evidence of a biological conclusion: some titles/captions contain fixed source-context claims, such as more than two targets or combined host sublabels, that must match the actual supplied data before delivery.

## Input tables

All inputs are ordinary UTF-8 CSV files with headers. Counts must be nonnegative. Denominators must match the displayed fractions. Missing values must be resolved or excluded with a separate admission receipt before rendering. An omitted input table means that figure is not requested, not that its biology is absent.

- `overlap.csv`: `category,count,total`. Mutually exclusive categories must sum to the one shared total.
- `host_calls.csv`: `host,organism,positive,tested,not_tested,percent`. Percent is positive divided by tested, multiplied by 100. Tested denominators must be positive.
- `concentration_observations.csv`: `dataset,organism,concentration_ug_ml,inhibition_pct,assay_plate,fraction_plate,source_well`. Every distinct dataset/organism/assay-plate/fraction-plate/well record must have exactly one observation at each of 15, 30, 60 and 120 micrograms per millilitre. Extra source-provenance columns are retained by the input files. Do not silently treat distinct assay records as biological replicates. This schema describes fraction records; do not mix crudes into it.
- `wider_inventory.csv`: `organism,format_label,records`. Recognized format labels are `384 well tagged`, `96 well tagged`, `Format untagged`. Counts can include controls; the output labels them as source records, not strain counts.
- `modeb_machinery.csv`: `strain,family,loci_with_annotation,loci_in_snapshot,percent_loci`. Each strain/family cell is unique. Count each exact region at most once per family, and retain the underlying four-part locus identities in an accompanying source table.
- `selected_class_profiles.csv`: `strain,class,regions,total_regions,Candida,MRSA`. Class labels may overlap. Qualitative calls are `positive` or `negative`; a separate missingness view is required for other states. These example panels do not test a genomic association.
- Optional `render_context.csv`: `key,value`. Keys `collection_label`, `architecture_label` and `package_label` supply source-specific subtitles. No default source date, workspace location, version, strain or host identity is inferred.

## Evidence and interpretation

Retain a source receipt with absolute or portable source locators, input hashes, original row or query identities, transformation rules, exclusions, cohort definition and assay conditions. The renderer validates selected arithmetic and shape constraints; this is not an evidence-admission gate. Do not label its success as scientific acceptance.

Full-range concentration figures retain negative and above-100% values. Zoom figures use only a viewing window; all records remain in boxplot calculations and the companion full-range plot. No fitted potency estimate, biological replicate count, significance test, biological absence, or causal gene-to-activity claim is generated.

The renderer is an optional companion tool, not a CLI registration or automatic post-seal hook. It accepts explicit input/output roots and generic tabular contracts. Existing figure-ready exporters and source-admission workflows remain the route for producing scientifically governed inputs. The input schema is deliberately separate from existing figure-ready tables; do not pass them directly without an explicit column and meaning mapping.

Method background: [Assay Guidance Manual](https://www.ncbi.nlm.nih.gov/books/NBK83783/) and [antiSMASH ClusterBlast documentation](https://docs.antismash.secondarymetabolites.org/modules/clusterblast/).

## Bounded inhibition scoring

Use `--score-0-100` only when the assay scoring convention calls for it. Values below zero are scored as zero and values above 100 as 100; boxplots are recomputed from scores. Raw values remain in the input table and `concentration_scored_data.csv` contains both raw and scored columns. This is a scoring transformation, not a viewport crop. The option must be documented in the caption and source receipt.

## Mandatory standalone delivery

A preview is not a complete figure delivery. Every delivered figure must have its caption, plotted data, source receipt, editable R code, dependency versions and reproduction instructions. Run the companion packager for each final figure; it fails when a required companion is absent or empty. Put only that figure's source tables in the input data directory.

```sh
python tools/package_screening_figure.py --figure-dir figures --figure-stem 01_screening_overlap --data-dir overlap_inputs --caption caption.txt --receipt receipt.json --renderer tools/render_screening_exploration.R --session-info figures/R_SESSION.txt --out standalone/overlap
```

The packager requires nonempty named files, at least one top-level CSV and a receipt that parses as JSON. It does not validate receipt schema, source identities/hashes, caption methods, PNG/PDF validity or a successful reproduction. A syntactically valid empty receipt object is not source admission. It copies every top-level CSV from `--data-dir`; use a minimal, dedicated directory with only this figure's required tables, including context when used. It also copies the renderer's adjacent `sapote_figure_theme.R`. Existing packet/ZIP destinations are refused, but writes after directory creation are sequential and can leave a partial packet.

The manifest hashes copied packet files; it does not automatically reopen their source locators or verify the manifest itself against a trusted external pin. Preserve upstream admission evidence in place, inspect the generated packet/manifest and run an authorized reproduction in a fresh destination before calling it portable in the selected environment. Reproduction creates its own outputs; it is not performed by packaging. Extra input tables can regenerate additional figures, so supplying only the intended input set matters.

For scored concentration figures, also supply `--score-0-100` to the packager. The output folder and ZIP contain the figure, data, caption, receipt, `render.R`, `reproduce.R`, instructions, session record and checksums. Extract the ZIP and run `Rscript reproduce.R` from any working directory. No original source path is required at runtime.

## Bundle integration boundaries

Read AGENTS.md, CURRENT_DOCS_INDEX.md, FIGURES_START_HERE.md and R_FIGURE_WORKFLOWS.md first. This candidate adds optional exploratory display contracts; it does not replace bioassay_observation_summary_v1 or claim its admission gates. Use the existing bioassay factory for governed material/target/time-point/dose summaries and explicit tree selection. Existing matrix/tidy/strain R renderers remain preferred for their registered inputs.

This renderer sources the existing tools/sapote_figure_theme.R. The standalone packager includes an unchanged copy of that dependency. Generic categories use the documented blue/green series palette; they do not borrow cohort-role labels. Captions are separate editable files; PNGs contain no caption prose. PNGs are 300 dpi at the saved size. This alone does not establish artwork acceptance at a manuscript column width.

Remaining integration work: shared Python quantitative preflight, figure registration, versioned caption/methods-v2 validation, and physical-size/label-collision artwork checks. Until those are wired and tested, these outputs are exploratory candidates. A portable ZIP or successful reproduction does not establish full Figure Factory compliance.

Scoring is a user-selected derived view. Preserve canonical unbounded measurements and their provenance; apply bounds only to a separately named score. The original bioassay observation contract remains unchanged.
