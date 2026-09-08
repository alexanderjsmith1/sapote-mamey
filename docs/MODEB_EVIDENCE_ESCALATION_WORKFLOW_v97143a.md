# Mode B Evidence-Escalation Workflow — v9.7.143a

## What changed

Mode B now has a patchable workflow contract for evidence escalation. When the
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
