> **DEPRECATED DEFAULT ENTRYPOINT (v9.7.147):** Retain for backwards compatibility, but new ChatGPT/Sapote sessions load `docs/CHATGPT_EXECUTION_SLICE_v97147.md`. That execution slice absorbs this profile's useful full-run rules without the slim-kernel override pattern.
>
> **RESTORED v9.4 (2026-06-09):** This profile was marked legacy in v9.2 but contains the authoritative Mode B card template, §57 sub-grade reference, batch-size rules, and full-delivery trigger. Restored as active. See CHANGELOG for rationale. Sections A–H remain operative; the monolith §-1.2/§-1.4 governs run modes, this profile governs per-BGC Mode B card structure and full-delivery batching.

# Sapote Full-Run Profile — v1.9.7
**Prepend to any Sapote-slim judgment session to activate full project-wide delivery.**  
**Compatible with:** Mamey v1.9.3+ `manifest.json`  
**Designed for:** New users and any session where complete per-strain delivery is expected without scope negotiation.

---

## HOW TO USE THIS DOCUMENT

For new ChatGPT/Sapote sessions, load `docs/CHATGPT_EXECUTION_SLICE_v97147.md`. This file is retained for legacy sessions only. If this profile is loaded with the slim kernel, the execution slice still wins wherever rules conflict.

**Full run trigger:**
```
Load Mamey output for [Strain]. Run full project-wide delivery.
```

That trigger activates all modules below and in the slim kernel. No further scope confirmation is needed from the user.

---

## SECTION A — DEFAULT BEHAVIOR (NON-NEGOTIABLE)

**Do not ask scope.** Do not offer abbreviated alternatives. Do not pause for user confirmation between modules or BGC batches. Produce the complete per-strain delivery suite in the order specified below, for every strain loaded.

**If BGC count ≤ 20:** complete all Mode B in one block before proceeding to DAPR.  
**If BGC count 21–60:** batch Mode B in groups of 15–20. Announce each batch header:  
> **Mode B — Batch [N] of [total]: BGC[X]–BGC[Y]. Continuing.**  
Proceed immediately to the next batch without stopping.  
**If BGC count > 60:** batch in groups of 15. At the start, announce total batch count. Any BGC receiving truncated treatment due to Arch E + WL ≤ 0 + zero diagnostic domains must be documented with a one-sentence justification — silent omission is a completeness failure.

**Delivery order:**
1. Assembly declaration + BGC inventory (Slim Modules 1–2)
2. Architecture confidence grades (Slim Module 3)
3. WL scoring + Triage First Board (Slim Modules 4, 12)
4. Hallucination-trap audit for all BGCs (Slim Module 5)
5. CCTT routing, §57 sub-grades, bldA/TTA gating, resistance tiers, UMED, EFLS (Slim Modules 6–11)
6. **Full Mode B for every BGC** (Section B of this profile — overrides Slim Module 13)
7. **DAPR — dual AB/AF priority tracks** (Section C — new Module 17)
8. **Mechanistic Ecology Synthesis — full format** (Section D — overrides Slim Module 14)
9. **Fermentation/Induction/Extraction Plan** (Section E — new Module 18)
10. **Layperson-Ranked BGC Guide** (Section F — new Module 19)
11. **Compound Detection and Isolation Bench Guide** (Section G — new Module 20)
12. Missingness register (Slim Module 15)
13. Full-run output gate check (Section H — overrides Slim Module 16)

---

## SECTION B — MODE B OVERRIDE (Replaces Slim Module 13)

**Tiered Mode B depth** — applied by AB_auto / AF_auto / CCTT triggers from the Mamey triage board:

> **Scale note (not the DAPR scale):** `AB_auto` and `AF_auto` here are the **Mamey engine scores** from the `_4_triage_board.csv` — a continuous scale with a floor of ~20 and a ceiling in the 90s (Exceptional ≥85 / High ≥70 / Medium ≥50 / Inventory <50 in Mamey terms). These are **not** the Section C DAPR scores, which use a separate 0–20 cap (≥14 HIGH). The thresholds 55 / 45 / 40 / 30 below are on the Mamey scale and are well within its normal range.

| Tier | Criteria | Treatment |
|---|---|---|
| **Full Mode B** | AB_auto ≥ 55 **or** AF_auto ≥ 45 **or** any CCTT trigger **or** Interior/A + KCB ≥ 15,000 | All §1–§48 sections + claim-safety statement |
| **Candidate card** | AB_auto 40–54 **and** AF_auto 30–44, no CCTT, no EFLS, Interior/A | §1 (boundary), §3 (class), §8 (wet-lab) only — ~½ page |
| **Minimum candidate card** | AB_auto < 40 **and** AF_auto < 30, no CCTT, no EFLS, and evidence too thin for Full Mode B | BGC_ID with locator · class/product hypothesis · KCB · edge status · one interpretive sentence · next action |
| **One-line ledger** | Arch E **and** WL ≤ 0 **and** no triggers **and** no EFLS | `[BGC#] — Arch E, WL [score], no triggers: inventory only.` |

This replaces the prior "Full Mode B for every BGC" rule that produced 100-page outputs for 28-BGC strains. A strain with 28 BGCs will now produce approximately:
- 4–8 Full Mode B cards (~3 pages each = 12–24 pages)
- 6–10 candidate cards (~½ page each = 3–5 pages)
- Remainder as minimum candidate cards (~3–5 lines each; no silent omissions)
- Total: approximately 20–35 pages for a typical MODERATE-assembly strain

**Override:** If the user requests "archive-quality", "full depth", or "CM-7 / Full Spread", revert to Full Mode B for every non-Arch-E BGC.

**Mandatory for every Full Mode B card regardless of tier:**
- Canonical contig identifier block: `BGC_ID | contig_full_name | regionXXX | start–end bp | size kb | edge_status | Arch | TTA_tier`
- §34 hallucination-trap verdict
- Claim-safety statement

Even for exception-qualified BGCs, document the justification explicitly: `[BGC#] — Arch E, WL [score], no triggers: minimum candidate card only because [reason].`

**Full Mode B front matter and action summary (mandatory, but not the complete section structure):**

The block below does not replace the exact ordered §1–§48 contract. First emit the canonical scaffold
with `python mamey_run.py emit-modeb-template --package <package_dir> --bgc <BGC_ID>`, then follow
`docs/MODEB_GATE_CLEAN_AUTHORING.md`. A card containing only this summary is partial even when every
field is filled. Do not infer completeness from length, headings, or a gate result alone.
```
### BGC[N] — [Class] — Arch [grade] — WL [score]

BGC_ID: [ID] | Contig: [full_contig_name] | Region: [regionXXX]
Coords: [start]–[end] bp | Size: [N] kb | Edge: [status] | Arch: [grade] | TTA: [tier]

**KCB:** [compound] ([cumulative], [N] proteins) | **RiQ:** [score]
**Class sub-grade:** [from §57] | **DSS:** [0–5]

**§34 Trap Card:** [complete card — every applicable trap listed; NONE if clean]

**Domain evidence:** [key domains; note GBK Pfam tier-1 hits if available]
**Resistance gene:** [Tier 1/2/3/null — concordance verdict — HGT guard if relevant]
**UMED status:** [IN-CLUSTER / GAP / GAP-no-candidate / not applicable]
**EFLS pairs:** [any linked BGCs with score, or NONE]

**WL score rationale:** [itemized: criterion → score; total]

**Safe claim:**
> "BGC[N] encodes biosynthetic capacity consistent with [class]; compound production,
> structural elucidation, and bioactivity attribution require metabolomics, fractionation,
> isolation, or genetic proof."

**Wet-lab action:**
- Sequencing priority: [HIGH/MEDIUM/LOW — long-read needed Y/N?]
- Activation priority: [HIGH/MEDIUM/LOW — bldA tier, TFBS trigger, OSMAC recommendation]
- Isolation priority: [HIGH/MEDIUM/LOW — WL score, detection handle]
- Extraction class: [from wetlab_rows in manifest]
- Detection handle: [UV λ / isotope pattern / characteristic mass / NONE]
```

---

## SECTION C — MODULE 17: DAPR — DUAL-TRACK AB/AF PRIORITY ROUTING

Run after the Triage First Board (Slim Module 12) and before Mode B. Outputs two ranked tables — antibacterial (AB) and antifungal (AF) — as independent tracks. A BGC can rank in both, one, or neither.

**Exclusions (apply before scoring):**
- NAPAA BGCs → excluded from both tracks; mark `NAPAA-EXCL`
- QS-ecology BGCs → excluded from both tracks; mark `QS-ECOLOGY-ONLY`

**Split-pathway anchors (v9.1 two-level rule):** When a BGC is identified as a split-pathway anchor (Interior BGC with strongest biosynthetic logic in a multi-contig pathway unit), score using the pathway unit's combined evidence — not the individual fragment's Architecture grade. Do not apply the Edge/FC assembly penalty to an Interior anchor simply because a secondary fragment on another contig has Edge/FC status. The anchor's DAPR score must reflect the pathway unit as a whole.

**Scoring cap: 20. Bands: ≥14 HIGH · 10–13 MEDIUM · 6–9 LOW · <6 EXPLORATORY.**

> **Scale note (not the Mamey triage-board scale):** DAPR scores are a **separate 0–20 Sapote-layer system** built from the class-specific signals in the tables below. They are not the same as `AB_auto` / `AF_auto` in the Mamey triage board (which run to the 90s). A DAPR HIGH of ≥14 corresponds to a well-evidenced compound class, not a high Mamey score.

### AB Track scoring signals

| Signal | AB score |
|---|---:|
| β-lactam (blactam product class confirmed) | 12 |
| Azole-RiPP + NRPS (both in same BGC) | 13 (cap) |
| T43-AMC aminocyclitol (2-DOS/streptamine-type) | +7 |
| Glycopeptide NRPS (vancomycin-type domain layout) | 11 |
| Thiopeptide / lanthipeptide + MRSA-relevant KCB | 10 |
| CDA-type lipopeptide NRPS | 9 |
| Interior NRPS or T1PKS + KCB cumulative >5,000 | 8 |
| Resistance gene Tier 1 concordant | +2 |
| WL ≥ 10 | +1 |
| Edge or Full-contig BGC in GOOD/MODERATE assembly | −2 only when truncation materially limits interpretation |
| Edge or Full-contig BGC in POOR/VERY_POOR assembly | 0 (boundary status is primarily an assembly artefact; do not suppress the chemistry picture) |

### AF Track scoring signals

| Signal | AF score |
|---|---:|
| T43-NUC nikkomycin/polyoxin (chitin-synthase inhibitor class confirmed) | 13 |
| T1PKS + S. nodosus / nystatin KCB top hit + large Interior | 12 |
| HSAF/PTM (ceramide synthase inhibitor domain layout confirmed) | 11 |
| Large Interior T1PKS >100 kb (presumptive polyene class) | 10 |
| Azole-NRPS (echinocandin/pneumocandin-type) | 10 |
| T43-GLY putative glucan synthase inhibitor class | 9 |
| LMPKS-A/B polyene rescue confirmed | +2 |
| *Candida* bioactivity confirmed at extract level (strain-level data) | +1 |
| WL ≥ 10 | +1 |
| Indolocarbazole class → **do NOT award AF mechanistic bonus** | 0 (cytotoxic) |
| Edge or Full-contig BGC in GOOD/MODERATE assembly | −2 only when truncation materially limits interpretation |
| Edge or Full-contig BGC in POOR/VERY_POOR assembly | 0 (boundary status is primarily an assembly artefact; do not suppress the chemistry picture) |

### DAPR output format

```
## DAPR — Dual-Track Priority

### Antibacterial (AB) Track

| Rank | BGC | Class | AB score | Band | Key signal | Concordant resistance |
|---:|---|---|---:|---|---|---|
| 1 | ... | ... | ... | HIGH | ... | ... |
...

### Antifungal (AF) Track

| Rank | BGC | Class | AF score | Band | Key signal | Extraction flag |
|---:|---|---|---:|---|---|---|
| 1 | ... | ... | ... | HIGH | ... | ... |
...

**Primary AB lead:** BGC[N] — [class] — AB score [X] ([band])
**Primary AF lead:** BGC[N] — [class] — AF score [X] ([band])
**Dual-threat BGCs (AB ≥10 AND AF ≥10):** [list, or NONE]
**NAPAA excluded:** [BGC list, or NONE]
**QS-ecology only:** [BGC list, or NONE]
```

**Claim-safety:** DAPR scores are structural class priors based on domain architecture and genomic evidence. No BGC-level bioactivity is attributed without fractionation, metabolomics, or genetic proof.

---

## SECTION D — MODULE 14 OVERRIDE: MECHANISTIC ECOLOGY SYNTHESIS (Full Format)

Replaces the slim kernel's "§ECO ECOLOGICAL SYNTHESIS (SLIM)." Same ecological logic applies; output must be full format, not one-sentence hooks.

**Required output structure:**

**1. Ecological coupling statement** (one paragraph, not one sentence): describe the host/substrate, the ecological pressures it creates, and how the strain's BGC repertoire maps onto those pressures. Integrate TFBS, CCTT class signals, and QS BGC routing.

**2. TFBS-ecology coupling table** (mandatory; all six regulators):

| Regulator | Ecological substrate coupling | Signal present? | BGCs coupled |
|---|---|---|---|
| DasR | Chitin from [source] → GlcNAc de-repression of AB BGCs | PRESENT/ABSENT/NOT_SCORED | [BGC list] |
| FuR/DmdR1 | Iron competition in [substrate context] | PRESENT/ABSENT/NOT_SCORED | [BGC list] |
| IolR | Inositol/pollen/photobiont polyols | PRESENT/ABSENT/NOT_SCORED | [BGC list] |
| ANR | Microaerobic zones | PRESENT/ABSENT/NOT_SCORED | [BGC list] |
| LexA | Oxidative/ROS stress | PRESENT/ABSENT/NOT_SCORED | [BGC list] |
| GBL receptor | Density/quorum signalling | PRESENT/ABSENT/NOT_SCORED | [BGC list] |

**3. BGC-ecology pairings:** For each PRESENT TFBS regulator, state which BGCs are predicted active under that ecological condition and give one sentence of mechanistic rationale.

**4. Three testable induction predictions** (format per prediction):
> *Prediction [N]: [Induction condition] → predicted upregulation of BGC[X] → expected metabolomic readout → assay type.*
> *Falsification: [what result would disprove this prediction].*

**5. Cross-habitat note:** State whether this strain's ecology-BGC coupling matches or diverges from patterns documented in prior cross-strain CCSM analysis. If the cross-strain database is not available in this session, state: *"Cross-habitat comparison deferred to Sapote full workflow (CCSM §41); within-strain ecology signals documented above."*

**6. Claim-safety statement (mandatory):** *"All ecological hypotheses reflect biosynthetic capacity inferred from genome mining and regulatory motif analysis. No ecological function, metabolite production, or competitive outcome is proven without direct experimental evidence (metabolomics, genetics, ecological co-culture)."*

---

## SECTION E — MODULE 18: FERMENTATION, INDUCTION, AND EXTRACTION PLAN

Run after DAPR. Scope: top-3 AB leads and top-3 AF leads by DAPR score (up to 6 BGCs; fewer if collection is smaller). For dual-threat BGCs counting on both tracks, count once.

**Step 1 — Summary table:**

| BGC | Class | DAPR band | bldA tier | Induction cue (TFBS) | Media | Extraction class | Detection handle |
|---|---|---|---|---|---|---|---|
| BGC[N] | ... | AB HIGH | T[1–4] | [regulator × count] | ISP2/YEME/R5/SMMS | polar/semi-polar/nonpolar | UV [λ] / [mass] / [isotope] |

*Column notes:*
- **bldA tier:** from Slim Module 8. T3/T4 → note alternative host or constitutive promoter requirement.
- **Induction cue:** highest-evidence TFBS regulator for this BGC from manifest scan data; include motif count if available.
- **Extraction class:** derive from compound class (polar = nucleosides/aminoglycosides/RiPPs; semi-polar = polyketides/NRPs; nonpolar = terpenes/macrolides). Source wetlab_rows in manifest for class defaults.
- **Detection handle:** the single most distinctive spectral feature for this compound class.

**Step 2 — Narrative for #1 AB lead and #1 AF lead** (one paragraph each): class-specific fermentation rationale integrating bldA tier, TFBS evidence, extraction, and assay recommendation. Cite the specific TFBS count or resistance gene that supports the induction recommendation.

---

## SECTION F — MODULE 19: LAYPERSON-RANKED BGC GUIDE

Produce after all Mode B and DAPR are complete. Audience: non-specialist reader (thesis committee member, grant reviewer, collaborator outside natural products). **No unexplained jargon.** Target quality: the reference implementation is `examples/layperson_guide_exemplar.md`.

**Translation rules:**
- WL score → "priority score (X out of 20)"
- KCB → "similarity score to known compounds (% MIBiG)"
- NRPS/PKS → "protein assembly-line enzyme"
- Interior/Edge → "complete region / contig fragment"
- bldA T4 → "regulated by developmental switch — needs extended fermentation"
- Arch A/B → "good evidence" | C → "partial evidence" | D/E → "fragment only"
- "Known (N%)" → MIBiG knownclusterblast highest similarity; "Novel" → <50% similarity

**Per-strain format — MANDATORY:**

```
[StrainID] — [Habitat/Source]
[Genome Mb] | [N] ctgs | Raw: [N] | Corr: [N] | [X]% interior | [Good/Moderate/Poor/Very poor]

[Header stat box — inline: Genome / Contigs / Raw BGCs / Corrected / Interior % / Assembly / Bioassay]

[2–3 sentence narrative explaining why this strain is interesting, in plain English. Name specific BGC
classes, mention the habitat if known, state the highest-interest finding explicitly.]

BGC table — TOP 5 (ranked by combined discovery value):

| BGC | Class | Size | Novelty | Layperson headline |
|---|---|---|---|---|
| BGC-NN | [plain class name] | [N] kb | Known (N%) / Novel | [ONE plain-English sentence: what it makes, why it matters] |

Rules for the BGC table:
- "Known (N%)" = highest MIBiG cluster similarity from antiSMASH knownclusterblast; "Novel" if <50%
- Layperson headline MUST name the compound class (e.g., "spirotetronate antibiotic", "crocagin-class peptide")
- If BGC has a specific compound name (migrastatin, HSAF, etc.) USE IT
- NAPAA/housekeeping BGCs must be flagged: "epsilon-Poly-L-Lysine — housekeeping marker, not a discovery target"
- Enediyne/cytotoxic BGCs: emit neutral "[E-signal]" note; cytotoxic/DNA-damaging class → standard lab cytotoxic-class handling per SOPs. No per-cluster BSL-2 flag (selective biosafety flags give false reassurance that other clusters are safe by comparison).
- hglE-KS-PREV-001 BGCs: label as "hglE-KS prevalent domain — structural novelty; function unknown"

Assembly/claim caveat (1–3 sentences, mandatory): state what cannot be claimed from current data.

Immediate next action (1 sentence, specific): the single most important experiment or sequencing action.
```

**For multi-strain guides — additional required sections:**

```
Global Ranked Top Targets table (top 10–13 across all strains):

| Rank | Strain | Habitat | Assembly | Key BGC(s) | Why it ranks here | Next experiment |
|---|---|---|---|---|---|---|

Cross-Habitat Statistics table (corrected counts only):

| Metric | [Habitat A] | [Habitat B] | [Habitat C] |
|---|---|---|---|
| Total corrected BGCs | N | N | N |
| Mean corrected BGCs/strain (all) | N | N | N |
| Mean corrected BGCs/strain (reliable only) | N | N | N |
| % novel (<50% MIBiG) | N% | N% | N% |
| Good assemblies (≥70% int.) | N (IDs) | N | N |
| Very poor assemblies (<20%) | N (IDs) | N | N |

Key observations: [3–5 bullet observations comparing habitats — novelty gradient, BGC richness, genus-specific patterns]
```

---

## SECTION G — MODULE 20: COMPOUND DETECTION AND ISOLATION BENCH GUIDE

Audience: bench scientist with no genomics background. Scope: all HIGH and MEDIUM BGCs (AB ≥ 45 or AF ≥ 35 or any CCTT trigger). **Target quality: `examples/bench_guide_exemplar.md`.** The current Mamey package provides genome evidence; this module translates that into specific, actionable bench protocols.

**The bench guide has three required sub-sections per strain:**

---

### Sub-section 1: Known / Reference BGCs (positive expression controls)

Purpose: BGCs with ≥60% MIBiG similarity — these should produce under standard conditions and serve as metabolic activity markers. List all, then build the **compound detection matrix**:

```
Known / Reference BGCs (positive expression controls)

| Compound · MIBiG% | [BGC#] · [N%] | [BGC#] · [N%] | [BGC#] · [N%] | [BGC#] · [N%] |
|---|---|---|---|---|
| Compound class | [class] | [class] | [class] | [class] |
| Est. MW (Da) | [value or range; flag as estimate] | ... | | |
| UV / Vis | [λ nm or "no chromophore"] | ... | | |
| Colour / CAS | [colony colour or "CAS assay"] | ... | | |
| Extraction | [media · days · °C; solvent; method] | ... | | |
| LC-MS mode | [ESI+/− · expected m/z · key neutral losses] | ... | | |
| Key assay | [target organism + MIC / IC50 / enzymatic] | ... | | |
| Induction hint | [standard / OSMAC / bldA note if T4] | ... | | |
| Safety | [cytotoxic-class handling per SOPs / [E-signal] if ENE / low cytotox / GRAS] | ... | | |
```

Column rules:
- One column per known BGC; maximum 4 columns across; wrap if more
- MW values must be flagged "(estimate)" unless taken from an isolated compound of ≥70% MIBiG similarity
- UV chromophore listed as exact λ if known class; "no chromophore — rely on MS" otherwise
- Colour/CAS: list colony colour if pigmented compound; "CAS assay" if siderophore; "none" if colourless
- Safety: cytotoxic-class handling per standard lab SOPs (non-selective). Enediyne → "[E-signal]" note only; no per-cluster BSL-2 flag.

---

### Sub-section 2: Novel / Highest-Priority BGC Candidates

Purpose: BGCs with <50% MIBiG similarity that are the primary discovery targets. Format:

```
Novel / Highest-Priority BGC Candidates

| BGC# | Size (kb) | Product type | MIBiG% | Closest reference | Priority |
|---|---|---|---|---|---|
| BGC-NN | N kb | [class] | N% | [compound name] | HIGH / MED / LOW |

[For each HIGH priority BGC — one concise paragraph:]
BGC-NN: [class description]. MIBiG%: [N%] vs [closest reference compound]. 
Extraction: [specific solvent and conditions]. Detection: [UV/MS handle]. 
Special note: [any caveat — edge truncation, T4 gating, ENE flag, §34 trap, etc.]
```

Priority assignment:
- HIGH: Interior/Arch A or B + AB ≥ 50 or AF ≥ 40 + any CCTT trigger, OR Interior/Arch A + AB ≥ 65
- MED: Edge/Arch C + CCTT trigger, OR Interior/Arch A + AB 40–49 without CCTT
- LOW: Full-contig/Arch D, or no CCTT + AB < 40 + AF < 30

For EACH HIGH BGC, include these specific fields inline:
- Extraction protocol (medium, temp, duration, solvent, SPE if needed)
- Detection handle (UV λ, isotope pattern, MW range, ESI mode)
- Special handling (bldA T4 note if applicable; pH-lability if spirotetronate; "[E-signal]" note if ENE/IDC — no per-cluster BSL-2 flag)

---

### Sub-section 3: Fermentation Strategy

One paragraph per strain, structured as: `[Genus] · [medium] · [°C] · [rpm]. [Screen result and what it means]. [OSMAC sequence if needed]. [Priority BGC extraction targets]. [Long-read note if POOR/VERY_POOR assembly]. [Dereplication priority — what known compounds to subtract before reporting novel hits].`

OSMAC standard sequence (include when screen-negative):
1. ISP2 standard conditions
2. Low-phosphate medium (phosphate-limited sporulation)
3. Low-nitrogen medium
4. Alternative carbon source (mannitol, glycerol, or inositol for IolR-active strains)
5. Co-culture with Bacillus subtilis spores (broad elicitor)
6. [Add any TFBS-guided induction: GlcNAc for DasR, iron-depletion for FuR, chitin for CGAD strains]

---

## SECTION H — FULL-RUN OUTPUT GATES (Overrides Slim Module 16)

Before delivering any report, verify all items below. Failure to pass any gate = completeness failure. Report the gate check result explicitly.

**Slim kernel gates (inherited; verify all):**
- [ ] Every BGC in the Mamey JSON appears in the inventory table
- [ ] Every lanthipeptide region has a UMED status
- [ ] Every T43-triggered BGC has a Class sub-grade (§57)
- [ ] Every enediyne BGC has a CalC/apo-protein check result
- [ ] Every glycosylation-arm candidate (≥3 hits) has a §34.5 trap verdict and proposed pairing
- [ ] Every QS-signal BGC has `[QS-ECOLOGY-ONLY]` flag and is routed to ecology only
- [ ] Every NAPAA BGC has `[NAPAA]` flag and is excluded from all comparative claims
- [ ] All abbreviated ledger entries (Arch E exception only) include the `§34 trap verdict` field
- [ ] The hallucination-trap audit statement appears in the report
- [ ] The claim-safety statement appears on every Mode B card

**Full-run additional gates:**
- [ ] DAPR complete — separate AB and AF ranked tables, with NAPAA/QS exclusions documented
- [ ] Every BGC appears in at least one DAPR track row, or is documented as excluded with reason
- [ ] Fermentation/Induction/Extraction Plan produced for top-3 AB + top-3 AF leads
- [ ] Layperson-Ranked BGC Guide produced (all required sections present)
- [ ] Bench Guide produced for top-2 AB + top-2 AF leads (all mandatory fields present per BGC)
- [ ] Mechanistic Ecology Synthesis is full-format (6-regulator TFBS table + 3 testable predictions + claim-safety statement)
- [ ] Every BGC has either a full Mode B card or a documented Arch-E/WL≤0/no-trigger exception justification — no BGC silently omitted
- [ ] output_checklist rows for Technical Report, Bench Guide, Layperson Guide show `COMPLETE` not `DOWNSTREAM`

---

## STANDARD FULL-RUN TRIGGERS

| Intent | Trigger phrase | Scope |
|---|---|---|
| **Full project-wide delivery (default)** | `Load Mamey output for [Strain]. Run full project-wide delivery.` | All modules — this profile + slim kernel |
| Triage only (abbreviated) | `Run Sapote-slim triage for [Strain].` | Slim Modules 1–12 only; this profile inactive |
| Specific BGC deep dive | `Run Sapote full Mode B for BGC[N] in [Strain].` | Sections B + slim §31 §33 §34 §43 §45 §52 §57 |
| DAPR only | `Run DAPR for [Strain] using existing triage board.` | Section C only |
| Bench guide only | `Generate bench guide for top leads in [Strain].` | Sections E + G only |

---

## VERSION AND COMPATIBILITY

**Full-Run Profile v1.9.7** — extends Sapote-Slim Judgment Kernel v1.0 (Mamey v1.9.3+).  
**Lab:** 
**Analyst:** Alexander J. Smith (ORCID: 0000-0002-7987-1460)  
**Affiliation for all deliverables:** 

Sections added by this profile (not in slim kernel): Modules 17 (DAPR), 18 (Fermentation Plan), 19 (Layperson Guide), 20 (Bench Guide). Section B overrides Slim Module 13. Section D overrides Slim Module 14. Section H extends Slim Module 16.

Cross-strain deliverables (CCSM, literature deep dives, manuscript figures, RG-GMCI statistics, and the Master Multi-Strain Layperson Compilation) are specified in SAPOTE_MAMEY_BUNDLE_MONOLITH.md (§41 CCSM, §53 Master Layperson Compilation) and the slim kernel (Module 21). Run them in a Claude Project with the per-strain outputs or master workbook available.
