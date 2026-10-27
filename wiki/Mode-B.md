# Mode B — the judgment-card system

*Start with [the Mode B document index](../docs/MODE_B_DOCUMENT_INDEX.md) and
[profile matrix](../docs/MODEB_PROFILE_MATRIX.md) in the selected bundle. Instructions are
deliberately spread across contract docs, implementation files, and tests, and the index is the
authoritative map. This page orients; it does not replace the contracts.*

## What a Mode B card is

Mode B is the **per-BGC interactive evidence-escalation workflow** — the structured deep-dive that
turns a triaged BGC into a written, gate-checked judgment card. It is explicitly *not* a static
BLASTp table: the card walks gene-level evidence, comparators, and alternatives, and every
interpretive statement carries OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER structure.
Cards are produced on demand from a **sealed** package (`mode-b` is a post-seal subcommand); the deterministic extraction is not rerun. Native `mode-b` authors post-seal output and
refreshes `post_seal_checksums.txt`, including when an external output directory is selected.
Use an authorized working package copy when original package bytes must remain unchanged.

## The section contracts

The card format grew through ratified contracts (each with canonical section titles and
validators): **§1–§10** core card with the §9/§10 gate → **§11–§20** enrichment floor →
**§1–§30** corrective-protocol format → **§1–§48** full depth, gate-enforceable since v9.7.369
("full48 gate binding"). Legacy priority/fragment floors are additional lexical
quality heuristics, not the selected finished-card definition. The full20 validator
is a compatibility facade derived from the first twenty default titles; it does
not verify a complete full48/current50 card. Native emission/verification defaults
to `--contract full48`; select `--contract current50_v2` consistently for that
opt-in profile. Verify the actual saved Markdown with the intended contract,
package and package-scoped alias, for example
`python mamey_run.py verify-modeb project/card.md --contract full48 --package project/package --bgc <package-scoped-alias>`.
Retain exact card/source hashes and invocation separately; warnings and receipt
PASS do not establish scientific review or complete source binding.
A template or generated top-leads table is not a finished card. The full48 exemplar is the phosphonate reference card
(`docs/reference/modeb_exemplars/`).

## Gene-first, not label-first

A card is written from the **per-CDS evidence** — gene functions, sec_met domains + E-values,
smCOGs — never from the antiSMASH product label. Guards encode hard-won lessons:
`mamey/mode_b/guards.py` returns large-protein/domain-review warnings from
length/title inputs. `mamey/mode_b/comparator_workflow.py` detects repeated
comparator-label patterns and drafts next-step guidance; it does not prevent
incorrect joins or verify comparator synteny. `mamey/mode_b/claim_safety.py`
classifies caller-supplied evidence booleans, not independently established
physical linkage. Keep proposed fragment relationships separate until the
source evidence is adjudicated; an RG-GMCI score is not permission to merge loci
(see [BLASTp-Novelty](BLASTp-Novelty.md)).

## Coverage honesty

For native `mode-b`, `--top-n` limits generated top-lead material. Its coverage
receipt records emitted/missing aliases relative to the supplied inventory;
`--strict-all` can return 2 after partial files have already been written. This
is not an audit of every saved authored card or its selected finished profile.

Source admission and promotion remain separate from gap-aware draft authoring.
The standalone `tools/modeb_evidence_gate.py` lints promotion language and
OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER terms; freshness is inferred
from text unless a caller supplies its boolean override. It does not independently
compute per-gene coverage or prove U = 0. Use actual channel/roster receipts and
[batch guidance](../docs/modules/MODE_B_BATCH_RUN.md), retaining evidence holds.

## Authoring hygiene

- **Context hygiene** (`MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md`): the LLM author gets minimal
  scientific context — no distribution stamps or packaging state that could leak into cards.
- **Status vocabulary is ratified** (`MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md`) — statuses are
  a controlled vocabulary, not free prose.
- **Stale cards are not evidence**: an on-disk card from an older engine must be verified against
  the current engine (or regenerated) before anything is built on it — the card carries its
  engine/bundle stamp for exactly this reason.
- **Domain-level add-on** (`docs/modules/DOMAIN_LEVEL_MODE_B.md`) adds architecture-confidence and
  domain-burden evidence with its own claim ceiling and safe/unsafe claim pairs.

## Where Mode B sits

```
sealed package ──▶ triage board (routing priors)
                        │
                         └─▶ selected-profile authoring (gap-aware draft or reviewed card)
                                 │  evidence admission + actual saved-card verification
                                 └─▶ separately selected compiled report + artifact/layout review
```

*Claim-safety: a Mode B card is the most interpretive artifact Tier 1 ever hosts, which is why it
is the most contract-bound — class-level hypotheses with explicit falsifiers, similarity never
identity, expression unknown without culture data.*
