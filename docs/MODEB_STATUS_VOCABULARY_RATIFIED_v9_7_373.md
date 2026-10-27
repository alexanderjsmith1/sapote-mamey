# Mode B status vocabulary: ratified mapping and current gate limits

This page preserves the status mapping recorded for the .373 patch queue on 21 August 2026
(`RATIFIED_STATUS_VOCABULARY_2026-08-21.md`). The retained record reports ratification of that mapping;
this page does not create a new approval. For a new card, choose the current [profile](MODEB_PROFILE_MATRIX.md),
then use the mapping below to keep document progress separate from evidence holds. The
[current implementation boundary](#current-implementation-boundary-mapping-retained) explains what the verifier checks.

## The problem it closes
Three status vocabularies were in use at once:
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

*Claim-safety: authoring-status vocabulary only; no science claims; judgment deferred. The project owner ratified this mapping.*

## Current implementation boundary (mapping retained)

The ratified mapping above is preserved as the dated governance record; this note does not change
its canonical terms or grant a new approval. The .373/.374 rollout notes are in
[history](history/MODEB_STATUS_VOCABULARY_373_ROLLOUT.md). Select the current
named profile and its actual producer/verifier; current50 v2 has its own FINISHED_FULL50_CURRENT50_V2
profile token and relocated evidence section.

The current full48 authored verifier tests recognized legacy/canonical finished tokens in its normalized
Markdown view to select stronger checks. That view also admits a recognized profile from the first-line
canonical Mode B metadata header. This is a routing signal: it does not independently prove exactly one
first-class document_state, validate every evidence_state list, reconstruct the eight-state history
or verify an owner’s approval. A saved label, alias-trigger or mechanical PASS cannot establish
MAINTAINER_ACCEPTED, INTEGRATION_APPROVED, RELEASE_APPROVED or PUBLICATION_APPROVED. Those require
the actual authorized owner record and bound reviewed bytes.

OBSERVED_UNBOUND/QUARANTINED rows can remain visible under the ratified two-axis policy, but supply no
admitted exact-gene/function evidence. They do not waive selected-profile readiness, complete matrix,
source/job binding, freshness or independent review requirements. Required evidence that is active,
attainable but unobtained or available but uningested remains a promotion hold; terminal limitations
need their typed reason and claim ceiling. Preserve the actual document state, evidence rows, selected
profile, gate findings and approval/hold receipts together rather than inferring them from filenames.
