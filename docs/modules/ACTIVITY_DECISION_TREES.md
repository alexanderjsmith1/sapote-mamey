# Metabolomics and Activity Decision Trees

`tools/build_activity_decision_trees.py` turns a portable lead table into per-locus decision gates. Each row must carry the complete exact identity, a safe relative locator to a deep-report receipt, a hypothesis, and an explicit claim ceiling. The receipt identity must agree in all four components.

The fixed gate order is expression, genetic linkage, reproducible chemical feature, activity with counterscreens, and bounded claim. A missing gate is an evidence requirement, not a negative result.

```bash
python tools/build_activity_decision_trees.py --leads-tsv leads.tsv \
  --receipt-root project_reports --output-dir decision_trees
```
