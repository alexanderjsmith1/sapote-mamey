# What `KCB_score` actually is — the exact antiSMASH source field

**Binding established v9.7.404**, by reading the current engine (1.9.145) end to end. Every line
reference below was verified in the sealed `v9.7.403` tree. This document exists because a figure
review asked a question the codebase could not previously answer from any single place: *does
antiSMASH calculate this, what does it mean, and how were the displayed bands produced?*

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
cumulative score. Taking `block_records[0]` keeps `KCB_top` and `KCB_score` describing **the same
hit** — the file's own rank 1. This is exactly the failure mode the whole question was about: a
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
available scores** and bins each BGC below/between/above those cut points. They are therefore:

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
absence of a hit is novelty-*leaning*, not proof of novelty. Judgment deferred.
