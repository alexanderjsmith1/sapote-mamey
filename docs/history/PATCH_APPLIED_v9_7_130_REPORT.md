# Patch applied — Sapote–Mamey v9.7.130

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

Command:

```bash
python3 -m pytest tests/test_bgc_decomp.py tests/test_tigrfam_extraction_consistency.py -v
```

Observed result:

```text
39 passed, 3 skipped in 0.39s
```

Skipped tests were live-fixture integrations that require local K_albida/SID-XXX packages not present in this sandbox.

## Notes

- I did not run the full test suite because only the targeted patch tests were requested and the live fixture packages are not mounted here.
- The expected patch spec text said `40 passed, 2 skipped`; the actual checked-in test file collects 42 tests here, with 39 passing and 3 skipping because K_albida has two live-fixture tests and SID-XXX has one live-fixture test.
- `mamey.__version__` remains engine `1.9.99`; bundle version is stored separately as `BUNDLE_VERSION = "9.7.130"` and `[tool.sapote].bundle_version = "9.7.130"`.
