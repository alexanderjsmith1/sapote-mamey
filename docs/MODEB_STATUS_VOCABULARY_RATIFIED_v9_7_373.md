# RATIFIED status vocabulary — Sapote-Mamey Mode B (the Developer or User ratification 2026-08-21)

*the Developer or User ratified the mapping table (green-light on the vocabulary-reconciliation path, 2026-08-21).
This is the single authority that resolves the three status vocabularies that were in flight; every
.373-and-later Mode-B card and gate keys on it. the patch lane records; the Developer or User ratified. Folded into the
bundle at v9.7.373 from the `.373` patch queue (`RATIFIED_STATUS_VOCABULARY_2026-08-21.md`).*

## The problem it closes
Three status vocabularies were live at once and would have shipped a fourth if the Codex Full48
spec were implemented as-written:
1. **Legacy** — `FINISHED_CURRENT_EVIDENCE`, the literal trigger token of the .372 matrix gate.
2. **Protocol §4 ladder** — the 8-state dual-writer/dual-auditor document ladder (ships in .372).
3. **Full48 spec** — `document_state` (SCAFFOLD | CANDIDATE | FINISHED_CURRENT_EVIDENCE) plus an
   `evidence_state` typed-holds axis, and the strict profile name `FINISHED_FULL48_CURRENT_EVIDENCE`.

## The ratified mapping (authority)

| Concept | Canonical term | Carries | Notes |
|---|---|---|---|
| **Strict finished profile** | `FINISHED_FULL48_CURRENT_EVIDENCE` | the gate trigger | the spec's name becomes the one finished-profile trigger |
| **Document ladder** (one axis) | the protocol §4 **8-state ladder** | `document_state` field | `SOURCE_INVENTORY_ONLY → DRAFT_NOT_RECONCILED → EVIDENCE_RECONCILED_CANDIDATE → INDEPENDENT_CONTENT_QA_PASSED_CANDIDATE → MAINTAINER_ACCEPTED → …`; bans `finished`-as-adjective states |
| **Evidence holds** (second axis) | `evidence_state` typed list | per-gene / per-stream | the spec's second axis; maps to the retention-ledger dispositions incl. the .373 `OBSERVED_UNBOUND` / `QUARANTINED` states from the sequence-first patch |
| **Legacy token** | `FINISHED_CURRENT_EVIDENCE` | grandfathered **alias** → `FINISHED_FULL48_CURRENT_EVIDENCE` trigger | resolves the .372 trigger-token conflict in the same stroke; existing cards using it keep validating |
| **Mechanical gate ceiling** | `EVIDENCE_MATRIX_VALIDATED` | deterministic states only | unchanged from .372; `RELEASE_READY` stays retired; no mechanical state ever says RELEASE/PUBLICATION |

## Two axes, not one
A card carries **exactly one** `document_state` (where it is in the authoring ladder) **and** a list
of `evidence_state` holds (what evidence is bound / observed-unbound / quarantined). These are
orthogonal: a `FINISHED_FULL48_CURRENT_EVIDENCE` card can still carry `OBSERVED_UNBOUND` evidence
rows — finished means *the reconciliation and contract are complete for the current evidence*, not
that every channel is bound.

## How the .373 sequence-first patch slots in
The admitted Codex sequence-first patch introduces `OBSERVED_UNBOUND` / `QUARANTINED` / admitted as
**evidence_state** values (not document_state). They are the typed holds for a BLASTp row that has a
result but not a bound (query-hash + exact-locus + channel + receipt) join. This ratification places
them on the evidence axis, so they never collide with the document ladder.

## What .373 implements vs defers
- **Implemented in .373 (engine 1.9.126):** the legacy token is honoured as an alias-trigger by the
  finished-profile check wired in `mamey/authored_verify.py` (B1) — a card carrying either
  `FINISHED_FULL48_CURRENT_EVIDENCE` or the legacy `FINISHED_CURRENT_EVIDENCE` activates the
  publication gate. The mechanical ceiling `EVIDENCE_MATRIX_VALIDATED` is unchanged.
- **Deferred to .374 (engine-bump):** the full Full48 named-profiles implementation
  (schema/emitter/gates emitting `document_state` + `evidence_state` as first-class fields) — it
  changes emitted output and warrants its own bump. Tracked with the sequence-first coded
  receipt-binding enforcement, which waits on the BLASTp-lane store schema migration
  (`hits` lacks `query_hash`/`result_job_receipt` columns).

*Claim-safety: authoring-status vocabulary only; no science claims; judgment deferred. the Developer or User ratified;
the patch lane records.*
