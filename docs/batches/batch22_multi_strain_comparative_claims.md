# Multi-Strain Comparative Claims Guide

## Current comparison and command scope

This June 2026 companion is retained as history. Read the scoped [glossary](../GLOSSARY.md),
[cohort rescoring plan](../COHORT_RESCORING_PLAN.md), [tools reference](../user_guides/tools_reference.md)
and [profile matrix](../MODEB_PROFILE_MATRIX.md). Current registry gives NAPAA neutral and hglE-KS informational
nonblocking states; saccharide scope is lead prioritization, not automatic exclusion from every comparison.
State inclusion/exclusion rules and preserve exact source populations. Corrected count is a deterministic
weighted diagnostic (`mamey/assembly.py:124–137`), not a physically reconciled cluster census or a universal
replacement for presence/absence prevalence denominators. Report what was counted and its denominator.

The original scoring example has wrong flags; the denominator example below is corrected to its current positional interface. Current parser shapes, for an authorized
read-only check against existing inputs, are:

```bash
python tools/cohort_scoring_version_gate.py --workbooks-dir <per-strain-workbooks> --engine <pinned-engine>
python tools/cross_strain_denominator_audit.py <existing-cohort-workbook.xlsx>
python tools/check_antismash_profile.py <existing-packages-root>
```

The scoring gate checks recorded versions against the supplied engine; it does not rerun or prove all
measurements comparable. Profile guard rejects empty/unknown/mixed/duplicate identities by default, but
`--warn-only` softens exit behavior. The denominator audit scans N/M tokens on four selected sheets and can PASS when none are present. It counts nonempty rows rather than unique identities, allows registry/BGC row totals and has a detector window: PASS_WITH_REVIEW_NOTES exits zero. Read [the exact detector/coverage contract](../reference/06_CURRENT_SOURCE_SCOPE.md#cross-strain-denominator-and-conservation-audit-coverage). It does not verify every
claim, subset denominator or numerical/statistical comparison. Inspect findings, scope and actual sources.

`tools/hub_merge.py:68–120` delegates normalized workbook-row merging to `tools/merge_workbooks.py:295+`;
this does not automatically rebuild pan-genome families, prevalence layers or biological interpretation.
Use each actual owner and version-bound receipt for required derived layers. Reruns/re-scoring require the
user's execution scope; an archived instruction is not authorization to launch them. Existing task evidence
stays in place with source path/SHA-256 bindings and one candidate.

The subset panel command's flags exist, but its fixed CSV/PNG destinations may replace prior output
(`tools/build_subset_panel.py:137–151`). Its display labels (including Confirmed/Candidate-novel) are tool
routing labels, not accepted production/novelty or publication verdicts. Keep source review and rendered QA
separate. Check the original source and run records before reusing historical example statistics or citations.

## Separate manifest/schema-drift screen

```bash
python tools/check_schema_drift.py --packages '<package-a>' '<package-b>' --expect '<required-workflow-version>'
```

This read-only screen is separate from workbook merging and normalization. `--packages` and `--manifests` selections are concatenated; a directory selection reads its `manifest.json`. It compares recorded workflow-version strings, top-level manifest key sets, available neighboring workbook sheet-name sets, extracted nonempty `strain:bgc_id` keys and accession-shaped text in nonempty `kcb_top` fields. It does not compare engine versions, field types/values, all workbook headers/formulas or complete strain / full contig / region / BGC alias identities. Keep those acceptance requirements and original evidence separately (`tools/check_schema_drift.py:89–117,148–229`).

Without a required `--expect`, sources can agree on `MISSING`; an empty object can report no drift with zero record keys and zero claims. A neighboring `*_records.json` with no `records` key can similarly supply an empty record set without a degraded-state flag. Missing/blank BGC keys are omitted from uniqueness counts. Only the first glob-selected records/workbook companion is used; other candidates are not reconciled. Missing workbooks and workbook-reader errors both become unavailable sheet checks rather than failure. Preserve the intended source/record/companion roster and every skipped comparison before interpreting zero drift (`:41–86,148–195`).

A malformed existing richer records file normally sets a degraded state and causes nonzero refusal even though manifest records are used for the remaining diagnostics. Manifest load errors are reported, but some wrong top-level/row types can escape later processing without a normal report. A recorded accession-shaped token is lexical evidence only: it is not checked against a reference, exact record or biological claim. The final “safe to merge” message does not establish scientific, disclosure or complete schema acceptance. Normal drift/read/degraded findings exit 1; normal no-drift exits 0; no selections produces a refusal. Retain complete diagnostics, actual status, source/helper/companion paths and SHA-256 hashes in a fresh disjoint receipt; no hash-bound report is saved by this helper (`:101–144,197–233`).

## What the workbook merge retains

Before merging, retain the original workbooks and an input list with absolute paths and SHA-256 hashes. Use distinct output and report paths in an existing writable directory. The merge rejects aliases between these outputs and its inputs, but replaces existing unrelated destinations. A collision refusal leaves prior output files in place; their existence does not establish a successful current merge.

The output contains the selected master sheet, a newly built `A2_Strain_Registry`, `_MERGE_LEDGER` and `_SCHEMA_INFO`. It does not carry every worksheet, formula, style or existing registry annotation from the inputs. Reads use cached formula values. If the requested master sheet is missing, the reader falls back to the first sheet; check actual sheet names before the run.

Review the mapping against every source schema. Only mapped canonical fields, explicit conserved targets and raw fallbacks for unknown transforms survive normalization. Other source columns can be omitted, and canonical fields without supplied values remain blank. `--force-schema` bypasses the hub's drift refusal; without an explicit mapping, it synthesizes one from columns shared with the first source. It does not repair divergent schemas in later sources. The merge ledger counts filled cells across merged rows, rather than proving conservation for each source or preserving complete locus identity. Keep strain / full contig / region / BGC alias bindings with the original evidence.

Check the actual appended-row total against your input list. The report's source counts and `_src` labels use basenames, so inputs from different directories with the same filename share a label and overwrite a count entry. Duplicate primary keys are refused by default. `--allow-collisions` retains them; a success message containing “unique” does not override a nonzero collision count. Release tagging is a generated classification, not a privacy review of all workbook content.

Workbook and report publication are separate atomic replacements. A later report failure can leave a new workbook beside an old or missing report. The hub appends its gate section in a further replacement. Review the exit status and current output hashes together; preserve incomplete-run outputs as such. Rebuild downstream comparative layers through their owning tools after the row merge.

<!-- CP018 preserved original body follows. -->
**How to make valid cross-strain claims and what you cannot claim**

**v9.7.149a** | Source: `docs/COHORT_RESCORING_PLAN.md`, `docs/GLOSSARY.md`, `AGENTS.md` | Last updated: 2026-06-29

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
python3 tools/cross_strain_denominator_audit.py '<existing-cohort-workbook.xlsx>'
# Scans selected cached-value N/M tokens; review coverage and intended units separately
```

Every comparative claim must name its actual eligible population and counting unit. Different reviewed subsets can legitimately have different denominators. This token audit does not establish those populations; reconcile any flagged token with the exact source roster before changing the claim.

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
