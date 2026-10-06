# Source-bound locus comparison maps

This presentation module draws two to twelve declared loci on one common scale. It reads a small JSON manifest of coordinates and already selected correspondences. It performs no search, scoring, gap rescue, assembly or biological annotation. Use the existing `tools/rggmci_pair_locus_map.py` for package-native RGGMCI pair selection. The strain-slide adapter is `tools/rescue_locus_comparison.py`; it selects and prepares source-bound inputs for this renderer.

From the extracted bundle root:

```sh
python tools/render_locus_comparison.py --input examples/locus_comparison_synthetic.json --outdir comparison_demo
```

Matplotlib is required for rendering. SVG text remains editable. Outputs are `comparison.svg`, `.png`, `.pdf`, `display_coordinates.json` and `receipt.json`. Existing outputs are refused. Give every research comparison its own descriptive directory; retain its input JSON beside the indexed output. Sources are read in place and streamed through SHA-256 verification. No packages or databases are copied.

## Input contract

Use the shipped synthetic example as the executable schema example. The root fields are `schema: locus-comparison-v1`, `title`, explicit `synthetic` boolean, `sources`, `tracks` and `links`.

Each source is a path and SHA-256; paths may be relative to the input JSON. A research manifest (`synthetic: false`) requires source records. Hash verification establishes file identity, not whether the supplied rows were correctly derived; the producer remains responsible for the gene-to-source join.

Every track has an ID, label, kind, identity, orientation, anchor gene and gene list. For `kind: bgc`, identity contains `strain`, full `contig`, `region` and `bgc`. References contain accession and description. Keep one contig per track. A comparison with rescue contigs must not concatenate them into an apparent assembled chromosome.

Every gene supplies ID, short label (32 characters maximum), start, end, strand, normalized protein `aa_sha256`, and optional correspondence `group`. Coordinates are integer, zero-based, half-open: subtract one from a one-based inclusive start; retain its inclusive end as the half-open end. Strand is +1 or -1. Normalize AA sequences consistently upstream (remove whitespace, uppercase, remove terminal stop) before hashing. A source-bound producer, rather than this graphics module, verifies the sequence against its CDS.

Every link has endpoints `a: [track_id, gene_id]`, `b: [track_id, gene_id]` and a nonempty `evidence` description. Endpoints must share the same explicitly supplied group. Optional identity, query coverage and reference coverage percentages are retained separately in the data sidecar. A gene with one correspondence on the selected identity_side (a by default, or b) displays its identity percentage beneath the arrow in report view, or appended to its outer BGC label in slide view; coverage stays in the sidecar. They are not conflated into one score. Best-hit correspondence is not automatically reciprocal orthology. Unmatched genes are grey.

## Orientation and layout

Orientation is an explicit +1 or -1 for the entire track. The anchor gene midpoint maps to the supplied `offset_bp` (zero by default). Reversing a track changes every coordinate and strand together; it never changes gene length or manually reorders genes. The original coordinates, displayed coordinates, strands, anchors and orientation are exported. Strand disagreements are reported rather than corrected automatically. The module does not claim that majority agreement proves the chosen biological orientation.

In report view, labels are centered over their arrows on one baseline per track. A detected gene-label overlap refuses the render before files are created; shorten labels or select a narrower locus view. Track labels and titles still require visual inspection. Reference origin or direction need not clutter the track heading; the exact transform remains in the receipt. Ribbons show the full-gene correspondence, not local alignment blocks. The common scale is fixed across tracks.

Colors are assigned deterministically within a manifest. Maps with more than twelve groups use a larger generated palette; similar hues may still be difficult to distinguish, so endpoints and ribbons remain authoritative. Stable cohort-wide group palettes are a follow-on. No individual gene is moved to improve the drawing.

## Integration and limits

Use `mamey.figures.locus_comparison` from Python or `tools/render_locus_comparison.py` from the extracted bundle root. The strain-slide workflow calls the same renderer through `tools/rescue_locus_comparison.py`. The renderer consumes declared coordinates and correspondences; the adapter owns input selection and source binding. See the slide-view and adapter responsibilities below.

Review the supplied-coordinate sidecar and the actual SVG/PNG before using a result. A completed render or passing test does not establish product identity, production, function, physical linkage or scientific acceptance. The companion suite diagrams describe the local documented workflows and optional tools; they do not install them.

## Assembly markers and orientation audit

Optional track `sequence_length` marks both native contig ends after applying the same orientation transform; genes outside that length are refused. Optional gene `missing_stop_codon: true` adds an asterisk and an explanatory report caption or slide heading annotation. These are supplied observations, not inferred completeness or pathway-boundary judgments. `label_caption` can map numeric arrow labels to complete locus tags. `identity_caption` names the protein comparison source; research producers should distinguish BLASTp and tblastn.

The `identity_side` field chooses a or b endpoints for percentages. Multiple correspondences at one endpoint are left in the sidecar rather than collapsed to a misleading number. The renderer exports actual arrow start/end/strand, verifies these against source transformations before writing, and records `drawn_orientation_check`. `verify_drawn_orientation(spec, drawn, receipt)` also rejects an external receipt whose orientation disagrees with the source. Tests deliberately reverse a drawn arrow and tamper with a receipt.

## Slide view

Use the same `render()` entry point and `locus-comparison-v1` manifest. Set
`display.label_rotation` to a nonzero value (normally 40), or explicitly set
`display.view` to `slide`. Existing manifests without those settings retain the
report view. `display.view: report` explicitly selects the report view.

The slide view accepts the strain-slide adapter's existing names:

- `display`: `label_rotation`, `font_size` (gene labels), `width_in`,
  `axis_zero_track`, `axis_label`.
- Per track: `row`, `offset_bp`, `subtitle`, `heading_align` (`left`/`right`),
  `label_side` (`above`/`below`/`none`), `heading_side` (`above`/`below`/`left`).

Rows appear in order of first occurrence in the track list. Tracks sharing a
`row` sit level but remain separate contigs. Each gene uses the rigid transform
`orientation * (native coordinate - anchor midpoint) + offset_bp`; offsets do
not alter source coordinates, strands, order, lengths or correspondence evidence.
The default row is the track ID. Offsets must be finite, and row IDs must be
nonempty strings or integers.

Top-row labels/headings face above; bottom-row labels/headings face below;
intermediate rows have no gene labels and place their headings to the left.
Conflicting inward settings are refused with the track ID. Headings anchor at
their own first/last drawn gene according to `heading_align`. Bold headings and
grey identity/subtitle text wrap. Label extents are measured after drawing;
outer headings start six points beyond visible labels on their row (including shared-row neighbours). Colliding shared-row
headings stack farther outward, and measured point extents determine the y-limits.

Labels angle outward and are thinned using measured rotated rectangles, including
labels on different tracks sharing a row. Matched/missing-stop labels receive
priority. All genes and ribbons remain drawn; the receipt lists every omitted
label. A unique supplied identity percentage is appended to an outer BGC gene
label on the selected `identity_side` (default `a`). Existing percentage suffixes
are retained; empty labels never acquire a bare percentage. Multiple supplied
comparisons do not produce an inferred percentage. Reference percentages are not
printed beneath the reference genes.

The axis counts nonnegative kb from the first drawn gene of `axis_zero_track`,
defaulting to the first reference track. It has no dotted anchor line. The slide
view has no caveat footer. Source contig-end ticks and missing-stop asterisks are
retained; marker descriptions appear in the track heading and receipt. Missing-stop
asterisks also mark the arrow itself, even if its gene label is omitted. Keep any
scientific interpretation or caveats in the surrounding slide/caption.

Cropping a long reference, selecting its real short gene names and selecting one
strongest correspondence per query gene remain adapter responsibilities. The
renderer does not search, crop, select hits or infer biological linkage.

Receipts retain source hashes and drawn-arrow/orientation checks, and add
`display_view`, `row_y`, `offset_bp`, `axis_zero_track`, `axis_zero_bp`,
`axis_ticks_kb`, `heading_placements`, `visible_gene_labels` and
`omitted_gene_labels`. Boundary errors identify offending text; overlap errors
identify the track. Automated layout checks do not replace inspection of the
rendered figure.
