# REPAIR_SPEC_Q-020 — V381-G03 KnownClusterBlast reference-score distribution

## Status

- Queue: FF402-Q-020, priority P1, status REPAIR_FIRST.
- Repair surface: exact `KCB_score` provenance, units, and cohort-derived tertile wording.
- Authority: explicit owner historical methods policy (`HISTORICAL_REPAIR_REQUIREMENT_NO_RENDER_OR_SOURCE_MUTATION`).
- This is a specification only. No frozen proof, source file, or render is touched by this document.

## Exact source field(s) — BOUND

Unlike the other eight items in this repair batch, G03's source-field question is **already
fully answered** by `docs/KCB_SCORE_PROVENANCE.md` (bound v9.7.404, read against the current
engine end to end). This spec binds to it directly rather than re-deriving it:

- **Producer:** antiSMASH's own ClusterBlast / KnownClusterBlast TXT output — Mamey never
  computes or rescales this value (`KCB_SCORE_PROVENANCE.md` §"The four things a reader needs
  to know", point 1).
- **Exact source field:** the `Cumulative BLAST score:` line of the rank-1 (`block_records[0]`)
  subject-cluster block in the KnownClusterBlast-precedence record for that region
  (`mamey/antismash_evidence.py:794`, `:826`, `:861`, `:1174-1176`, `:1206`).
- **Units:** an unnormalized cumulative BLAST-score sum, not a per-hit bitscore — it grows with
  cluster size and match count. Two BGCs' scores are comparable only when the BGCs are of
  comparable size.
- **Version:** the antiSMASH version recorded in the sealed package's own manifest
  (`antismash_version` in `manifest.json`) — this spec does not itself hardcode one; the
  candidate must read it per-strain, not assume a cohort-wide constant.
- **Missing/no-hit rule:** when no KnownClusterBlast record exists for a region and the value
  falls back to a non-KCB ClusterBlast record, `bgc.parse_confidence = "LOW"` and
  `bgc.needs_manual_kcb_check = "yes"` are set (`antismash_evidence.py:1177-1179`) — a
  fallback-derived score must never be plotted or captioned as if it were MIBiG-derived without
  surfacing that flag.
- **Emitted column:** `KCB_score` (inventory CSV / workbook), aliased from `kcb_cumulative`
  (`mamey/b1_normalizer.py:20`).

## Denominator

The cohort denominator is every BGC in the governed final subset that carries a non-null
`KCB_score` after the fallback rule above is applied — BGCs with no comparable KCB record at all
are excluded from the tertile computation, not silently binned at zero. The candidate must state
this denominator (n admitted / n total governed BGCs) directly in the caption, not only in a
sidecar.

## Exclusions / defaults

- No BGC with `needs_manual_kcb_check = "yes"` may be plotted without a distinguishing marker
  (a hatch, a footnote asterisk, or a separate "fallback-derived" facet) — POL-FF402-025 fails
  closed on missing producer/field/units/version/denominator disclosure, and an unflagged
  fallback score is exactly a units/producer disclosure failure by omission.
- Band edges are `numpy.percentile(scores, [33, 66])` computed **over this cohort's own admitted
  scores** (`mamey/cohort_figures.py`) — never a fixed, cross-cohort, or hardcoded cut point.

## Collision / legend-materiality / caption policy

- **POL-FF402-025** (reusable acceptance check, verbatim from
  `REUSABLE_CANDIDATE_POLICY_TEST_REQUIREMENTS.tsv`): "Disclose the exact antiSMASH
  KnownClusterBlast producer and source field for KCB_score, metric units, version,
  missing/no-hit rule, cohort denominator, and label 33rd/66th percentile splits as
  cohort-derived tertiles rather than biological thresholds. A candidate must fail closed when
  producer, field, units, version, or denominator is absent; labels must include cohort-derived
  tertile wording."
- Band labels must read "lower / middle / upper cohort third" (or equivalent cohort-relative
  wording), never "low/medium/high" alone — the current engine's own figure title already
  states the tertile basis and size-dependence as of v9.7.404; a candidate must preserve or
  strengthen that, not regress it.

## Acceptance checks

1. Caption/methods block names the exact source field (`Cumulative BLAST score`, KnownClusterBlast
   TXT, rank-1 block) and the antiSMASH version actually used for the plotted cohort — not a
   generic "antiSMASH score" label.
2. Caption states the denominator explicitly (n admitted / n total governed BGCs).
3. Any fallback-derived (`needs_manual_kcb_check = "yes"`) score plotted is visually distinguished
   and disclosed as such.
4. Tertile cut points are computed from `numpy.percentile(scores, [33, 66])` over the admitted
   cohort at render time, and the caption states them as cohort-derived, not biological.
5. No claim of biosynthetic identity, compound identity, or bioactivity is attached to any band.

## Owner binding required

None for the source-field question itself — it is fully bound (see above). What remains for
Alex to supply before an actual candidate/render exists:

1. **Which sealed cohort** (which strain set, which sealed engine version) is the target subset
   for this figure's next candidate — this spec does not select or bind a cohort.
2. **Whether the fallback-derived-score visual marker** (hatch vs. footnote vs. separate facet)
   has a preferred house convention, or whether any of the three is acceptable.

## Non-overlap statement

This spec does not implement, render, or touch any existing G03 frozen proof, patch card, or
source file. It only binds the source-field/denominator/tertile-wording contract a future G03
candidate must satisfy, per the already-existing `docs/KCB_SCORE_PROVENANCE.md` binding.
