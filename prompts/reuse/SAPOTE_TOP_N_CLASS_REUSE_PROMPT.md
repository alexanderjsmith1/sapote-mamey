# REUSE PROMPT — Top-N Compound-Class Enumeration (polyketide / nucleoside / rare-class)
**Vetted against:** Sapote–Mamey v9.7.7 contract · `docs/DELIVERABLE_CONTRACT.md` Part B (cross-strain
rankings), `docs/WORKBOOK_SCHEMA.md` (B8–B12 top-class sheets, C1/C2 DAPR), monolith §43 (CCTT) / §57.
**Use:** cross-strain or single-strain enumeration of a target compound class — the ranked "top-N"
tables (e.g. Top-100 leads, Top PKS, nucleoside/rare-class). One template, parameterized by class.

---

## Parameters (set before running)
- **CLASS_TARGET:** one of {polyketide/PKS, nucleoside, halogenation, phosphonate, lanthipeptide/RiPP,
  rare-class (phosphonate/ranthipeptide/azole), or "Top-100 all-class"}.
- **SCOPE:** single strain | cross-strain cohort.
- **N:** ranking depth (e.g. top 10/50/100).

## Role & preconditions
Sapote layer over sealed package(s). Do not re-run scans. First:
1. Confirm integrity (gate + checksums) for every package in scope.
2. **Read each `*_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits` to ground class membership in
   tier-1 diagnostic domains, NOT bare antiSMASH product labels or KCB type strings.** (e.g. a
   "ranthipeptide" label is only a class member if a radical-SAM+SPASM maturase is actually present;
   an "enediyne" needs the ene_KS; a phosphonate needs PEP_mutase/PepM.)
3. Pull CCTT triggers (`6_cctt`), KCB, and the class-relevant scan states.

## What to produce
- **Ranked top-N table for CLASS_TARGET**, columns: `BGC_ID (contig · regionXXX)`, strain, the
  grounding diagnostic domain(s) + bitscore, KCB top hit + score, boundary/Arch, novelty, WL score,
  claim ceiling. Rank by evidence weight (diagnostic-core present > label-only).
- **Grouped-frequency block:** counts of the class across strains/habitats (feeds B2_Product_Class_Matrix
  / B8–B12 top-class sheets as applicable).
- **Class-membership audit:** explicitly separate (a) diagnostic-core-confirmed members from
  (b) label-only candidates lacking a visible core — the latter flagged for HMMER/BLASTp, never ranked
  as if confirmed.
- For cross-strain scope, also feed C1_DAPR_Antibacterial / C2_DAPR_Antifungal where the class is
  bioactivity-relevant.

## Non-negotiable rules
- **Diagnostic-core-first:** the recurring failure is ranking a label-only BGC as a confirmed class
  member. Ground every top-N entry in the evidence JSON's domains; demote label-only to a flagged
  sub-list.
- **Rare-class caveat:** for phosphonate/ranthipeptide/azole/enediyne, state that these are
  rare-class *enumerations* requiring orthogonal confirmation (e.g. ³¹P-NMR for phosphonate) before
  compound-class claims.
- **Claim-safety + locator mandate** throughout; candidate language; PMID/DOI Bert-verified only.
- **NAPAA excluded** from any ranking; **hglE-KS** entries flagged prevalent (PREV-001), not novel.

## Handback
The ranked top-N table + grouped-frequency block + the confirmed-vs-label-only audit + relevant
workbook deltas (B-group/C-group by code). End with exactly 8 unique numbered next paths.
