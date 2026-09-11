# Sapote Slim Judgment Kernel — v2.3

> **DEPRECATED DEFAULT CONTROLLER (v9.7.147):** Keep this file for legacy integrations only. New ChatGPT/Sapote sessions load `docs/CHATGPT_EXECUTION_SLICE_v97147.md`, which contains the non-abbreviated execution rules, post-`MAMEY_COMPLETE` handback block, interpretive floors, and edge-BGC equality rules. If both files are loaded, the execution slice overrides this slim kernel.
# Derived from: SAPOTE_MAMEY_BUNDLE_MONOLITH.md
# Role: Sapote interpretation layer (Layer 2) for Mamey manifest inputs
# Claim boundary: May interpret evidence using claim-safe language. Must cite Mamey fields. Must not override extraction outputs without logging a correction.
# Last generated: 2026-06-16 (reconciled to corrected monolith — PC-02 BSL-2 reframe)

## HOW TO USE THIS DOCUMENT

Load this kernel into any frontier LLM session (Claude, GPT-4o, Gemini). Upload the Mamey package for the strain you want to interpret. The kernel will run through all judgment modules in sequence.

**Prerequisites:** A completed Mamey gold package (`MAMEY_COMPLETE`) containing: `manifest.json`, `_2_inventory.csv`, `_3_scan_states.json`, `_4_triage_board.csv`, `_4A_RGGMCI_ranked_pairs.csv`. Do not run judgment on a `MAMEY_FAILED` or `MAMEY_DEFERRED` package.

**Run mode:** Default is `sapote_standard` (Triage First Board + top candidate cards + ecology synthesis). Add "archive mode" to trigger full Mode B for every BGC.

**Session-start commitment:**
```
SAPOTE SESSION HANDSHAKE
Mamey package loaded: [strain_id] MAMEY_COMPLETE v[version]
Run mode: sapote_standard / sapote_archive
BGC count: [raw] raw / [corrected] corrected / [interior] interior
Committed this session: Modules 0–17 + Batch 1 Mode B
Checkpoint: after each Mode B batch
```

---

## MODULE 0 — INTAKE: LOADING MAMEY MANIFEST

Read `manifest.json`. Confirm:
- `status` = `MAMEY_COMPLETE` (abort if not)
- `source` field → record as **provenance only** (caveated context). Interpretation is genome-grounded and source-independent; an optional ecological-category lens may be noted but is never a gate and never a functional claim. Unknown/`not supplied` source does NOT defer or downgrade any deliverable.
- `bioactivity` field → preserve typed metadata state; null means `NOT_SUPPLIED` and must not be expanded.
- All ten scans in `scan_status` are PASS or have explicit failure codes

State the intake summary before any analysis:
```
Strain: [strain_id] | Taxonomy: [taxonomy] | Source: [source] → Category [N]
Assembly: [genome_bp] bp · [contigs] contigs · N50 [n50] · [assembly_tier] tier
BGCs: [raw] raw → [corrected] corrected ([interior_pct]% interior)
Scans: [list PASS/FAIL with counts]
Bioactivity: [typed state from manifest; `NOT_SUPPLIED` when absent]
```

---

## MODULE 0.5 — RG-GMCI FRONT-END VALIDATION

**Before any Mode B analysis begins**, read the split-pathway reconstruction data:

1. Read `mamey/diagnostic_rescue.py` — the FULL module docstring (lines 1-25). The docstring contains the motivating positive-control case: which strain, which BGC pair, which triggers, which reference accession.
2. Check the strain's `_4A_RGGMCI_ranked_pairs.csv` for all CORROBORATED pairs.
3. If the strain matches the motivating case, report the positive control with full evidence chain (CORE trigger + ARM trigger + reference accession + why it's a positive control).
4. Report the split-pathway network before proceeding to Mode B cards.

**The answer is in the code, not the data.** Read `diagnostic_rescue.py` first — do not guess from output CSVs.

---

## MODULE 1 — ASSEMBLY AND FRAGMENTATION DECLARATION

From `manifest.json` → `assembly` and `bgc_counts`:
- State assembly tier and interior %
- If POOR or VERY POOR: add assembly warning box; note long-read as Priority 1
- If FLBR = STRONG: flag LMPKS_FRAGMENT_SET; note at least one megasynthase pathway is fragmented

---

## MODULE 2 — BGC INVENTORY TABLE
> After inventory, emit cross-strain family seeds + ≥3-strain CCSM threshold check: `docs/modules/DELIVERABLE_FamilySeeds.md`.
> Any T1PKS triggers LMPKS rescue alongside the KCB sweep: `docs/modules/DELIVERABLE_LMPKSRescue.md` (null result mandatory if no trigger).

From `_2_inventory.csv`. Required columns in output table:
BGC_ID | Node | Length_kb | ES | Products | Arch | KCB_anchor (similarity; use closest_candidate_kcb_product) | KCB_score/prot | TTA_tier | CCTT | Res_tier

Sort all BGCs by `Corrected_rank` when present; otherwise by the active priority axis (`AB_auto`, `AF_auto`, or user-requested ranking). Do not sort Interior first and Edge/FC later. Edge status is an assembly-context column, not a visibility limiter. If assembly tier is POOR or VERY_POOR, add the banner: "POOR-tier assembly — edge/FC distinction is primarily an assembly artefact; rank by score, not by boundary status."

---

## MODULE 2.5 — ARCHITECTURE-FIRST ASSESSMENT (v9.7.107)

**Before writing ANY §3 Biosynthetic Core interpretation**, run the architecture-first workflow (see `mamey/architecture_first.py` for the implementation and SAPOTE_INSTRUCTIONS block):

1. **assess_architecture(genes, boundary_status)** — KCB-BLIND. Classifies the pathway type from gene domain content alone (30 types: trans-AT PKS, cis-AT, T2PKS, T3PKS, PTM, NRPS, hybrid, lanthipeptide, LAP, ranthipeptide, mycofactocin, terpene subtypes, NIS siderophore, ectoine, NAPAA, betalactone, nucleoside, indolocarbazole, primary metabolism, etc.).
2. **check_kcb_concordance()** — compares architecture vs KCB compound class. Five states: CONCORDANT (use both), DISCORDANT (architecture wins), WEAK_SIGNAL (KCB <30% coverage — ignore), ARCHITECTURE_DEFERS (UNKNOWN arch + ≥60% KCB → provisional), NO_KCB (orphan).
3. **make_assignment()** — final product class. Architecture is PRIMARY EVIDENCE. KCB is corroboration, not proof.

**Critical rule:** The KCB compound name is a SIMILARITY SIGNAL, not a product class assignment. When architecture and KCB disagree, architecture wins. Always.

**Known misanchor patterns:** T2PKS KCB on terpene BGC (boundary-bleed from shared flanking genes); PTM KCB on collinear trans-AT PKS (KS subdomain match); macrolide KCB on full-contig fragment (generic module match).

**Provenance:** KCB values in the inventory table use `closest_candidate_kcb_product` with provenance tracking — see MASTER_SCHEMA_FROZEN_v1_1.md §Provenance gate (lines 75-101) for the full specification.

---

## MODULE 3 — §31 ARCHITECTURE CONFIDENCE (two-level split-pathway rule, v9.1)

Validate Mamey-assigned Arch grades. Apply the **v9.1 two-level rule** for split pathways:

**Pathway unit:** assign Architecture grade C for pathway-level structural interpretation (claims about the full compound must cite the unit).
**Anchor fragment:** retain standalone Grade A or B in the inventory and in WL scoring. Flag `Split-Pathway Anchor`.
**Secondary fragments:** Grade D or E individually. Flag `Split-Pathway Secondary`.

**Finding a second fragment is confirmatory evidence, not penalizing evidence.** A HIGH anchor stays HIGH.

Grade A wording: "The visible gene architecture is sufficiently complete for a class-level structural hypothesis."
Grade B: "The core pathway is interpretable, but boundary truncation or annotation gaps limit full structural prediction."
Grade C (pathway unit): "This BGC should be interpreted jointly with other fragments as a split-pathway candidate."

---

### Manifest schema boundary

`manifest.json` is the authoritative handoff object. Read scan outputs from the fields written by Mamey, including `source_scans.glycosylation_arms` when present. Do **not** assume a top-level `context` object; strain/source/taxonomy fields may be flattened or nested depending on package provenance, so recover them from the manifest keys actually present and record any missing value transparently.


## MODULE 4 — §33 WET-LAB DECISION SCORE (WL)
> Full matrix (four independent action scores + decision categories + LMPKS bonuses): `docs/modules/DELIVERABLE_WetLabMatrix.md`. This module's abbreviated table is the summary; the module is the deliverable.

Score each BGC using the §33.3 criteria. For split-pathway anchor BGCs, use pathway-unit combined evidence for WL — do not apply the Arch C penalty to the anchor.

Key criteria (abbreviated):
- Interior BGC: +3
- Arch A: +3 | Arch B: +2 | Arch C (pathway unit): +1 | Arch C penalty NOT applied to anchor
- No KCB + strong diagnostic domains (Arch A): +4
- Strong KCB >5000 with divergent tailoring: +3
- RiQ <0.50 with coherent domains: +3
- TFBS clear induction condition: +2 | T3/T4 bldA: +2
- Specific mechanistic link to tested activity: +2
- Distinctive detection handle: +2
- Concordant Tier 1/2 resistance gene: +1
- Edge/FC truncation: −2 only in GOOD/MODERATE assemblies when truncation materially limits interpretation; 0 in POOR/VERY_POOR assemblies where truncation is primarily an assembly artefact | Tiny unanchored fragment: −3 | Likely housekeeping: −3
- Split-Pathway Secondary: apply standard per-fragment score (usually low)

Decision categories: ≥10 Immediate | 7–9 Strong | 4–6 Conditional | 1–3 Inventory | ≤0 Deprioritized

---

## MODULE 5 — §34 HALLUCINATION-TRAP AUDIT
> Class calls audited here are assigned via `docs/modules/KNOWLEDGE_DiagnosticDomainCombos.md` (domain-combination → class table).

Run before Mode B. Flag and correct:
- Saccharide BGC hitting macrolide/glycopeptide KCB → deoxysugar arm candidate
- Tiny T1PKS FC fragment → Arch D/E unless FLBR split-pathway anchor
- ≥2 BGCs same KCB compound >3000 → apply §30.3 split-pathway gate (two-level rule)
- KCB >5000 with ≤4 proteins → truncation likely; do not call full pathway
- 0% MIBiG cluster similarity but ≥1 individual gene bitscore >300 → call class from gene homology
- Halogenase without scaffold → do NOT fire T43-HAL
- Aminoglycoside KCB without DOIS → affirmatively rule out
- HGT resistance island misread as producer self-protection

Required statement: "Product labels treated as hypotheses. Split-cluster, fragment, and class-mismatch patterns checked before assigning priority."

---

## MODULE 6 — §43 CCTT CRYPTIC-CLASS TRIGGERS

From `manifest.json` → `source_scans.cctt.counts`. For each trigger that fired:
- **T43-HAL:** flag halogenated scaffold candidate; add Cl/Br isotope HRMS handle; tier by count (1 → routing; ≥2 → floor MEDIUM)
- **T43-THA:** gene-beats-cluster override → thioamide-RiPP class; route to §37 thioamide row
- **T43-TET:** spirotetronate candidate; HRMS window 400–800 Da
- **T43-NUC:** peptidyl-nucleoside; polar extraction; SAX/ion-exchange; UV 262 nm; NOT standard C18
- **T43-PHO:** phosphonate via PepM; floor MEDIUM if interior
- **T43-ENE:** enediyne warhead → [E-signal] claim-safety note; cytotoxic/DNA-damaging class → cytotoxicity/self-protection review, handling per standard lab SOPs (non-selective; no per-cluster BSL-2 flag — selective biosafety flags give false reassurance); CalC absence check mandatory
- **T43-AMC:** aminoglycoside if DOIS present; rule-out if absent despite aminoglycoside KCB hit
- **T43-LAN:** lanthipeptide constellation; fires automatically on any antiSMASH lanthipeptide-class region; triggers UMED §52 together; assign LAN sub-grade (§57.5) — LAN-A requires complete maturation route
- **T43-DKP:** CDPS/diketopiperazine; CDPS alone = DKP-B; + co-located oxidase = DKP-A (dehydro-DKP, cytotoxic — no MRSA/Candida bonus); see §57 Block B
- *(All other triggers — T43-XHAL, T43-LASSO, T43-IDC, T43-PTM, T43-NN, T43-TOMM — route to §57 sub-grade table in the monolith; assign grade from criteria there)*

CCTT bonuses bounded, non-stacking (max +2); apply highest applicable only.

---

## MODULE 7 — §57 PER-CLASS CONSTELLATION SUB-GRADES

Assign lettered sub-grade after CCTT trigger: T43-NUC-A/B/C, T43-HAL-A/B/C, T43-ENE-A/B/C, T43-LAN-A/B/C, etc. Record in BGC inventory `Class_sub_grade` column. See §57 for sub-grade definitions.

---

## MODULE 8 — §9 bldA / TTA GATING

From `manifest.json` → `source_scans.blda_tta`. State T4 BGC list and culture implications:
- T1 → liquid or solid standard
- T2 → liquid stationary or solid ISP2
- T3 → solid ISP2/R5, 14+ days
- T4 → sporulating solid media only; flag as critical culture condition

---

## MODULE 9 — §45 RESISTANCE GENE TIERS

From `manifest.json` → `source_scans.resistance_tiers`. For each BGC:
- **Tier 1 within BGC coordinates:** near-definitive class confirmation (+1 WL, supports Arch B→A); flag with full marker description
- **Tier 2 within 15 kb:** strong contextual support (+1 WL); apply HGT guard (check for flanking integrase/transposase)
- **Tier 3:** polarity routing only; no WL adjustment
- **HGT resistance island:** flag per §34; do not count as class confirmation

CalC absence flag: mandatory for any T43-ENE triggered BGC lacking CalC-type within 15 kb.

---

## MODULE 10 — §52 UMED MATURATION ENZYME

From scan states: if `UMED: N lanthipeptide GAP regions`, flag the affected BGCs as maturation-gap candidates. State: "Maturation protease unclustered; full lanthipeptide yield may require separate expression conditions. External HMMER proteome scan required for definitive verdict."

**v9.7.62:** the `UMED_gap` column in `_4_triage_board.csv` now propagates this flag directly per BGC. When `UMED_gap = MATURATION_GAP`, include the following note in the Mode B §6 (Fermentation & Expression): "Maturation enzyme not co-clustered (UMED scan). Full product yield requires maturation protease expression; separate expression construct or heterologous host with appropriate protease background recommended."

---

## MODULE 11 — §55 EFLS LINKAGE INTERPRETATION

From `_4A_RGGMCI_ranked_pairs.csv`. For FLBR STRONG strains: identify the top cross-contig pairs that may represent split megasynthase fragments. Flag COMPLEMENTARY pairs (Jaccard <0.25) vs. REDUNDANT (J >0.55). COMPLEMENTARY + high class fragility → split-pathway candidate; anchor = fragment with most complete core logic.

---

## MODULE 12 — TRIAGE FIRST BOARD

Generate before Mode B. Required columns:
Rank | BGC | ES | Arch | WL | AB_score | AF_score | Class | Key triggers | Depth floor

AB track top 3 and AF track top 3 explicitly labelled. Note any BGC with QS signal → "QS signal — ecology routing only."

---

## MODULE 13 — MODE B DEEP DIVES (Full-Run Profile default)
> Each strong claim ships a reviewer-attack block: `docs/modules/DELIVERABLE_ReviewerAttack.md` (auto-placed after the exec summary).

Every BGC receives a Mode B report. Interior BGCs and triggered BGCs (CCTT/§45 Tier1/FLBR anchor) in Batch 1; remaining in subsequent batches.

Each Mode B report must contain:
**§1** Overview table (BGC_ID, contig, coords, length, ES, Arch, KCB, RiQ, TTA, WL, lead tier) + compact Evidence Traceability
**§2** Gene-by-gene domain analysis table: every CDS ± 3 kb, locus tag, strand, coords, gene_kind, top PFAM/TIGRFAM (accession + bitscore), functional assignment, functional flag (biosynthetic/resistance/transport/regulatory/housekeeping)
**§3** Module architecture (NRPS/PKS) or RiPP logic
**§4** Biosynthetic pathway hypothesis (≥120 words; cites specific domain IDs and bitscores; includes expanded Evidence Traceability block)
**§5** MIBiG/KCB comparison
**§6** Mechanistic link to bioactivity (≥60 words)
**§7** Isolation strategy (≥80 words; bldA tier, TFBS induction, extraction, detection handle)
**§8** Claim-safety audit

Split-pathway anchor BGCs: note the pathway unit and secondary fragments in §1 and §5. Score WL at pathway-unit level. Report standalone Arch grade.

---

## MODULE 14 — §ECO MECHANISTIC ECOLOGY SYNTHESIS
> Full eleven-step method (TFBS coupling → polysaccharide gating → bldA mapping → disease-defence → integrated model → ecological RAS): `docs/modules/DELIVERABLE_EcologicalSynthesis.md`. This module is the abstract; that is the method.

Required sections:
1. Host / ecological source context (Category 1–7) — **OPTIONAL provenance lens, source-independent default**: note the category only if a source is supplied, caveated as isolation-source ≠ function; on unknown source state the general framing (actinomycete antimicrobial/defensive capacity) and proceed. Never a gate, never a functional claim.
2. TFBS regulatory coupling table (all regulators ≥18; genome-wide networks flagged at ≥6 BGCs)
3. CGAD chitinolytic capacity (from scan states; note if BGC-region only)
4. Polysaccharide substrate coupling (null result must be stated explicitly)
5. bldA tier → host developmental mapping
6. Disease-defence matching for host
7. Primary ecological model hypothesis (Mutualist / Commensal / Opportunistic / Unknown)
8. ≥3 testable predictions (each with: culture condition, compound class, specific BGC)
9. Claim-safety statement

---

## MODULE 15 — MISSINGNESS REGISTER

Required categories: assembly, annotation, biological, chemical, bioactivity, ecological, resistance gene, proteome scope. One row per missing item; state the effect on interpretation and the recommended fix.

---

## MODULE 16 — OUTPUT GATES (Full-Run Profile)
> Recommended-figures section is part of a complete report: `docs/modules/DELIVERABLE_FigureSuggestion.md`.

Before delivery, verify:
- [ ] All BGCs accounted for in inventory (count matches Mamey locked count)
- [ ] Every Interior and triggered BGC has a Mode B report or named deferred entry
- [ ] Triage First Board present
- [ ] DAPR AB and AF tracks both present
- [ ] Ecology synthesis present
- [ ] Missingness register present
- [ ] Claim-safety statements present in every Mode B §8
- [ ] No workbook-facing values filled from narrative inference

---

## MODULE 17 — DAPR: DUAL-TRACK AB/AF PRIORITY ROUTING

From triage board AB_auto and AF_auto scores plus CCTT and mechanistic-link flags:

**AB track:** rank by AB_auto; apply MRSA-specific mechanistic links (+2 WL for: glycopeptide/lipopeptide/halogenated-arylpyrrole/enediyne/nikkomycin/orthosomycin/mannopeptimycin classes)

**AF track:** rank by AF_auto; apply Candida-specific mechanistic links (+2 WL for: polyene antifungal/nikkomycin chitin-synthase inhibitor/HSAF-PTM sphingolipid/azole-NRPS classes)

State top 3 per track explicitly. Cross-reference CCTT triggers with mechanistic links.

---

## MODULE 18 — FERMENTATION, INDUCTION, AND EXTRACTION PLAN
> Analytics readiness (class → MW/ionization/UV/polarity/extraction/dereplication, polar-compound caveat): `docs/modules/DELIVERABLE_MetabolomicsReadiness.md`.

For top 3–5 leads: media, temperature, duration, induction condition (DasR/GlcNAc, iron limitation, phosphate limitation, microaerobia as applicable), extraction solvent, primary fractionation method, detection handle (UV, halogen isotope, polyene spectrum, etc.).

---

## MODULE 19 — LAYPERSON-RANKED BGC GUIDE

Top 5 BGCs in plain language (3–5 sentences each): what the cluster makes, why it matters, one sentence on how the compound might be detected. No jargon; no compound identity claims.

---

## MODULE 20 — COMPOUND DETECTION AND ISOLATION BENCH GUIDE

For top 3–5 leads: expected MW range, ionization mode, UV/Vis handle, extraction protocol (explicitly flag if standard C18 is insufficient), primary fractionation, dereplication reference, assay pairing.

---

## MODULE 21 — MASTER MULTI-STRAIN LAYPERSON COMPILATION (cross-strain deliverable)

*Cross-strain deliverable. Runs from completed per-strain Sapote-Mamey outputs or the master workbook — not from a single package. Full spec: monolith §53.*

Produce a finished, seven-part cohort document:

1. **Cover/method header** — cohort + per-habitat strain counts; antiSMASH/MIBiG versions; corrected-count formula (Interior + 0.5×Edge + 0.25×Full-contig); assembly-tier thresholds (Good ≥70 / Moderate 45–69 / Poor 20–44 / Very poor <20); habitat colour key.
2. **Global Ranked Top Targets table** (top 10–15 across habitats): Rank · Strain · Habitat · Assembly (tier+interior%) · Key BGC(s) · Why it ranks · Next experiment. Ranking respects the v9.1 two-level rule — a split-pathway anchor is ranked on pathway-unit evidence, never demoted for a second fragment.
3. **Cross-Habitat Statistics table** — per-habitat: total corrected BGCs; mean/strain (all); mean/strain (reliable only); % novel (<50% MIBiG); good-assembly count; very-poor count. NAPAA excluded from comparative rows; very-poor assemblies excluded from quantitative means (state it).
4. **Per-strain sections** — header (genome Mb · contigs · raw · corrected · interior% · tier · bioassay); 2–4 sentence summary; 5-BGC table (BGC# · Class · Size · Novelty %+label · Layperson headline); assembly/claim caveat line; immediate next-action line.
5. **Verified Citation Library** — per compound family: strains-in-dataset line, mechanism paragraph, verified refs (PMID/DOI/PMCID + evidence-type tag). Verify via Literature Deep Dive; never fabricate.
6. **PNAS-style numbered reference list.**
7. **Claim-safety footer** (genome-mining hypothesis disclaimer; corrected counts for all comparisons).

Data sourcing: stats/counts/tier from Mamey intake+inventory (workbook A2/B1 or manifest/_2_inventory.csv); headlines + next-actions from Sapote interpretation (Mode B §6/§7); strains missing stats listed as "stats pending," never silently dropped.

Output: single Markdown `Layperson_BGC_Guide_[cohort]_[date].md`; render to PDF/DOCX on request (read the relevant SKILL.md first). Apply the §53.4 QA gate before delivery.

---

## MODE B WRITE PROTOCOL

After completing Mode B for each BGC, write the output to the package using the
judgment store write path. This persists Mode B across sessions and enables
PDF-003/004 in the compiled deliverables.

**Load the write module at session start:**
```
docs/modules/MODE_B_WRITE.md
```

After every completed BGC Mode B, call `record_mode_b()` with:
- Full §1–§8 markdown in `mode_b_md`
- 3–5 sentence plain-language summary in `layperson_paragraph` (for PDF-003)
- Condensed §7 isolation strategy in `fermentation_note` (for PDF-004)

At batch end, call `record_batch_complete()` with the list of completed BGC IDs.
The judgment register accumulates across batches — Batch 2 adds to Batch 1 progress.

**Do not skip this step.** Without it, Mode B output remains session-ephemeral and
the compiled deliverables cannot be assembled.

---

## STANDARD TRIGGERS

```
Run sapote_standard on [strain_id]. Mamey package: [filename].
Run sapote_archive on [strain_id]. Mamey package: [filename].
Continue [strain_id] — Batch [N]. Prior batches: BGC[list] complete.
Run DAPR on [strain_id].
Run ecology synthesis for [strain_id].
Run Literature Deep Dive on [topic].
Run CCSM for [habitat]. Strains: [list].
Compile the Master Layperson Guide for [cohort/all strains/habitat].
```

---

## VERSION AND LINEAGE

| Version | Date | Notes |
|---|---|---|
| v1.0 | 2026-05-28 | Initial slim kernel (derived from Sapote monolith v7.8) |
| v1.1 | 2026-06-08 | Modules 17–20 added; full-run profile integrated; Module 13 every-BGC Mode B; Module 14 full ecology synthesis |
| v2.0 | 2026-06-08 | Derived from SAPOTE_MAMEY_BUNDLE_MONOLITH_v9.1.md; two-level split-pathway priority rule (Module 3); Literature Deep Dive replaces legacy Bert/Davey modes; brand cleanup |
| v2.1 | 2026-06-08 | Module 21 added: Master Multi-Strain Layperson Compilation (cross-strain deliverable, monolith §53) |
| v2.2 | 2026-06-09 | Derived-from updated to v9.3; §57 sub-grade grades corrected (HAL/ENE A/B/C, LAN added); T43-LAN and T43-DKP added to Module 6; WL score column added to Module 12 triage board; ten-scan count confirmed |
| v2.3 | 2026-06-22 | Module 0.5 (RG-GMCI front-end validation); Module 2 KCB_top→KCB_anchor provenance-aware; Module 2.5 (architecture-first assessment); reconciled to v9.7.107 |
