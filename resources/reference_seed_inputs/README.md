# Reference seed inputs — external-source policy

Small reference seeds and validation summaries may live here. **Heavy inputs do not.**

## What stays OUT of the bundle (external sidecars only)

- **Real strain antiSMASH zips** (any AS-/AJS-/PENDING- genome). These are
  20-80 MB each, contain unpublished data, and must never enter a public-facing cut. They are
  passed to `domain-level --source-antismash` as an external path at run time.
- **Full MIBiG dumps.** The bundle already carries a compact reference index under
  `mamey/data/mibig/`; raw MIBiG GenBank dumps are not vendored.

## What may live here

- Compact validation summaries (counts, not sequences).
- Exact-bound reference-panel manifests, using `reference_bgc_validation_manifest.tsv`
  and the shipped `.template.tsv` header as the portable contract.
- Structural reference-panel measurements in `reference_bgc_structural.csv`.
- Synthetic or minimized fixtures for CI (see `tests/fixtures/`).
- Non-heavy metadata describing where external sidecars are expected.

Generic Sapote-Mamey component and artifact names use `reference_bgc_*`. Collection
codes remain only when they are part of an actual strain designation or cited source
identity; they do not name or brand the validator.

The domain-level feature is built so that its CI path uses only the synthetic fixture; the
real strain evidence is reproduced manually from external sidecars, never from the repo.
