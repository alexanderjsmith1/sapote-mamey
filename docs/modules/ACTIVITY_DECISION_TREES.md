# Metabolomics and Activity Decision Trees

`tools/build_activity_decision_trees.py` turns a portable lead table into per-locus decision gates. Each row must carry the complete exact identity, a safe relative locator to a deep-report receipt, and an explicit claim ceiling. The receipt identity must agree in all four components. Supply a source-bound hypothesis for useful interpretation: the implementation does not require that field and substitutes `unresolved` only when the column is absent; a supplied blank stays blank.

The fixed gate order is expression, genetic linkage, reproducible chemical feature, activity with counterscreens, and bounded claim. Every admitted row starts at the expression gate with `EVIDENCE_REQUIRED`; the builder does not inspect completed gate evidence or advance a saved workflow. A missing gate is an evidence requirement, not a negative result.

Use a fresh output directory: existing directories are refused. Markdown, TSV and receipt are written sequentially, so a failure can leave a partial candidate. The receipt hashes the lead input and emitted Markdown/TSV, but does not bind each selected deep-report receipt or verify the report artifacts named within it. Retain those source receipts and their hashes separately; identity equality is not report-content validation.

```bash
python tools/build_activity_decision_trees.py --leads-tsv leads.tsv \
  --receipt-root project_reports --output-dir decision_trees
```
