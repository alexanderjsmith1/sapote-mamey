# Sapote Full-Run Deliverable Manifest — [STRAIN_ID]
<!-- The LLM MUST fill this out and emit it as the LAST artifact of a full run. -->
<!-- It turns FULL_RUN_PROFILE Section A (the 13-item contract) + Section H gate from trusted prose -->
<!-- into a checkable artifact. tools/check_deliverable_suite.py validates it. -->
<!-- Status vocabulary (one per item): COMPLETE | SKIPPED | N/A  -->
<!--   COMPLETE  → must give a path/filename in the Artifact column.  -->
<!--   SKIPPED   → must give a one-line reason (e.g. "deferred to Batch 3 per user"). -->
<!--   N/A       → must give a one-line reason (e.g. "no AF leads in collection"). -->

**Strain:** [STRAIN_ID] · **Run mode:** [smoke|standard|gold] · **Bundle:** sapote-mamey-vX.Y.Z · **Date:** YYYY-MM-DD
**BGC count:** [raw] raw / [corr] corrected · **Batches:** [n] (this manifest is cumulative across batches)

## Deliverable suite (FULL_RUN_PROFILE §A — 13 items, ordered)
| # | Deliverable | Status | Artifact (path) or Reason |
|---|---|---|---|
| 1 | Assembly declaration + BGC inventory | COMPLETE/SKIPPED/N/A | ____ |
| 2 | Architecture confidence grades | COMPLETE/SKIPPED/N/A | ____ |
| 3 | WL scoring + Triage First Board | COMPLETE/SKIPPED/N/A | ____ |
| 4 | Hallucination-trap audit (all BGCs) | COMPLETE/SKIPPED/N/A | ____ |
| 5 | CCTT routing / §57 sub-grades / bldA-TTA / resistance tiers / UMED / EFLS | COMPLETE/SKIPPED/N/A | ____ |
| 6 | Full Mode B for every BGC | COMPLETE/SKIPPED/N/A | ____ |
| 7 | DAPR — dual AB/AF priority tracks | COMPLETE/SKIPPED/N/A | ____ |
| 8 | Mechanistic Ecology Synthesis | COMPLETE/SKIPPED/N/A | ____ |
| 9 | Fermentation / Induction / Extraction Plan | COMPLETE/SKIPPED/N/A | ____ |
| 10 | Layperson-Ranked BGC Guide | COMPLETE/SKIPPED/N/A | ____ |
| 11 | Compound Detection & Isolation Bench Guide | COMPLETE/SKIPPED/N/A | ____ |
| 12 | Missingness register | COMPLETE/SKIPPED/N/A | ____ |
| 13 | Full-run output gate check (Section H) | COMPLETE/SKIPPED/N/A | ____ |

## Packaging deliverables (Tier-2 contract)
| Item | Status | Artifact (path) or Reason |
|---|---|---|
| Master workbook surfaced (Mamey_*_Master_After_[STRAIN].xlsx) | COMPLETE/SKIPPED/N/A | ____ |
| Sapote sheets appended (S1–S5) to workbook | COMPLETE/SKIPPED/N/A | ____ |
| manifest.json + SHA-256 checksums present | COMPLETE/SKIPPED/N/A | ____ |
| Final ZIP bundled | COMPLETE/SKIPPED/N/A | ____ |

## v9.7.338 interpretive & cohort add-ons (OPTIONAL — report-only, non-scoring; NOT part of the §A 13-item contract)
<!-- List only those actually produced; these consume already-sealed packages and change no score/tier/gate/version. -->
<!-- Capacity-level / claim-safe: similarity not identity; measured bioactivity is strain-level context, never a per-BGC production claim; judgment deferred. -->
| Deliverable | Status | Artifact (path) or Reason |
|---|---|---|
| Good Guesses (`good-guesses` → GOOD_GUESSES.md/.csv/.docx/.pdf) | COMPLETE/SKIPPED/N/A | ____ |
| Mode-B docx/pdf export (`modeb-export`) | COMPLETE/SKIPPED/N/A | ____ |
| Antifungal Lead Dossier (`af-dossier` → AF_LEAD_DOSSIER.csv/.md) | COMPLETE/SKIPPED/N/A | ____ |
| KCB comparative locus map (`figures kcb-locusmap` → *_kcb_locusmap.png/.svg/_data.csv) | COMPLETE/SKIPPED/N/A | ____ |
| Comparator-coverage evidence (`comparator-coverage` → *_3b_comparator_coverage.csv) | COMPLETE/SKIPPED/N/A | ____ |
| Cohort priority-leads ledger (`cohort-leads` → COHORT_PRIORITY_LEADS.csv) | COMPLETE/SKIPPED/N/A | ____ |
| Cross-cohort assembler (`cohort-assemble` → COHORT_MASTER.csv) | COMPLETE/SKIPPED/N/A | ____ |
| Domain reference / realistic-count / novelty-shortlist (advisory) | COMPLETE/SKIPPED/N/A | ____ |

## Section H — output gate (self-reported, then machine-checked)
- gold_completeness: [COMPLETE | JUDGMENT_PENDING]  ← must be COMPLETE for a gold run to pass
- Mode B cards written: [n] / [raw BGC count]
- BSL-2 / enediyne flags surfaced: [list BGCs or NONE]
- NAPAA exclusions applied: [list BGCs or NONE]
- Standing-constraint check (claim-safety, typed bioactivity state with no named default, affiliation): [PASS|FAIL]
