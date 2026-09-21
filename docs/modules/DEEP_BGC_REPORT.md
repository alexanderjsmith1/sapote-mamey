# Deep BGC Report Builder

`tools/build_deep_bgc_report.py` converts one portable JSON locus record and an optional exact-identity evidence TSV into a gene-level Markdown report, canonical roster, SVG locus map, and hash-bound receipt.

Every input row must carry `strain`, `full_node_or_contig`, `region`, and `bgc_alias`. Evidence is joined only when all four fields agree and the gene belongs to the canonical slice. Protein hashes, when supplied in the locus record, must agree. Missing or conflicting fields fail before output.

Boundary interpretation separates the whole-region comparator fraction from coherent matched components. This supports overmerge review without turning a component match into a product claim. Comparator matches remain navigation evidence; product identity, expression, and activity remain unresolved without orthogonal evidence.

```bash
python tools/build_deep_bgc_report.py \
  --locus-json inputs/locus.json \
  --evidence-tsv inputs/evidence.tsv \
  --output-dir outputs/deep_report
```

Paths are supplied by the caller. The tool contains no workspace-specific roots or private identifiers.
