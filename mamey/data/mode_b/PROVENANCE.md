# Mode B contract data provenance

`modeb_full30_corrective_contract.json` (schema_version `modeb_corrective_full48_v1`) is the single machine-readable section and artifact-drift contract for current prose-first Mode B cards. It defines the §1–§48 finished-deliverable profile and is the file loaded by `mamey/modeb_structure_gate.py`, the template emitter, and `tools/regen_modeb_contract_docs.py`. Note: the `full30` in the filename is historical (code and tests bind to that name); the authoritative section count is `schema_version` / the `sections[]` list, i.e. §1–§48.

Current policy: the §1–§48 titles are owned by that contract JSON and its generated doc (see `docs/CURRENT_DOCS_INDEX.md` for the canonical section doc). Assistants and renderers must not invent, rename, reorder, or substitute sections. Evidence tables are appendices/supporting material, not substitutes for the card body.

Legacy: the earlier standalone `modeb_full20_corrective_contract.json` (§1–§20) has been retired and now lives at `legacy/modeb_full20_corrective_contract_legacy_v97144.json`. It is an era record, not the live contract; do not cite it as current.
