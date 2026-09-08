# Test suite — what runs and what is gated

Most tests run with no setup. A block of tests SKIP by design because they need local antiSMASH
outputs that are not shipped (they are large and/or strain-private). Skips here mean "gated," not
"broken."

## Always run
Engine logic, scans, scorers, schema, rules registry, claim-safety, redaction invariant
(`test_no_unpublished_ids_in_public_tier.py`), version/build-stamp drift, marker catalog parity.

## Gated (skip unless local data is present)
- `test_reference_panel.py` — signature concordance over the reference BGCs. Needs antiSMASH zips.
  Set `MAMEY_REF_ZIPS=/path/to/ref_zips`, or commit a small public slice (see
  `docs/CI_REFERENCE_FIXTURES_GUIDE.md`) so a live slice runs in CI.
- `test_boundary_live.py` and other *_live fixtures — need specific local antiSMASH outputs
  (e.g. philanthi / rifamycini).

## Run
    PYTHONPATH=... pytest tests/ -q
Skip count ≈ the gated set above; if a normally-green test starts skipping, that is a signal, not noise.
