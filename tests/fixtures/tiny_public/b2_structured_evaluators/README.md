# Tiny public fixtures — B2 structured evaluators

Synthetic public fixtures for first-batch B2 structured evaluator cassettes.

These fixtures intentionally contain no private strain identifiers and no raw AS/SID strain data. They test deterministic support/caution logic for selected manual cassettes before any global Phase 2 backend activation.

The two CSVs are synthetic annotation-row inputs, not measured genomes, sequences, expression or activity. `tests/test_b2_structured_evaluators.py:22–103` checks deterministic status/support/caution and report-writing behavior from those rows; passing expected synthetic outputs does not validate biological sensitivity/specificity. The global-backend inactivity assertions are separate from evidence tests. Preserve fixture bytes and map any real evidence through its actual admitted reader rather than treating a synthetic row format as a universal result-ingestion interface.

These synthetic CSVs are evaluator fixtures; fixture existence does not establish an evaluator run. See [the fixture index](../../README.md).
