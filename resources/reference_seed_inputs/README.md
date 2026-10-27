# Reference seed inputs — external-source policy

Small reference seeds and validation summaries may live here. **Heavy inputs do not.**

## What stays OUT of the bundle (external sidecars only)

- **Real-strain antiSMASH ZIPs.** Keep these potentially large inputs as external
  sidecars, and keep unpublished or private sequences out of a public-facing cut.
  An `AS-` identifier alone does not establish publication status or disclosure authority;
  use the exact input identity and admitted [privacy/evidence authority](../../docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md),
  retaining the applicable private guards. Approved inputs are passed to
  `domain-level --source-antismash` as an external path at run time.
- **Full MIBiG dumps.** Raw GenBank dumps remain external. Engine reference-index consumers require a separately provisioned `mibig_reference_index.bacterial.json`; see the [external-assets guide](../../docs/EXTERNAL_ASSETS_GUIDE.md).

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
