# Bioassay → activity channel (measured screening context)

`tools/bioassay_to_activity_channel.py` turns MEASURED fraction-screen data into Sapote-Mamey
`bioactivity_metadata_v1` objects (see `docs/BIOACTIVITY_METADATA_CONTRACT.md`) so a strain's real
screening result can travel with its package as **strain-level, extract-level context** — never a BGC claim.

## Run
```
python3 tools/bioassay_to_activity_channel.py \
  --recon <fraction_concentration_response_48h.csv> \
  --out <dir> [--strain AS-XXX] [--min-hit 50.0] [--validate <sealed-mamey-tree>]
```
Then feed one strain's object into a run:
```
python3 mamey_run.py run --strain AS-XXX --input-zip AS-XXX.zip \
  --bioactivity-json "$(cat <dir>/AS-XXX_bioactivity_metadata.json)"
```

## What it emits (per strain)
`bioactivity_metadata_v1` with `metadata_state` MEASURED_POSITIVE/MEASURED_NEGATIVE, `observation_state`,
`usage_scope=PRODUCTION`, `compound_linkage=NOT_ESTABLISHED`, and per-organism inhibition%/dose-vector/tier in
free-form `assays[]`. Every object carries `warnings`: the data is a **preliminary single-replicate 384-well
screen with no biological replication** — dose inversions and single-concentration spikes are expected
artifacts, not validated activity.

## Claim-safety (why it is safe to admit)
The engine treats this as score-neutral context (changes no triage bytes) and refuses any per-BGC phenotype in
report text (`mamey/claim_safety_gate.py`, H3 bioactivity linter). Screening observations only; capacity is not
production; no BGC is credited; judgment deferred. The tool NEVER writes a BGC/cluster/region into an assay.

## Second output: af-dossier activity table
`--af-dossier-csv <path>` also writes the measured activity table consumed by
`mamey_run.py af-dossier --activity-table` — columns `strain,anti_Candida,anti_MRSA,host,genus` (per-strain
positive/negative calls from credible screening hits). A report-only, post-seal AF-lead crosswalk; never scoring.
