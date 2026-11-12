# Reference seed inputs — external-source policy

Small reference seeds and validation summaries may live here. **Heavy inputs do not.**

## What stays OUT of the bundle (external sidecars only)

- **Full real-strain antiSMASH ZIPs.** Keep these potentially large inputs as external
  sidecars, and keep unpublished or private sequences out of a public-facing cut.
  A strain label alone does not establish publication status or disclosure authority;
  use the exact input identity and admitted [privacy/evidence authority](../../docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md),
  retaining the applicable private guards. Approved inputs are passed to
  `domain-level --source-antismash` as an external path at run time, for example
  `python mamey_run.py domain-level --package <package> --source-antismash <antiSMASH.zip> --out <new folder>`.
  Without `--out` the tables are written inside the package. The archive is used only when its
  SHA-256 matches the package manifest's `input_zip_sha256`; see
  [domain-level Mode B](../../docs/modules/DOMAIN_LEVEL_MODE_B.md).
- **Full MIBiG dumps.** Raw GenBank dumps remain external. Engine reference-index consumers require a separately provisioned `mibig_reference_index.bacterial.json`; see the [external-assets guide](../../docs/EXTERNAL_ASSETS_GUIDE.md).

## What may live here

- Compact validation summaries (counts, not sequences).
- Exact-bound reference-panel manifests. Copy the shipped `reference_bgc_validation_manifest.template.tsv`
  to `reference_bgc_validation_manifest.tsv` and fill it in. Only the template ships.
- Structural reference-panel measurements in `reference_bgc_structural.csv`. The validator writes this file;
  see the [validator guide](../../docs/REFERENCE_BGC_STRUCTURAL_VALIDATOR.md).
- Synthetic or minimized fixtures for CI (see `tests/fixtures/`). Some are small subsets cut from
  public deposited genomes and named by their accession, such as
  `tests/fixtures/rggmci_public_VWPH00000000.1_subset.zip`. Only approved public subsets ship there;
  a full real-strain ZIP does not.
- Non-heavy metadata describing where external sidecars are expected.

The domain-level feature is built so that its CI path uses only the synthetic fixture; the
real strain evidence is reproduced manually from external sidecars, never from the repo.
