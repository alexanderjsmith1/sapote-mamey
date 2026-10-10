# KCB score provenance and current aggregation limits

**Binding established v9.7.404**, by reading the current engine (1.9.145) end to end. Every line
reference below was verified in the sealed `v9.7.403` tree. This document exists because a figure
review asked a question the codebase could not previously answer from any single place: *does
antiSMASH calculate this, what does it mean, and how were the displayed bands produced?*

## Current v9.7.447 reading boundary

The line numbers and historical defect examples below describe the earlier .403–.405 investigation. They are retained as history, not current executable offsets or a verified individual-locus record. `AS-XXX BGC058` is a redacted example; it is not sufficient identity for adoption. Use strain / full node-or-contig / region / BGC alias in an actual locus record.

Current source parses the **first score-bearing detail block**, strips commas and converts its numeric token to a float (`mamey/antismash_evidence.py:895–930,958–966`). A preceding block without a parsed score is skipped. No rescaling is introduced, but “verbatim” does not mean byte-preserving text and does not independently verify antiSMASH's statistical definition.

KnownClusterBlast records take precedence when present (`:1380–1388`). Within surviving records, cumulative score and protein-hit count are each separately maximized (`:1400–1418`), while the displayed MIBiG reference is the first available reference (`:1391–1398,1425–1444`). With multiple records, those maxima and the displayed reference can come from different records. Preserve the per-file evidence and source accession/rank; do not infer an exact score-to-displayed-product binding from the aggregate fields alone. Candidate product-level similarity additionally has coverage/class and fragment ceilings (`:1445–1467`); none grants product identity or activity.

CSV/workbook emitters use `bgc.kcb_cumulative or ""` (`mamey/cli.py:3330,3715`), so a stored numeric zero exports as blank. G03's cutoff collection excludes only a short token list and uses `_num`; its bin assignment also requires `KCB_top` (`mamey/cohort_figures.py:1730–1760`). A score with a missing top can affect cut points but be placed in the “no KCB hit” bin. Missing source, parser failure or blank export can share that label. Inspect `KCB_evidence_state`, source records and parse holds before calling any row a verified no-hit. Malformed/nonfinite fields require correction rather than biological interpretation.

The current local bindings are `models.py:92`, `b1_normalizer.py:20`, and the CLI offsets above. The historical tertile interpretation remains valid as a description of **this computation**, with ties not guaranteeing equal-sized thirds. Cohort-relative bands are not calibrated probabilities, universal similarity cutoffs or evidence that a named product is made. The source definition and named historical comparator assertions below were not externally re-verified in this software audit.

## The chain, in full

| Step | Where | What happens |
|---|---|---|
| 1 | `mamey/antismash_evidence.py:794` | `re.search(r"Cumulative\s+BLAST\s+score:\s*([0-9][0-9,]*(?:\.\d+)?)", block)` over `>>`-delimited subject-cluster blocks of antiSMASH's ClusterBlast / KnownClusterBlast **TXT** output |
| 2 | `mamey/antismash_evidence.py:826` | `best = block_records[0]` — the **rank-1** block in antiSMASH's own file order |
| 3 | `mamey/antismash_evidence.py:861` | `"cumulative_score": best["score"]` |
| 3.5 | `mamey/antismash_evidence.py:1174-1176` | **source precedence**: `kcb_recs = [r for r in recs if r["source_kind"] == "knownclusterblast"]`, then `source_recs = kcb_recs if kcb_recs else recs`. When any knownclusterblast record exists for the region, **only** knownclusterblast records feed the aggregation |
| 4 | `mamey/antismash_evidence.py:1206` | `bgc.kcb_cumulative = max(score_vals)` — across the surviving records from step 3.5 |
| 5 | `mamey/models.py:92` | `BGCRecord.kcb_cumulative: float \| None` |
| 6 | `mamey/b1_normalizer.py:20` | `"kcb_cumulative": "kcb_score"` — the alias |
| 7 | `mamey/cli.py:2657`, `:2898` | emitted as the `KCB_score` column in the inventory CSV and workbook |

## The four things a reader needs to know

**1. antiSMASH computes it; Mamey does not.** The value is read verbatim from antiSMASH's own
output and is never re-derived, re-scaled, or normalised anywhere in this engine. What the number
*means* is antiSMASH's definition, not ours — this codebase establishes only that it is parsed
faithfully.

**2. It is a cumulative sum, not a per-hit bitscore.** The field is antiSMASH's
`Cumulative BLAST score` for one subject cluster — an unnormalised total over the matched protein
pairs in that cluster. It therefore **grows with cluster size and with the number of matching
proteins**. A large BGC with moderate similarity can outscore a small BGC with excellent
similarity. **Two BGCs' scores are not comparable unless they are of comparable size**, and no
figure or table in this engine should be read as if they were. Figure axes were corrected at
v9.7.404 to stop calling it a "bitscore".

**3. It is rank-1's score, not the file's maximum — and that was once a real defect.** A fix dated
2026-07-01 (comment at `antismash_evidence.py:814-825`) records the case: on `AS-XXX` BGC058, the
rank-46 hit (tetrafibricin, 61753.0) numerically **outscored** rank 1 (aculeximycin, 37992.0),
and the previous `max(block_records, key=score)` silently reported tetrafibricin as the top KCB
hit. antiSMASH's "Significant hits" list is ordered by BLAST **significance**, not by raw
cumulative score. Taking `block_records[0]` keeps the parsed score and protein count on the first score-bearing detail block within one file. Current aggregation can take a maximum score across records while selecting a reference from the first record, so it does not universally guarantee that the final displayed product and score describe the same hit. This is exactly the failure mode the whole question was about: a
bigger number that means less.

**4. The `max()` at step 4 is narrower than it looks, because step 3.5 has already filtered.**
`_region_key_for_bgc` collapses `knownclusterblast/`, `clusterblast/` and `subclusterblast/` onto
the same region key — the three antiSMASH output folders use identical `<contig>_c<N>.txt`
filenames. A blind `max()` across all of them would let a generic whole-genome ClusterBlast hit,
which is **not a curated MIBiG comparator at all**, outscore and overwrite the correct
KnownClusterBlast score. A second 2026-07-01 fix ("KCB source-precedence", comment at
`antismash_evidence.py:1160-1173`) prevents that: when any knownclusterblast record exists,
**only** those records are aggregated. The `max()` therefore runs across multiple
*knownclusterblast* records, not across folders of different kinds.

The same fixture demonstrates it, but this is a **second, separately-dated defect**, not a
restatement of point 3. On `AS-XXX` BGC058 the corrupted score `73038.0` traced to
`clusterblast/..._c1.txt`'s top hit against *"Streptomyces violaceusniger Tu 4113, complete
sequence"* — not a MIBiG cluster — while `knownclusterblast/..._c1.txt` correctly reported
`37992.0` for aculeximycin (BGC0000002.5). One region, two independent ways of reporting a bigger
number that meant less.

And when the fallback *does* fire — no knownclusterblast record at all — it is **flagged, not
silent**. The precedence filter first sets `parse_confidence = "LOW"` and
`needs_manual_kcb_check = "yes"` (`antismash_evidence.py:1177-1179`); the later provenance step
then records the named ClusterBlast subject as `closest_product_provenance = "KCB_TOP_FIELD"`,
`denominator_type = "clusterblast best subject cluster"`, `product_claim_ceiling =
"source-derived similarity anchor only"` and **raises the confidence to `MEDIUM` — never `HIGH`**,
while `needs_manual_kcb_check` stays `"yes"`. So the *final* state a reader meets on a
clusterblast-only region is MEDIUM + manual-check-required + anchor-only ceiling, not LOW; the
v9.7.404 text above said LOW because it read the first assignment and not the last (corrected
v9.7.405, pinned by `tests/test_kcb_rank1_and_source_precedence_v97405.py`). A score aggregated
from non-MIBiG comparators is never presented as if it were MIBiG-derived.

*(This section was corrected after an independent replay of the chain by a second Claude Code
lane; the first draft described step 4 as an indiscriminate cross-folder max and so understated
the code's own safety.)*

## The displayed bands (figure G03) are cohort tertiles

`mamey/cohort_figures.py` computes `np.percentile(scores, [33, 66])` over **this cohort's own
available-looking score fields** and bins each BGC below/between/above those cut points. They are therefore:

- **cohort-relative** — re-run on a different cohort and the same BGC can change band with no
  change whatsoever to its evidence;
- **not similarity thresholds** — no biological boundary is claimed, implied, or known;
- **not comparable across figures** built from different cohorts.

Band labels were reworded at v9.7.404 to *"lower / middle / upper cohort third"*, and the figure
title states the tertile basis and the size-dependence, because a reader who sees "high" beside a
number will otherwise read it as a threshold.

## Claim-safety

KCB is **similarity, not identity**. A KCB hit to a named reference cluster is a **class-level
hypothesis** about biosynthetic capacity — never a structural, compound-identity, or bioactivity
claim. A high cumulative score does not establish that the strain makes the reference compound;
missing or unavailable evidence is not a verified no-hit or novelty result. Even a verified no-hit is scoped to its source/reference search, not proof of novelty. Judgment deferred.
