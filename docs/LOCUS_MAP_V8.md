# Locus map v8

A locus map draws the genes of one BGC region as arrows, pointing the way the source strand
says. A gene with no readable strand is drawn as a plain box. Locus map v8 is the default renderer for
package gene maps. It is built for exact-locus review, not for overview art.

## Draw the maps

You need a package that `run` wrote and `validate` passed ([Your first run](reader/01_FIRST_RUN.md)).
The command refreshes checksums inside the package it is given, so copy the package first and
draw on the copy ([figures start here](FIGURES_START_HERE.md#make-a-working-copy-first)). From the
program folder, replacing `EXAMPLE`:

```bash
test ! -e runs/EXAMPLE/package_work \
  && cp -R runs/EXAMPLE/package runs/EXAMPLE/package_work \
  && diff -rq runs/EXAMPLE/package runs/EXAMPLE/package_work \
  && python mamey_run.py render-figures --package runs/EXAMPLE/package_work --figure-set locus-maps
```

If `package_work` already exists, `cp -R` would put the new copy inside the old folder, and the
render would then run on the old copy. The `test` stops the whole chain instead. Pick a new name;
do not reuse an old working copy. `diff -rq` prints nothing and lets the render start only when the
copy matches the original.

`--top-n` sets how many BGCs to draw. The default is 10. Maps go to `<package>/locus_maps/`. The
`--outdir` option must resolve inside the package; see [figures start here](FIGURES_START_HERE.md#locus-maps).

You should see `locus-maps v8 (post-seal): N maps -> <package>/locus_maps`. ("post-seal" means drawn from a finished, validated package.) If any BGC could not
be drawn, the command also prints `skipped:` or `per-BGC holds:` lines with the reason. Exit 0 does
not mean every BGC was drawn, so read those lines.

The command reads `<strain>_gene_by_gene_all_bgcs.csv`, which `run` writes into the package. If that
file is missing, no maps are drawn and the skip line says why. The ranking takes the first
`--top-n` rows of the triage board in corrected-rank order, then alias. It is not a full-inventory
list.

## What each BGC gets

- `<BGC>_locus_map.png` and `<BGC>_locus_map.svg`
- `<BGC>_locus_map_data.csv`, one row per gene, with the exact locus tag
- `<BGC>_locus_map_v8_receipt.json`, with the identity, sources, output hashes and label counts

From Python, `render_for_compile_report(package_dir, top_n=5)` in `mamey/locus_map.py` does the
same work and returns `rendered`, `skipped` and `skipped_reason`. Use the command above unless you
are scripting.

## How to read a map

- Every gene shows its exact locus tag. Dense loci use a spaced label rail with leader lines
  and do not drop labels.
- The **comparator** is the MIBiG cluster that best matches the region, chosen by rule: most
  query genes with a supported hit, then median identity, then reference rank, then accession.
  MIBiG is the database of characterized clusters. A supported hit is a per-gene row with a query
  gene, a subject gene and a numeric percent identity. Other rows are left out of the choice, and
  the receipt counts them in `comparator_rows_unresolved`.
- Each gene matched to the comparator is highlighted and gets an identity and coverage row.
- Domain, HMM (profile-match), module and motif annotations are summed up in the evidence panel.
  The CSV keeps them in full.
- The renderer does not score a BGC. Similarity is not product identity. The map shows capacity
  only, not expression, production, activity, novelty, a merge or split, or physical linkage.

## Check the result

Each map needs the full identity **strain / full node-or-contig / region / BGC alias**. The receipt
records it.

`READY` in a receipt is a mechanical count check. The receipt reader confirms that the PNG, SVG
and CSV exist and match their recorded bytes and hashes, and that the counts and the chosen
comparator agree. It does not re-check the identity fields or the source-file hashes. Compare
those with the package yourself. Until they match, treat the map as unverified.

Genes with a missing locus tag, start or end, or a non-numeric coordinate are skipped without a
message. A gene whose strand is blank or is not `+`, `1`, `-` or `-1` is kept and drawn as a box
with no arrowhead. The CSV leaves its `strand` blank, and the receipt lists it in
`strand_unknown_loci`. Check those genes against the source before reading direction from the map. The receipt counts only the genes it accepted. Compare the CSV row count with the region's
gene count and note any gap.

Filenames are fixed, so a repeat render into the same folder overwrites. If a receipt check fails,
the artwork and a non-ready receipt can remain. Render into a new output folder and keep the
earlier files. Do not edit a sealed package to repair a map.

`label_displayed=YES` in the CSV means the renderer placed that tag on the label rail. It does not
check that the label is legible or unclipped. Receipt counts do not replace looking at the image at
the size it will be used. The R script
`tools/sapote_locus_map.R` is an alternate arrow view without the comparator panel. See
[R figure workflows](R_FIGURE_WORKFLOWS.md).
