# Sapote–Mamey Documentation Index
**Master navigation page for all user-facing docs**

**v9.7.149a** | Last updated: 2026-06-29

> ⚠️ **Bundle integration status note (added v9.7.151b, 2026-06-30).** This index was authored
> assuming a complete 28-document set (batch01–batch28). As of this bundle, **18 of 28 exist**:
> batch06, 11, 12, 14 (from the first set) and batch15–28 (the full second set). **Missing:**
> batch01, 02, 03, 04, 05, 07, 08, 09, 10, 13 — these were referenced throughout this index and
> 10 of 28 are missing (batch01–05, batch07–10, batch13); they were never delivered to this bundle. Links to a missing batch number resolve to nothing.
> below will 404 until that document arrives in a future patch.
>
> **Numbering correction:** this index's own "Complete document list → Second set" table uses
> a numbering scheme that is **one off** from the actual filenames shipped in this bundle (e.g.
> the table calls the interpretive-floor document `batch15_modeb_interpretive_floor.md`, but the
> file on disk — and the file this index itself is named — is `batch16_modeb_interpretive_floor.md`,
> with this index document being `batch15_master_index.md`). **The filenames in `docs/batches/`
> are authoritative.** Cross-references elsewhere in this set that cite the table's numbering
> (e.g. "see batch15_modeb_interpretive_floor.md") should be read as +1 from what's printed.

---

## What you're looking at

28 documents covering every aspect of Sapote–Mamey. Use the audience paths below to find your starting point, or use the task lookup tables to go directly to what you need.

---

## Reading paths by audience

**Brand new user (never run Mamey before)**
1. `batch03` — 5-Minute Runbook ← start here
2. `batch08` — Workflow Guide (plain English)
3. `batch07` — Glossary (three levels)
4. `batch05` — Worked Example (SID8370 walkthrough)

**LLM operator (running Mamey and writing Mode B)**
1. `AGENTS.md` or `AGENTS.md` ← bundle root
2. `batch10` — Mode B Output Guide
3. `batch15_modeb_interpretive_floor.md` ← this set
4. `batch07` — Glossary (expert level)
5. `batch04` — Gotcha Guide (when stuck)

**Natural products researcher (science focus)**
1. `batch05` — Worked Example
2. `batch16_dapr_scoring_explainer.md` ← this set
3. `batch20_bgc_class_reference.md` ← this set
4. `batch21_multi_strain_comparative_claims.md` ← this set
5. `batch22_literature_deep_dive_protocol.md` ← this set

**Developer / tool builder**
1. `batch02` — Bundle File Structure Guide
2. `batch01` — Tools Discoverability Map
3. `batch09` — Tools Quick-Pick Decision Tree
4. `batch24_engine_lineage_and_compatibility.md` ← this set
5. `batch14` — Structural Factual Report

**Collaborator onboarding (new lab member)**
1. `batch25_onboarding_packet.md` ← this set
2. `batch03` — 5-Minute Runbook
3. `batch08` — Workflow Guide
4. `batch26_session_start_and_handoff_protocol.md` ← this set

**Release manager**
1. `batch13` — Release Verification Checklist
2. `batch02` — Bundle File Structure Guide (tier architecture)
3. `batch23_fetch_kcb_structures_guide.md` ← this set (if structures in reports)

---

## Complete document list

### First set (batches 01–14)

| # | Document | What it covers |
|---|----------|---------------|
| 01 | `batch01_tools_discoverability_map.md` | All 111 tools categorised, with purpose, I/O, and task-based flowchart |
| 02 | `batch02_bundle_file_structure_guide.md` | Every file explained; four-tier architecture; 1,694-file inventory |
| 03 | `batch03_new_user_5min_runbook.md` | Zero-jargon path from download to first results |
| 04 | `batch04_gotcha_guide.md` | 40+ failure modes with root cause and fix |
| 05 | `batch05_worked_example_sid8370.md` | Schematic walkthrough: antiSMASH ZIP → Mamey → Mode B |
| 06 | `batch06_doc_navigation_guide.md` | "I want to X" → which doc? Task cross-reference |
| 07 | `batch07_glossary_plain_language_pass.md` | KCB, CCTT, UMED, CGAD, assembly tier at 3 levels; verified citations |
| 08 | `batch08_workflow_accessibility_rewrite.md` | Mamey + Sapote pipeline in plain English |
| 09 | `batch09_tools_quick_pick_decision_tree.md` | Decision flowcharts for every task type |
| 10 | `batch10_modeb_output_contract_plain_english.md` | Mode B teaching structure + real contract pointer |
| 11 | `batch11_common_failure_recovery_matrix.md` | Error → root cause → fix; LLM-specific error handling |
| 12 | `batch12_figure_system_one_pager.md` | Figure catalog, real CLI flags, house style, reproducibility |
| 13 | `batch13_release_verification_checklist.md` | 7-stage release pipeline; macOS + Linux checksums |
| 14 | `batch14_structural_factual_report.md` | Verified file counts, sizes, dependencies, schemas |

### Second set (batches 15–28) — this set

| # | Document | What it covers |
|---|----------|---------------|
| 15 | `batch15_modeb_interpretive_floor.md` | Minimum interpretive depth per Mode B section (§5, §9, §11, §12, §19) |
| 16 | `batch16_dapr_scoring_explainer.md` | AB/AF dual-axis scoring; antifungal and antibacterial buckets |
| 17 | `batch17_rggmci_split_cluster_guide.md` | Split clusters, reconstruction, RGGMCI, how to cite in Mode B |
| 18 | `batch18_literature_protocol.md` | FLR vs VLR; five-bucket search map; punch-card; §8 deferral |
| 19 | `batch19_claim_safety_field_manual.md` | Claim-safety language rules; hallucination traps; standing exclusions |
| 20 | `batch20_bgc_class_reference.md` | PKS, NRPS, RiPP, terpene, enediyne — what to look for, Mode B pitfalls |
| 21 | `batch21_multi_strain_comparative_claims.md` | Corrected counts; exclusions; denominators; re-scoring gate |
| 22 | `batch22_common_mistakes_extended.md` | 11 documented failure modes from `docs/COMMON_MISTAKES.md` expanded |
| 23 | `batch23_deliverable_contract_plain_english.md` | What Sapote must produce; A1/A2 outputs; co-location mandate |
| 24 | `batch24_claude_chatgpt_handoff_protocol.md` | Trigger loop; brief format; merge procedure; handoff log |
| 25 | `batch25_onboarding_packet.md` | First-week guide; what to read; how to run your first strain |
| 26 | `batch26_session_handoff_protocol.md` | CDSW; session start; receipt/ingest; judgment store |
| 27 | `batch27_engine_lineage_and_compatibility.md` | Engine version history; scoring boundary changes; compatibility matrix |
| 28 | `batch28_manuscript_figure_atlas_template.md` | Required figures for a natural product paper; data contracts; captions |

---

## Task lookup (combined, both sets)

| I want to... | Go to |
|--------------|-------|
| Get running in 5 min | `batch03` |
| Understand the whole workflow | `batch08` |
| Find a specific tool | `batch01` or `batch09` |
| Fix something broken | `batch04` or `batch22` |
| Write a Mode B card | `batch10`, `batch15` |
| Understand DAPR scoring | `batch16` |
| Handle a split cluster | `batch17` |
| Do a literature search | `batch18` |
| Check a claim for safety | `batch19` |
| Look up a BGC class | `batch20` |
| Make a cross-strain claim | `batch21` |
| Build figures | `batch12` |
| Understand the deliverable contract | `batch23` |
| Hand off between Claude and ChatGPT | `batch24` |
| Onboard a new collaborator | `batch25` |
| Start or close a session properly | `batch26` |
| Understand engine versions | `batch27` |
| Build figures for a paper | `batch28` |
| Find any doc | `batch06` (first set) or `batch15_index` (this file) |

---

## Key reference files in the bundle

These are bundle root or `docs/` files that the batch docs frequently point to:

| File | What it is |
|------|-----------|
| `docs/BUNDLE_CAPABILITIES.md` | Command menu + tool catalog (start every session here) |
| `AGENTS.md` | ChatGPT execution contract |
| `AGENTS.md` | Claude execution contract |
| `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` | Authoritative Mode B §1–§20 spec |
| `docs/CHATGPT_EXECUTION_SLICE_v97147.md` | Active judgment controller (supersedes contract) |
| `docs/DELIVERABLE_CONTRACT.md` | What Sapote must produce per strain |
| `docs/DAPR_CLASS_FRAMEWORK.md` | AB/AF activity buckets (literature-verified) |
| `docs/COMMON_MISTAKES.md` | 11 documented failure modes with fixes |
| `docs/GLOSSARY.md` | Canonical 78-entry glossary |
| `docs/LITERATURE_SEARCH_PROTOCOL.md` | Per-class PubMed search strings + verified bank |
| `docs/BERT_MODE_PROTOCOL.md` | Citation verification discipline |
| `verified_reference_bank_2026-06-29.md` | 13 Bert-Mode-verified citations |
| `docs/ENGINE_LINEAGE.md` | Engine version history |
| `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` | Minimum interpretive depth per section |

---

## Version note

All batch documents in this set target bundle **v9.7.149a / engine 1.9.100**. File counts, tool flags, and structural data were verified against the actual bundle ZIP (`sapote-mamey-v9_7_149-CODE-20260629-224140.zip`, 6.2 MB).
