# Bioassay context adapter workflow

This adapter is optional and narrow. It works for **one assay layout only**: a 48-hour fraction
screen at 120, 60, 30 and 15 ug/mL (the assay label is fixed as `fraction_screen_multidose_48h`).
Do not use it for another time point, platform or dose layout. The adapter does not check that
your data came from that layout. It stamps the label and the dose list from its own template on every
assay, and records that in the output: `assay_label_basis` and `doses_ugml_basis` are
`ADAPTER_TEMPLATE_NOT_READ_FROM_INPUT`, and `template_dose_columns_state` says whether the input
header has the four columns `inhibition_120ug_ml`, `inhibition_60ug_ml`, `inhibition_30ug_ml` and
`inhibition_15ug_ml` (`ALL_TEMPLATE_DOSE_COLUMNS_PRESENT`, `TEMPLATE_DOSE_COLUMNS_PARTIAL` or
`TEMPLATE_DOSE_COLUMNS_ABSENT`). Every object also carries a `LAYOUT_TEMPLATE_NOT_VERIFIED` warning. For general bioassay figures, use
[the bioassay figure factory](BIOASSAY_FIGURE_FACTORY.md), which is the front door.

`tools/bioassay_to_activity_channel.py` reads a screening summary CSV you already have and writes
strain-level `bioactivity_metadata_v1` context files. It does not read raw plate data, compute
inhibition, or tie an extract result to a BGC. The CSV stays the evidence.

## Run it

```bash
python tools/bioassay_to_activity_channel.py --recon inputs/EXAMPLE_screening.csv \
  --out reviews/EXAMPLE/activity_context --strain EXAMPLE
```

Options:

- `--out` is a new folder.
- `--strain` keeps one strain. It is optional, and a value that matches no rows is not an error.
- `--min-hit` is the percent-inhibition cut-off between positive and negative. The default is 50.
- `--validate <bundle-root>` checks each output against that tree's metadata validator. Use a
  tree you trust.
- `--af-dossier-csv <file>` writes an extra antifungal dossier table.
- `--declare-layout fraction_screen_multidose_48h` records that you checked the input comes from
  that screen. Each assay and the manifest then carry `layout_declaration_state` =
  `OPERATOR_DECLARED_NOT_SOFTWARE_VERIFIED`. Without the flag the state is
  `UNDECLARED_HOLD_LAYOUT_ASSUMED_FROM_TEMPLATE`. Any other value is refused.

You should see `wrote 1 per-strain bioactivity_metadata_v1 objects -> reviews/EXAMPLE/activity_context`
and exit 0. The folder holds `EXAMPLE_bioactivity_metadata.json` and `MANIFEST.json`. A strain
filter that matches nothing still exits 0 and writes a manifest with zero strains, so check the
count in that line.

## The input CSV

No bundled tool writes this CSV. You prepare it from your screening results. It needs these
columns, and extra unnamed columns are refused:

```text
strain_id,organism,screening_pattern,max_inhibition_raw
EXAMPLE,Candida albicans,STRONG_DOSE_CONSISTENT,92.5
EXAMPLE,MRSA,NO_50PCT_OBSERVATION,12.0
EXAMPLE,Other target,SINGLE_CONCENTRATION_SPIKE,70.0
```

`strain_id` and `organism` cannot be blank. `screening_pattern` is the tier you assigned.
`max_inhibition_raw` is the highest percent inhibition seen.

## How each row is judged

| Row | State |
|---|---|
| Tier is `STRONG_DOSE_CONSISTENT` or `SUPPORTED_MULTI_CONCENTRATION_HIT`, value at or above `--min-hit` | positive |
| Same tiers, value below `--min-hit` | negative |
| Tier is `NO_50PCT_OBSERVATION`, value below `--min-hit` | negative |
| Any other tier, or a missing or non-numeric value | unknown |

A target is positive if any of its rows is positive. It is negative only if every one of its rows
is negative. Otherwise it is unknown. An unknown or missing value is never a measured negative.
In the example above, the three rows give positive, negative and unknown.

The shown "best" row and the target's state use different rules: the state considers every row for
that target. The `source_rows` field lists all of them, so check it before you quote one number.

The antifungal dossier groups targets by whether the name contains `candida` or `mrsa`. That is a
text match, not an organism check, so review unusual target names.

## Output and checks

Keep the source CSV and the output folder together. `MANIFEST.json` records the source file hash,
the cut-off and the list of outputs. It does not hash the outputs or the tool code, so record those
yourself if you need them.

Pass an output file's contents to a new `run` with `--bioactivity-json`. The flag takes the JSON
text itself, not a file path, for example `--bioactivity-json "$(cat <output>.json)"`. Text that
is not valid JSON is refused with `BIOACTIVITY_LEGACY_SHAPE_HOLD` and exit 2. It supplies context to that run. It
does not change a sealed package. The context is extract-level: it says nothing about which BGC
made an active fraction. See [the metadata contract](BIOACTIVITY_METADATA_CONTRACT.md).
