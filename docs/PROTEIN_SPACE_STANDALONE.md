# Standalone protein space and reference match explorer

`tools/protein_space_standalone.py` packs an existing protein-space viewer and a reference-comparison catalogue into two single-file HTML tools. Each runs offline in a browser. The tool does no sequence analysis, ordination, reference search or figure redraw, and it does not run during a genome-mining job.

This is an advanced tool, and it is not a `mamey_run.py` command. It needs two input files that nothing in this bundle makes. Do not start here unless you already have them. For the bundle's figure tools, see the [figures start page](FIGURES_START_HERE.md) and [locus and PCoA tools](LOCUS_AND_PCOA_TOOLS.md).

## What you need

- An enriched protein-space viewer (an HTML file) and its comparison catalogue (an HTML file), both made outside this bundle. The tool reads the data embedded in them. Linked inputs must still have their per-strain `data/regions` and `data/reference` folders next to them. Inputs that are already single-file can be packed again.
- A current browser that supports `DecompressionStream`, to open the results.
- New file names for the outputs and the receipt.

The page templates, the shared reference reader, Plotly 2.27.0 and the font files ship with the bundle, in `tools/protein_space_viewer_assets` and `assets/protein_space_vendor`. The tool uses only the Python standard library.

## Run it

From the bundle root:

```sh
python3 tools/protein_space_standalone.py \
  --viewer /path/to/enriched/viewer/index.html \
  --catalogue /path/to/catalogue/index.html \
  --viewer-out /path/to/new/Protein_Space.html \
  --catalogue-out /path/to/new/Reference_Matches.html \
  --receipt /path/to/new/STANDALONE_BUILD_RECEIPT.json
```

Before any work, the tool refuses an output that already exists (either HTML file or the receipt), two outputs that name the same file, and an output that is, or resolves to, one of the inputs (viewer, catalogue, templates, reader, vendor files, sibling source exports). `--replace-candidate` replaces existing outputs only when the existing receipt is a standalone receipt whose recorded output hashes match those files now, that is, this tool's own unchanged earlier candidate. Anything else stops with `REPLACE_CANDIDATE_UNIDENTIFIED`.

## Check that it worked

Success: both HTML files and the receipt exist, and the tool prints a JSON summary. Check these keys:

- `point_fingerprint_before` equals `point_fingerprint_after`. The tool stops with an error if they differ, so a printed summary means every plotted point is unchanged;
- `network_dependencies` is `0`;
- `new_analysis` is `false`;
- `layouts`, `point_rows` and `comparison_rows` match the counts in your inputs.

The receipt also records the SHA-256 of the inputs, the vendor files and the outputs. Keep it with the outputs. The point-fingerprint check runs before either HTML file is written. Failure shows as a Python error on stderr. A failure while writing can still leave one new HTML file without a receipt, so compare each output's hash with the receipt before you trust it.

## What the two files contain

The protein viewer holds every saved layout and the source-region gene detail in its input. The reference explorer has cohort summaries, numeric display filters, sorting, comparison, locus and coverage views, bookmarkable filters, and exports of the filtered comparisons and of the full reference-gene rows with their annotations. It keeps every reference row, including genes in the focal region, flanks, other contigs and rows where the saved search found nothing.

Each file can be moved alone. It needs no server, CDN or sibling folder. The original map graphics are not embedded. They are referenced by path and hash, so keep those graphic files at the same paths. The rest of a moved HTML file does not depend on them.

## Reading the results

"Core" means the focal antiSMASH region, not only the core biosynthetic enzymes. Homology outside the core, split candidates and concentrated partners do not show physical linkage. Source labels such as STRONG, assembly holds, repeated protein assignments, and missing or not-queried states stay visible as saved. Matching strain, contig, locus and protein length does not rebind the original alignment sequence. Filters and means are descriptive. The tool adds no acceptance score and no statistical test.

Software and font licenses are kept in the vendor folder and embedded in the HTML. `VENDOR_MANIFEST.tsv` pins the asset bytes.
