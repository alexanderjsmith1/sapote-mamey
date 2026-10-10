# Mode B Evidence-Escalation Workflow — v9.7.143a

## Current helper and review boundary

The original policy and transition table below remain intact. `mamey/modeb_evidence_state.py:44–76`
implements a pure transition validator returning a record; it does not mutate a source, open a locator,
hash source bytes, persist a ledger, authenticate its producer or scientifically adjudicate admission.
Evidence-bearing transitions require a nonempty locator and syntactically valid hash, which is different
from independently verifying that locator/hash against actual evidence. Same-state transitions still require
reason/binding, and SUPERSEDED still requires replacement_id. The table's transition rules match the helper.

Inspected production call sites import its vocabulary (`modeb_blastp.py`, `modeb_round.py`,
`modeb_publication_gate.py`); no production caller of transition_evidence was located. Thus the helper is
implemented, but the doc's “one machine-checked lifecycle” is not proof every stream runs through it.
Retain actual transition receipts and source verification separately; emitting queries remains UNBOUND.
Use the [profile matrix](MODEB_PROFILE_MATRIX.md), [contract/gate scope](MODEB_CONTRACT_HISTORY_AND_GATE_SCOPE.md)
and [support-card contract](MODE_B_SUPPORT_CARD_CONTRACT.md) for the selected route.

The final node-only regression bullets are historical incomplete identities, not current exact-locus
assignments or proof their scientific model was accepted. Obtain strain / full node-or-contig / region /
BGC alias and bound source evidence before reviewing any particular locus. Preserve contradictions,
conditional interpretations and holds rather than initiating new external jobs from those bullets.

<!-- Historical source text follows. -->

## When to escalate evidence

The evidence-escalation workflow applies when the
analysis sees large modular proteins, repeated comparator hits, possible
split/composite BGCs, or missing pathway parts, the system must guide the user to
the next decisive evidence step.

## Core rules

1. Every Mode B evidence table must include `protein_length_aa`.
2. Large proteins with small-enzyme labels must trigger a large-protein override.
3. Repeated comparator hits must trigger a comparator workflow card.
4. Split/composite BGCs must use conservative claim-safety labels.
5. Comparator axes must not be collapsed into one story without evidence.

## Executable evidence lifecycle

External escalation evidence uses one machine-checked lifecycle:

| Current | Permitted next state | Meaning |
|---|---|---|
| `UNBOUND` | `CONTEXT_ONLY`, `ADMITTED`, `ABSENT_IN_SCOPE`, `SUPERSEDED` | A request, query batch, path, or unverified result is not evidence admitted to the card. |
| `CONTEXT_ONLY` | `ADMITTED`, `SUPERSEDED` | Hash-bound evidence may orient interpretation but may not support the focal claim. |
| `ADMITTED` | `SUPERSEDED` | Hash-bound evidence is admitted for its explicitly stated claim scope. |
| `ABSENT_IN_SCOPE` | `SUPERSEDED` | The named stream is not available in the declared scope; absence is not a negative result. |
| `SUPERSEDED` | none | Terminal historical record; start a new record for replacement evidence. |

Idempotent same-state writes are allowed. `CONTEXT_ONLY` and `ADMITTED` require a source locator and
SHA-256. Every transition requires a reason. `SUPERSEDED` also requires a replacement or withdrawal
identifier. The implementation is `mamey.modeb_evidence_state.transition_evidence`; illegal transitions
raise typed `MODEB_EVIDENCE_TRANSITION_INVALID` errors. Emitting Mode B BLASTp FASTA batches remains
`UNBOUND`: query preparation is not a result and cannot promote an evidence stream.

## AS-XXX regression examples

- `NODE_24 + NODE_30` must trigger an NPDC041969 antiSMASH next-step card.
- `ctg24_2` at 4548 aa and `ctg30_19` at 4840 aa must not be read as small SDRs.
- `NODE_58` must remain separate from the NPDC041969 composite model.
