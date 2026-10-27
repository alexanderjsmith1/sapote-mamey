# Lean BiG-SCAPE and selected R locus maps

BiG-SCAPE 2.0.3 can retain its scientific results in one SQLite database without
building the native viewer, network exports or family trees. Keep the DB dump;
`--no-db-dump` would remove the durable scientific result and is not the storage
profile used here. A DB-only run still writes its ordinary small log/config files.

```sh
PYTHONHASHSEED=0 /path/to/bigscape-env/bin/python tools/bigscape_seeded.py \
  --hash-seed 0 --numpy-seed 0 --random-seed 0 --receipt /new/run/seed.json -- \
  cluster -i /existing/staged/regions -p /existing/Pfam-A.hmm \
  -o /new/run/out --db-path /new/run/bigscape.db --cores 2 \
  --mix --classify none --alignment-mode glocal --extend-strategy simple_match \
  --include-singletons --gcf-cutoffs 0.3,0.5,0.7 --no-trees --db-only-output
```

Create the output folders first.
The example uses existing local inputs; it does not provision Pfam or references.
Record source hashes, settings and software versions. Use ordinary repeated hash
seeds only when testing reproducibility; routine biological exploration does not
need eight independently rescanned databases. These settings reproduced the earlier run exactly (below);
they are not tuned for biology.

## Render an explicitly selected pair

`tools/bigscape_locus_r.py` consumes:

- a completed BiG-SCAPE 2.0.3 single-run DB and its explicit run ID;
- one existing `locus-comparison-v1` JSON manifest with exactly two complete
  tracks, rigid orientations/anchors, source GBK hashes, per-gene AA hashes and
  optional supplied protein correspondences;
- the selected bundle root and an existing Rscript executable.

The comparison format is the existing `mamey.figures.locus_comparison` contract;
it is not a new molecule or protein search format. Protein links are supplied
evidence. BiG-SCAPE does not supply gene-level orthology. No search is launched.

```sh
/path/to/sapote-python tools/bigscape_locus_r.py \
  --db /existing/run/bigscape.db --run-id 1 \
  --comparison /existing/selected_pair.json \
  --bundle-root /selected/sapote-mamey-bundle \
  --rscript /path/to/Rscript --out /existing/parent/new_pair \
  --preview-png
```

The adapter validates every supplied source hash; matches each complete track to
one DB region; checks all source/DB CDS coordinates, strands and translated
protein hashes; and filters the pair by the selected run's exact distance
parameters. Shared multi-run DBs currently refuse rather than infer historical
input membership. A new output folder is required; existing results are preserved.
No GBKs or whole alignments are copied into the result.

For an intentional redraw in that same folder, add `--refresh`. The adapter
requires a prior COMPLETE prototype receipt, unchanged selected DB/comparison,
and matching hashes for every prior declared output before replacing those
prototype files. Sources remain read-only. Prior output/code hashes remain in
the same receipt's history, without copying images or making a new directory.
Unreceipted, modified or incomplete prior outputs refuse. This explicit option
is intended for development figure edits; it does not rewrite a released packet.

The R renderer reuses `sapote_figure_theme.R` and the six role colors from
`sapote_locus_map.R`. It adds paired tracks, supplied protein ribbons, and the
stored LCS/final comparable CDS spans. Reversed record-B indices are mapped back
through the reversed source CDS list before projection into the fixed display
orientation. Source order and inter-gene spacing never change. Label visibility
and shown/total counts are explicit; source tags remain in `genes.tsv`.

Default images are **one clean vector SVG and one captioned vector PDF**.
`--preview-png` adds a single directly rendered 300-DPI PNG. Compact selected
gene/link/span tables, configuration, caption, R runtime and source/output receipt
travel with them. There is no all-pairs JSON, viewer asset copy, contact-sheet
batch, automatic family atlas or duplicate PNG size. Editing a map reruns the
small source-bound renderer, not BiG-SCAPE clustering.

The R path needs ggplot2, svglite, jsonlite, scales and grid; preview PNG additionally
uses ragg. The prototype uses R grid text-width measurements and three fixed
external label lanes. ggrepel is available in the tested environment but is not
used for these fixed gene-arrow tracks.
All raw annotation roles remain predictions. Raw-GBK BGC aliases are
explicitly unassigned where absent; no alias, compound or production is inferred.

## Validation on a selected Nocardia set

A full fresh 337-region DB-only Simple Match run was compared with the earlier
full-output run using the same inputs/settings/RNG seeds. All 56,616 distance
records (components, orientation and stored boundaries), all 16,471 normalized
domain/alignment records and all canonical family memberships at cutoffs
0.3/0.5/0.7 matched exactly. Compact checksums replaced another all-pairs export.

| Retained output | Files | Bytes |
|---|---:|---:|
| Prior upstream DB plus native outputs | 38 | 49,878,963 |
| DB-only upstream DB plus log/config | 3 | 31,128,127 |
| Prior case including added all-pairs JSON/receipts | 41 | 72,470,361 |
| Lean case including receipts/console log | 6 | 31,268,681 |

That is a 37.6% reduction in upstream output and a 56.9% reduction in the full
previous workflow. The larger 589.8 MB experiment repeated eight configurations;
it is not the size of one ordinary analysis. Maps were only about 6.7 MB of that
experiment. Existing scientific evidence has not been deleted or repacked.

The two real R examples retain all 139 and 68 source CDSs and all 60 and 19
supplied protein correspondences. Their actual label visibility, source bindings,
R/package versions, fonts/devices, command and file hashes are in their receipts.
Visual inspection and PDF/SVG/raster checks remain required after every redraw.

The DB still grows with the number of comparisons; DB-only mode does not change
quadratic all-vs-all computation or biological results. Render selected loci from
an existing DB before considering a larger cohort or a new parameter sweep.
