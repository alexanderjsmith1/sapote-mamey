# TEST_PARTITIONS — ChatGPT-safe pytest slices

Use these named slices when a full `pytest tests/` run is too large for a capped chat session. Run from the bundle root with `PYTHONPATH=.`. These commands are kept to files present in this v9.7.144b quality-recheck candidate.

## P0_BOOTSTRAP

```bash
python -m pytest -q tests/test_cross_assistant_bootstrap_discoverability.py tests/test_bunny_hop_discoverability.py tests/test_chatgpt_start_here_current.py tests/test_chatgpt_safe_batch_profile.py tests/test_cli_version_flag.py tests/test_version_sync.py
```

## P1_RELEASE_HYGIENE

```bash
python -m pytest -q tests/test_release_zip_hygiene.py tests/test_public_cut_audit.py tests/test_no_stale_version_literals_v9795.py tests/test_no_brace_paths.py tests/test_no_dangling_examples_refs_v9795.py tests/test_v97133_bughunt_regressions.py
```

## P2_CLI_SMOKE

```bash
python -m pytest -q tests/test_cli_version_flag.py tests/test_release_surfacing_v9787.py tests/test_report_mode.py tests/test_inspector_commands.py
```

## P3_WORKBOOK_SCHEMA

```bash
python -m pytest -q tests/test_domain_workbook_v9789.py tests/test_merge_workbooks.py tests/test_mmw1_workbook_reporting.py tests/test_workbook_dedup.py tests/test_workbook_populated_sheet_gate.py tests/test_scoring_coverage_and_merge_policy.py tests/test_cohort_scoring_version_gate.py
```

## P4_SCIENCE_SCORING

```bash
python -m pytest -q tests/test_scan_scoring_bugfixes.py tests/test_ptm_af_scoring.py tests/test_cctt_uncorroborated_claim_gate.py tests/test_claim_safety_linter_gate.py
```

## P5_FIGURES

```bash
python -m pytest -q tests/test_render_figures_regression.py tests/test_mamey_native_figures_policy.py tests/test_sapote_figures_v9750.py tests/test_domain_figures_v9789.py tests/test_cohort_figures_v9792.py tests/test_cohort_figures_v9793.py
```

If the combined P5 slice exceeds a capped ChatGPT session, run the six files one at a time and record any timeout. In this quality recheck, `tests/test_cohort_figures_v9793.py` did not complete under the bounded session limit.

## P6_FULL_RELEASE

```bash
python -m pytest -q tests/
```

Record skipped tests and wall-clock limits in the release note if a capped session cannot complete P6.
