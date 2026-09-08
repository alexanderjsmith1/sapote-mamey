# Mode-B integration supplement — `<STRAIN> <BGC_ID>`

*Cross-layer integration of a Mode-B card with per-gene MIBiG convergence, structured antiSMASH
tables (modules / RiPP / motif / RRE-Finder / HMM), and any BLASTp panel. Reconciles the layers
into one claim-safe reading. Deterministic where sourced; judgment is an explicit stub.
Capacity-level, claim-safe — comparators are class-level hypotheses, not identified products.*

## Integration disposition
- **Card:** `<card_id>` · **Value tier:** `<tier>` · **Layers reconciled:** `<mode-b | convergence | structured | blastp>`
- **Agreement:** `<do the layers agree, partially agree, or conflict?>`

## Integrated interpretation
`<The single reading supported by ALL available layers together — e.g. "a <family>-related cassette with <RiPP/PKS/NRPS> architecture, boundary <interior/edge>." Deterministic synthesis, not a product identification.>`

## Evidence-layer reconciliation
| Layer | What it shows | Weight |
|---|---|---|
| antiSMASH class / architecture | `<class, core/tailoring domain counts>` | fact (annotation) |
| Per-gene MIBiG convergence | `<comparator, genes, %id/%cov, tier>` | family relatedness (same channel as KCB) |
| Structured RiPP / HMM | `<RRE-Finder / PFAM / TIGRFAM diagnostics>` | capacity evidence |
| BLASTp panel | `<coverage, top-hit provenance>` | per-gene homology |

`<Note explicitly where layers reinforce vs. where one is not independent replication of another.>`

## Claim-safe thesis sentence
`<One sentence usable in a manuscript: "The data support a <family>-related biosynthetic cassette in <strain> <BGC>; exact product, activity, and completeness remain to be tested." No production/activity claim.>`

## Next discriminating evidence
`<The single most informative next step across layers: all-CDS BLASTp, core-completeness vs the cited MIBiG locus, MS/MS, or an assembly fix if edge-truncated.>`

## Preserved limits
- `<Edge/boundary lower-bound; over-merge risk; mis-anchor/primary-metabolism guards; cohort-recurrence as evidence AGAINST premature novelty language.>`

## Source receipts
`<The exact package files each layer was read from — inventory, mibig_convergence, antismash_structured/hmm, blastp panel.>`

## Claim ceiling
`<Maximum defensible statement + explicit exclusions: no exact structure, no bioactivity, no expression, no novelty, no cross-contig physical linkage.>`
