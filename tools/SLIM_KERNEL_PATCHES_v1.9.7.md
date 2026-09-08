
> **APPLICATION STATUS (v9.3, 2026-06-09):** All patches in this specification have been applied.
> Patches 1–7 → `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` (now at v2.2).
> Patch 8 → `mamey/output_checklist.py` (DOWNSTREAM → REQUIRED; DAPR rows added).
> Patch 9 → `docs/HOW_TO_USE.md` (default trigger updated).
> `prompts/FULL_RUN_PROFILE.md` is active (restored in v9.3; was marked legacy in v9.2).
> Do not re-apply; this document is retained as a specification record.

# Slim Kernel + output_checklist.py — Patch Specification v1.9.7
**Apply these patches to:** `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` and `mamey/output_checklist.py`  
**Effect:** Full project-wide delivery becomes the default; no scope negotiation.  
**Alternative:** Load `prompts/FULL_RUN_PROFILE.md` before the slim kernel to achieve the same effect without patching the kernel.

---

## Patch 1 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: HOW TO USE — Default behavior block

**Location:** After the line `The LLM will read the JSON, run all judgment modules in this kernel, and deliver the full analytical package.` (end of Step 3 block)

**Insert after that line:**

```markdown
**Default delivery behavior (enforced for all full-run sessions):**  
Do not ask scope. Do not offer abbreviated alternatives. Do not pause for user confirmation between modules or BGC batches. Produce the complete per-strain delivery suite in the order specified, for every strain loaded. If the user explicitly requests a shorter scope (triage-only, specific BGC), honour that request; otherwise, full delivery is the default.

If BGC count ≤ 20: complete all Mode B in one block before proceeding to DAPR.  
If BGC count 21–60: batch Mode B in groups of 15–20; announce each batch:  
> **Mode B — Batch [N] of [total]: BGC[X]–BGC[Y]. Continuing.**  
If BGC count > 60: batch in groups of 15; announce total batch count at the start; any BGC truncated to a one-sentence ledger entry requires explicit Arch-E/WL≤0/no-trigger justification.
```

---

## Patch 2 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: MODULE 13 — Expand trigger scope

**Location:** Lines beginning `Apply to: every Interior BGC` through `Abbreviated ledger entry for all others (Edge/FC, no trigger, KCB ≤5,000, WL <7).`

**REPLACE the two lines:**
```
Apply to: every Interior BGC · every T43-triggered BGC · every BGC with WL ≥7 · every KCB >5,000 · every EFLS split-pathway candidate.

Abbreviated ledger entry for all others (Edge/FC, no trigger, KCB ≤5,000, WL <7).
```

**WITH:**
```
Apply to: EVERY BGC. Full Mode B for all BGCs regardless of edge status, WL score, or KCB.

Exception — a BGC may receive a one-sentence ledger entry (not a full Mode B card) if and only if ALL THREE hold:
(1) Architecture Confidence = E  (2) WL score ≤ 0  (3) No CCTT trigger, no EFLS pairing, no UMED flag, no resistance gene.
Even for exception-qualified BGCs, document the justification explicitly: `[BGC#] — Arch E, WL [score], no triggers: one-sentence ledger only.`
```

**Also REMOVE the "Abbreviated ledger minimum fields" table** (the table with columns BGC #, Node/contig, Class, Edge status, Architecture Confidence, WL score, Priority tier, §34 trap verdict, Treatment status). This table no longer applies in full-run mode.

---

## Patch 3 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: MODULE 14 — Upgrade ecology synthesis

**Location:** Line `## MODULE 14 — §ECO ECOLOGICAL SYNTHESIS (SLIM)`

**REPLACE the header:**
```
## MODULE 14 — §ECO ECOLOGICAL SYNTHESIS (SLIM)
```

**WITH:**
```
## MODULE 14 — §ECO MECHANISTIC ECOLOGY SYNTHESIS
```

**Location:** At the end of MODULE 14, after the last existing paragraph, before the `---` separator.

**INSERT:**
```markdown
**Full-format output required (mandatory structure):**

1. **Ecological coupling paragraph** (not a single sentence): host/substrate, ecological pressures, BGC repertoire mapping.

2. **TFBS-ecology coupling table** (all six regulators):

| Regulator | Ecological coupling | Signal present? | BGCs coupled |
|---|---|---|---|
| DasR | Chitin → GlcNAc de-repression of AB BGCs | PRESENT/ABSENT/NOT_SCORED | [list] |
| FuR/DmdR1 | Iron competition | PRESENT/ABSENT/NOT_SCORED | [list] |
| IolR | Inositol/polyols | PRESENT/ABSENT/NOT_SCORED | [list] |
| ANR | Microaerobic zones | PRESENT/ABSENT/NOT_SCORED | [list] |
| LexA | Oxidative/ROS stress | PRESENT/ABSENT/NOT_SCORED | [list] |
| GBL receptor | Density/quorum signalling | PRESENT/ABSENT/NOT_SCORED | [list] |

3. **BGC-ecology pairings:** for each PRESENT regulator, name the coupled BGCs with one sentence of mechanistic rationale.

4. **Three testable induction predictions:** format each as  
> *Prediction [N]: [condition] → BGC[X] upregulation → [metabolomic readout] → [assay type]. Falsification: [what result disproves this].*

5. **Cross-habitat note:** state concordance with prior CCSM patterns, or defer: *"Cross-habitat comparison deferred to Sapote full workflow (CCSM §41)."*

6. **Claim-safety (mandatory):** *"All ecological hypotheses reflect biosynthetic capacity inferred from genome mining and regulatory motif analysis. No ecological function or competitive outcome is proven without direct experimental evidence."*
```

---

## Patch 4 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: Add Modules 17–20 and update STANDARD TRIGGERS

**Location:** Between `## MODULE 16 — OUTPUT GATES` block and `## CLAIM-SAFETY STATEMENT`

**INSERT the four new modules in full** — see `prompts/FULL_RUN_PROFILE.md` Sections C, E, F, G for the complete module text. Copy Sections C through G verbatim and insert here, renumbering as Modules 17–20.

---

## Patch 5 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: MODULE 16 — Extend output gates

**Location:** At the end of the MODULE 16 checklist, before the `---` separator.

**INSERT after the last existing `- [ ]` gate item:**
```markdown
**Full-run deliverable gates (required when this profile is active):**
- [ ] DAPR complete — separate AB and AF ranked tables produced, NAPAA/QS exclusions documented (Module 17)
- [ ] Every BGC appears in at least one DAPR track, or is documented as excluded with reason
- [ ] Fermentation/Induction/Extraction Plan produced for top-3 AB + top-3 AF leads (Module 18)
- [ ] Mechanistic Ecology Synthesis is full-format: 6-regulator TFBS table + 3 testable predictions + claim-safety (Module 14 full)
- [ ] Layperson-Ranked BGC Guide produced — all required sections present (Module 19)
- [ ] Bench Guide produced for top-2 AB + top-2 AF leads — all mandatory fields present (Module 20)
- [ ] Every BGC has a full Mode B card or a documented Arch-E exception justification — no silent omissions
```

---

## Patch 6 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: STANDARD TRIGGERS — Add full-run trigger and rename default

**Location:** `## STANDARD TRIGGERS` table

**REPLACE:**
```markdown
| Full analysis from JSON | `Load Mamey output for [Strain]. Run Sapote-slim judgment analysis.` | All modules |
```

**WITH:**
```markdown
| **Full project-wide delivery (default)** | `Load Mamey output for [Strain]. Run full project-wide delivery.` | All modules including DAPR, Bench Guide, Layperson Guide |
| Slim analysis (triage + Mode B for top leads only) | `Load Mamey output for [Strain]. Run Sapote-slim judgment analysis.` | Modules 1–16 (abbreviated Mode B scope) |
```

**Also ADD at end of the table:**
```markdown
| DAPR only | `Run DAPR for [Strain] using existing triage board.` | Module 17 only |
| Bench guide only | `Generate bench guide for top leads in [Strain].` | Modules 18 + 20 |
```

---

## Patch 7 — SAPOTE_SLIM_JUDGMENT_KERNEL.md: VERSION AND LINEAGE — Update version number

**REPLACE:**
```
**Sapote-Slim Judgment Kernel v1.0** — extracted from Sapote Actinomycete Natural Product Discovery Workflow v8.10.2 (2026-06-04).
```

**WITH:**
```
**Sapote-Slim Judgment Kernel v1.1** — extracted from Sapote Actinomycete Natural Product Discovery Workflow v8.10.2; extended with full-run profile modules 2026-06-08.
```

**Also REMOVE from the Sections removed list:**
```
§21 (Literature Deep Dive)
```
and add:
```
§21 (Literature Deep Dive) — hooks for top AB/AF leads retained; full deep dive requires Sapote v8.10.2 with web search.
```

---

## Patch 8 — mamey/output_checklist.py: Change DOWNSTREAM status to REQUIRED

**Location:** Lines 105–107 of `mamey/output_checklist.py`

**REPLACE all three DOWNSTREAM rows:**
```python
{'Phase': 'Sapote reporting', 'Output_or_task': 'Technical report PDF', 'Expected_artifact_or_evidence': f'{strain}_Mamey_Sapote_Technical_Report.pdf', 'Status': 'DOWNSTREAM', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote report layer', 'Next_action': 'Generate after judgment workbook/ledger.'},
{'Phase': 'Sapote reporting', 'Output_or_task': 'Bench detection/isolation guide PDF', 'Expected_artifact_or_evidence': f'{strain}_Compound_Detection_Isolation_Bench_Guide.pdf', 'Status': 'DOWNSTREAM', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote report layer', 'Next_action': 'Generate with metabolomics targets and assay plan.'},
{'Phase': 'Sapote reporting', 'Output_or_task': 'Layperson ranked guide PDF', 'Expected_artifact_or_evidence': f'{strain}_Layperson_Ranked_BGC_Guide.pdf', 'Status': 'DOWNSTREAM', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote report layer', 'Next_action': 'Generate after ranked lead selection.'},
```

**WITH:**
```python
{'Phase': 'Sapote reporting', 'Output_or_task': 'Technical report PDF', 'Expected_artifact_or_evidence': f'{strain}_Mamey_Sapote_Technical_Report.pdf', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote full-run profile (Modules 1-20)', 'Next_action': 'Run full project-wide delivery trigger in Sapote; compile Mode B + DAPR + Ecology into technical report.'},
{'Phase': 'Sapote reporting', 'Output_or_task': 'DAPR dual-track priority table', 'Expected_artifact_or_evidence': f'{strain}_DAPR_AB_AF_Priority.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 17 (DAPR)', 'Next_action': 'Run DAPR module after triage board is complete.'},
{'Phase': 'Sapote reporting', 'Output_or_task': 'Fermentation/Induction/Extraction Plan', 'Expected_artifact_or_evidence': f'{strain}_Fermentation_Induction_Plan.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 18 + wetlab_rows from manifest', 'Next_action': 'Run Module 18 after DAPR; derive from bldA tier + TFBS + wetlab_rows.'},
{'Phase': 'Sapote reporting', 'Output_or_task': 'Layperson ranked guide', 'Expected_artifact_or_evidence': f'{strain}_Layperson_Ranked_BGC_Guide.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 19', 'Next_action': 'Generate after Mode B and DAPR are complete; use plain-English translation rules from Module 19.'},
{'Phase': 'Sapote reporting', 'Output_or_task': 'Compound Detection and Isolation Bench Guide', 'Expected_artifact_or_evidence': f'{strain}_Compound_Detection_Isolation_Bench_Guide.md', 'Status': 'REQUIRED', 'Progress': 'not produced by extraction layer', 'Evidence': 'requires Sapote Module 20 + DAPR top leads', 'Next_action': 'Generate for top-2 AB + top-2 AF leads; include all mandatory fields from Module 20 template.'},
```

---

## Patch 9 — docs/HOW_TO_USE.md: Update default trigger in Stage 2

**Location:** Under `## Stage 2 — Run the judgment kernel`, the `Trigger:` block.

**REPLACE:**
```
Trigger:

```text
Load Mamey output for [Strain]. Run Sapote-slim judgment analysis.
```
```

**WITH:**
```
**Default trigger (full project-wide delivery — recommended):**

```text
Load Mamey output for [Strain]. Run full project-wide delivery.
```

This trigger activates all modules including DAPR, Fermentation Plan, Layperson Guide, and Bench Guide. No scope confirmation is required from the user.

**Abbreviated trigger (triage + top-lead Mode B only):**

```text
Load Mamey output for [Strain]. Run Sapote-slim judgment analysis.
```

Use the abbreviated trigger only when quick triage is needed and full delivery will follow in a separate session.
```

---

## Summary — Files changed

| File | Patches | Effect |
|---|---|---|
| `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` | 1, 2, 3, 4, 5, 6, 7 | Full Mode B every BGC; DAPR + Bench Guide + Layperson Guide as required defaults; full ecology synthesis; updated triggers |
| `mamey/output_checklist.py` | 8 | DOWNSTREAM → REQUIRED for all 3 reporting deliverables; DAPR + Fermentation Plan added as tracked items |
| `docs/HOW_TO_USE.md` | 9 | Default trigger updated; abbreviated trigger documented as secondary option |
| `prompts/FULL_RUN_PROFILE.md` | (new file) | Standalone prepend — loads before slim kernel; achieves same effect as patches 1–7 without editing the kernel |

**Recommendation:** If you want the bundle to ship with full delivery as the default, apply patches 1–9 to the kernel and output_checklist, and include `FULL_RUN_PROFILE.md` as a convenience document for users who want to override a legacy kernel without editing it.
