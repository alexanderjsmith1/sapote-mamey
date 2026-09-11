# PATCH — Gated PDF Compilation (100+ page full-genome compendium)
**Patch ID:** PDF_COMPILATION_GATE_20260624  
**Applies to:** Sapote (Claude / LLM tier) + the per-session compendium generator  
**Bundle version:** v9.7.121+  
**Status:** ACTIVE  
**Authority:** extends `AutoPipeline_antiSMASH_to_Compendium.md` step 8 (compendium
assembly) and `DELIVERABLE_CONTRACT.md`; consumes `tools/md_to_pdf.sh` +
`tools/sapote_md_preflight.py` (existing renderer, do not replace).

---

## Problem this patch fixes

A "complete" PDF for a full actinomycete genome was shipping at ~59 pages. A full
13-deliverable compendium with per-BGC §1–§8 Mode B for a 48-BGC *Streptomyces* is
~115 pages; a 100+ BGC genome exceeds 150. A 59-page PDF is roughly half a compendium —
the same ~15–20% completion that the progress-reporting patch was filed against, now in
PDF form. The PDF hand-off was implying a finished deliverable while carrying half the
contracted analysis.

The renderer (`md_to_pdf.sh`) is sound — it preflights wide tables and treats xelatex
failures as fatal. The gap is upstream: **nothing checks that the markdown fed to the
renderer actually contains a full compendium before it becomes a PDF.** This patch adds
that gate.

---

## Core rule

**A PDF compilation is not offered, named "compendium", or handed over as a strain
deliverable until it passes the compilation gate.**

A PDF that fails the gate may still be produced — but it must be labelled a **partial
extract** (filename `_PARTIAL_`), and the Control Panel must show which contract items
are missing from it. It is never called a compendium and never implies completeness.

---

## The compilation gate

Before rendering a strain compendium PDF, the source markdown must satisfy ALL of:

### G1 — Deliverable presence
All 13 `FULL_RUN_PROFILE §A` deliverables present as sections (✅ in the Control Panel),
OR each absent one explicitly marked SKIPPED/N/A with a reason in a missingness register.
A 🔲 not-started contract item is a hard gate failure — it cannot be silently absent
from a "compendium."

### G2 — Mode B coverage
Item 6 (Full Mode B for every BGC) carries a card for **every scorable BGC**, at §1–§8
depth. The denominator is the full scorable count, not the carded count. Partial Mode B
coverage (e.g. 10 of 48) fails the gate.

### G3 — Page-count floor (genome-size-scaled)
The rendered PDF must meet a minimum page count scaled to genome size:

| Scorable BGCs | Minimum pages | Rationale |
|---|---|---|
| < 15 (small/fragment) | 30 | small genome or heavy fragmentation |
| 15–35 | 60 | typical small *Streptomyces* / *Micromonospora* |
| 36–70 | **100** | full mid-size actinomycete genome |
| 71–110 | 140 | large genome |
| > 110 | 180 | very large / highly fragmented (e.g. AS-XXX) |

The floor is a **lower bound, not a target** — a thin PDF below the floor is a signal
that Mode B depth or deliverables are missing, not an instruction to pad. Padding to
hit a page count is a gate failure of its own (see G5).

### G4 — Per-BGC depth floor
Each Mode B card meets the existing `mode_b_quality_gate.py` depth contract (§1–§10
present, enrichment block, character floor by tier). A compendium of stub cards fails
even if the page count is met.

### G5 — Anti-padding check
Page count must come from analysis, not whitespace or repetition. The preflight reports
the §-section count and gene-table row count; a PDF that hits its page floor with too
few sections or gene rows per page is flagged as padded and fails the gate.

---

## Gate mechanism (how it runs)

The gate is a preflight step that runs BEFORE `md_to_pdf.sh`:

```
session compendium markdown
        │
        ▼
  compilation_gate (new)  ──fail──▶  label _PARTIAL_, Control Panel shows gaps, STOP
        │ pass
        ▼
  sapote_md_preflight.py  (existing — wide-table handling)
        │
        ▼
  md_to_pdf.sh            (existing — xelatex, fatal on error)
        │
        ▼
  post-render page-count check (G3/G5)  ──fail──▶  label _PARTIAL_, report gap
        │ pass
        ▼
  AS-XXX_COMPENDIUM_vN.pdf  +  gate receipt JSON
```

G1/G2/G4/G5 run on the markdown pre-render. G3 runs post-render (page count needs the
actual PDF — use `pdfinfo` or equivalent). A post-render G3 failure does not delete the
PDF; it relabels it `_PARTIAL_` and records the shortfall.

### Gate receipt

Every gated compile emits a receipt alongside the PDF:

```json
{
  "strain": "AS-XXX",
  "scorable_bgcs": 48,
  "mode_b_cards": 48,
  "contract_items_present": 13,
  "contract_items_total": 13,
  "page_count": 116,
  "page_floor": 100,
  "gate": "PASS",
  "filename": "AS-XXX_COMPENDIUM_v1.pdf"
}
```

A `"gate": "FAIL"` receipt names the failing checks and the PDF is `_PARTIAL_`.

---

## Gating mechanism options (pick one at cut time)

The user asked whether the gate should be a hard requirement or another mechanism.
Three options, in order of strictness:

1. **Hard gate (recommended).** No PDF is named `_COMPENDIUM_` or offered as a strain
   deliverable unless it passes. Failing PDFs are produced but labelled `_PARTIAL_`.
   The word "compendium" is reserved for gate-passing PDFs — mirrors how the
   progress-reporting patch reserves "complete."
2. **Soft gate (warn-and-proceed).** The PDF is produced regardless, but a failing gate
   forces a prominent banner on page 1 ("PARTIAL EXTRACT — N of 13 deliverables, M of X
   Mode B cards") and a Control Panel readout. Less strict; relies on the banner being
   read.
3. **Advisory.** The gate runs and reports, but does not change the filename or block
   the offer. Weakest — essentially just the receipt JSON.

**Recommendation:** Hard gate. It is the PDF analogue of the "never say complete" rule
and is the only option that structurally prevents a half-compendium from being handed
over as finished.

---

## Integration with the Control Panel

A compendium PDF hand-off is a deliverable hand-off → the Control Panel fires. The panel
gains a row:

```
    [✅/⚠️/🔲]  Compendium PDF   [gate PASS/FAIL · N pages · floor M]
```

A `_PARTIAL_` PDF reads ⚠️ with the gate shortfall in the notes. A gate-passing
compendium reads ✅ with the page count.

---

## Implementation checklist

- [ ] Build `compilation_gate.py` running G1–G5 against session compendium markdown
- [ ] Wire it as a preflight before `md_to_pdf.sh` in the compendium step (runbook step 8)
- [ ] Add the post-render page-count check (G3) using `pdfinfo`
- [ ] Emit the gate receipt JSON alongside every compiled PDF
- [ ] Reserve the `_COMPENDIUM_` filename token for gate-passing PDFs; `_PARTIAL_` otherwise
- [ ] Add the Compendium PDF row to the Control Panel
- [ ] Add a contract test: a stub-card markdown must FAIL the gate; a full 13-deliverable
      markdown with full Mode B must PASS

---

*PDF Compilation Gate Patch v1.0 · Sapote–Mamey v9.7.121 · 2026-06-24*
