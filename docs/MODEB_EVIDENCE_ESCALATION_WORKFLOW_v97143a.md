# Mode B evidence-escalation workflow

## Current helper and review boundary

The original policy and transition table below remain intact. `transition_evidence` in `mamey/modeb_evidence_state.py`
implements a pure transition validator returning a record; it does not mutate a source, open a locator,
hash source bytes, persist a ledger, authenticate its producer or scientifically adjudicate admission.
Evidence-bearing transitions require a nonempty locator and syntactically valid hash, which is different
from independently verifying that locator/hash against actual evidence. Same-state transitions still require
reason/binding, and SUPERSEDED still requires replacement_id. The table's transition rules match the helper.

No command in the bundle calls `transition_evidence`. Some modules import its state names. The run
path does not enforce the lifecycle below: a caller may use the validator, and nothing requires it.
Keep your own transition records and source checks. Emitting queries remains UNBOUND.
Use the [profile matrix](MODEB_PROFILE_MATRIX.md), [contract/gate scope](MODEB_CONTRACT_HISTORY_AND_GATE_SCOPE.md)
and [support-card contract](MODE_B_SUPPORT_CARD_CONTRACT.md) for the selected route.

Obtain strain / full node-or-contig / region / BGC alias and bound source evidence before reviewing
any particular locus.

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

External escalation evidence follows this lifecycle. `transition_evidence` checks a single transition
against it when a caller uses it; no command enforces it:

| Current | Permitted next state | Meaning |
|---|---|---|
| `UNBOUND` | `CONTEXT_ONLY`, `ADMITTED`, `ABSENT_IN_SCOPE`, `SUPERSEDED` | A request, query batch, path, or unverified result is not evidence admitted to the card. |
| `CONTEXT_ONLY` | `ADMITTED`, `SUPERSEDED` | Hash-bound evidence may orient interpretation but may not support the focal claim. |
| `ADMITTED` | `SUPERSEDED` | Hash-bound evidence is admitted for its explicitly stated claim scope. |
| `ABSENT_IN_SCOPE` | `SUPERSEDED` | The named stream is not available in the declared scope; absence is not a negative result. |
| `SUPERSEDED` | none | Terminal historical record; start a new record for replacement evidence. |

Idempotent same-state writes are allowed. `CONTEXT_ONLY` and `ADMITTED` require a source locator and
SHA-256. Every transition requires a reason. `SUPERSEDED` also requires a replacement or withdrawal
identifier. Each of these must be a non-empty string; `None` or another type is refused. These are
syntax checks: the helper does not open the locator or compare the hash with any file. The implementation is `mamey.modeb_evidence_state.transition_evidence`; illegal transitions
raise typed `MODEB_EVIDENCE_TRANSITION_INVALID` errors. Emitting Mode B BLASTp FASTA batches remains
`UNBOUND`: query preparation is not a result and cannot promote an evidence stream.

