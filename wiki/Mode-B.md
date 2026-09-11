# Mode B — the judgment-card system

*Source of truth: `docs/MODE_B_DOCUMENT_INDEX.md` in the current bundle — Mode B's instructions are
deliberately spread across contract docs, implementation files, and tests, and the index is the
authoritative map. This page orients; it does not replace the contracts.*

## What a Mode B card is

Mode B is the **per-BGC interactive evidence-escalation workflow** — the structured deep-dive that
turns a triaged BGC into a written, gate-checked judgment card. It is explicitly *not* a static
BLASTp table: the card walks gene-level evidence, comparators, and alternatives, and every
interpretive statement carries OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER structure.
Cards are produced on demand from a **sealed** package (`mode-b` is a post-seal subcommand); the
deterministic run is never altered by them.

## The section contracts

The card format grew through ratified contracts (each with canonical section titles and
validators): **§1–§10** core card with the §9/§10 gate → **§11–§20** enrichment floor →
**§1–§30** corrective-protocol format → **§1–§48** full depth, gate-enforceable since v9.7.369
("full48 gate binding"). Priority tier sets the depth floor; genuine fragments carry a documented
exemption rather than fake depth. `mamey/mode_b_quality_gate.py` checks section presence, length
floors, and enrichment blocks; `mamey/validators/modeb_full20.py` validates the corrective-protocol
sections. The exemplar for current authoring is the phosphonate full48 reference card
(`docs/reference/modeb_exemplars/`).

## Gene-first, not label-first

A card is written from the **per-CDS evidence** — gene functions, sec_met domains + E-values,
smCOGs — never from the antiSMASH product label. Guards encode hard-won lessons:
`mamey/mode_b/guards.py` catches huge modular proteins mislabelled as small enzymes;
`mamey/mode_b/comparator_workflow.py` detects repeated comparator hits and stops different loci
collapsing into one comparator's story; `mamey/mode_b/claim_safety.py` labels split/composite loci
conservatively. Split fragments are only merged on gene-confirmed COMPLEMENTARY_SPLIT evidence
(see [BLASTp-Novelty](BLASTp-Novelty.md)), never on an RG-GMCI score alone.

## Coverage honesty

`--top-n` is not full-inventory coverage — coverage receipts state exactly which BGCs have cards
and which do not, and `--strict-all` fails on missing cards rather than papering over them.
Promotion of an anchored lead requires its per-gene BLASTp channel fresh (U = 0 uncovered anchor
genes). Batch runs are rank-ordered with resume behavior and a compile gate
(`docs/modules/MODE_B_BATCH_RUN.md`).

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
                        └─▶ Mode B cards (per-BGC judgment, gate-checked)
                                 │  requires: fresh per-gene BLASTp (U=0), quality gate PASS
                                 └─▶ compiled report (locus map + class line + card = one page-unit)
```

*Claim-safety: a Mode B card is the most interpretive artifact Tier 1 ever hosts, which is why it
is the most contract-bound — class-level hypotheses with explicit falsifiers, similarity never
identity, expression unknown without culture data.*
