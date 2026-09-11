# DELIVERABLE — Wet-Lab Decision Matrix (WLDM)

> **Filing.** `docs/modules/DELIVERABLE_WetLabMatrix.md`.
> **Extends / references:** `SAPOTE_SLIM_JUDGMENT_KERNEL.md` MODULE 4 (§33 WL score), `DAPR_CLASS_FRAMEWORK.md` (AB/AF routing, kernel MODULE 17), `DELIVERABLE_CONTRACT.md` (Offer Protocol, Contig-ID Mandate, Next-Paths). Architecture grades come from kernel MODULE 3 (§31); LMPKS rescue grades from `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md`. **Do not restate those rules — point to them.**
> **Precedence.** The active parent monolith (`SAPOTE_MAMEY_BUNDLE_MONOLITH.md`) wins over this module. This module wins over the *abbreviated* WL score table in slim-kernel MODULE 4 (M4 is a lossy summary; this is the full restoration). The criteria table below is a **portable copy** — the authority is the monolith / Mamey scoring code, not this doc.
> **Status:** `SCHEMA_BACKED` — `tools/build_wetlab_matrix.py` emits `<strain>_WetLab_Decision_Matrix.csv` + the `WetLab_Decision_Matrix` sheet; `score_bgc()` in that tool is the single source of truth and this doc is its portable spec. (Sapote may still compute by hand from §3a when no package is present.)
> **One-line purpose.** Convert each BGC's evidence into four independent, actionable wet-lab priorities (sequence / activate / isolate / dereplicate) plus a single decision category, in the full matrix format that v7.5.2 §33 carried and the slim kernel compressed to a bare score.

---

## 1. When it is offered (Deliverable Offer Protocol)

Per `DELIVERABLE_CONTRACT.md`, the user must never need to know this exists to receive it.

- **Auto-build** whenever a Mode B run (Full-Run Profile) or a Deep Dive Synopsis is produced: the top-10 wet-lab target table is part of the synopsis, and the `WetLab_Decision_Matrix` workbook sheet is part of the Excel deliverable.
- **Offer as first next-path** when a sealed `MAMEY_COMPLETE` package exists but only a triage board has been produced (no wet-lab routing yet).
- **Incomplete delivery** = producing a WL *score* (kernel M4) without the four action scores (§33.5), the decision-category mapping (§33.4), and the top-10 target table. A lone score is not this deliverable.

---

## 2. Inputs required

| File / field (Mamey package) | Feeds | Required for |
|---|---|---|
| `manifest.json → bgc_counts.assembly_tier`, `assembly.quality` | POOR/edge penalties; sequencing-priority flag | Decision category; Action score 1 |
| `manifest.json → bgcs[].edge_status`, `architecture_confidence` | +Interior / Arch A–C terms; truncation penalties | Base score |
| `_4_triage_board.csv → KCB_score, Novelty_auto (RiQ), CCTT_triggers` | KCB & RiQ bonuses; cryptic-class handles | Base score; Action score 4 |
| `_4A_RGGMCI_ranked_pairs.csv` | split-pathway anchor rule; "split arm without TE" penalty | Base score; Action score 1 |
| `manifest.json → bioactivity` | "strain bioactivity matches class" +2 (extract-level only) | Base score |
| LMPKS rescue result (if run) | post-score LMPKS adjustment (§33.3 LMPKS table) | Base score |

**Skip-not-fake.** Any term whose input is absent is omitted and the cell labelled (e.g. `RiQ: not computed`), never assumed. A BGC with no TFBS scan does not silently lose the +2 induction term — it is marked `induction: unscanned`.

---

## 3. Pipeline

Currently `PROMPT_BACKED`: Sapote computes the score per BGC from the §33.3 portable table (below), citing the Mamey field behind each term (Contig-ID Mandate applies — every BGC carries `BGC_ID (contig · regionXXX)`).

To promote to `SCHEMA_BACKED`, add the deterministic writer (keeps the score out of prose):
```bash
python tools/build_wetlab_matrix.py --package-dir <pkg> --out-dir <dir>
# emits: <strain>_WetLab_Decision_Matrix.csv  +  workbook sheet WetLab_Decision_Matrix
# single source of truth for the score = score_bgc() in that tool; this doc then becomes its portable spec.
```
Until that tool exists, the score is reproducible by hand from §33.3 and must cite fields, not assert numbers.

---

## 3a. Scoring criteria — PORTABLE COPY (authority: monolith §33 / scoring code)

Base score (sum all that apply; bonuses are orthogonal unless noted):

| Criterion | Score |
|---|---:|
| Interior BGC | +3 |
| Architecture Confidence A | +3 |
| Architecture Confidence B | +2 |
| Architecture Confidence C (pathway unit) | +1, plus sequencing priority |
| Strong KCB >5,000 with divergent tailoring | +3 |
| No KCB + strong diagnostic domains (Arch A) | +4 |
| No KCB + moderate evidence (Arch B) | +2 |
| RiQ <0.50 with coherent domains | +3 |
| RiQ 0.50–0.85 with unusual tailoring | +2 |
| TFBS gives clear induction condition | +2 |
| T3/T4 bldA gating suggests hidden expression | +2 |
| Strain-level bioactivity matches BGC class (extract-level) | +2 |
| Predicted LC-MS/UV detection handle available | +2 |
| Full-contig / edge truncation | −2 |
| Tiny unanchored fragment | −3 |
| Likely split-cluster arm without TE/release | −2 |
| Likely housekeeping / conserved cluster | −3 |
| No chemical/expression evidence | −1 caveat at discovery stage, **not** a penalty |

**Stacking rule.** "No KCB + strong diagnostic domains" and "RiQ <0.50 with coherent domains" are orthogonal — claim both. **Split-pathway rule:** for a split-pathway *anchor*, score the pathway unit; do **not** apply the Arch C penalty to the anchor (consistent with kernel MODULE 3 two-level rule).

**LMPKS post-score adjustment** (apply highest applicable only; stacks with RiQ and zero-KCB bonuses, not with each other):

| LMPKS rescue result | WL adjustment |
|---|---:|
| LMPKS-A (≥3 complete modules, TE, classifiable) | +2 |
| trans-AT PKS confirmed | +2 |
| Polyene rescue (≥5 DH, no ER run) | +2 |
| LMPKS-B (≥2 modules + docking domains) | +1 |
| LMPKS-C (fragment accumulation ≥4 mod_KS) | +1 sequencing priority only |
| Linear PKS (no TE, ≥3 modules) | +1 |

**Decision categories:**

| Score | Category | Recommended action |
|---:|---|---|
| ≥10 | Immediate follow-up | Culture induction + LC-MS + bioassay-guided fractionation |
| 7–9 | Strong follow-up | Targeted culture/HRMS or sequencing clarification first |
| 4–6 | Conditional follow-up | Retain; revisit after long-read assembly or metabolomics |
| 1–3 | Inventory only | Do not prioritize unless cross-strain evidence emerges |
| ≤0 | Deprioritized | Keep for completeness; no immediate wet-lab action |

---

## 3b. The four independent action scores (this is what the slim kernel dropped)

For **every** BGC, output four HIGH/MED/LOW priorities — they are independent, not derived from the single score:

1. **Sequencing priority** — long-read need. HIGH if Edge / FC / split-pathway / Arch C.
2. **Activation priority** — special culture conditions matter. HIGH if TFBS clear induction or T3/T4 bldA.
3. **Isolation priority** — purification/fractionation suitability. HIGH if decision score ≥10.
4. **Dereplication priority** — HRMS/reference comparison need before isolation. HIGH if KCB >1,000 or RiQ >0.50.

A BGC can be (e.g.) sequencing-HIGH + isolation-LOW simultaneously — that is the point: a fragment worth fixing but not yet worth isolating.

---

## 4. Outputs & the contract surface

| Artifact | Stable id | Where |
|---|---|---|
| Top-10 wet-lab target table | `WLDM_top10` | Deep Dive Synopsis |
| Per-BGC matrix (score + category + 4 action scores) | `WLDM_full` | `WetLab_Decision_Matrix` workbook sheet (Schema v1.0) |
| Top 3–5 action targets | `WLDM_fermcard` | Fermentation Card A5 |
| Memory line (top targets + categories) | `WLDM_memory` | Project Memory Snapshot |

Registration into the workbook schema (not hand-editing) is the single source of truth once the §3 tool exists.

---

## 5. Acceptance checklist ("done" = all)

- [ ] Every BGC has a base score **and** all four action scores (§3b) — not just a score.
- [ ] Each score term cites the Mamey field it came from; no asserted numbers.
- [ ] Split-pathway anchors scored as pathway units (no Arch C penalty on anchor).
- [ ] LMPKS adjustment applied only where a rescue result exists; highest-only.
- [ ] Decision category present for every BGC; top-10 table sorted by score.
- [ ] Contig-ID locator on every BGC (`BGC_ID (contig · regionXXX)`) — never a bare `BGC###`.
- [ ] Bioactivity terms held at **extract level**; no BGC→activity causal claim.
- [ ] No retired codenames; affiliation = .
- [ ] Closes with exactly 8 unique plain-text numbered next-paths.

---

## 6. Tool / knowledge inventory

| Piece | Owner (source of truth) |
|---|---|
| Score criteria & categories | monolith §33 / `tools/build_wetlab_matrix.py` (when built); this doc = portable copy |
| Architecture grades (A–E) | kernel MODULE 3 (§31) |
| AB/AF routing context | `DAPR_CLASS_FRAMEWORK.md` / kernel MODULE 17 |
| LMPKS grades | `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md` |
| Workbook sheet schema | Workbook Schema v1.0 / `mamey/workbook_schema_check.py` |

---

## 7. Worked next-paths closer (example — SID-XXX, *Amycolatopsis rubida*)

> Wet-Lab Decision Matrix complete: 12 BGCs scored, 2 in **Immediate**, 3 in **Strong**. Top sequencing target: the 017/035/072 NRPS megaset (all sequencing-HIGH). Next paths:
> 1. Build the Fermentation Card A5 for the two Immediate targets (BGC047 enediyne, BGC063 phosphonate).
> 2. Run the LMPKS rescue on the 017/035/072 set to resolve their +1/+2 adjustment.
> 3. Promote this module to `SCHEMA_BACKED` by writing `tools/build_wetlab_matrix.py`.
> 4. Generate the Metabolomics Readiness deliverable for the dereplication-HIGH BGCs.
> 5. Bank a second *Amycolatopsis* strain to test whether the phosphonate/enediyne pairing recurs.
