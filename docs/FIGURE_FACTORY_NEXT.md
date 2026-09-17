# Aggregate evidence coverage figure

**Use this renderer when you already have a table of counted observations and a
separate, checked list of which strains belong in the comparison.** It draws one
horizontal bar for each cohort, genus, evidence channel, and metric. For example,
it can show the fraction of declared proteins with a returned nr record beside
the corresponding fraction for ClusteredNR. The two channels remain separate.

This is one specialized Figure Factory route. It does **not** read raw BLASTp
databases, discover strains, choose a manuscript cohort, or interpret BGCs for you.
For figures directly from one Mamey package or a set of packages, start with
[Figures start here](FIGURES_START_HERE.md). For figure-specific preflight and
methods, see the [methods manual](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md).

## Try it with invented data

From the extracted bundle root, run:

```bash
python tools/figure_factory_demo.py --project-dir ./figure_demo
python mamey_run.py figure-factory --config ./figure_demo/figure_factory_next.json
```

Choose a new directory if `figure_demo` already exists. The first command copies
two **synthetic** TSVs and writes a configuration with their SHA-256 hashes. The
second makes both single-column and double-column SVG and PNG figures. Open
`figure_demo/figure/figure_factory_next_double_column.png` and then read
`figure_factory_next_caption_methods.md` in the same folder. The latter is the
figure's generated methods and denominator record, not optional prose.

In the demonstration, blue bars are invented bee and wasp study groups. Other
colors identify separately selected sensitivity examples. An open diamond marks
an included assembly flag; an x marks a selected default-off identity. A count
of returned records is not a validated hit or a compound assignment.

## Use your own data

Make two tab-separated files and edit the generated `figure_factory_next.json`:

| File | Required columns | What it decides |
| --- | --- | --- |
| Aggregate metrics | `identity, channel, metric, numerator, denominator, denominator_key` | What was counted for each identity and database or other evidence channel. |
| Cohort manifest | `identity, role, include_by_default, genus, cohort, assembly_state, assembly_reason` | Which identities are study members, optional references, or held sensitivity cases. |

Every identity must appear exactly once in the manifest and match the metrics.
Use the real provenance and admission decision that produced each numerator and
denominator. In particular, do not treat an error response or an unadmitted BLASTp
row as a biological no-hit. Put nr, ClusteredNR, and Swiss-Prot in distinct
`channel` values if you have counted them separately.

Update `external_data_root` to the absolute directory containing these files,
change each `inputs[].logical_locator` to its path **within that root**, and
replace each `inputs[].sha256` with the file's SHA-256. Set a new `output_dir`,
a descriptive `title` and `figure_question`, and the real `source_release`
and `software_versions`. In `comparison`, choose the default genera and any
optional genera or identities deliberately. The example's names and counts are
not a template for the user's cohort.

Run the same `mamey_run.py figure-factory --config ...` command. Changed hashes,
an invalid identity join, unsupported cohort categories, bad denominators, and
layout failures are errors to correct in the inputs or configuration. A manual
render refuses an existing output directory so it cannot silently replace a
figure you reviewed.

## Review before using a figure

Open the PNG at the intended print size and inspect the SVG's live text. Check
that titles, labels, ratios and assembly markers are legible. Then check:

1. `figure_factory_next_data.tsv` or `.csv`: the exact values that were plotted.
2. `figure_factory_next_exclusions.tsv`: identities left out of the plotted study.
3. `figure_factory_next_caption_methods.md`: units, denominators, selection,
   transformation, and the limit of the interpretation.
4. `figure_factory_next_receipt.json`: input hashes, figure dimensions, raster
   resolution, and layout checks.

Keep the methods text with the artwork when placing a figure in a manuscript.
The current aggregate renderer writes it as a companion file; it does not print
the complete methods paragraph beneath the plot automatically. Owner notes are
stored separately from the scientific caption.

## Where this fits

The renderer accepts the `sapote.figure-factory-next.v2` configuration written by
the demo script. A configured run can also discover `MAMEY_FIGURE_FACTORY_CONFIG`
or `figure_factory_next_config.json` and write an automatic figure; absent
configuration means `SKIPPED_NO_CONFIG`. Automatic output is separate from the
sealed core package and may replace its designated `figure_factory` directory.
Use the manual command above while learning or reviewing a specific manuscript
figure.

The same `figure-factory` command also accepts distinct phylogeny figure kinds;
they have different inputs. The [Figure Factory index](figure_factory/README.md)
links the other figure guides and review tools.
