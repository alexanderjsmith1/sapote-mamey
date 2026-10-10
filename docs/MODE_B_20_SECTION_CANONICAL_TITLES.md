# MODE_B_20_SECTION_CANONICAL_TITLES.md — DEPRECATED (v9.7.150e+)

## Current entry and implementation scope

Select the actual task profile in [MODEB_PROFILE_MATRIX.md](MODEB_PROFILE_MATRIX.md),
then use [MODEB_CONTRACT_HISTORY_AND_GATE_SCOPE.md](MODEB_CONTRACT_HISTORY_AND_GATE_SCOPE.md)
for the owner/legacy boundaries. Preserve every individual locus as strain / full node-or-contig /
region / BGC alias from a bound source. A section count, phrase, typed label or zero-finding pattern
check is not scientific adjudication, independent source verification, owner acceptance or publication approval.
Existing evidence remains in place with path/SHA-256 bindings; use the selected candidate and retained
receipts rather than copying a package or inventing completed work.

This deprecated redirect is not one of the two outputs owned by `tools/regen_modeb_contract_docs.py`.
Its title list is historical and its full48-only routing sentence does not replace explicit current50-v2
selection. The historical 20-section JSON is retained for reference; the current compatibility facade
`mamey/validators/modeb_full20.py:30–65` derives its first twenty titles from the loaded default contract.
Preserve this redirect's history without making the facade a finished current-evidence acceptance gate.

<!-- Historical source text follows. -->

> **This file is retained as a redirect pointer only.** It listed §1–§20 titles
> when the contract was a §1–§20-only spec. The §1–§30 contract that replaced it
> is itself now the legacy `MODEB_CANDIDATE_30` profile.

## Read instead

- **`docs/MODE_B_USER_WALKTHROUGH.md`** — current profiles. Finished cards use
  `FINISHED_FULL48_CURRENT_EVIDENCE` (§1–§48); the §1–§30 pages below describe the legacy
  `MODEB_CANDIDATE_30` profile.
- **`docs/MODE_B_30_SECTION_CANONICAL_TITLES.md`** — legacy §1–§30 titles.
- **`docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md`** — full contract spec
  including conditional predicates and quality gate.

Both files are **generated** from
`mamey/data/mode_b/modeb_full30_corrective_contract.json` by
`tools/regen_modeb_contract_docs.py`. Do not edit the markdown by hand —
edit the JSON and re-run the regen tool. CI enforces this via
`python3 tools/regen_modeb_contract_docs.py --check`.

## Why this file is gone

Before v9.7.150e the bundle carried six separate §1–§20 schema sources:

1. `mamey/data/mode_b/modeb_full20_corrective_contract.json` (live read)
2. `mamey/data/mode_b/modeb_full30_corrective_contract.json` (live read)
3. `mamey/data/mode_b/legacy/modeb_full20_corrective_contract_legacy_v97144.json` (archival)
4. Hard-coded fallback list inside `mamey/validators/modeb_full20.py:30-52`
5. This file
6. `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md`

Any change to a §1–§20 title would have required editing all six. N10 (W9-C)
collapsed this surface: the JSON contract is now the single source, the
validator reads from it, the §1–§20 facade derives from it, and the markdown
docs are generated from it.

## If you need the §1–§20 historical contract

It's archived at
`mamey/data/mode_b/legacy/modeb_full20_corrective_contract_legacy_v97144.json`.
Nothing in the code reads it — it's kept for forensic reference only.
