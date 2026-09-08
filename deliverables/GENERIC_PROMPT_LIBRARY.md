# Sapote–Mamey — Generic Deliverable Prompt Library (v1)

Reusable, parameterized prompts. Paste **GLOBAL GUARDS** once per session, then any G-block, filling `{PARAMS}`.

## Readiness audit (against the v9.5.9 toolset)

| prompt | driving tool | status | note |
|---|---|---|---|
| **G1** BGC Atlas | `tools/generate_bgc_atlas.py` | ✅ **READY** | built this cycle (was missing); emits tier-coloured HTML |
| **G2** Cross-Cohort Panel | `build_subset_panel.py --tag {TAG}` | ✅ **READY** | closed via DLV-008; deterministic filter→CSV→panel |
| **G3** Strain Lead One-Pager | `build_priority_leads.py` → md/PDF | ✅ READY | tool yields the ranked leads; one-pager assembly is the narrow Sapote step |
| **G4** Single-BGC Mode B | `build_modeb_deepdive.py --targets {S}:{B}` | ✅ READY | deterministic; §1–§8 |
| **G5** Cross-Strain Table | `add_xstrain_sheets.py` | ✅ READY | confirm it covers `{AXIS}`; else per-strain tally fallback |
| **G6** Priority-Leads Figure | `build_priority_leads.py` + `build_subset_panel.py --strain-set` | ✅ **READY** | subset figure now via build_subset_panel (DLV-008) |
| **G7** Layperson Guide | (Sapote LLM step) | ✅ READY | no tool; ranked + plain-language |
| **G8** Manuscript Paragraph | (Sapote LLM step) | ✅ READY | every number sourced to a bank |
| **G9** Pangenome / Rarefaction | `build_pangenome.py [--replot]` | ✅ READY | families are anchor-based/approximate |

**DLV-008 closed.** `tools/build_subset_panel.py` provides the deterministic filter→CSV→panel for G2 (`--tag`) and G6 (`--strain-set`). All nine prompts are now tool-backed. See `docs/modules/DELIVERABLE_SubsetPanel.md`.

---

## GLOBAL GUARDS (paste once per session)
- Build from **banked data only** (`merged_cohort/*.json`, `modeb_verdicts.csv`); never re-scan packages (skip `build_deep_data` / `build_bgc_markers`).
- **KCB = similarity anchor, not identity.** `azoxy-crosslink`, `~enediyne`, `~halogenase` are antiSMASH **[E-signals]**, not structures.
- **Bioactivity metadata is optional and typed.** Without supplied metadata, use `NOT_SUPPLIED` and do not name an assay target.
- **AS verdicts are `[EG]`** (offline) until verified-literature-upgraded — tag them.
- **Corrected BGC count = Interior + ½·Edge + ¼·Full-contig.**
- **Confidence tiers:** Confirmed · Predicted-functional · KCB-anchored · Candidate-novel (no anchor). Palette in `DELIVERABLE_INSTRUCTION_TEMPLATE.md`.
- **Any deliverable containing AS strains is PRIVATE** — no public release. Don't surface AS strain IDs in public-facing text.
- Every locus shown carries: `Strain / Region · class · ~KCB anchor · edge-status · SARP y/n · ModeB verdict`.
- On finish: hand back the file + a 2–3 line note, and update the relevant HIVE Board row → DONE.

**Parameter glossary:** `{STRAIN}` · `{BGC}` region/NODE id · `{PRODUCT_TAG}` antiSMASH class tag · `{COHORT}` merged/SID/AS/habitat · `{STRAIN_SET}` comma list · `{AXIS}` feature axis · `{SECTION}` manuscript section.

---

## G1 — BGC Atlas for `{STRAIN}`
**Goal:** browsable HTML atlas of `{STRAIN}`'s BGC inventory. **Type:** BGC Atlas (HTML).
**Method:** `python tools/generate_bgc_atlas.py --strain {STRAIN} --banked-dir merged_cohort [--out {STRAIN}_BGC_Atlas[_PRIVATE].html]`. Sapote step (narrow): bucket regions into bioactivity axes; unassignable → "Other / cryptic."
**Output:** header (strain/host/region+corrected count/strictness); one card per region (class · ~KCB anchor · kb · edge · tier · ModeB); legend; claim-safety footer. **Accept:** all regions · corrected count · tiers+legend · PRIVATE if AS.

## G2 — Cross-Cohort Panel for `{PRODUCT_TAG}`
**Goal:** comparative figure of every `{PRODUCT_TAG}` locus in `{COHORT}`, grouped by host/habitat.
**Method:** `python tools/build_subset_panel.py --banked-dir merged_cohort --tag {PRODUCT_TAG} --out-dir figures` (deterministic filter→CSV→panel; lanes by genus, habitat when available). **Do not infer a shared product** — KCB anchors may differ. Caption: the shared thread is the `{PRODUCT_TAG}` **[E-signal]/machinery, not one compound**. **Accept:** all tagged loci · habitat from strains.json · SARP+`[EG]` shown · PRIVATE if AS.

## G3 — Strain Lead One-Pager for `{STRAIN}`
**Goal:** one-page ranked-lead + arsenal summary. **Method:** `build_priority_leads.py` rows for `{STRAIN}` → rank Class-A→C; Sapote writes ≤1-line rationale per lead; emit md/1-page PDF. **Accept:** ranked+tiered · rationale ≤1 line · claim-safety footer · PRIVATE if AS.

## G4 — Single-BGC Mode B Deep Dive for `{STRAIN}/{BGC}`
**Goal:** §1–§8 dive on one cluster. **Method:** `python tools/build_modeb_deepdive.py --banked-dir merged_cohort --targets {STRAIN}:{BGC} --out {STRAIN}_{BGC}_ModeB.md`. **Accept:** all 8 sections · anchor flagged as similarity · verdict + next-step.

## G5 — Cross-Strain Comparison Table for `{STRAIN_SET}` on `{AXIS}`
**Goal:** side-by-side `{STRAIN_SET}` × `{AXIS}` table. **Method:** `tools/add_xstrain_sheets.py` if it covers `{AXIS}`, else deterministic per-strain tallies; Sapote 2–3 sentence read-out. Flag **strictness confounds** if loose vs relaxed mixed. **Accept:** all strains · strictness flagged · ≤3-sentence note · PRIVATE if AS.

## G6 — Priority-Leads Figure for `{COHORT}`
**Goal:** two-panel ranked-leads-over-field figure. **Method:** `build_priority_leads.py` for data; figure via `build_figures.py` (cohort-subset needs the G2 `--subset` fallback). Harmonize strictness before cross-cohort class-count claims. **Accept:** Class-A highlighted · counts match banks · PRIVATE if AS.

## G7 — Layperson Ranked Guide for `{STRAIN}`
**Goal:** plain-language ranked cluster guide. **Method:** rank by novelty+tier+bioactivity; Sapote writes 2–4 jargon-free sentences/lead. **Accept:** ranked · jargon-free · confidence in plain terms · PRIVATE if AS.

## G8 — Claim-Safe Manuscript Paragraph for `{SECTION}`
**Goal:** drop-in `{SECTION}` paragraph grounded in banked facts. **Method:** Sapote drafts ≤1 paragraph; every number tied to `[bank: file/field]`; flag any `[EG]`-dependent sentence. **Accept:** every number sourced · `[EG]` flagged · ≤1 paragraph.

## G9 — Pangenome / Rarefaction for `{COHORT}`
**Goal:** pan-BGC-ome + rarefaction. **Method:** `python tools/build_pangenome.py --banked-dir merged_cohort [--replot] --out fig_pangenome_{COHORT}.png`. **Accept:** core/accessory/private counts · approximate-families caveat · saturation noted.

---
### Adding a new generic prompt
Copy a block → `G{n} — {Deliverable} for {PARAM}`; list `{PARAMS}`; point Inputs at the banks; name the driving tool (or the Sapote judgment step); keep **Guards: GLOBAL**; register a HIVE board row and add it to the readiness audit. New blocks must also conform to the authoring discipline in `prompts/CLAUDE_SYSTEM_PROMPT.md` §13 (source-grounded claims, bounded claim language, format-from-example).
