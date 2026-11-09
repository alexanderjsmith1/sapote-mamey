# Patch applied — Sapote–Mamey v9.7.130

> **Historical page.** It is a record of one old patch, written as first-person notes from a sandbox. It is not an instruction and not a current test result. Current release status is in [RELEASE_MANIFEST](../../RELEASE_MANIFEST.md); changes are in [CHANGELOG](../../CHANGELOG.md).

Source bundle: `Sapote_Mamey_v9.7.129_TWO_MODEL_SYNCFIX_20260626(3).zip`
Patch spec: `PATCH_BGC_DECOMP_DOMAIN_EXPANSION_v9_7_130(2).md`

## Applied changes

- Replaced `mamey/bgc_decomp.py` with the v9.7.130 domain classifier expansion.
- Replaced `tests/test_bgc_decomp.py` with the expanded regression suite.
- Replaced `tests/test_tigrfam_extraction_consistency.py` with the expanded `KNOWN_NOT_EXTRACTED` guard.
- Updated `pyproject.toml` bundle version to `9.7.130`.
- Updated `BUILD_STAMP.txt` to build `20260626f`, engine `1.9.99`.
- Ran `tools/sync_version.py` and `tools/gen_release_manifest.py --apply`.
- Prepended the v9.7.130 changelog entry.

## Verification run in this sandbox

Historical: do not run the command below as a check of the current tree. It names test files as they were at v9.7.130. The report gives file names for its source and patch but no build digest, log or environment receipt, so the "Observed result" below is a reported result, unverified here. A build archive with the v9.7.130 stamp exists in the maintainer's archive (SHA-256 `503664e49a56147cb85bc5d3d32d80b20af68ae78d48c1a523a67b4a14f41530`); its stamp and file names alone do not tie it to this run.

Command:

```bash
python3 -m pytest tests/test_bgc_decomp.py tests/test_tigrfam_extraction_consistency.py -v
```

Observed result (as reported, not re-run):

```text
39 passed, 3 skipped in 0.39s
```

Skipped tests were live-fixture integrations that require local packages for two private fixtures not present in this sandbox.

## Notes

- I did not run the full test suite because only the targeted patch tests were requested and the live fixture packages are not mounted here.
- The expected patch spec text said `40 passed, 2 skipped`; the actual checked-in test file collects 42 tests here, with 39 passing and 3 skipping because the first fixture has two live-fixture tests and the second has one.
- `mamey.__version__` remains engine `1.9.99`; bundle version is stored separately as `BUNDLE_VERSION = "9.7.130"` and `[tool.sapote].bundle_version = "9.7.130"`.
