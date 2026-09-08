# Multi-Strain Comparative Claims Guide
**How to make valid cross-strain claims and what you cannot claim**

**v9.7.149a** | Source: `docs/COHORT_RESCORING_PLAN.md`, `docs/GLOSSARY.md`, `CHATGPT_START_HERE.md` | Last updated: 2026-06-29

---

## The fundamental constraint

Cross-strain comparisons are only valid when every strain in the comparison was scored by the **same engine version**. Mixing strains scored at different engine versions produces numbers from different rulebooks — not valid for any comparative claim.

The `cohort_scoring_version_gate.py` tool enforces this as a fail-closed gate: a comparative build refuses to aggregate strains with mixed scoring engine versions.

```bash
python tools/cohort_scoring_version_gate.py \
  --banked-dir cohort \
  --workbook master_workbook.xlsx
# Exits non-zero if any strain was scored at a different engine version
```

---

## What you need before making any comparative claim

1. **Engine version check:** All strains in the comparison scored at the same engine version (verify with `cohort_scoring_version_gate.py`)
2. **antiSMASH profile check:** All strains run with the same antiSMASH strictness setting (verify with `check_antismash_profile.py`)
3. **Corrected counts:** Use corrected BGC counts (Interior + ½·Edge + ¼·FC), never raw counts
4. **Standing exclusions applied:** NAPAA, hglE-KS-PREV-001, and saccharide excluded before any comparative statement
5. **Denominator stated:** Every comparative claim must state the denominator (e.g. "4/12 bee-associated strains")

---

## Corrected BGC count — the only valid count for comparisons

**Formula:** Interior × 1.0 + Edge × 0.5 + Full-contig × 0.25

This is locked. Do not re-derive it in downstream tools. The formula is authoritative.

**Why:** A fragmented assembly splits one biological cluster across multiple BGC calls. Edge clusters get 0.5 because they may be incomplete on one end. Full-contig clusters get 0.25 because they span the entire contig and are likely cut at both ends — essentially a lower bound.

**Reporting:** Always report both raw and corrected:
> "Raw: 42 BGCs; Corrected: 38.25 equivalent (GOOD assembly, 94% interior)"

**In cross-strain comparisons:** Use corrected counts for ranking and prevalence claims. Raw counts are reported for transparency but never used in comparative statements.

---

## Standing exclusions (mandatory before any cross-strain claim)

These three classes must be excluded from every cross-strain comparison:

### NAPAA
- **Why:** Ubiquitous across phyla and habitats. Non-informative for natural product discovery. Nosema hypothesis retired.
- **In output:** Include in BGC inventory. Exclude from all comparative/ecological statements. Add: "NAPAA — excluded from comparative claims per standing rule."

### hglE-KS-PREV-001 / hexacosalactone
- **Why:** Prevalent across ≥8 strains spanning 7 genera and 3 habitats. Habitat-non-specific. BRYO-HGT-001 hypothesis retired.
- **In output:** Include in BGC inventory. Exclude from comparative/ecological statements. Add: "hglE-KS-PREV-001 — habitat-non-specific; excluded from comparative claims per standing rule."

### Saccharide BGCs
- **Why:** Primary or housekeeping carbohydrate metabolism in many cases. Non-informative for natural product discovery comparisons.
- **In output:** Move to background section of deliverables. Add: "Saccharide — excluded from comparative claims; primary metabolism."

---

## What comparative claims you can make (and how)

### ✓ Valid: prevalence with denominator

> "PKS-class BGCs were detected in 9 of 12 bee-associated strains (corrected mean: 4.2 ± 1.1 per strain) vs 2 of 3 wasp-associated strains (corrected mean: 3.8 ± 0.7 per strain). Excluding NAPAA, hglE-KS-PREV-001, and saccharide classes."

### ✓ Valid: shared accessory chemistry with denominator

> "HSAF/PTM-class BGCs were detected in 5/12 bee-associated strains, representing a shared antifungal biosynthetic capacity across *Streptomyces* sp. strains from this habitat — consistent with a guild-level antifungal function (inferred)."

### ✓ Valid: strain-unique capacity (provisional, sample-limited)

> "A fluorinated phosphonate BGC was detected in SID8375 (NODE_3 · region_004) with no close KCB match in any other strain in the 12-bee cohort — a strain-specific biosynthetic capacity not represented elsewhere in this sample (provisional; sample-limited observation)."

### ✗ Invalid: phenotypic binary

> "Bee-associated strains are more antifungal than wasp-associated strains."

Never. Contrast by biosynthetic mechanism, not phenotype. Absence of recorded activity ≠ absence of activity.

### ✗ Invalid: compound-level comparative claim

> "Bee strains produce more polyene antifungals than wasp strains."

Never claim production. Rephrase: "Polyene-class biosynthetic capacity is more prevalent in the bee-associated subset (X/12) than the wasp-associated subset (Y/3) of this cohort."

### ✗ Invalid: universal prevalence from small cohort

> "HSAF is a bee-associated compound class."

Never generalise from small N. "HSAF-class biosynthetic capacity was detected in 5/12 bee-associated strains in this cohort" is valid. "HSAF is bee-associated" is not.

---

## Denominator audit

Before any comparative statement, run:

```bash
python tools/cross_strain_denominator_audit.py \
  --workbook master_workbook.xlsx
# Verifies consistent cohort sizes across all comparative claims
```

Every comparative claim in a deliverable must carry the same denominator as the denominator audit confirms. Discrepancies between claims and the audit = non-conformant deliverable.

---

## antiSMASH profile guard

BGC counts are only comparable within one antiSMASH strictness profile. Before any cross-strain claim:

```bash
python tools/check_antismash_profile.py <packages_root>
# Exits non-zero if strains were run under different profiles or any is "unknown"
```

If profiles are mixed → comparative claims on BGC counts are invalid. Resolve by re-running the affected strains under a consistent profile.

---

## Cohort-local layers — recompute, never concatenate

After re-scoring or adding strains, these layers must be recomputed from scratch — they are computed within a cohort and invalid if carried over from a prior cohort state:

- Product-class prevalence matrices
- Pan-genome / BGC family groupings
- Cross-strain rankings

The merge tool (`hub_merge.py`) recomputes these automatically after merge. If you build these layers manually, never concatenate a new strain's cohort-local layer onto an existing one — always recompute from all strains together.

---

## The cohort re-scoring gate (when it applies)

If strains in your cohort were scored at different engine versions — a common situation during active development — the comparative layer is blocked until re-scoring is complete.

**Scope:** All strains in the comparative cohort must be re-run at the target engine version. Per strain:
1. Re-run deterministic Mamey extraction at the pinned engine version
2. Re-emit the Sapote judgment layer
3. Record the engine version in the per-strain receipt

**What survives re-scoring without change:**
- Standing permanent exclusions (NAPAA, hglE-KS-PREV-001, saccharide)
- Claim-safety conventions
- Mechanism-level observations (e.g. HSAF/PTM recurrence as a mechanism observation, not a score ranking)

**What must be recomputed:**
- All cohort-local layers (product-class matrices, pan-BGC-ome, cross-strain rankings)

---

## Cross-cohort subset panel

For figures comparing subsets (by habitat, genus, or geography):

```bash
python tools/build_subset_panel.py \
  --banked-dir cohort \
  --tag [PRODUCT_TAG] \
  --out-dir figures/
```

This produces a deterministic filter → CSV → panel workflow. Caption: "The shared thread is the [PRODUCT_TAG] machinery, not one compound." Never imply shared compound identity from cross-strain shared BGC class.

---

## See also

- **Corrected count formula:** `docs/GLOSSARY.md` §3 (Corrected BGC count)
- **Standing exclusions detail:** `batch20_claim_safety_field_manual.md`
- **Scoring version gate tool:** `tools/cohort_scoring_version_gate.py`
- **Denominator audit tool:** `tools/cross_strain_denominator_audit.py`
- **Profile guard tool:** `tools/check_antismash_profile.py`
- **Re-scoring plan:** `docs/COHORT_RESCORING_PLAN.md`
- **Pan-genome tool:** `tools/build_pangenome.py`
- **Normalization matrix:** `tools/build_normalization_matrix.py`
