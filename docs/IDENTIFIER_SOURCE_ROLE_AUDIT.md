# Identifier roles in source and staged tests

`tools/identifier_source_roles.py` is the shared validator. The existing
`tests/reviewed_public_reference_sites.json` is the only source-site role table;
its historical filename is retained. Schema v2 includes public references and
reviewed authored inputs. `tests/_identifier_role_policy.py` is a compatibility
import, with no second validator or policy copy.

Each site binds a relative path, whole-file SHA-256, byte span, token and context
SHA-256, Python owner and lexical kind. Public reference spellings come from the
existing `tools/test_public_reference_tokens.json` catalog. An exact reference
cannot be borrowed for an identity field, alias or token continuation. Assignment
checks trace Name, Attribute and Subscript targets and corresponding nested
tuple/list positions. Computed selectors and opaque/starred unpacking retain a
public-role hold when the destination cannot be verified; a separate matched
product position stays public. Authored
input roles bind string literals to an existing canonical declaration and a
source-review provenance record. Comments/docstrings naming empirical or
historical cases cannot be admitted as authored input strings.

The role table declares 237 sites in 55 files: 57 public-reference sites (51 product,
6 organism) and 180 authored-fixture sites. Seven listed files have changed since their
hashes were pinned, and 23 sites fail token or context binding. Policy selection will
refuse until an owner re-reviews and rebinds them. Do not refresh role records automatically.

Older proposal counts and projected ratchet reductions describe their original
stages; they do not report the current table, runtime coverage or release clearance.

The literal source grammar includes underscore spellings but does not cover every
runtime-generated label or every identifier embedded after an underscore or escaped
newline. Detection is not permission. The role validator pins the declaration list,
reference catalog and identity-normalization owner; registry membership or absence
does not assign a source-site role (`tools/identifier_source_roles.py`).

In the current cut script, export-registry preflight is optional. Requesting any of
its four explicit options requires all four and their strict bindings; omitting them
emits `NOT_REQUESTED` with fixture/source disclosure clearance `NOT_EVALUATED`
(`tools/make_public_tier.sh`). Neither that diagnostic nor site counts
establishes runtime, whole-artifact or disclosure coverage.

## Role checks and cut snapshot binding

An explicitly requested source-role audit uses the shared validator and exact policy
table. Its receipt parser checks schema, scoped PASS state, policy digest and snapshot
digest; output writes must make verified progress (`tools/identifier_source_roles.py`).
This is distinct from the current cut script's independent test-byte snapshot:

1. After the non-private staged content audit and intentional omissions, the cut
   inventories the staged tree and binds its test subtree's bytes and namespace.
2. After staged pytest (or its explicit bypass) and cache cleanup, it repeats that
   snapshot and refuses drift. Snapshot construction excludes named cache paths and
   refuses them in final-inventory mode.
3. A non-private cut requires a verified snapshot before archive construction,
   including the explicit empty-test snapshot. It passes the digest to the finalizer,
   which compares it with its bound stage inventory before writing the archive.
4. Archive/inventory parity and the unchanged-stage check preserve that byte binding.
   They do not assign identifier roles or prove a source-role audit ran.

Owners: `tools/make_public_tier.sh`;
`tools/identifier_source_roles.py`; `tools/finalize_public_archive.py`.
The current cut route uses `test_source_snapshot` and `write_line`; it does not call
`audit_test_identifiers` or `validate_role_audit_receipt`. A private merged scaffold
retains its separate route. The finalizer's optional standalone argument is
`--expected-test-source-sha256`; omitting it preserves standalone archive parity
without establishing source-role or public-release permission.

The receipt reports `PASS_SOURCE_ROLE_SCOPE`, never a full release approval.
Binary test artifacts are counted as outside readable-source scope and remain
subject to the existing mandatory archive/privacy audits. Documentation,
external authorized public inputs, empirical artifacts, privacy-profile holds,
source integrity, canonical metadata and release governance retain their own
requirements. No list expansion, baseline refresh, private-family exception or
biological identity inference is made here.

Changes to source, role context, declaration list, catalog or table require
explicit owner review and new bindings. The cut does not regenerate permissive
role records. Known historical/empirical source cases remain unchanged and held
until their artifact disposition is selected. Runtime-generated test outputs
are not automatically granted roles by their fixture constructor's name.
