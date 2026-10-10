## Current registry inputs and parity limits (.447)

Read-only ID census confirms the shipped JSON still has 156 unique IDs and CSV 151, with the same five JSON-only entries listed below and no CSV-only IDs. This verifies ID population only, not field equality, detector activity, marker validity or complete backend admission. JSON inventory presence is separate from actual active detector source; consult `mamey/registry_detector.py` and `source_scans.py`. The historical “not a blocker” decision applies to its named .140d research base and does not grant approval for a new versioned cut. Resolution remains an implementation/export-policy hold for the maintainers; no registry evidence was modified.

## Registry-ID checker scope

Request `tools/check_registry_ids_unique.py` to screen exact extracted IDs for duplicates within each selected JSON or CSV file. Run from the selected bundle root and supply the intended paths explicitly, for example:

```bash
python tools/check_registry_ids_unique.py '<selected-registry.json>' '<selected-export.csv>'
```

With no paths, its default is the working-directory-relative `bundle_support/registry_inventory_v1.9.4.json`; it does not locate or scan all registries automatically. Missing files, unsupported suffixes and recognized reader errors are reported with exit 1. Exact duplicate IDs also produce exit 1; no such finding produces exit 0. Multiple paths are checked independently, so matching IDs across files are not treated as collisions and the command does not compare populations or fields for parity (`tools/check_registry_ids_unique.py:45–64`).

JSON accepts a top-level list, otherwise selects `entries` ahead of `inventory`. It retains only dictionary entries with truthy `id` values. Missing inventory keys, some malformed container shapes and omitted/blank IDs can therefore produce “unique (0 IDs)” rather than an admission failure. CSV requires an `id` header but permits a header-only file and skips blank ID values. Repeated `id` column names are not refused: the CSV reader keeps the last value under that key, potentially hiding duplicates in an earlier column. Reconcile every source row, container/header shape, omitted ID and intended denominator before relying on the reported ID count (`:16–42`).

IDs are compared as supplied, without string-type, prefix, whitespace or canonical-identity validation. JSON truthy numeric/boolean values can enter the counter, and an array/object ID can raise during counting outside the reader-error catch. Treat an interrupted command as incomplete, retain diagnostics and resolve the input issue before rerunning. Any normalization must use the registry owner's policy and preserve the original values; do not silently rewrite identifiers to clear a finding (`:26–27,53–58`).

The checker reads files without modifying them and emits terminal diagnostics only. There is no saved source/hash receipt, exclusion roster, cross-file parity report, detector-admission check or release authorization. Preserve exact input hashes, selected paths, full diagnostics and exit status in a fresh disjoint receipt; perform population/field parity and active-backend checks separately. A “unique” result does not establish a nonempty, complete or scientifically valid registry.

The original carry-forward note follows unchanged.

---

# Registry JSON/CSV parity note — v9.7.141

## Status

This is a documented carry-forward note from the v9.7.140d sign-off.

The registry inventory has **unique IDs in both formats**, but the JSON and CSV surfaces are not perfectly parallel:

- `bundle_support/registry_inventory_v1.9.4.json`: 156 unique IDs
- `bundle_support/registry_inventory_v1.9.4.csv`: 151 unique IDs
- JSON-only IDs: `MMK-CCTT-015`, `MMK-CCTT-016`, `MMK-CCTT-017`, `MMK-CCTT-018`, `MMK-CCTT-019`
- CSV-only IDs: none

## Interpretation

This is **not a uniqueness failure** and it is **not a blocker** for the v9.7.140d research base. It is a parity/documentation gap: five JSON registry entries are not represented in the CSV export.

## Risk

Tools or reviewers that treat the CSV as the complete registry will miss the five JSON-only `MMK-CCTT-*` entries. Tools that read the JSON see all 156 IDs.

## v9.7.141 follow-up

Before this note can be closed, choose one of these policies and encode it in a test:

1. **Strict parity:** CSV must include all JSON IDs.
2. **Intentional subset:** CSV is a documented public/export subset, and JSON-only IDs must be listed in an explicit allowlist with rationale.
3. **Generated CSV:** regenerate the CSV directly from JSON so parity is automatic.

Recommended test name: `test_registry_json_csv_parity_policy`.

## Claim-safety

Until resolved, cite the JSON registry as the authoritative complete registry and describe the CSV as a tabular export surface, not as the complete registry.
