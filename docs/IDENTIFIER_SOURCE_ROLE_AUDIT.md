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

The initial proposal retains 57 public sites, binds 33 inputs from the accepted
seven-file fixture correction, and proposes 10 exact grammar-input sites in the
existing AST-identical grammar assertion function. These are 100 sites across
22 source files. Four queued fixture batches add 27 exact authored sites, giving
127 sites across 31 files: 57 public and 70 authored. The one table remains the
source of those bindings; no source spelling gains token-wide permission.

The original 223-site legacy inventory and the T06 changed-line ratchet are
separate. Before the queued fixture batches, integrated source had 147 original role holds
and 35 T06 lines. The H3/H5/H6 composition projects 145 role holds and 21 T06
lines; adding H9 projects 145 role holds and 14 T06 lines. These are conditional on owner adoption, not release
clearance. Genuine history and empirical examples remain authentic and held.

The shared candidate grammar also recognizes the underscore spelling in one
accepted fixture input. This expands detection, not permission: any other
unbound underscore occurrence is held. Registry membership or absence never
assigns a role. The existing explicit registry preflight remains mandatory and
separate; the role table pins the declaration list, reference catalog and identity-normalization owner.
The literal source grammar does not cover every runtime-generated label or every
identifier embedded after an underscore/escaped newline in Python source. Site
counts do not establish runtime, whole-artifact or disclosure coverage.

## Cut sequence

1. Before staging, validate the selected source table and capture its digest.
2. Audit staged test source with the same table and validator used by the source
   test. The table and reviewed source bytes must survive staging unchanged.
   Unlisted sites and declared spellings without artifact-specific roles are
   explicit holds. No source text or scientific record is rewritten by the audit.
3. Repeat the audit after staged pytest and documentation regeneration. The
   machine receipt binds the test subtree's bytes and namespace, including the
   policy table. The receipt parser checks schema, status, policy digest and
   snapshot digest; output writes must make verified progress.
4. Pass that snapshot digest to the finalizer. It must agree with the existing
   bound stage inventory before archive construction. The existing archive-vs-
   inventory and unchanged-stage checks then preserve that binding. Caches are
   excluded from the audit snapshot because the cut removes them; reintroduced
   test caches in final inventory are refused.

A private merged scaffold retains its separate route. A non-private cut cannot
launch the finalizer without a verified snapshot, even when no tests are staged:
that case has an explicit empty snapshot. The finalizer's optional standalone
argument is `--expected-test-source-sha256`; absent arguments preserve standalone
archive-parity behavior and do not establish public release permission.

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
