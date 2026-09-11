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
