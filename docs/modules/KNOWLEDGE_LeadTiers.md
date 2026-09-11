# KNOWLEDGE — Lead tiers: what Class-A means (and what it does not)

## 0. Header block
> **Filing.** `docs/modules/KNOWLEDGE_LeadTiers.md`.
> **References / inherits from:** `KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md` (the canonical class
> definitions, score weights, and the **12 Class-A = 6 SID + 6 AS** count), `modeb_verdicts.csv`,
> `GENERIC_PROMPT_LIBRARY.md` (G3/G6). This module does **not** redefine the classes — it adds the
> precision-vs-recall framing and the chemistry-first recall view. Scoring code wins on any drift.
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins; the active monolith wins over this module.
> **Status:** `KNOWLEDGE`.
> **One-line purpose.** State plainly that Class-A = "high-confidence + actionable regulation," **not** "most
> important," so the chemistry-first recall leads are never silently benched.

## 1. Why this exists / who reads it
Anyone reading the priority dossier or building a leads figure (G3/G6). The Class-A label is a **precision**
filter, not a recall one. Several CONFIRMED, bioactivity-relevant pathways sit below the headline not because the
chemistry is weaker but because of a regulation/composite axis. For a target-focused paper (e.g. antifungal),
the most on-topic lead can be a *benched* CONFIRM. Read the recall view alongside the Class-A list, never instead.

## 2. What the banks actually show (audited v9.5.9; corrected to use the per-BGC coupling bank)
- **Correction (supersedes an earlier note).** An earlier audit read SARP from the strain-level palindrome count
  (`gene_data.tfbs.SARP_BTAD_like`) and wrongly concluded "Class-A = CONFIRM ∩ SARP does not match its set."
  Read from the **authoritative per-BGC bank `tfbs_coupling.json`**, the definition *does* hold cleanly: all six
  SID Class-A leads (SID-XXX/BGC024, SID-XXX/BGC032, SID-XXX/BGC037, SID-XXX/BGC059, SID-XXX/BGC014,
  SID-XXX/BGC067) carry in-cluster SARP; every benched high-value CONFIRM lacks it. The `build_modeb_deepdive.py`
  §6 line was fixed to read the same per-BGC bank (SID-XXX previously under-claimed `?`).
- **So the critique is the clean one:** Class-A = CONFIRM ∩ in-cluster-SARP is a **precision** filter; it benches
  CONFIRMED, bioactivity-relevant pathways purely for lacking a pathway-specific activator. The mechanism really
  is "for want of SARP."
- **High-value benched CONFIRMs (chemistry-first recall):**
  - `SID-XXX/BGC029` — polyene modular T1PKS, **antifungal (Candida)**, 107.9 kb Interior, **T1 self-protection**.
    *The headline antifungal candidate; benched only for want of SARP, yet carries the strongest self-protection
    signal.* Look here first for a Candida paper.
  - `SID-XXX/BGC087` — glycosylated arylpolyene, **antifungal**, **T1 self-protection**.
  - `SID-XXX/BGC048`, `SID-XXX/BGC003` — the two genuine enediynes (**anticancer**; no source-derived resistance).
  - `SID-XXX/BGC077` — merochlorin (**anti-MRSA**, T1 self-protection); `SID-XXX/BGC043` — spirotetronate.

## 3. The rule to state in any dossier / figure caption
> **Class-A = high-confidence chemistry + an actionable regulation/score signal. It is a precision tier, not a
> ranking of importance.** Target-relevant CONFIRMED pathways that miss the composite cut are listed in the
> chemistry-first recall view (`ChemistryFirst_Recall.csv`) and must be surfaced for any target-focused selection.

## 4. Recall view artifact
`ChemistryFirst_Recall.csv` — all CONFIRM leads × {Class-A? · strain-SARP · in-cluster-SARP · bioactivity axis ·
edge · kb}, sorted to surface antifungal → anticancer → anti-MRSA benched leads first. Reproduce from
`modeb_verdicts.csv` + banks. Single source of truth for Class-A membership = `build_priority_leads.py`.

**Target-query is a filter, not a judgment (deterministic).** "What is the antifungal lead?" must never depend on
a model *recognising* a chemistry. `resources/bioactivity_axes.json` maps chemistry → axis by KCB anchor / class
name, so nikkomycin and polyoxin (chitin-synthase nucleosides) and HSAF / dihydromaltophilin (polycyclic tetramate
macrolactams) tag **antifungal** even though their names contain no "antifungal". Run
`python tools/build_lead_tiers.py --bioactivity antifungal` for a deterministic lookup, identical across runners.
Extend the table rather than relying on judgment when a new chemistry appears.

## 5. The fix — add self-protection as an orthogonal second axis
`resistance_tier` is already computed in `bgc_profile` but **unused** in the priority score. Fold it in as a
second, independent axis (the orthogonal-evidence logic the tier was built on):

> **proposed Class-A = CONFIRM ∩ (in-cluster-SARP  OR  T1 source-derived self-protection)**

`tools/build_lead_tiers.py` implements this. Effect on the SID cohort: Class-A 6 → 11, promoting **SID-XXX &
SID-XXX (antifungal)**, SID-XXX/BGC077 (anti-MRSA), SID-XXX/BGC034, SID-XXX/BGC005 — each on self-protection, not
SARP. The enediynes correctly do **not** promote (no source-derived resistance) and stay flagged by bioactivity.
Code change is one function (`confidence_class`) plus folding `resistance_tier` onto the board the way
`SARP_support` is folded — additive, low-risk. **Proposal, not yet executed in `build_priority_leads.py`.** The
canonical Class-A count stays **12** (CONFIRM ∩ SARP, per Evidence_Axes) until/unless this change is adopted;
`build_lead_tiers.py` emits the proposed re-rank as a *recall* view beside the canonical set, not as a new count.

## 6. Strictness caveat (azoxy headline — cross-reference)
The azoxy theme leans partly on `relaxed`-strictness E-signal calls (AS-side loci, not in this cohort's banks).
`azoxy-crosslink` is an antiSMASH **E-signal**, the kind of call that can shift on a relaxed→loose re-run, so
strictness harmonization (Open-decision #1) **does gate the azoxy headline** — the prior "does not affect
materially" line is too glib for an E-signal and should be removed. The SID cohort carries no per-locus strictness
field, so AS-side azoxy loci must be re-confirmed in the AS chat; the SID side (SID-XXX/BGC037 trioxacarcin,
CONFIRM, plus a 5-locus SID tambjamine-azoxy family) is independent supporting evidence that the theme is not
only a relaxed-strictness artifact.

## 7. Next-paths closer
```
1. Promote SID-XXX/BGC029 (antifungal polyene) into the headline for any Candida-focused selection; run G4 on it.
2. Print the chemistry-first recall view beside every Class-A list (relabel per §5 option 1).
3. Re-confirm the AS azoxy loci (AS-XXX/AS-XXX) under loose in the AS chat; keep SID-XXX + tambjamine as the SID anchor.
4. Re-weight or document the composite priority score so Class-A membership is transparent.
5. Add a bioactivity-axis column to Priority_Leads so target-focused recall is one filter away.
```
