# Wheelhouse — your strain & scanner data store

The Wheelhouse is a self-contained folder inside the bundle for **your own** lab data: strain
records, scanner definitions, and validation evidence. It contains data plus a prototype helper module. It is distinct from lowercase `wheels/`, which holds Python build dependencies. Preserve selected bundle contents and stage personal data in a working copy; adding it to an archive does not authorize publication.

## Layout
- `strains/strain_registry.json` — one record per strain (genus, host, assembly, scanner hits, KCB
 anchors, known compounds, priority). Ships with one worked example (`HH130629`, the published
 selvamicin producer); add your own records alongside it.
- `scanners/` — the scanner registry (declarative gate rules) plus prior versions. A raw HMM domain
 hit is not a scanner hit: each scanner carries a cluster-level gate that must fire.
- `validations/` — scanner validation evidence. Ships with two public worked examples: the AJS327
 answer key (published UC San Diego chemistry) and the selvamicin validation.
- `engine/pyhmmer_scanner_engine.py` — prototype helpers for extracting region-CDS proteins and constructing HMMs. Its main block only prints “loaded”; it implements no scanning or registry-gate CLI. Imports require pyhmmer and Biopython; multi-sequence construction also imports pyfamsa.
- `hmm/scanner_pfam.hmm` — a possible provisioned 35-family HMM path; model payloads are not guaranteed to ship in this lean cut. Selector lists in `bundle_support/` are not HMM models.
- `reports/` — put generated cross-strain reports here.

## How to use / maintain
- **Add a strain:** append a record to `strains/strain_registry.json` (or drop scanner results in
 `validations/`).
- **Add a scanner:** append a rule to the current `scanners/scanner_registry_v*.json`.
- **Clean it:** `mamey wheelhouse clean --apply` removes all but the highest numeric registry version; it does not deduplicate strain records. Start with dry-run `python mamey_run.py wheelhouse clean` on a working copy; `--apply` deletes older registry JSON files.
- **List it:** `mamey wheelhouse list` summarizes strains + scanners + validations.

## Writes and provenance

`python mamey_run.py wheelhouse list` is an inventory, not a scan or validation. It can print an unreadable scanner registry and still return 0; model counts are hints from filenames, not measured model contents. HMM resolution uses explicit `SM_HMM_DB`, directory overrides, then bundle/add-on candidates; absent data yields tier `none` (`mamey/wheelhouse.py:57–124,149–172`).

`wheelhouse add-strain <record.json>` updates the bundle-local registry, replacing matching IDs, and writes JSON directly without an atomic transaction or backup (`:200–224`). The helper accepts an `id` record or ID-to-record mapping; a zero exit does not establish schema validity or scientific acceptance. Preserve the old registry before an authorized edit. Historical `test_status` fields and validation JSON require their original input/version/run receipts; listing them does not rerun or certify them.

See [scanner interface hold](reports/SCANNER_RUN_RECIPE.md), [external data](../docs/EXTERNAL_DATA.md) and [provisioning controls](../docs/447_COMPANION_RETRIEVAL_CONTROLS.md).
