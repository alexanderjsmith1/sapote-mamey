# Reference fixtures: CI scope and source admission

This guide explains current test behavior; it is not an instruction to run antiSMASH, fetch genomes or add public sequence payloads. Keep source evidence in place with exact paths/hashes, and stage only approved minimal documentation or fixtures. Public database availability does not by itself authorize redistribution or establish an exact locus/answer key. See [external reference policy](../resources/reference_seed_inputs/README.md).

## What the reference-panel tests actually check

`tests/test_reference_panel.py:50–58` skips the entire module when its curated `mamey/data/reference_bgc_library.json` is absent. The .447 bundle includes that library; confirm its presence and hash in the selected extraction. A bundled library alone does not establish a test pass or external ZIP availability.

The module's integrity layer checks required fields, marker syntax, duplicate accession and recorded signature consistency. Concordance requires `MAMEY_REF_ZIPS` naming a directory of top-level `.zip` files; filenames are indexed by the test's accession regex, with the first matched ZIP retained for each key (`:71–83`). A ZIP filename alone is not proof of source or exact locus identity. No conftest default wires a bundled slice automatically.

Concordance selects the largest `obs_size_kb` parsed region from each matching ZIP and compares its computed markers to recorded `found_markers`, not to an independently verified `expected_marker_set` (`:141–162`). Adding arbitrary multi-region ZIPs or naming a file after an accession cannot establish that the intended reference region was tested. Missing ZIPs skip, not pass. These are regression checks against recorded observations, not independent sensitivity/specificity or biological/product validation.

## Ledger inspection and outputs

The ledger tool's positional interface is `python tools/reference_panel_ledger.py <selected-zips-directory> <fresh-output.csv>`, during a separately authorized execution task. It runs local extraction/source scans, so a documentation-only review must read its source instead. Correct output columns include `obs_region_type` and `cmp_t43_markers`; there is no `obs_t43_markers` field (`tools/reference_panel_ledger.py:115–117`).

The CLI discovers only top-level `.zip` filenames, catches individual archive errors and prints `skip`, returns normally with no output when no rows exist, and directly overwrites the selected CSV when rows exist (`:101–127`). A normal exit or a summary mentioning N ZIPs does not certify all N archives produced rows. Preserve original inputs and inspect logs, per-source rows, output counts and exact bindings. Use an existing permitted output directory and a fresh file path.

## Fixture adoption holds

Before adopting a real reference fixture, record exact accession/version, strain/contig/region/BGC identity, source archive/hash, admitted source subset and answer-key basis, software/cut versions and evaluated question. Record synthetic/minimized fixtures explicitly as such. Tests of synthetic annotation logic do not become observed biological evidence.

The old instruction to block every AS-shaped identifier through `test_no_unpublished_ids_in_public_tier` is obsolete: that test's current policy is not a universal AS-prefix ban. Exact privacy/source-disclosure policies and release review govern sharing. Neither prefix nor fixture size clears those gates. Record any CI/fixture change and its executed checks separately.

See [tests and gated coverage](../tests/README.md), [fixture index](../tests/fixtures/README.md) and [historical external-validation limitations](EXTERNAL_VALIDATION.md).
