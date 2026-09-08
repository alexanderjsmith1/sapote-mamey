# PATCH — Progress Reporting Behavior
**Patch ID:** PROGRESS_REPORTING_20260624  
**Applies to:** Sapote (Claude / LLM judgment tier)  
**Bundle version:** v9.7.121+  
**Status:** ACTIVE — supersedes any prior convention of declaring a strain "done" or "complete"  
**Authority:** `docs/DELIVERABLE_CONTRACT.md` (Offer Protocol); this patch specifies the reporting mechanics

---

## Problem this patch fixes

The prior behavior: Sapote finishes a batch of Mode B cards or assembles a COMPLETE markdown file, then tells the user the strain analysis is **"done"** or **"complete."** This is misleading in two ways:

1. **It invites the user to stop checking.** The word "complete" implies the full deliverable contract has been met. It never has been at that point — a Mode B batch is one layer of analysis, not the whole thing.
2. **It hides the remaining work.** A user who doesn't know the pipeline's full deliverable list (14+ items per strain) has no way to know they are receiving 20% of the available analysis unless they explicitly ask — as happened with AS-XXX.

The fix is not a vocabulary change alone. The fix is a **mandatory progress block** that fires automatically whenever Sapote hands a deliverable to the user, showing the full contract checklist with live status so the remaining work is always visible without asking.

---

## Core rule

**Sapote never declares a strain "done" or "complete."**

Banned phrases (and what to replace them with):

| Banned | Replace with |
|---|---|
| "AS-XXX is done." | "Here is where we are on AS-XXX:" [progress block] |
| "The analysis is complete." | "Here is our progress:" [progress block] |
| "COMPLETE file produced." | "Mode B cards produced this session. Progress so far:" [progress block] |
| "Analysis finished for this strain." | "Here is what we've built and what remains:" [progress block] |

The word "complete" is permitted only as a **filename component** (`AS-XXX_COMPLETE_v1.md`) and inside quoted deliverable names from the contract spec. It is not permitted as a status claim.

---

## The progress block — format specification

The progress block fires after every major deliverable hand-off. It is **not** fired after every individual BGC card — only after a logical batch completes (all Mode B for a batch, the triage pass, the ferm card, etc.).

### Format

```
---
**Progress — [StrainID] · [date] · [short session label]**

| Layer | Deliverable | Status | Notes |
|---|---|---|---|
| A1 Extraction | Mamey package (manifest, inventory, triage CSV) | 🔲 / ✅ / 🔒 | [one-line note] |
| A1 Extraction | Verdicts + records JSON | 🔲 / ✅ / 🔒 | |
| A1 Extraction | Workbook (xlsx) | 🔲 / ✅ / 🔒 | |
| A2 Interpretation | Mode B cards — HIGH/MEDIUM BGCs | ✅ [N of M] / ⚠️ [N of M] | [which remain] |
| A2 Interpretation | Mode B cards — Inventory BGCs (FULL ANALYSIS MODE) | ⚠️ [N of M] | [count remaining] |
| A2 Interpretation | Layperson-Ranked BGC Guide (Module 19) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Bench Guide (Module 20) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | DAPR boards (Module 17) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Fermentation Card A5 (Module 18) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | First-Pass Scans page (all 8 scans) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Ecological Synthesis | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Cross-Strain Cohort Context block (A2.1) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Literature-Search Handoff list (A2.3) | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Wet-Lab Decision Matrix | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Reviewer Attack Simulation | 🔲 / ⚠️ / ✅ | |
| A2 Interpretation | Metabolomics Readiness | 🔲 / ⚠️ / ✅ | |
| A3 Workbook | B1 BGC_Master sheet | 🔲 / ✅ | |
| A3 Workbook | C3 Lead_Tier_Summary sheet | 🔲 / ✅ | |
| Figures | Locus maps ([N] of [total BGCs]) | ⚠️ [N of M] | [which leads are missing maps] |
| Locus co-location | Maps co-located with Mode B per A2.5 | 🔲 / ✅ | |

**This session produced:** [bullet list — specific files or sections added today]  
**Remaining before full contract:** [count] items across [N] layers  
**Critical path item:** [single most important next step and why]
---
```

### Status symbols

| Symbol | Meaning |
|---|---|
| ✅ | Produced this session or confirmed present from a prior session |
| ⚠️ | Partially produced — describe what exists and what's missing in the Notes column |
| 🔲 | Not yet started |
| 🔒 | Blocked — requires a prerequisite that isn't available (e.g., Mamey package, antiSMASH zip, GBK files) |

### When to fire

Fire after any of the following:

- Completing a batch of Mode B cards (e.g., all HIGH/MEDIUM BGCs for a strain)
- Producing the triage ledger
- Producing the DAPR boards or Ferm Card
- Assembling a `_COMPLETE_vN.md` file
- Running Mamey extraction for a strain
- Starting a new session with a strain that has partial prior work
- Any turn where the user asks "how far are we?" or "what's done?" or "what's left?"

Do NOT fire after every individual BGC card — wait for a logical batch boundary.

### What counts as a "session"

A session is a continuous conversation on a strain. The session label in the progress block header should be brief and descriptive, not a UUID: `"Mode B batch 1"`, `"Mamey extraction + cards"`, `"Ferm card + DAPR"`.

---

## Condensed form (for in-chat use)

The full table is the authoritative format. In chat turns where space is tight, a condensed form is acceptable — but must still be present:

```
**Progress — [StrainID]:**
✅ Produced this session: [list]
⚠️ Partial: [list with what's missing]
🔲 Not started: [list]
🔒 Blocked on: [blocker]
Critical path: [next step]
```

The condensed form must not drop the "Critical path" line — that line is what makes the block actionable, not just informational.

---

## Integration with CDSW next-paths

The progress block and the CDSW next-paths block are complementary and both required. They serve different functions:

- **Progress block**: backward-looking — what has been built so far
- **CDSW next-paths**: forward-looking — what to do next and in what order

Both appear at the end of a substantive turn. Progress block comes first, CDSW next-paths second.

---

## Score corrections generated by this patch (AS-XXX example)

When the Mamey run completes and returns authoritative scores, the progress block must flag any score discrepancies with the prior worker_diff or triage ledger. This prevents stale scores from persisting into deliverables.

**AS-XXX correction ledger (2026-06-24, from Mamey v9.7.121 run on AS-XXX_loose.zip):**

| BGC | Prior worker_diff score | Mamey authoritative | Correction needed |
|---|---|---|---|
| BGC033 | Flagged down (bldA T4); AF not scored in card | **AB 63, AF 46, Novelty 39, Medium** | BGC033 is the **highest AF score in the strain** (tied with BGC015 at 46). The bldA T4 silence flag still applies, but the cluster warrants a full Mode B card noting the silence risk. The prior COMPLETE is non-conformant on BGC033. |
| BGC012 | Inventory only (locus map generated, no card) | **AB 58, AF 20, Novelty 45, Medium; products: PKS/RiPP/T3PKS/fatty_acid on NODE_1 FC** | BGC012 is Medium tier per the engine; needs a full Mode B card. Currently it only has a locus map. |
| BGC020 | Open PQQ question (PqqD flag) | **Interior, Medium, Novelty 50, arginomycin KCB (BGC0000883.5); no PQQ confirmation** | PQQ question resolved: arginomycin is an aminoglycoside, the KCB is a class mismatch. The cluster is an Interior RRE-containing RiPP at Novelty 50. The PQQ flag should be CLOSED (no TIGR03859 companion confirmed); the cluster should be promoted to full Mode B. |
| BGC042 | AB listed as "—" (score not stated in COMPLETE) | **AB 66, AF 28** | AB 66 is the second-highest AB score in the strain, tied with BGC046. Should be listed explicitly in DAPR boards. |
| BGC016 | Down: NRP-metallophore (coelibactin KCB) | **AB 41, AF 36, Novelty 27, Inventory; coelibactin KCB confirmed** | Score confirmed. Note: coelibactin is technically a genotoxic/siderophore hybrid (not a pure siderophore); the NRP-metallophore DOWNGRADE still applies, but the note is more nuanced than a simple siderophore. |

These corrections should be applied to `AS-XXX_COMPLETE_v1.md` before any report compilation.

---

## Example progress block (AS-XXX after COMPLETE v1)

This is what the progress block should have looked like at the end of the AS-XXX COMPLETE session, instead of "AS-XXX COMPLETE done":

```
---
**Progress — AS-XXX · 2026-06-24 · Mode B cards + COMPLETE v1**

| Layer | Deliverable | Status | Notes |
|---|---|---|---|
| A1 | Mamey package (manifest, inventory CSV, triage CSV) | ✅ | Partial run — verdicts.json + records.json recovered; workbook write failed at source_locator step |
| A1 | Verdicts + records JSON | ✅ | Authoritative scores confirmed for all 48 BGCs |
| A1 | Workbook (xlsx) | 🔒 | Source-locator I/O error; re-run needed with writable zip |
| A2 | Mode B cards — HIGH BGCs (BGC001, BGC002, BGC046) | ✅ | All 3 High-tier leads carded |
| A2 | Mode B cards — MEDIUM BGCs | ⚠️ 7 of 11 | Missing: BGC012 (PKS/RiPP/T3PKS, Novelty 45), BGC020 (Interior RiPP, Novelty 50), BGC033 (highest AF in strain, bldA T4), BGC016 (NRP-metallophore) |
| A2 | Mode B cards — Inventory BGCs (FULL ANALYSIS MODE) | 🔲 0 of ~9 | BGC018/022/026/035/043/044/045 not carded |
| A2 | Layperson-Ranked BGC Guide (Module 19) | ⚠️ | 2-paragraph summary only; no per-BGC ranked entries |
| A2 | Bench Guide (Module 20) | 🔲 | Not started |
| A2 | DAPR boards | ⚠️ | Embedded in COMPLETE; BGC042 AB score missing; BGC033 absent |
| A2 | Fermentation Card A5 | ⚠️ | Embedded in COMPLETE, not standalone A5 format |
| A2 | First-Pass Scans page (8 scans) | 🔒 | Requires manifest.json (workbook step failed) |
| A2 | Ecological Synthesis (Vespidae wasp host) | 🔲 | Not started |
| A2 | Cross-Strain Cohort Context (A2.1) | 🔲 | Not started |
| A2 | Literature-Search Handoff list | 🔲 | Not started |
| A2 | Wet-Lab Decision Matrix | 🔲 | Not started |
| A2 | Reviewer Attack Simulation | 🔲 | Not started |
| A2 | Metabolomics Readiness | 🔲 | Not started |
| A3 | Workbook sheets (7 sheets) | 🔒 | Blocked on workbook write |
| Figures | Locus maps | ⚠️ 9 of 48 | BGC030 (EF-Tu lead), BGC046 (High), BGC020, BGC012 missing maps |
| Locus co-location | Maps co-located with Mode B per A2.5 | 🔲 | Maps and cards in separate files |

**This session produced:** AS-XXX_COMPLETE_v1.md (10 Mode B cards, triage ledger, DAPR, Ferm Card); Mamey verdicts.json + records.json (48 BGC authoritative scores).  
**Remaining before full contract:** ~12 deliverables across 4 layers, plus 3 missing Mode B cards and 9 inventory cards.  
**Critical path:** Re-run Mamey with writable zip to get the workbook and First-Pass Scans; then write BGC033/BGC012/BGC020 Mode B cards (all three are Medium and were missed or undercounted).
---
```

---

## Patch provenance

This patch was generated in response to direct user feedback (2026-06-24) that a session labeled AS-XXX "COMPLETE" gave a misleading impression that the full Sapote–Mamey analysis had been delivered. A subsequent deliverable audit against `docs/DELIVERABLE_CONTRACT.md` showed ~15–20% completion at the point the word "complete" was used. The patch formalises the progress reporting behavior so this cannot recur silently.

**Filed by:** Sapote (Claude / LLM tier) · 2026-06-24  
**Review required:** No — behavior patch, not code patch. Applies immediately.
