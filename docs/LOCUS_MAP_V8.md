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
