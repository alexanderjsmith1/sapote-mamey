# Wheelhouse — your strain & scanner data store

The Wheelhouse is a self-contained folder inside the bundle for **your own** lab data: strain
records, scanner definitions, and validation evidence. It is data, not pipeline code — edit the
files here, re-zip the bundle, and the data travels with it.

## Layout
- `strains/strain_registry.json` — one record per strain (genus, host, assembly, scanner hits, KCB
 anchors, known compounds, priority). Ships with one worked example (`HH130629`, the published
 selvamicin producer); add your own records alongside it.
- `scanners/` — the scanner registry (declarative gate rules) plus prior versions. A raw HMM domain
 hit is not a scanner hit: each scanner carries a cluster-level gate that must fire.
- `validations/` — scanner validation evidence. Ships with two public worked examples: the AJS327
 answer key (published UC San Diego chemistry) and the selvamicin validation.
- `engine/pyhmmer_scanner_engine.py` — the pyHMMER scanner engine (builds HMMs from discriminating
 domains, searches proteomes). Requires pyhmmer + pyfamsa.
- `hmm/scanner_pfam.hmm` — the core 35-family scanner HMM used by the pipeline.
- `reports/` — put generated cross-strain reports here.

## How to use / maintain
- **Add a strain:** append a record to `strains/strain_registry.json` (or drop scanner results in
 `validations/`).
- **Add a scanner:** append a rule to the current `scanners/scanner_registry_v*.json`.
- **Clean it:** `mamey wheelhouse clean --apply` prunes superseded scanner-registry versions and
 duplicate records.
- **List it:** `mamey wheelhouse list` summarizes strains + scanners + validations.
