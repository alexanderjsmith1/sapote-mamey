# REPAIR_SPEC_Q-018 — FF402-SCI-01B-F13R genus-faceted BGC domain-count ordination

## Status

- Queue: FF402-Q-018, priority P1, status REPAIR_FIRST.
- Repair surface: perceptually distinct categorical genera plus redundant encoding, and the
  exact ten-feature log1p-centered SVD methods/loadings block.
- Disposition: `RETAIN_AND_REDESIGN` (per the parent renderer-policy addendum). No frozen-proof
  mutation, delegated presentation, or render is authorized by this spec.

## Exact source field(s) — PARTIALLY BOUND

- **Feature count**: exactly ten features (addendum, verbatim: "the exact ten-feature input").
  The identity of the ten fields themselves is not named in the addendum or queue row — owner
  binding required.
- **Transformation**: log1p, then centering with **no scaling**, then SVD (addendum, verbatim:
  "log1p transformation, centering/no-scaling SVD"). This is a bound methodological requirement,
  not a candidate's free choice — a candidate that scales the features, or skips the log1p step,
  fails this spec regardless of the ten fields' identity.
- **Genus source**: must be a source the same as, or reconciled with, the authoritative
  strain/genus roster this bundle already tracks elsewhere (see `REPAIR_SPEC_Q-014_F15.md`'s
  identical requirement for its label roster) — a candidate must name which source it reads.

## Denominator — NOT YET BOUND (owner binding required)

The "fitting subset" (which BGCs/strains the SVD is actually fit against) is required to be
stated per the addendum's methods-block list, but no specific subset is named anywhere in the
queue row or addendum. Owner binding required.

## Exclusions / defaults

- Missing-value handling must be stated explicitly and applied consistently — the addendum lists
  it as a mandatory methods element; this spec does not choose a default (e.g. row-drop vs.
  imputation) on the owner's behalf.
- A compact loading interpretation, biplot, or interactive companion "must not overstate
  biological separation" (addendum, verbatim) — any prose accompanying the ordination must stay
  within what PCA/SVD axes and distances can actually support (see the limited-interpretation
  requirement below), and any claim beyond that is a spec violation independent of correct math.

## Collision / legend-materiality / caption policy

- **POL-FF402-027** (verbatim): "Use perceptually distinct colorblind-safe categorical genus
  colors and a redundant non-color encoding so near-identical shades cannot erase genus
  differentiation. A candidate must test pairwise categorical distinguishability and provide a
  redundant encoding in the static review surface."
- **POL-FF402-028** (verbatim): "Place a complete adjacent ordination methods block: observation
  unit, exact ten-feature input, log1p transformation, centering/no-scaling SVD, missing-value
  handling, fitting subset, explained variance, loadings, and the limited meaning of PCA
  axes/distances. A candidate review-delivery check must fail if any required method element is
  absent; a compact loading interpretation or biplot/interactive companion must not overstate
  biological separation."
- This is a **review-surface** policy (`RETAIN_AND_REDESIGN_POLICY_ONLY_NO_FROZEN_PROOF_
  MUTATION_OR_RENDER`) — the acceptance checks below govern the *review delivery*, not a final
  publication artifact; do not treat passing them as authorization to seal or publish.

## Acceptance checks

1. Every plotted genus category uses a colorblind-safe, perceptually distinct color **and** a
   redundant non-color encoding (e.g. marker shape) — verified by a pairwise-distinguishability
   test, not visual inspection alone.
2. Methods block states, in full: observation unit, the ten named features, log1p transform,
   centering-without-scaling, missing-value handling, fitting subset, explained variance, and
   loadings — all eight elements present; any one missing fails the check.
3. A sentence stating the limited meaning of PCA/SVD axes and distances (what proximity does and
   does not establish) is present adjacent to the figure.
4. Any loading interpretation, biplot, or interactive companion text is checked against the
   limited-interpretation sentence — it must not claim more than the stated boundary allows.
5. No frozen proof, source file, or render is mutated in satisfying this spec.

## Owner binding required

1. **Exact ten feature fields.**
2. **Fitting subset** (which BGCs/strains).
3. **Genus-source confirmation** (reconciled with the authoritative roster or not).
4. **Missing-value-handling policy** (row-drop vs. imputation vs. another named method).

## Non-overlap statement

This spec governs the SCI-01B-F13R **review surface** only, per its `RETAIN_AND_REDESIGN_
POLICY_ONLY` authority state — it does not authorize implementation, and it deliberately shares
its "redundant encoding + limited-interpretation sentence" requirement in spirit with
`REPAIR_SPEC_Q-013_F14.md`'s and `REPAIR_SPEC_Q-014_F15.md`'s PC-distance-boundary requirement,
so a future implementation is not asked to invent three different phrasings of the same
scientific caveat.
