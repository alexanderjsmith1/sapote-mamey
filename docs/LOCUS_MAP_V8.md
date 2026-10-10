# Locus map v8

Locus map v8 is the default package-native renderer for compile-report and
post-seal figure workflows. It is designed for exact-locus review, not for
decorative overview figures.

For every rendered BGC, v8 emits:

- `<BGC>_locus_map.png` and `<BGC>_locus_map.svg`;
- `<BGC>_locus_map_data.csv`, with one row per exact package-bound gene; and
- `<BGC>_locus_map_v8_receipt.json`, with label, comparator, evidence, source,
  and claim-ceiling checks.

The renderer always displays every exact locus tag. Dense loci use an evenly
spaced label rail and leader lines instead of suppressing labels. A comparator
is selected deterministically from the package's MIBiG per-gene table: most
unique supported query genes, then median identity, reference rank, and
accession. Every selected exact gene is highlighted and receives a visible
identity/coverage row. Domain, HMM, module, and motif annotations are summarized
in that collision-managed evidence panel and preserved without truncation in
the companion CSV.

The renderer does not score or adjudicate a BGC. Similarity is not product
identity; annotations show capacity only; and the figure does not establish
expression, production, activity, novelty, a biological merge/split, or
physical linkage. Judgment remains deferred.

Legacy rendering remains available only as a bounded compatibility comparison:

```python
from mamey.locus_map import render_for_compile_report

render_for_compile_report(package_dir, top_n=5)                    # v8
render_for_compile_report(package_dir, top_n=5, renderer="legacy") # comparison only
```

## Completion and receipt verification

`render_for_compile_report` is non-blocking: inspect `rendered`, `skipped`, and `skipped_reason`. Per-locus exceptions are recorded in `skipped`; an empty list may reflect missing tables or renderer failure. The adapter requires `_gene_by_gene_all_bgcs.csv`, even though direct `render_bgc_v8` can fall back to `_cds_table.csv`. Ranking selects the first `top_n` triage rows by corrected rank (then alias); it is not a full-inventory worklist.

Each direct render requires complete strain / full node-or-contig / region / BGC alias, and its receipt records that identity, sources and output hashes. `READY` is a mechanical label/comparator count status. The current receipt reader checks the PNG/SVG/CSV triple, bytes/hashes, counts, signatures and selected comparator agreement. It does **not** revalidate the complete identity fields or source-file hashes. Independently compare those fields and recorded source hashes against the bound package; retain identity parity and source-coverage holds until resolved.

Gene loading silently skips rows with missing locus/start/end or nonnumeric coordinates. The receipt counts the accepted genes, not all source-region rows. Reconcile the source gene roster with the CSV and record any excluded row. `render_bgc_v8` writes fixed filenames in an existing directory; a later receipt refusal can leave artwork and a non-ready receipt. Use a fresh review copy/output namespace and preserve earlier bound artifacts before rebuilding. Do not change a sealed package as an undocumented repair.

The R locus-map template is an alternate arrow view and omits v8's comparator/evidence panel; see [R figure workflows](R_FIGURE_WORKFLOWS.md). No receipt or label count substitutes for intended-size visual inspection.

Source owners: `mamey/locus_map.py:471–481`; `mamey/locus_map_v8.py:174–281,352–398,651–692,790–856,860–909`.
