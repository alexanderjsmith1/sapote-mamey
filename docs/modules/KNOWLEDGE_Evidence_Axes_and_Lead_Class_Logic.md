# Sapote-Mamey Knowledge Module — Evidence Axes, Lead Scoring & Class Logic

**Filing.** `docs/modules/KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md`. Reference knowledge for any runner
that scores leads, assigns confidence classes, or writes lead/figure captions. It is consistent with
`DAPR_CLASS_FRAMEWORK.md` (DasR / regulator framework) and `MODE_B_CARD_CLAIM_SAFETY_AUDIT.md` (claim-safety);
where this module restates a number, the scoring code (`build_priority_leads.py` / `lead_board.py` /
`scoring.py`) is the executable source of truth and wins on any drift.

**Why this exists.** The lead figures (1a–2g) and the priority panel (C3) are only meaningful if every runner
uses the **same five axes, the same weights, and the same class definitions**. This module is the portable copy
of that logic so a fresh chat produces the same classes and the same captions.

> **Precedence.** `DELIVERABLE_CONTRACT.md` wins; the active parent monolith wins over everything. This module is
> the canonical class/score reference; `KNOWLEDGE_LeadTiers.md` inherits the class definitions from here (it adds
> the precision-vs-recall framing and the chemistry-first recall view; it does not redefine the classes).

---

## 1. The five evidence axes
Each axis is an independent, named line of support for a BGC lead. A lead carries an axis or it doesn't.

| Axis | What it is | Role | Caption phrasing |
|---|---|---|---|
| **Mode B** | a Sapote deep-dive §1–§8 verdict: `CONFIRM` / `DOWNGRADE` / `DROP` | the judgment axis | "Mode B CONFIRM" — never "confirmed compound" |
| **SARP** | a pathway-specific activator (ActII-ORF4 / RedD archetype) physically coupled to the BGC | strongest **regulator** axis | "SARP-coupled", "carries a pathway-specific activator" |
| **DasR** | GlcNAc/chitin-responsive global regulator (`dre` sites) | **ecology** axis; dominates Class C | "DasR/`dre`-linked" — a nutrient-sensing signal, not activity |
| **KCB** | KnownClusterBlast / MIBiG similarity anchor | identity context; **absence = KCB-dark = novelty pool** | "KCB-anchored to X" = *similar to*, **not** "is X" |
| **Tier-1** | a class-definitive CCTT / TIGRFAM marker, **edge-agnostic** | class identity that survives fragmentation | "Tier-1 marker present" — the marker beats fragmentation |

**AS verdict caveat.** Mode B verdicts on unpublished **AS** strains are currently tagged `[EG]` (generated
offline, no live literature). They count for class assignment but must be upgraded to **Verified** (a "Verified
Literature Deep Dive" pass, not "Rapid") before any AS-based claim goes into a manuscript.

**SARP source of truth.** SARP coupling is the per-BGC `tfbs_coupling.json` set containing `SARP` — NOT the
strain-level `tfbs.SARP_BTAD_like` palindrome count. Tools must read the per-BGC bank (`build_modeb_deepdive.py`
§6, `build_subset_panel.py`, `build_lead_tiers.py` all do).

---

## 2. Composite score (what the ranked-field figures plot)
```
score =  +3.0  Mode B CONFIRM        (DOWNGRADE +0.5 ; DROP → lead excluded entirely)
         +2.0  SARP coupling
         +1.0  KCB anchor
         +1.0  Tier-1 marker
         +0.5  DasR
         +0.2  each other regulator   (cap +4.0)
         +0.15 each independent signal (n_signals, cap +6.0)
```
This is the `score` column in `Priority_Leads.csv` / `Priority_Scores_All.csv` and the y-axis of 1b, 2b, 2c, 2e,
1g. The field is a **continuous gradient with no natural gap** (see 1b) — the class cutoffs below are
definitional, not a valley in the data.

---

## 3. Confidence classes (definitional, in priority order)
| Class | Definition | Reading |
|---|---|---|
| **A** | Mode B `CONFIRM` **∩** SARP | both the judgment axis and the strongest regulator axis agree |
| **B** | Mode B `CONFIRM` **OR** (SARP **∩** Tier-1) | one strong leg, not both of A's |
| **C** | Tier-1 **∩** KCB **∩** (SARP **or** DasR), and **not** A/B | structural + identity + a regulator, ecology-weighted |

Class A is the **intersection** of the two strongest axes — that is the whole reason it is small and high-trust.
It is a **precision** tier, not a ranking of importance (see `KNOWLEDGE_LeadTiers.md` for the chemistry-first
recall view that surfaces CONFIRMED-but-benched leads alongside it).

---

## 4. The canonical Class-A count — **12 (6 SID + 6 AS)** — and the 17 reconciliation
**Canonical: 12 Class-A = 6 SID + 6 AS.** Every figure and caption uses 12. Full field at the time of this
module: **247 leads → 12 A, 148 B, 87 C, 1,784 evaluated.**

**Why not 17.** An earlier handoff estimate of "17 Class-A (6 SID + 11 AS)" assumed *all 11 banked AS Mode B
CONFIRM verdicts* promote to A. They do not: **Class A = CONFIRM ∩ SARP**, and only **6** of those 11 AS BGCs
also carry a SARP. The other **5** AS CONFIRMs are **Class B pending a SARP**. An older cross-set diagnostic said
"6" because it predated the AS verdict banking entirely. **12 is the reconciled truth; 17 and the bare 6 are both
retired.** (`HANDOFF_merged_cohort.md` and `deliverables/CrossSet_Diagnostic_AS_vs_SID.md` carry this note.)

The six AS Class-A BGCs: **AS-XXX/BGC040, AS-XXX/BGC059, AS-XXX/BGC046, AS-XXX/BGC055, AS-XXX/BGC017, AS-XXX/BGC016**
(each `[EG]` — Verified-upgrade required before manuscript use). Cross-set theme worth a caption: **azoxy
machinery reaches Class A in 3 loci across both cohorts** (AS-XXX/BGC017, AS-XXX/BGC046, SID-XXX/BGC037);
halogenated aromatics in 4.

---

## 5. Class-B promotion routes (the verification worklist — drives figure 1d and the punch card)
Every Class-B lead is one axis short of A. Split by what it needs:

| Route | Count | Needs | Action |
|---|---|---|---|
| **SARP-only** | **122** | a Mode B CONFIRM | run a Verified Literature Deep Dive (Mode B) on the BGC |
| **Mode-B-only** | **26** | a SARP | re-interrogate the locus / flanking regulators for a pathway-specific activator |

This is exactly what **figure 1d** plots (split by cohort) and the rows that should be minted as literature
**punch-card** tasks (`BGC_Class_Link` set to the BGC's class) so the verification track and the figures stay in
lock-step. Closing a route promotes the lead to A — and updates 1a/1c/2a automatically on the next pipeline run,
because nothing is hand-maintained.

---

## 6. Claim-safety language for captions (inherited from `MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`)
- **Leads are class-level hypotheses**, not identified compounds. "candidate", "consistent with", "lead" — never
  "produces" / "is".
- **KCB similarity ≠ identity.** "anchored to / similar to MIBiG X", never "is X".
- **Novelty = distance from characterized clusters**, a candidate signal; confirmation needs Mode B / wet-lab.
  Interpret small/poorly-assembled genomes' novelty fractions with caution.
- **Bioactivity metadata is optional and typed**; omission is `NOT_SUPPLIED` and does not imply a target or outcome.
  strain-specific assay data takes priority over the default.
- **Corrected BGC count = Interior + ½·Edge + ¼·Full-Contig.** Use the corrected count in cross-strain figures.
- **Locked exclusions:** `hglE-KS-PREV-001` (prevalent glycolipid domain; structural novelty stands, but no
  habitat-exclusive claim); **NAPAA** (ε-poly-L-lysine class) excluded from all comparative/ecological claims;
  ubiquitous saccharide machinery is not ecologically informative.

---

## 7. Quick map: axis → which figures show it
- **Mode B** → 1a, 1c, C3 (and the score in every ranked panel)
- **SARP** → 1a, 1c, 1d (routes), C3
- **DasR** → 1a, C3 (ecology axis)
- **KCB / KCB-dark** → 2g (novelty per class), C1 (KCB-dark %), C4
- **Tier-1** → 1a, C3
- **class counts (12/148/87)** → 1c, 2a, C3
