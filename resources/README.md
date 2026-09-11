# Bundled resources

These are small supporting assets with specific consumers, not a single evidence database.

| File | Purpose and consumer |
|---|---|
| `bioactivity_axes.json` | Chemistry-to-activity-axis vocabulary read by `tools/build_lead_tiers.py`; vocabulary does not establish measured activity. |
| `gcf_thesaurus.json` | GCF tag vocabulary read by `tools/build_gcf_tags.py`. |
| `validation_runs.csv` | Historical validation-panel observations used by `tools/build_validation_panel.py`; see the limitations below. |
| `reference_seed_inputs/` | Policy and manifest template for separately supplied reference inputs. |

## Validation-panel limitations

The historical CSV lacks per-row software-version and input/receipt hashes. Its `retention_pct`
column is not internally reconciled with all raw/corrected count pairs: two rows record 51/50.5
and 67/67 alongside retention values 31 and 22. Do not use those values as verified corrected/raw
percentages or as current-release validation. Preserve the source observations until their original
definition and receipts are recovered; silently recalculating them would change historical evidence.

The plotting tool currently uses these values in labels. Use separately admitted, reconciled input
for a final figure. The [validation folder](../validation/README.md) explains the older evidence scope.
