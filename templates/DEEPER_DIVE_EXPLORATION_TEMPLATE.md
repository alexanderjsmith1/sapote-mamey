# Deeper-dive exploration — `<STRAIN> <BGC_ID>`

*Per-lead deep evidence synthesis. Deterministic fields are assembled from the sealed package
(inventory, MIBiG convergence, structured antiSMASH tables, BLASTp panel). Judgment fields are
explicit stubs for Sapote / wet-lab. Capacity-level, claim-safe: comparator compounds are
class-level hypotheses, not identified products; no activity/structure claim beyond the evidence.*

## Executive verdict
`<One paragraph: strongest architecture, convergence tier, direct-query coverage, principal limitation, and the maximum defensible statement.>`

## 1. Source lock and locus identity
| Item | Audited source | Result |
|---|---|---|
| Manifest | `<package>/manifest.json` | `<engine version, assembly tier, release>` |
| Crosswalk | `<package>/<crosswalk.csv>` | `<BGC → contig, region, coordinates, boundary>` |

## 2. Observed physical architecture
`<Domain/module inventory (antiSMASH facts): core biosynthetic genes, tailoring, transport, regulation. From the structured module + HMM tables. State counts, not products.>`

## 3. Cluster-comparison evidence
`<Per-gene MIBiG convergence: dominant comparator, distinct query genes, median identity/coverage, best reference rank, class concordance, convergence tier (H1..H5 / CAUTION). Note KCB and convergence derive from the same antiSMASH channel — not independent replication.>`

## 4. Integrated reading
`<The single most defensible reading of the locus: e.g. "a <family>-related biosynthetic cassette," with boundary-aware completeness. This is the deterministic synthesis, not a product call.>`

## 5. Competing explanation
`<The strongest alternative(s): over-merged/neighboring protocluster, edge-truncation lower bound, mis-anchor, primary-metabolism confound. Why each is or is not resolved.>`

## 6. Missing evidence and next decision
`<What would discriminate: all-CDS BLASTp completeness, gene-order/core-completeness vs the cited MIBiG locus, targeted MS/MS. The next single most informative step.>`

## 7. Value tier and safe use
- **Value tier:** `<THESIS_READY | USEFUL_WITH_LIMITATIONS | CONTEXT_ONLY | HOLD>`
- **Safe use:** `<the maximum defensible capacity-level statement + explicit exclusions>`
- **Claim ceiling:** `<no production/activity/novelty/structure/cross-contig-linkage claim>`

## 8. QA receipt
- Support card: `<PRESENT | MISSING>` · gene-level card gate: `<PASS | NOT_VERIFIED>`
- Independent all-CDS BLASTp completeness: `<VERIFIED_COMPLETE | NOT_VERIFIED_COMPLETE>`
- Source receipts: `<the exact package files this card was assembled from>`
