# Optional external AB/AF activity-prediction channel

## Purpose

Sapote-Mamey may ingest or run compatible third-party models that predict antibacterial or antifungal
activity from BGC sequence-derived features. These results are optional post-seal evidence. They do not
replace Mamey's deterministic AB/AF routing priors.

## Output boundary

An adapter reads a sealed package and writes a sibling result directory. It must never write within,
rewrite, or re-seal the source package. The authoritative join key is:

`(strain, bgc_id, contig_region, model_id)`

Across-strain joins by `bgc_id` alone are prohibited.

## Required artifacts

- `<strain>_6_optional_activity_predictions.csv`
- `<strain>_6_optional_activity_predictions.json`
- `optional_activity_prediction_manifest.json`
- `optional_activity_prediction_validation.json`
- `SHA256SUMS.txt`

## Interpretation

| Field family | Meaning |
|---|---|
| `ab_score`, `af_score` | Transparent Mamey routing priors |
| `ab_recall`, `af_recall` | Guarded family-level antimicrobial recall priors |
| `antibacterial_probability`, `antifungal_probability` | One named external model's predicted probabilities |
| `reference_threshold` | Threshold distributed or reported with that model; not cohort calibration |
| `applicability_status` | Whether the model's input contract was met |
| `warning_codes` | Boundary, version, feature, truncation, or provenance limitations |

Agreement among channels may increase review priority. It does not establish compound identity,
production, activity, potency, mechanism, or producer immunity.

## Initial adapter policy

- Walker–Clardy: isolated optional adapter after exact model/environment pinning.
- DeepBGC: reproduce the domain-only method in current libraries rather than installing the legacy stack.
- NPBDetect: experimental until implementation and fragment perturbations are resolved.
- BGC-MLM: research-only until edge, length, padding, and deterministic inference gates pass.
- PRISM: ingest attributable user-supplied results; absence of a predicted structure is a channel-specific HOLD.

