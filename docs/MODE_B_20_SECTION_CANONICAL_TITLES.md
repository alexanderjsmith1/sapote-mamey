# MODE_B_20_SECTION_CANONICAL_TITLES.md — DEPRECATED (v9.7.150e+)

> **This file is retained as a redirect pointer only.** It listed §1–§20 titles
> when the contract was a §1–§20-only spec. The current canonical contract is
> §1–§30, with §28 and §30 mandatory and §21–§27/§29 conditional.

## Read instead

- **`docs/MODE_B_30_SECTION_CANONICAL_TITLES.md`** — current canonical titles.
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
