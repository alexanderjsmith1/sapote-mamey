# Figure Factory: aggregate evidence coverage

Render channel coverage from a metrics table and a cohort manifest:

```bash
python mamey_run.py figure-factory --config project/figure_factory_next.json
```

Use the configuration below for the aggregate renderer. The same command also routes the
`phylogeny_annotation_tracks_v1`, `phylogeny_shared_tip_concordance_v1`, and
`phylogeny_evidence_receipt_widget_v1` figure kinds to the phylogeny renderer; their inputs differ.
See the [preflight and methods manual](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md).

## Automatic output

The run/cohort hook searches `MAMEY_FIGURE_FACTORY_CONFIG`, then
`figure_factory_next_config.json` in the source and target directories. Without a discoverable
configuration it returns `SKIPPED_NO_CONFIG`. A separate Python helper,
`mamey.figure_factory_default_config.emit_default_figure`, can generate a configuration from
package cohort tables; it is not called by this CLI hook.

Automatic output goes to the target's `figure_factory` directory, replacing that directory if it
already exists. Automatic rendering errors are reported separately from the sealed package.
For manual rendering, choose a new output directory: the direct renderer refuses an existing one.
Use an absolute `external_data_root`; a relative `output_dir` resolves beside the configuration file.

## Portable contract

Figure Factory Next v2 renders aggregate evidence coverage from two exact, content-addressed inputs:
an aggregate-metrics TSV and an authoritative cohort manifest. It does not discover developer
workspaces, infer roles from identifiers, or hardcode a private identity.

The metrics columns are `identity`, `channel`, `metric`, `numerator`, `denominator`, and
`denominator_key`. The manifest columns are `identity`, `role`, `include_by_default`, `genus`,
`cohort`, `assembly_state`, and `assembly_reason`. Every identity must occur in both files exactly.

Roles are `STUDY`, `REFERENCE`, `EXTERNAL_BENCHMARK`, or `OUTGROUP`. External benchmarks and
outgroups must be default-off. Assembly states are `PASS`, `FLAG`, `DEFAULT_OFF`, or `UNRESOLVED`.
A selected default-off identity is rendered only as a separately labelled sensitivity row and never
enters the study denominator. Within-genus grouping is the default; optional genera require explicit
declaration and selection.

Example configuration:

```json
{
  "schema_version": "sapote.figure-factory-next.v2",
  "external_data_root": "/configured/data/root",
  "output_dir": "outputs/figure_factory_next",
  "title": "Evidence readiness by channel",
  "figure_question": "How much of each declared evidence channel is observed?",
  "source_release": "project-release-receipt",
  "software_versions": "renderer version receipt",
  "inputs": [
    {
      "role": "aggregate_metrics",
      "logical_locator": "admitted/figure_metrics.tsv",
      "sha256": "<64 lowercase hex characters>"
    },
    {
      "role": "cohort_manifest",
      "logical_locator": "admitted/cohort_manifest.tsv",
      "sha256": "<64 lowercase hex characters>"
    }
  ],
  "comparison": {
    "default_genera": ["Genus alpha"],
    "optional_genera": ["Genus beta"],
    "selected_optional_genera": [],
    "selected_optional_identities": []
  },
  "owner_notes": []
}
```

Run from the extracted bundle root:

```bash
python mamey_run.py figure-factory --config project/figure_factory_next.json
python tools/figure_factory_next.py --config project/figure_factory_next.json
```

The renderer transactionally emits live-text SVG and native 300-DPI PNG artwork for both 3.5-inch
single-column and 7.2-inch double-column profiles into the configured `output_dir`, together with the
exact plotted data (`figure_factory_next_data.tsv` and `figure_factory_next_data.csv`), the audit-only exclusion table
(`figure_factory_next_exclusions.tsv`), a dynamic caption/method record (`.json` and `.md`), separate
owner-notes metadata (`figure_factory_next_owner_notes.json`), and a hash receipt
(`figure_factory_next_receipt.json`). Solid accessible cohort colors are the default. Open diamonds
mark included assembly flags; an `x` marks a deliberately selected default-off assembly sensitivity
row. The output directory must not pre-exist; the renderer stages to a temp directory and atomically
replaces the target so a partial render is never left on disk.

## Restyle in R

The aggregate renderer writes matching TSV and CSV data sidecars. With R and ggplot2 installed,
render that CSV using the shipped companion:

```bash
Rscript tools/figure_factory_next_ggplot.R outputs/figure_factory_next/figure_factory_next_data.csv restyled single_column "Evidence coverage"
```

This writes SVG and PNG artwork from the exported table. Keep the original receipt and data
alongside restyled output. Other figure families have their own export contracts; this guide does
not guarantee a common CSV schema across all figures.

## Troubleshooting

The aggregate renderer rejects the old v1 schema, changed input hashes, paths outside the
configured root, invalid denominators, unsupported cohort colors, and layout or raster-quality
failures. Correct the reported input or configuration rather than editing a receipt to bypass it.
The receipt records `PASS_PORTABLE_POLICY_RENDERER_CANDIDATE` on success. Owner notes are
stored separately from the artwork.

For palette previews, use [optional gallery tools](OPTIONAL_FIGURE_FACTORY_TOOLS.md).
Engineering specifications and unresolved bindings are indexed separately in the
[Figure Factory folder](figure_factory/README.md).
