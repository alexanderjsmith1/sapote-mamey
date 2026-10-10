# Bioassay screening context admission

`tools/bioassay_to_activity_channel.py` converts an already reviewed screening evidence CSV into
per-strain `bioactivity_metadata_v1` objects. Read the
[metadata contract](../docs/BIOACTIVITY_METADATA_CONTRACT.md). This is measured screening context
at the strain/extract level, with compound and locus linkage explicitly unestablished.

## Required inputs and command

The CSV requires `strain_id`, `organism`, `screening_pattern` and `max_inhibition_raw`.
Keep missing/unparseable evidence unknown. Optional dose/source columns are carried only when
present; do not substitute measurements. Bind the source checksum and interpretation scope.

```bash
python3 tools/bioassay_to_activity_channel.py \
  --recon project/reviewed_screen.csv \
  --out project/activity_context_new \
  --strain EXAMPLE \
  --validate .
```

`EXAMPLE` is a placeholder for a source-bound exact strain identifier. `--validate` takes the
**code bundle root containing `mamey/bioactivity_metadata.py`**, not a results-package directory;
it loads that normalization implementation to admit the objects. Omit it only when that validation
is deliberately deferred and reported. `--min-hit` is an optional finite nonnegative screening
threshold (default 50.0), not a potency or clinical efficacy threshold.

To admit a reviewed object during a separately authorized extraction, `--bioactivity-json` expects
the JSON object text, not a filename. Select the exact object for the same bound strain and include
the rest of the extraction inputs and metadata as in the [first analysis guide](../docs/MASTER_WALKTHROUGH.md).
This converter does not update an existing sealed package automatically.

## States and output contract

The converter writes `<strain>_bioactivity_metadata.json` and `MANIFEST.json`, containing the raw
source-file hash, threshold, per-strain states and output locators. It refuses existing artifact
paths, collisions and source aliases; use fresh destinations. `--af-dossier-csv` additionally writes
a table with `strain,anti_Candida,anti_MRSA,host,genus`; its parent directory must already exist.
Output publication uses the existing multi-file payload transaction after admission/serialization.

The conservative screening ruling is POSITIVE when at least one credible qualifying observation
exists, NEGATIVE only when every supplied relevant row supports a below-threshold observation,
and UNKNOWN otherwise. Objects map these to `MEASURED_POSITIVE`, `MEASURED_NEGATIVE` and
`SUPPLIED_UNKNOWN`. Dossier calls are `positive`, `negative`, `unknown` or `not_tested`; the last
two must not be rewritten as negative. This is a ruling over supplied target rows, not proof that
all relevant organisms were tested or that the strain lacks activity.

The emitted `usage_scope=PRODUCTION` is schema metadata; it does not establish production of an
identified compound. Each object carries the preliminary single-replicate 384-well screen warning
and `compound_linkage=NOT_ESTABLISHED`. No biological replication or assay validation is inferred.
The converter's neutral-context role does not mean a subsequent extraction has no output changes.
Keep assay observations, class-level genomic hypotheses and locus attribution separate.
