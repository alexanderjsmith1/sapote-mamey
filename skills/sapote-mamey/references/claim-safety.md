# Claim-Safety Field Card

A normative claim-language field card; the implemented linters cover a narrower heuristic subset. When writing any interpretive text (Mode B cards, synopses, lay guides, ecological synthesis), these are the substitutions and rules. Use the selected authored-card `python mamey_run.py claim-safety <file> --package <pkg> --mode warn --json` front door from the bundle root. Retain findings; warn exits zero with findings, and CSV persistence requires --report. This card and a clean heuristic result do not replace source/content review.

## The core substitution: capacity, not production

| Don't write | Write instead |
|---|---|
| "produces kirromycin" | "biosynthetic **capacity consistent with** a kirromycin-like compound" |
| "the strain makes an enediyne" | "carries a BGC with **capacity consistent with** an enediyne-class product" |
| "this cluster synthesizes X" | "the cluster's architecture is **consistent with** X-like biosynthesis" |

A BGC's presence is **capacity**, not phenotype. The linter's `_SAFE_AFTER_PRODUCES` allowlist is narrow — assume "produces X" is a violation unless X is an allowlisted architectural term.

## Similarity, not identity

- Keep measured sequence identity distinct from compound identity. "72% identity to subject Y" describes an alignment; it does not establish the product made by the query strain.
- Preserve exact reported metrics and denominators in evidence records. Use `mamey.precision` for appropriately rounded/banded narrative summaries without replacing the underlying measurements.
- A KCB hit names a *reference compound the cluster resembles*, not the strain's product.

## Bioactivity stays at the extract level

- Bind bioactivity (inhibition, zones, MICs) to the material actually assayed. Strain/extract evidence alone does not support BGC attribution; stronger admitted experimental evidence permits only the specific link it establishes.
- An individual locus needs its complete source-bound four-part identity. Do not attribute an assayed effect to that locus without admitted linkage evidence; identify the actual assayed material and supported scope.

## Provenance and citation

- **Display every individual locus as strain / full node-or-contig / region / BGC alias**, copied from one admitted source record. A shortened NODE token or NODE·region alone is incomplete. Hold missing/conflicting components.
- **Tag provenance** on every non-trivial claim: `store-backed` (from the banked store), `reconstructed` (assembled/tiled from fragments — a hypothesis, not a contig join), or `corpus` (from the reference corpus).
- A **reconstruction is a hypothesis**, never a contig join and never product identity.
- **Reconcile BGC numbering across sources before authoring.** antiSMASH, the store, and the corpus can number differently. Flag any ID collision explicitly; don't silently pick one.

## The fabrication line — never cross it

- **Every selected-profile per-gene BLASTp row (default §4; current50 v2 §50) must trace to a real result.** No templated, inferred, or plausible-sounding observations. The phantom-locus incident put fabricated per-gene observations into 74+ cards across strains — the correctness gates (`PHANTOM_LOCUS`, `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`) exist because of it.
- If a value isn't in a real result, it does not appear in the card — not even to fill a required slot. Use the selected profile’s explicit typed state/hold with its reason, never an invented observation or a blank substituted for a required state.
- Consult the actual evidence file (e.g. the strain's `*_online_blastp.csv`) to learn **which organism** a hit belongs to; don't infer it.

## Retractions

- If new evidence overturns a claim, **retract it plainly** and move on. State what changed. No hedging, no burying it.

## Signals that you're about to violate the rule

- You're reaching for "produces / makes / synthesizes" + a named compound → stop, rewrite as capacity.
- You're about to state a % as if it settles identity → retain the actual metric/denominator and limit the claim; rounding alone does not repair unsupported identity.
- You're filling a selected-profile evidence row from memory or inference rather than a result file → stop; use the selected explicit typed hold and reason.
- You're attributing extract bioactivity to one BGC → stop; keep it extract-level.

*Authoritative enforcement: `mamey/mode_b/claim_safety.py`, `mamey/claim_safety_gate.py`, `tools/claim_safety_linter.py`. Audit rubric: `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`.*

Authored-card CLI, package claim gate and split/composite helpers are different owners/check scopes. The historical extraction-card audit rubric is not a complete full48/current50 content validator. All external retrieval, audits and writes remain within the actual user task; reading this reference is not execution permission.
