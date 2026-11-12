# Extract a marker-co-occurrence candidate region

Finds a candidate gene-cluster region in a raw genome FASTA by looking for matches to your marker proteins on predicted genes that lie close together. Use it for genomes without an antiSMASH run.

    python tools/extract_cluster.py --genome genome.fna --marker markers.faa \
      --label EXAMPLE --min-markers 2 --outdir OUT

| Flag | Meaning | Default |
|---|---|---|
| `--genome` | Genome FASTA (`.fna`) | required |
| `--marker` | Marker protein FASTA with one or more diagnostic genes | required |
| `--label` | Label for the output GBK and locus tags | required |
| `--min-markers` | Markers needed to call the region present, each matched to a different predicted gene | 2 |
| `--min-identity` | Minimum percent identity for a marker match | 40 |
| `--window` | Most genes the marker window may span | 25 |
| `--flank` | Genes of flank kept on each side of the region | 2 |
| `--outdir` | Output folder | `extract_cluster_out` |

This tool predicts genes with Pyrodigal, searches supplied marker proteins with
pyswrd, and admits a region when the declared distinct-marker/window thresholds
are met. It requires the optional gene-call and alignment dependencies. Install them with `bundle_support/install_sapote_addons.sh` (see [prerequisites](PREREQUISITES.md)). No antiSMASH
run occurs. The result is a computational candidate region, not confirmation of
a complete cluster, compound or activity. Insufficient matches mean no region
was admitted by this procedure, not biological absence.

The marker count is the largest number of markers that can each be assigned a
different predicted gene in the window. Two marker names that both match one protein
count once. When a marker window is found, `LABEL_extract.json` reports `n_markers_found` on that basis, together
with `n_marker_names_matched` (distinct marker names with any hit),
`n_distinct_target_genes`, and `shared_target_genes` (each gene hit by more than one
marker, with the marker names). A shared hit is ambiguous evidence; review it before
you describe the window as several co-occurring genes. If no marker window is found,
these count and shared-hit fields are omitted; use `present` and the other fields
to interpret the result rather than assuming the fields contain zero.

Outputs are `LABEL_cluster.gbk` when admitted and `LABEL_extract.json`. Names must
be safe basenames; every output destination must be fresh and contained, including
symlinks. Output aliases of input files are refused before gene calling. Marker
labels in the GBK report the supplied matches; they do not establish function.

Output artifacts are serialized before publication and ordinary write failures roll back owned files. Publication is not crash-atomic; stable inputs and no uncooperating output writer are required. Nonfinite identities or hit indices outside the supplied roster refuse before region admission.

## Coordinates

Pyrodigal's one-based inclusive gene intervals are converted once to zero-based
half-open intervals before any slicing. The GBK CDS intervals use that convention
within the extracted slice, on both strands. The JSON records the source and
output conventions; `region_nt` is a zero-based half-open source-genome interval.
Gene coordinates are bounded by their contig, duplicate FASTA record identities
are refused, and sequence padding is clamped at contig ends.

## Status and evidence binding

`present` in the JSON is marker-window admission under the declared method; the console's `PRESENT` or `absent/insufficient` strings are not biological presence/absence findings. The CLI returns zero after either admitted output or JSON-only non-admission. Require the current JSON and expected GBK roster rather than accepting zero exit or a previously existing GBK as confirmation.

The JSON retains label, called-gene count, marker requirement, marker names and admitted coordinates; it does not record input genome/marker hashes, caller/alignment versions, every window/flank/identity parameter, output hashes or a validated four-part antiSMASH locus identity. Preserve a separate source/parameter receipt, using the source FASTA contig and extracted interval as candidate coordinates; do not invent a region number or BGC alias before a separately reviewed binding exists. Marker labels remain supplied-match labels, not functional annotation proof.

Both possible destination names must be fresh even when only JSON is eventually emitted. Ordinary rollback preserves pre-existing files and removes owned new outputs; interruption or cleanup failure still requires actual-file inspection. Keep the source files in place and record path+SHA-256 rather than copying genomes into the documentation candidate.
