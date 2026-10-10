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

## Hash-binding states and write behavior

The receipt binds the input files and emitted Markdown/roster/SVG hashes. Protein-level binding is separate: read `protein_hash_binding.state`, which can be `NO_EVIDENCE_SUPPLIED`, `PROTEIN_HASH_BOUND`, `PARTIALLY_PROTEIN_HASH_BOUND`, or `EXACT_IDENTITY_BOUND_ONLY`. An evidence hash supplied without a canonical gene hash remains unverifiable and is counted as such; file hashing alone does not make its protein comparison current. No query/database-run receipt is admitted automatically.

Identity, gene slice and evidence checks happen before creating outputs, but later report validation can still fail after the roster and SVG are written. For example, invalid whole-region matched/total counts are checked after those writes. Existing output folders and fixed filenames are reused, with no atomic publication or stale-receipt removal. Use a fresh output directory and treat any failure as an incomplete attempt; preserve its files for diagnosis and rebuild separately. Do not accept a preexisting `REPORT_RECEIPT.json` after a failed attempt.

The Markdown evidence section reports the number of bound rows; it does not serialize the full imported evidence TSV into the report. Keep the exact input TSV with the report or a resolvable logical source locator and verify its hash when auditing individual evidence. The SVG and supplied component descriptions remain source-artwork candidates; this tool does not run the full current50 Mode B gate or rendered visual review.

Source owner: `mamey/deep_bgc_report.py:80–111,139–162,165–215`.
