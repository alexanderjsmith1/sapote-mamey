# Claim-Safety Field Card

The one-page version of the discipline the `claim_safety_linter` enforces. When writing any interpretive text (Mode B cards, synopses, lay guides, ecological synthesis), these are the substitutions and rules. **Run `tools/claim_safety_linter.py` on the output — this card is for getting it right the first time, not a substitute for the gate.**

## The core substitution: capacity, not production

| Don't write | Write instead |
|---|---|
| "produces kirromycin" | "biosynthetic **capacity consistent with** a kirromycin-like compound" |
| "the strain makes an enediyne" | "carries a BGC with **capacity consistent with** an enediyne-class product" |
| "this cluster synthesizes X" | "the cluster's architecture is **consistent with** X-like biosynthesis" |

A BGC's presence is **capacity**, not phenotype. The linter's `_SAFE_AFTER_PRODUCES` allowlist is narrow — assume "produces X" is a violation unless X is an allowlisted architectural term.

## Similarity, not identity

- KCB and BLASTp report **similarity**, never identity. "72% identity to subject Y" describes an alignment, not that the query *is* Y.
- Route every percentage through `mamey.precision` — it coarsens to bands and attaches the "similarity, not identity" disclaimer. Never ship a bare over-precise figure.
- A KCB hit names a *reference compound the cluster resembles*, not the strain's product.

## Bioactivity stays at the extract level

- Bioactivity (MRSA / *Candida* inhibition, zones, MICs) is a property of a **crude extract**, never of a single BGC.
- Never write "BGC008 is responsible for the anti-MRSA activity." The extract inhibits; which BGC is responsible is unknown unless proven.

## Provenance and citation

- **Cite every BGC by NODE·region** (`NODE_12·region3`), never a bare running index.
- **Tag provenance** on every non-trivial claim: `store-backed` (from the banked store), `reconstructed` (assembled/tiled from fragments — a hypothesis, not a contig join), or `corpus` (from the reference corpus).
- A **reconstruction is a hypothesis**, never a contig join and never product identity.
- **Reconcile BGC numbering across sources before authoring.** antiSMASH, the store, and the corpus can number differently. Flag any ID collision explicitly; don't silently pick one.

## The fabrication line — never cross it

- **Every §4 per-gene BLASTp row must trace to a real result.** No templated, inferred, or plausible-sounding observations. The phantom-locus incident put fabricated per-gene observations into 74+ cards across strains — the correctness gates (`PHANTOM_LOCUS`, `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`) exist because of it.
- If a value isn't in a real result, it does not appear in the card — not even to fill a required slot. A blank with a stated reason beats an invention.
- Consult the actual evidence file (e.g. the strain's `*_online_blastp.csv`) to learn **which organism** a hit belongs to; don't infer it.

## Retractions

- If new evidence overturns a claim, **retract it plainly** and move on. State what changed. No hedging, no burying it.

## Signals that you're about to violate the rule

- You're reaching for "produces / makes / synthesizes" + a named compound → stop, rewrite as capacity.
- You're about to state a % as if it settles identity → coarsen and disclaim.
- You're filling a §4 row from memory or inference rather than a result file → stop; leave it blank with a reason.
- You're attributing extract bioactivity to one BGC → stop; keep it extract-level.

*Authoritative enforcement: `mamey/mode_b/claim_safety.py`, `mamey/claim_safety_gate.py`, `tools/claim_safety_linter.py`. Audit rubric: `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`.*
