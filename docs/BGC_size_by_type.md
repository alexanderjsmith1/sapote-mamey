# BGC size-by-type: annotated region content and scope

`tools/build_size_profile.py` summarizes saved banked BGC `length_kb` by one primary class per region. This is a companion view to counts, not an estimate of an unknown true number of clusters or independent proof that fragmentation has been removed. Region length and cluster count have different units; opposite correlations cannot mathematically bracket one biological quantity.

## Current computation

Input is `bgc_data.json` under `--banked-dir` (default `cohort`). Pure-saccharide omission policy applies before local classification, so `--include-saccharide` cannot necessarily restore rows already omitted. Family labels are derived for grouping; one primary class follows a preference list, with a fallback to the first available class. Hybrids do not contribute their full length to every component class. Each retained row's saved `length_kb` is summed; missing/falsey length contributes zero, not a verified zero-length BGC. Rows/overlaps/duplicates are not merged or deduplicated as genomic interval unions. No calculation establishes the “true length” of a split pathway.

Columns are the **top eight** classes by summed retained content. Strains are ordered by saved contig count; missing/falsey contig count sorts as zero, while plotted fragmentation uses `log10(max(contigs,1))`. The stacked figure/CSV show selected classes, while whole-cohort total correlations and workbook `total_kb` use all retained classes. Those different denominators must be named (`tools/build_size_profile.py`). Fewer than three observations or a zero-variance series returns correlation zero, not a measured null association. The separate plotted trend line still calls `numpy.polyfit` without a matching small/constant-cohort refusal, so that correlation fallback does not guarantee a successful figure for degenerate cohorts.

## Outputs and recovery

Outputs go to `--out-dir` (default `figures`): three 160-dpi PNGs (`fig_bgc_size_by_type.png`, `fig_count_vs_size_fragmentation.png`, `fig_strain_class_size_heatmap.png`) and `fig_bgc_size_by_type_data.csv`. When a supplied workbook exists, `Size_By_Type` is replaced and that workbook is saved; a missing supplied workbook is silently not updated. Input reading uses the bank reader guard, but no source/code/config/output hash receipt is emitted. PNGs are direct writes; CSV and workbook use their respective atomic helpers, not an all-output transaction. Use a new external output and a separately authorized candidate workbook; inventory and hash actual inputs/outputs.

`--replot` restores rounded size columns from the CSV but initializes an **empty count table**. Its count panels are not reproduced from the original run. The source itself prints “count panels need full data.” Preserve the original full-data outputs and hashes; do not replace them with a replot and call the count/size comparison reproduced. Bank guard still applies even for replot.

The count-versus-size panel is titled “BGC count and BGC size (kb) by class: correlation with assembly fragmentation”. It describes what is plotted; the earlier title, “opposite biases bracket the truth”, was withdrawn because counts and kb cannot bound one quantity. Full individual-locus discussion requires strain / full node-or-contig / region / BGC alias; this summary does not supply that mapping.

## Unit label and supplied tables

`--unit` changes the relevant size-axis labels and unit-bearing panel text; it does not convert numbers or rewrite every title. In bank/replot mode the values remain saved nucleotide kb, and CSV/workbook columns retain their kb convention. Keep `kb` for those values. In supplied-table mode, choose both a label matching the measured quantity and the intended scale: the defaults combine `core_aa_total` with a `kb` label, which would mislabel amino-acid totals unless explicitly corrected (`tools/build_size_profile.py`).

`--table PATH` draws a supplied long TSV instead of reading a banked cohort. It needs the columns `strain`, `bgc_class` and a numeric value column (`--value-column`, default `core_aa_total`), and optionally `genus`. It draws one stacked bar per strain by class, in the order the strains first appear, with classes ordered PKS, NRPS, RiPP, Terpene, Other and then any others. The figure is `--print-width` inches wide (default 6.5), has 8 pt text and no title, and writes `fig_size_by_class_table.png`, `.svg` and `_data.tsv`. `--value-scale` multiplies the values (for example 0.001 to plot thousands). A missing required value column, a non-numeric raw value, or a negative or non-finite raw value is refused. The scale factor and scaled totals are not checked by that predicate: a negative/non-finite scale or floating-point overflow can produce invalid plotted values. Verify a finite, appropriate scale and inspect scaled totals before invoking the renderer. Repeated strain/class rows are summed; this is not row deduplication or an interval union. Blank or inconsistent identity/class fields are not independently bound, and the first genus value wins for a strain. The values and their meaning come from the table; the figure does not compute or validate the underlying measurement.

## Historical cohort note

The original cohort note, whose bracketing claim was withdrawn, is in [history](history/BGC_size_by_type_original_note.md).
