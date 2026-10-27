# Sapote-Mamey Knowledge Module — Evidence Axes, Lead Scoring & Class Logic

**Filing.** `docs/modules/KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md`. Reference knowledge for any runner
that scores leads, assigns confidence classes, or writes lead/figure captions. It is consistent with
`DAPR_CLASS_FRAMEWORK.md` (DasR / regulator framework) and `MODE_B_CARD_CLAIM_SAFETY_AUDIT.md` (claim-safety);
where this module restates a number, the scoring code (`build_priority_leads.py` / `lead_board.py` /
`scoring.py`) is the executable source of truth and wins on any drift.

Use this page to explain a row in `Priority_Leads.csv` or `Priority_Scores_All.csv` produced by
`tools/build_priority_leads.py`. Read the input fields, score and A/B/C rule together. This
workbook-based composite is a separate view from the native triage board's AB/AF/novelty scores.
The weights are tunable ranking choices, not calibrated probabilities or measured evidence independence.

Read [Lead tiers](KNOWLEDGE_LeadTiers.md) alongside this page for the separate current/proposed
recall view. Use the selected writer and its bound input fields to resolve numeric differences;
a historical cohort count or prose heading does not redefine the implemented class rule.

---

## 1. The five evidence axes
Each row below describes an input to the composite. The writer checks stored values; it does not independently verify the biology, literature review or statistical independence of those inputs.

| Axis | What it is | Role | Caption phrasing |
|---|---|---|---|
| **Mode B** | Stored `ModeB_Status`: `CONFIRM` / `DOWNGRADE` / `DROP` | judgment input; the score does not verify the authored card | "recorded Mode B CONFIRM"; use [the current authoring profile](../MODE_B_USER_WALKTHROUGH.md), not the old §1–§8 scaffold |
| **SARP** | Stored per-locus regulator-coupling evidence folded into `SARP_support` | +2 in this composite; candidate regulator context | "recorded SARP coupling"; regulatory effect is not demonstrated by this field |
| **DasR** | GlcNAc/chitin-responsive global regulator (`dre` sites) | **ecology** axis; dominates Class C | "DasR/`dre`-linked" — a nutrient-sensing signal, not activity |
| **KCB** | Stored `KCB_anchor` text | comparator context; check the upstream source and availability separately | "similar to the recorded reference"; missing evidence is not a completed no-hit or novelty result |
| **Tier-1** | Stored `Tier` value equal to `1` | qualification from the selected lead-board producer; some rows can be KCB-only hypotheses | State the actual marker or qualification; eligibility at an edge does not establish pathway completeness |

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
         +0.2  each other regulator entry (at most 4 entries; maximum +0.8)
         +0.15 each comma-separated signals entry (at most 6 entries; maximum +0.9)
```
This is the `score` column in `Priority_Leads.csv` and `Priority_Scores_All.csv`, rounded to two
decimals. The shortlist sorts A before B before C, then by descending score within each class;
the all-scores table sorts by score. A higher score alone therefore need not lead the shortlist.
The A/B/C rules below do not use numeric cutoffs. Figure references and claims about the shape
of an earlier score distribution are historical, not guaranteed properties of a new input.

The KCB bonus accepts any nonempty anchor except `none` or `-`; a placeholder such as
`UNRESOLVED` can still receive it. Check the underlying comparator evidence before describing
that bonus as an observed match. Preserve the recorded input rather than silently recoding it.

---

## 3. Confidence classes (definitional, in priority order)
| Class | Definition | Reading |
|---|---|---|
| **A** | Mode B `CONFIRM` **∩** SARP | both the judgment axis and the strongest regulator axis agree |
| **B** | Mode B `CONFIRM` **OR** (SARP **∩** Tier-1) | one strong leg, not both of A's |
| **C** | Tier-1 **∩** KCB **∩** (SARP **or** DasR), and **not** A/B | structural + identity + a regulator, ecology-weighted |

Class A is the intersection of the stored CONFIRM and SARP inputs. This is a stricter selection
rule, not a measured precision estimate or a ranking of biological importance. Compare the
separate [recall view](KNOWLEDGE_LeadTiers.md) when selecting a question for review.

---

## 4. Read historical counts as a cohort receipt

The earlier record reports **247 shortlisted leads: 12 A, 148 B and 87 C, from 1,784 evaluated**,
with Class A split **6 SID + 6 AS**. Its correction from an earlier estimate of 17 applied the
CONFIRM-and-SARP rule rather than treating every CONFIRM as Class A. These are historical
reports, not expected counts for another cohort or independent validation of the named chemistry.

Use your bound input roster and writer output to report current counts. The redacted examples
in the older record lack full locus identities; recover the same-run inventory and review sources
before using an individual case or an across-cohort theme. An `[EG]` or `Verified` label alone
does not establish manuscript readiness.

---

## 5. Class-B promotion routes (the verification worklist — drives figure 1d and the punch card)
Every Class-B lead is one axis short of A. Split by what it needs:

| Route | Count | Needs | Action |
|---|---|---|---|
| **SARP-only** | **122** | a Mode B CONFIRM | run a Verified Literature Deep Dive (Mode B) on the BGC |
| **Mode-B-only** | **26** | a SARP | re-interrogate the locus / flanking regulators for a pathway-specific activator |

The route counts above belong to the historical cohort. For a current row, identify the missing
stored input and the evidence needed to resolve it. A literature review alone does not update the
workbook or prove SARP coupling. After admitted input fields are updated, the priority writer
recomputes classes when explicitly run; it writes the workbook/CSV/Markdown outputs, not the
historical figure set. Figure selection, rendering and review are separate tasks.

---

## 6. Claim-safety language for captions (inherited from `MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`)
- **Leads are class-level hypotheses**, not identified compounds. "candidate", "consistent with", "lead" — never
  "produces" / "is".
- **KCB similarity ≠ identity.** "anchored to / similar to MIBiG X", never "is X".
- **Novelty scores are review signals under the recorded inputs and method.** Missing comparator evidence does not establish novelty. A Mode B verdict or score alone does not demonstrate a new compound.
- **Bioactivity metadata is optional strain-level context.** Omission is `NOT_SUPPLIED` / `NOT_OBSERVED`, with no supplied assay or compound linkage. The metadata contract does not score leads or assign an observation to a locus.
- **Boundary-weighted count = Interior + ½·Edge + ¼·Full-Contig.** Report it separately from raw regions and the boundary distribution, with comparable input processing. It is a heuristic statistic, not a recovered pathway fraction or a proven lower bound on distinct pathways.
- **Locked exclusions:** `hglE-KS-PREV-001` (prevalent glycolipid domain; structural novelty stands, but no
  habitat-exclusive claim); **NAPAA** is neutral under the current rules registry (no blanket comparative/ecological exclusion; the old specific hypothesis remains retired);
  ubiquitous saccharide machinery is not ecologically informative.

---

## 7. Historical figure map for the recorded cohort
- **Mode B** → 1a, 1c, C3 (and the score in every ranked panel)
- **SARP** → 1a, 1c, 1d (routes), C3
- **DasR** → 1a, C3 (ecology axis)
- **KCB / KCB-dark** → 2g (novelty per class), C1 (KCB-dark %), C4
- **Tier-1** → 1a, C3
- **class counts (12/148/87)** → 1c, 2a, C3
