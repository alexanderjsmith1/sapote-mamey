# Bioactivity Metadata Contract

## Current portable contract

Bioactivity metadata is optional, typed strain-level context. It is not a named assay default, a BGC-level result, a production claim, or a scoring input.

The canonical object has `schema_version` `bioactivity_metadata_v1`, separate `metadata_state`, `observation_state`, and `usage_scope` fields, an `assays` list, and `compound_linkage` fixed to `NOT_ESTABLISHED` unless a separately governed workflow establishes another state. Omitting metadata produces `NOT_SUPPLIED`, `NOT_OBSERVED`, and an empty assay list.

Only three exact legacy input shapes are normalized: a scalar string, a dictionary with exactly `status`, `targets`, and `compound_linkage`, or a dictionary with exactly `status` and `targets`. Any other object or key combination is held as `BIOACTIVITY_LEGACY_SHAPE_HOLD`; the software must not guess a schema or recover arbitrary objects.

Receipt locators are checked structurally for portable grammar only. A release/privacy profile may independently allow or deny a structurally valid locator. `EXAMPLE_ONLY` metadata is not admitted to a production run. Metadata contributes zero wet-lab priority points under this contract.

## Migration boundary

The legacy `--bioactivity` scalar remains a compatibility input only. A nonempty scalar becomes `LEGACY_UNTYPED_CONTEXT`; an empty string becomes warned `NOT_SUPPLIED`. New callers should provide a typed object using `--bioactivity-json` or the direct API. No input form supplies a target name, positive result, or BGC linkage by omission.
