# Aggregate evidence coverage figures — advanced guide

Use this renderer to compare **counted observations with their declared
denominators** across cohorts, genera and evidence channels. It draws one
horizontal bar for each cohort, genus, evidence channel and metric. It does not
search BLASTp databases or choose a cohort.

Start with two prepared inputs: a metrics table and a checked cohort manifest.
For example, compare the share of declared proteins that returned an nr record
with the share that returned a ClusteredNR record. Keep the two channels separate.

If you have those tables, go to **Use your own data** below. To learn the file
layout first, try the synthetic example. If you have a Mamey package, gene-map
request or tree instead, choose its route in [Figures start here](FIGURES_START_HERE.md).
Figure-specific preflight and methods are in the [methods manual](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md).

## Try it with invented data

From the extracted bundle root, run:

```bash
python tools/figure_factory_demo.py --project-dir ./figure_demo
python mamey_run.py figure-factory --config ./figure_demo/figure_factory_next.json
```

Choose a new directory if `figure_demo` already exists. The first command copies
two **synthetic** TSVs and writes a configuration with their SHA-256 hashes. The
second makes single-column and double-column figures, each as SVG and PNG. Open
`figure_demo/figure/figure_factory_next_double_column.png`. Then read
`figure_factory_next_caption_methods.md` in the same folder. That file is the
figure's generated methods and denominator record, not optional prose.

In the demonstration, blue bars are invented bee and wasp study groups. Other
colors identify separately selected sensitivity examples. An open diamond marks
an included assembly flag; an x marks a selected default-off identity. A count
of returned records is not a validated hit or a compound assignment.

## Use your own data

If you do not yet have a configuration, run the first demonstration command above in a new directory. It stages inputs and a configuration without drawing a figure. Then edit that `figure_factory_next.json` to use your two tab-separated files:

| File | Required columns | What it decides |
| --- | --- | --- |
| Aggregate metrics | `identity, channel, metric, numerator, denominator, denominator_key` | What was counted for each identity and database or other evidence channel. |
| Cohort manifest | `identity, role, include_by_default, genus, cohort, assembly_state, assembly_reason` | Which identities are study members, optional references, or held sensitivity cases. |

Every identity must appear exactly once in the manifest and match the metrics.
Use the real provenance and admission decision that produced each numerator and
denominator. In particular, do not treat an error response or an unadmitted BLASTp
row as a biological no-hit. Put nr, ClusteredNR, and Swiss-Prot in distinct
`channel` values if you have counted them separately.

Then edit the configuration:
- Set `external_data_root` to the absolute folder that holds these files.
- Set each `inputs[].logical_locator` to the file's path **within that root**.
- Replace each `inputs[].sha256` with the file's SHA-256.
- Set a new `output_dir`, a descriptive `title` and `figure_question`, and the real
  `source_release` and `software_versions`.
- In `comparison`, choose the default genera and any optional genera or identities on purpose.

The example's names and counts are not a template for your cohort.

Run the same `mamey_run.py figure-factory --config ...` command. Fix these errors in
the inputs or the configuration: changed hashes, an invalid identity join, unsupported
cohort categories, bad denominators and layout failures. A manual render refuses an
existing output folder, so it cannot quietly replace a figure you reviewed.

## Review before using a figure

Open the PNG at the intended print size and inspect the SVG's live text. Check
that titles, labels, ratios and assembly markers are legible. Then check:

1. `figure_factory_next_data.tsv` or `.csv`: the exact values that were plotted.
2. `figure_factory_next_exclusions.tsv`: identities left out of the plotted study.
3. `figure_factory_next_caption_methods.md`: units, denominators, selection,
   transformation, and the limit of the interpretation.
4. `figure_factory_next_receipt.json`: input hashes, figure dimensions, raster
   resolution, and layout checks.

The receipt status `PASS_PORTABLE_POLICY_RENDERER_CANDIDATE` means the renderer
made a candidate and recorded its input and output hashes. It is not visual or
scientific acceptance. Review the artwork, data and layout before use. Keep a
separate record of the exact configuration hash and renderer version.

Keep the methods text with the artwork when you place a figure in a manuscript.
The renderer writes it as a companion file. It does not print the full methods
paragraph under the plot. Owner notes go in a separate file
(`figure_factory_next_owner_notes.json`), apart from the scientific caption.

## Where this fits

The renderer accepts the `sapote.figure-factory-next.v2` configuration that the
demo script writes. A run can also find `MAMEY_FIGURE_FACTORY_CONFIG` or
`figure_factory_next_config.json` and write a figure automatically. With no
configuration, the status is `SKIPPED_NO_CONFIG`. Automatic output sits outside the
sealed core package. It can replace its own `figure_factory` folder. Use the manual
command above while you learn or review a specific manuscript figure.

The same `figure-factory` command also accepts phylogeny and bioassay figure kinds.
They have different inputs. The [Figure Factory index](figure_factory/README.md)
links the other figure guides and review tools.

<details>
<summary>Technical details: receipts, automatic replacement and recovery</summary>


The aggregate receipt status is `PASS_PORTABLE_POLICY_RENDERER_CANDIDATE`, with authority `ENGINEERING_CANDIDATE_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED`. The receipt hashes the two input tables and the files it wrote. It does not hash the configuration or the renderer source. Keep a separate run record with the exact config hash, bundle or source version, interpreter and selected profiles. Inspect each file and the layout it will sit in before you accept how it looks.

Automatic discovery uses the first config that exists, in this order: `MAMEY_FIGURE_FACTORY_CONFIG`, the source folder, then the target folder. If the environment path does not exist, the search moves on to the next candidate.

The automatic hook deletes `<target>/figure_factory` **before** it checks input hashes and draws the replacement. If the build then fails, it returns `SKIPPED_<exception-type>`. Save the previous figure folder and its receipt before a rerun. For a replacement you can review, use the manual route with a new folder.

`SKIPPED_NO_CONFIG` means the feature did not run. A successful surrounding run or a figure count does not prove this channel finished.

For R restyling, use [R figure workflows](R_FIGURE_WORKFLOWS.md). R does not check the factory receipt or write a new receipt for its output. An R output needs its own renderer, input and output record, and a visual review.

Source owners: `mamey/figure_factory_next.py`; `mamey/cli.py`.

</details>
