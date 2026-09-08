# DELIVERABLE — Cross-Strain Family Seeds (FAM)

> **Filing.** `docs/modules/DELIVERABLE_FamilySeeds.md`.
> **Extends / references:** `tools/build_gcf_tags.py` (the `gcf_tag` logic — live code), `SAPOTE_SLIM_JUDGMENT_KERNEL.md` MODULE 21 (cross-strain compilation), §41 CCSM (the analysis this hook feeds), Workbook Schema v1.0 (`CrossStrain_Family_Seeds` sheet). **Do not restate CCSM — point to it.**
> **Precedence.** Parent monolith wins. This module owns the per-strain **seed-emission hook and naming**; CCSM owns the cross-strain *analysis* the seeds trigger.
> **Status:** `SCHEMA_BACKED` (the seed row is a workbook sheet) **+ `PROMPT_BACKED`** (the ≥3-strain threshold check and family-seed labelling). Thin by design — it is a wiring hook, not a heavy deliverable.
> **One-line purpose.** Ensure every strain emits a comparable family-seed row so project-wide BGC-family comparisons are possible later, and fire the CCSM trigger when a class reaches the ≥3-strain threshold.

---

## 1. When it is offered (Deliverable Offer Protocol)

Auto-run **after the BGC inventory** for every strain (this is the v7.5 "cross-strain hook"): append family-seed rows, then check the threshold. **Incomplete delivery** = finishing a strain inventory without writing its `CrossStrain_Family_Seeds` rows, or reaching a ≥3-strain class without surfacing the CCSM trigger.

---

## 2. Inputs required

| Field (per BGC) | Feeds |
|---|---|
| Strain ID, Habitat, Genus, BGC #, product class | seed row + naming |
| Architecture grade, KCB top/score, RiQ comparator/score | seed row |
| diagnostic domains, module signature, TFBS signature, TTA tier | seed row (comparability axes) |
| master JSON (prior strains' seeds) | the ≥3-strain threshold check |

**Skip-not-fake.** A seed axis with no value is left blank-labelled (`RiQ: not computed`), never imputed; a class is counted toward the ≥3 threshold only with a real seed, not an inferred one.

---

## 3. Pipeline

```bash
python tools/build_gcf_tags.py --package-dir <pkg> --master <master.xlsx>   # emits/updates seed rows
```
Then (PROMPT_BACKED) the threshold check: scan the master for classes with seeds in ≥3 strains; for each, surface the CCSM trigger. **Project-wide audit rule:** after every fifth strain, run a full family-seed audit against the master JSON.

---

## 3a. Family-seed naming (§35.3)

```text
[Genus]_[Habitat]_[CompoundClass]_[StrainID]_BGC[N]
```
Examples: `Amycolatopsis_Insect_Enediyne_SID-XXX_BGC047`, `Amycolatopsis_Insect_Phosphonate_SID-XXX_BGC063`.

---

## 3b. Threshold trigger (§35.4)

If ≥3 strains carry seeds in the same class → surface, verbatim:
```text
Run cross-strain BGC family clustering for [class/family].
```

---

## 4. Outputs & contract surface

`CrossStrain_Family_Seeds` workbook sheet (Schema v1.0) with the 16 columns of §35.2 + any fired CCSM trigger lines. Registration into the schema (not hand-editing) is the source of truth.

---

## 5. Acceptance checklist

- [ ] Every BGC has a family-seed row with all comparability axes (blanks labelled, not imputed).
- [ ] Seed labels follow the §35.3 naming exactly.
- [ ] Threshold checked against the master; CCSM trigger surfaced for any ≥3-strain class.
- [ ] Five-strain audit rule honored when applicable.
- [ ] Standing constraints respected (NAPAA not used as a comparative family signal; hglE-KS habitat-non-specific).
- [ ] Contig-ID locators; affiliation = ; exactly 8 unique next-paths.

---

## 6. Tool / knowledge inventory

| Piece | Owner |
|---|---|
| Seed-row emission / gcf tags | `tools/build_gcf_tags.py` |
| Naming + threshold logic | this module |
| Cross-strain analysis | §41 CCSM / kernel MODULE 21 |
| Sheet schema | Workbook Schema v1.0 |

---

## 7. Worked next-paths closer (SID-XXX)

> Family seeds emitted: `Amycolatopsis_Insect_Enediyne_SID-XXX_BGC047`, `…_Phosphonate_…_BGC063`, `…_AromaticPKS_…_BGC025`, `…_Thioamitide_…_BGC012`, `…_CatecholateSiderophore_…_BGC019`. Threshold: no class yet at ≥3 strains (first Amycolatopsis-insect strain in this set). Next paths:
> 1. Bank a second Amycolatopsis to test whether enediyne/phosphonate seeds recur.
> 2. Add SID-XXX seeds to the master via `merge-packages`.
> 3. Run the five-strain family-seed audit once the set reaches five.
> 4. Pre-register the enediyne and phosphonate family labels for cross-strain watch.
> 5. When any class hits ≥3 strains, fire the CCSM clustering trigger.
