# Committing public type-strain fixtures so the reference panel runs in CI

Today every `tests/test_reference_panel.py` concordance parametrization SKIPS unless
`MAMEY_REF_ZIPS` points at local antiSMASH zips. So the headline pass count does **not** exercise
any signature concordance — the green panel only exists on your laptop. Commit a small slice of
PUBLIC type-strain zips so a live concordance check runs in CI.

## What to commit (PUBLIC ONLY — hard guard)
Pick 2–3 reference BGCs already in the panel whose source genome is a public type strain, e.g.:
- a positive control with a clear signature (e.g. the *Nonomuraea* sp. ATCC 55076 kistamicin run
  used as your prospective-validation positive control),
- one halogenase-bearing entry (a T43-HAL true positive),
- the documented T43-negative control (e.g. 2'-chloropentostatin or piericidin).

Do **not** use any AS-### strain — fixtures live in the public repo.

## How to make each fixture small
antiSMASH output is large; the panel ledger only needs the regions JSON (+ optional region GBK). Per strain:
1. Run antiSMASH on the public genome locally (the bundle does not run it).
2. Keep only the region(s) of interest:
   ```
   zip -j tests/fixtures/ref_zips/<name>.zip <antismash_out>/*.region0NN.gbk <antismash_out>/<name>.json
   ```
   Aim for well under 1 MB per zip (drop the full-genome GBK).
3. Verify the ledger reads it (CLI is `reference_panel_ledger.py <zips_dir> <out.csv>`):
   ```
   python tools/reference_panel_ledger.py tests/fixtures/ref_zips /tmp/led.csv
   ```
   Confirm `obs_region_type` / `obs_t43_markers` populate.

## Wiring it into CI
The panel test reads zips from `MAMEY_REF_ZIPS`. Add a conftest default so committed fixtures are
used when the env var is unset:
```python
# tests/conftest.py
import os, pathlib
_FIX = pathlib.Path(__file__).parent / "fixtures" / "ref_zips"
if not os.environ.get("MAMEY_REF_ZIPS") and _FIX.is_dir():
    os.environ["MAMEY_REF_ZIPS"] = str(_FIX)
```
Now the 2–3 committed references parametrize and run a live concordance slice in CI; the rest still
skip unless you point `MAMEY_REF_ZIPS` at the full local set. Even 3 exercised beats 74 skipped.

## Guard
Add nothing under `fixtures/` that derives from an unpublished AS strain. The
`test_no_unpublished_ids_in_public_tier` invariant fails the build if an AS-### slips in — but keep
the fixtures public by construction.
