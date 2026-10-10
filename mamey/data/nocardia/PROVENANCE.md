## Current reading boundary — v9.7.447

The historical provenance below is retained verbatim. Its “current engine 1.9.97” refers to the historical boundary, not this bundle's engine 1.9.172. The stored bank remains engine 1.9.96-pinned. Historical public/identity/comparability assertions and numerical receipts have not been independently reaccepted by this documentation audit.

`mamey/genus_reference.py` reads the stored CSVs; it does not recalculate prevalence or rescore. `assert_comparable_with(current_engine)` compares exact version strings when explicitly called. A source-wide search found no non-test call site outside its own definition/docstring, so its existence is not automatic enforcement across consumers. The prevalence reader trusts the CSV and does not prove engine robustness, current taxonomic/reference completeness or binding to a new cohort. `genus_core_classes` filters the residual other bucket but uses the stored `genus_core_7of7` flag; generalizing to another denominator requires a separately bound calculation.

Reference evidence in place by path/hash, keep roster, annotation mode and engine scope explicit, and do not pool pinned capacity scores into a current-engine cohort without an accepted comparability record. Reading the historic bank does not authorize regenerating or replacing it. A release flag is stored metadata, not universal publication or redistribution clearance.

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
