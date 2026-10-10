# Optional external AB/AF activity-prediction channel

This is optional model evidence, separate from Mamey's deterministic routing priors and from measured strain-level assay context. The shipped `mamey/activity_predictions.py` validates supplied prediction documents and writes JSON. This guide does not establish a working inference adapter for every named third-party model.

## Implemented contract

The schema is `sapote.optional_activity_predictions/1`. The authoritative record key is `(strain, bgc_id, contig_region, model_id)`; duplicate keys are refused. Across-strain joins by BGC alias alone are prohibited. The validator checks nonempty identity fields and BGC alias format; it does not parse `contig_region` into a verified full node and region or join it to the package inventory. Where a locus is discussed, retain and verify all four parts: strain / full node-or-contig / region / BGC alias, alongside model identity.

`applicability_status` is `IN_DOMAIN`, `LIMITED`, `OUT_OF_DOMAIN` or `FAILED`. Probabilities, when present, must be finite values in [0,1]. `OUT_OF_DOMAIN` and `FAILED` require null probabilities and a HOLD. `IN_DOMAIN` requires model, environment, feature-schema and input hash fields and is restricted by fragment adequacy **when that optional field is present**. Legacy rows without it do not pass through this fragment check; absence is not evidence of completeness. Hash-field syntax validation does not read and verify the corresponding files. Keep the actual referenced bytes and verify hashes separately. The NPBDetect model identifier is restricted to `OUT_OF_DOMAIN`/`FAILED`; the former phrase “experimental” did not mean it could be admitted as an in-domain prediction.

`write_predictions(doc, package_dir, out_dir=None)` validates the document, refuses a resolved output path inside the package, and writes **`optional_activity_predictions.json`**. The default directory is a sibling of the package; an explicit output may be elsewhere outside it. It creates or reuses that directory and atomically replaces the JSON through a fixed sibling `.tmp` file. This is not an exclusive new-output or concurrency guard. The writer does not verify package sealing, check that declared source hashes match the package, or emit a multi-file receipt. Use a unique output directory and retain a separately verified source/package, code and output hash record before adoption.

## Adapter artifact policy versus current writer

A separately governed adapter is expected to supply `<strain>_6_optional_activity_predictions.csv`, `<strain>_6_optional_activity_predictions.json`, `optional_activity_prediction_manifest.json`, `optional_activity_prediction_validation.json`, and `SHA256SUMS.txt`. These are adapter deliverable requirements, **not artifacts automatically produced by the generic writer**. Do not infer that the five-file package exists from a successful JSON write. The adapter registry's `core_tier_influence: false` prevents policy declarations from authorizing changes to core tiers; it does not execute a model or certify its environment.

## Interpretation and model holds

`ab_score`/`af_score` and `ab_recall`/`af_recall` are routing/recall priors. `antibacterial_probability`/`antifungal_probability` are one named model's predictions, with that model's applicability, provenance and threshold. A model threshold is not cohort calibration. Agreement can prioritize review; it does not establish compound identity, production, activity, potency, mechanism or producer immunity.

Earlier policy names Walker–Clardy, DeepBGC, NPBDetect, BGC-MLM and PRISM as possible external channels. Those names are policy/research scope, not installed capability, an instruction to reimplement a model, or evidence of a validated adapter. Exact model/environment provenance and the owner's admission decision remain required. In particular, fragment and deterministic-inference holds remain unresolved by formatting a prediction document.

Source: `mamey/activity_predictions.py:94–202,246–290`. For measured context see [Bioactivity metadata](BIOACTIVITY_METADATA_CONTRACT.md).
