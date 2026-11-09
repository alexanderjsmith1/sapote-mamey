# Metabolomics and Activity Decision Trees

`tools/build_activity_decision_trees.py` turns a portable lead table into per-locus decision gates. Each row must carry the complete exact identity, a safe relative locator to a deep-report receipt, and an explicit claim ceiling. The receipt identity must agree in all four components. Supply a source-bound hypothesis for useful interpretation: the implementation does not require that field and substitutes `unresolved` only when the column is absent; a supplied blank stays blank.

The fixed gate order is expression, genetic linkage, reproducible chemical feature, activity with counterscreens, and bounded claim. Every admitted row starts at the expression gate with `EVIDENCE_REQUIRED`; the builder does not inspect completed gate evidence or advance a saved workflow. A missing gate is an evidence requirement, not a negative result.

## Input columns

The lead table is tab-separated, one row per locus. A blank cell, or a cell missing because the row is shorter than the header, counts as missing, so a short row without `claim_ceiling` is refused. A row with more cells than the header is refused.

| Column | Required | Holds |
|---|---|---|
| `strain` | yes | Strain label |
| `full_node_or_contig` | yes | Full contig or node name, not shortened |
| `region` | yes | antiSMASH region |
| `bgc_alias` | yes | BGC alias |
| `claim_ceiling` | yes | The strongest statement allowed for this locus |
| `report_receipt` | yes | Path to the deep-report receipt JSON, relative to `--receipt-root` |
| `hypothesis` | no | Your source-bound hypothesis; printed as given |

The four identity columns must equal the receipt's `identity` object exactly. Two rows with the same identity stop the run.

## Outputs

- `ACTIVITY_DECISION_TREES.md`: one section per locus with the five gates;
- `ACTIVITY_DECISION_TREES.tsv`: columns `exact_locus`, `next_gate`, `status`, `claim_ceiling`;
- `ACTIVITY_DECISION_TREE_RECEIPT.json`: the lead count, the lead-table hash and the hashes of the two files above.

A refusal prints one `build_activity_decision_trees: refused: <reason>` line on stderr and exits 2. Success prints the output folder and exits 0.

## Running it

Use a fresh output directory: existing directories are refused. Markdown, TSV and receipt are written sequentially, so a failure can leave a partial candidate. The receipt hashes the lead input and emitted Markdown/TSV, but does not bind each selected deep-report receipt or verify the report artifacts named within it. Retain those source receipts and their hashes separately; identity equality is not report-content validation.

```bash
python tools/build_activity_decision_trees.py --leads-tsv leads.tsv \
  --receipt-root project_reports --output-dir decision_trees
```
