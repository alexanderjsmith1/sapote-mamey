# Nocardia genus reference bank — PROVENANCE

**What:** comparative reference for the genus *Nocardia*, used by `mamey/genus_reference.py` to supply
claim-safe genus baselines and priors (specialization-plan Layer A). Shipped in all tiers — every row is
a public, published genome, `release_flag=PUBLIC`, no hard-guard (the embargo is only for unpublished
`AS-` strains).

**Files**
- `nocardia_reference.csv` — one row per (strain × bgc_class), long-format. 7 strains, 123 rows.
  Columns: strain_id, accession, organism, species, release_flag, engine_version, strain_total_bgcs,
  bgc_class, n_bgcs_in_class, ab_max, ab_mean, af_max, af_mean, comparative_eligible.
- `nocardia_class_prevalence.csv` — COMPUTED Layer-A baseline (derived from the reference, not authored):
  per comparative-eligible class, how many of the 7 carry it. Recompute, never hand-edit.

**Provenance (all observed/computed — nothing from memory)**
- 7 public *Nocardia* genomes: CS682, BMG111209, *cerradoensis*, *aurea*, *arseniciresistens*,
  *suismassiliense*, *vulneris*. Run through **Mamey engine 1.9.96** (deterministic).
- Counts are corrected Mamey BGC counts (exclusions applied), not naive antiSMASH region tallies.
- Mode note: CS682 was run `gold`, the other six `standard`; Mamey extraction/scoring is deterministic
  and mode-independent (held by tests), so the cohort is internally comparable.

**Version discipline (IMPORTANT)**
- The bank is stamped `engine_version=1.9.96`. The current bundle engine is **1.9.97** (RiPP-extraction
  boundary). The **class-prevalence baseline is engine-robust** (membership from antiSMASH product types).
  The **AB/AF capacity scores are 1.9.96-pinned** — `genus_reference.assert_comparable_with("1.9.97")`
  will refuse to pool them with a 1.9.97 cohort until the 7 are re-scored under 1.9.97.
- The RiPP-extraction boundary is directly relevant here: the cohort carries `linaridin` (a RiPP family
  outside the original four), so a 1.9.97 re-run may surface RiPP precursor cores that 1.9.96 dropped.
  Re-score before using the capacity scores comparatively under 1.9.97.

**Caveat on the computed baseline**
- The `other` catch-all class appears as 7/7 — it is a residual bucket, not a real genus-core signal;
  consumers should disregard it when reading `genus_core_7of7`.

**Claim-safety (unchanged):** capacity-level only; KCB = similarity not identity; bioactivity
extract-level; no strain called activity-negative. A genus reference sharpens priors and sensitivity —
it never licenses "this BGC *is* [compound]".

**Extending:** append new *Nocardia* run on the current engine, then recompute the prevalence file. Keep
one engine across the bank or re-score on a boundary bump.
