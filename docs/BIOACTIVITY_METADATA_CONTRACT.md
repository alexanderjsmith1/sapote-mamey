# Bioactivity Metadata Contract

## Current portable contract

Bioactivity metadata is optional, typed strain-level context. It is not a named assay default, a BGC-level result, a production claim, or a scoring input.

The canonical object has `schema_version` `bioactivity_metadata_v1`, separate `metadata_state`, `observation_state`, and `usage_scope` fields, an `assays` list, and `compound_linkage` fixed to `NOT_ESTABLISHED`. A separately governed linkage workflow requires its own contract; it cannot supply an alternative linkage value to this schema. Omitting metadata produces `NOT_SUPPLIED`, `NOT_OBSERVED`, and an empty assay list.

Only three exact legacy input shapes are normalized: a scalar string, a dictionary with exactly `status`, `targets`, and `compound_linkage`, or a dictionary with exactly `status` and `targets`. Any other object or key combination is held as `BIOACTIVITY_LEGACY_SHAPE_HOLD`; the software must not guess a schema or recover arbitrary objects.

Receipt locators are checked structurally for portable grammar only. A release/privacy profile may independently allow or deny a structurally valid locator. `EXAMPLE_ONLY` metadata is not admitted to a production run. Metadata contributes zero wet-lab priority points under this contract.

## Migration boundary

The legacy `--bioactivity` scalar remains a compatibility input only. A nonempty scalar becomes `LEGACY_UNTYPED_CONTEXT`; an empty string becomes warned `NOT_SUPPLIED`. New callers should provide a typed object using `--bioactivity-json` or the direct API. No input form supplies a target name, positive result, or BGC linkage by omission.

## What the validator checks

The validator in `mamey/bioactivity_metadata.py` requires the six canonical keys, permits only `receipt_locator` and `warnings` as additional keys, checks schema and the three enums, requires `assays` to be a list, refuses nonempty assays for `NOT_SUPPLIED`, and rejects `EXAMPLE_ONLY` in production. It deep-copies admitted input. Receipt-locator validation checks portable syntax, not locator existence, referenced bytes, privacy or evidence authority.

The canonical validator requires `NOT_SUPPLIED` to use `NOT_OBSERVED`, `MEASURED_NEGATIVE` to use `NEGATIVE`, and `MEASURED_POSITIVE` to use `POSITIVE`. It rejects conflicting pairs and every `compound_linkage` value other than `NOT_ESTABLISHED`. The current strain-context schema has no alternative linkage-admission route.

It does **not** inspect individual assay entries, verify evidence hashes, validate warning-list element types, or constrain every remaining metadata/observation combination. So an object can pass with bad assay entries; review them yourself. Tests: `tests/test_lane04_bioactivity_state_claims.py`.

Keep strain/sample/material identity, target, time point, dose, missingness, source locator and evidence hash in the governed assay record. No absent field establishes a measurement, a negative result or linkage to a BGC. If an individual locus is mentioned, preserve strain / full node-or-contig / region / BGC alias; this strain-context validator does not perform that join.
