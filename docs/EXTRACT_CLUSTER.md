# Extract a marker-co-occurrence candidate region

    python tools/extract_cluster.py --genome fixture.fna --marker markers.faa \
      --label FixtureA --min-markers 2 --outdir OUT

This tool predicts genes with Pyrodigal, searches supplied marker proteins with
pyswrd, and admits a region when the declared distinct-marker/window thresholds
are met. It requires the optional gene-call/alignment dependencies; no antiSMASH
run occurs. The result is a computational candidate region, not confirmation of
a complete cluster, compound or activity. Insufficient matches mean no region
was admitted by this procedure, not biological absence.

Pyrodigal's one-based inclusive gene intervals are converted once to zero-based
half-open intervals before any slicing. The GBK CDS intervals use that convention
within the extracted slice, on both strands. The JSON records the source and
output conventions; `region_nt` is a zero-based half-open source-genome interval.
Gene coordinates are bounded by their contig, duplicate FASTA record identities
are refused, and sequence padding is clamped at contig ends.

Outputs are `LABEL_cluster.gbk` when admitted and `LABEL_extract.json`. Names must
be safe basenames; every output destination must be fresh and contained, including
symlinks. Output aliases of input files are refused before gene calling. Marker
labels in the GBK report the supplied matches; they do not establish function.
Synthetic tests check terminal intervals and both strands. Historical example
runs do not establish current-byte biological validation.

Output artifacts are serialized before publication and ordinary write failures roll back owned files. Publication is not crash-atomic; stable inputs and no uncooperating output writer are required. Nonfinite identities or hit indices outside the supplied roster refuse before region admission.

## Status and evidence binding

`present` in the JSON is marker-window admission under the declared method; the console's `PRESENT` or `absent/insufficient` strings are not biological presence/absence findings. The CLI returns zero after either admitted output or JSON-only non-admission. Require the current JSON and expected GBK roster rather than accepting zero exit or a previously existing GBK as confirmation (`tools/extract_cluster.py:145–171,174–220`).

The JSON retains label, called-gene count, marker requirement, marker names and admitted coordinates; it does not record input genome/marker hashes, caller/alignment versions, every window/flank/identity parameter, output hashes or a validated four-part antiSMASH locus identity. Preserve a separate source/parameter receipt, using the source FASTA contig and extracted interval as candidate coordinates; do not invent a region number or BGC alias before a separately reviewed binding exists. Marker labels remain supplied-match labels, not functional annotation proof.

Both possible destination names must be fresh even when only JSON is eventually emitted. Ordinary rollback preserves pre-existing files and removes owned new outputs; interruption or cleanup failure still requires actual-file inspection. Keep the source files in place and record path+SHA-256 rather than copying genomes into the documentation candidate.
