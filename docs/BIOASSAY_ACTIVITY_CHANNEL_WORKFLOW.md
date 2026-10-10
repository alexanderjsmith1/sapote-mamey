# Bioassay context adapter workflow

`tools/bioassay_to_activity_channel.py` translates a previously governed screening-evidence CSV into optional, strain-level `bioactivity_metadata_v1` context. It does not read raw plate data, reconstruct assays, validate physical replication, calculate new inhibition values, or attribute an extract phenotype to a BGC. Owner-reviewed source evidence and its unresolved assay holds remain authoritative.

## Input admission and missingness

The CSV requires `strain_id`, `organism`, `screening_pattern`, and `max_inhibition_raw`; blank strain/organism and unnamed extra columns are refused. An optional strain filter may select no rows. Numeric adjudication is conservative: a finite value in a credible tier can be positive at or above the chosen threshold or negative below it; a `NO_50PCT_OBSERVATION` row below threshold can be negative; other evidence remains unknown. Any positive row wins a target's state; a negative state requires all its rows negative. Missing, unsupported or malformed values are not measured negatives.

The emitted assay description is hardcoded to `fraction_screen_multidose_48h` and doses `[120,60,30,15]`. These labels must match the admitted source scope. Do not apply the adapter to another time point/platform/dose layout and assume it discovers the correct scope. `--min-hit` changes adjudication but does not rename source fields such as `doses_at_or_above_50pct`. The displayed representative row and the adjudicated state use different selection logic: the state considers all target rows. Retain `source_rows` and reconcile any apparent discrepancy rather than treating the representative value as the complete evidence.

The optional AF dossier groups target names by case-insensitive substring `candida` or `mrsa`. That is not an organism-identity resolver; unrelated or ambiguous target names need review. Host/genus values are retained only where the selected rows agree.

## Output, validation and recovery

Output is a new external directory containing per-strain objects and `MANIFEST.json`. The source CSV is hashed before and after reading; a changed input is refused. `receipt_locator` binds a sorted canonical serialization of selected rows, **not the raw CSV bytes**. The manifest records the raw source hash, threshold and output inventory, but lacks output-content hashes and adapter/validator code hashes. Retain those separately. Empty selection can still successfully publish a manifest with zero strains; exit zero does not prove a requested strain was found.

`--validate <bundle-root>` loads that root's `mamey/bioactivity_metadata.py`. Use a trusted, hash-recorded source tree. This optional check is shape normalization, with the limitations in [the metadata contract](BIOACTIVITY_METADATA_CONTRACT.md); it is not scientific evidence approval. The adapter stages outputs and uses the shared publication helper's normal exception rollback; this is not a crash-atomic package transaction.

Passing an emitted object to a newly authorized `run --bioactivity-json` supplies typed context to that new run. It is not an in-place update of an existing sealed package. Preserve the original package and source evidence; maintain the sidecar context independently unless the owner has authorized a new run. Do not treat the adapter as required to refresh deterministic scoring. Capacity, activity, production and compound linkage remain separate evidence claims.

Source: `tools/bioassay_to_activity_channel.py:34–149,152–232`; `mamey/bioactivity_metadata.py:63–87`.
