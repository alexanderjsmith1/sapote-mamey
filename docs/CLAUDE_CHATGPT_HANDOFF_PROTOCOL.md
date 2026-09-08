# Claude ↔ ChatGPT Handoff Protocol
**Version:** 1.1 · Mamey v1.9.152 / Sapote v9.7.414  
**File location:** `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`

---

## Companion-tool handoff override

For BiG-SCAPE, GToTree, IQ-TREE, ANI, and reference-download work, the shared workbook is not the
run controller. `docs/LLM_COMPANION_TOOL_PROTOCOL.md` governs: `CURRENT_RUN.txt`, immutable input
manifest, state/events, exact command, QA receipt, portable exports, and `HANDOFF.md`. A receiving
agent resumes from those files and does not rediscover or rerun verified work.

## Overview

The Sapote-Mamey system splits work across two LLM platforms:

- **Claude (Sapote tier):** Judgment, scoring, ecology, literature, hallucination-trap audit. Writes C1–C4, D3, E1–E4, F1–F3, G1–G3.  
- **ChatGPT (Mamey tier):** Extraction, assembly stats, RGGMCI computation. Writes A2 (assembly stats), A3, B1–B4, D1–D2.

The master workbook (`SID-XXX_master_v1_0_Claude_filled_N.xlsx`) is the shared contract. Both platforms validate schema on receipt and log every write to H1_Handoff_Log before handing back.

This document defines when Claude automatically triggers a follow-up request to ChatGPT, what format that request takes, and how the loop closes.

---

## The trigger loop

```
User uploads batch zip
        ↓
Claude merges → produces filled_N+1.xlsx
        ↓
Claude evaluates trigger conditions (see §2)
        ↓
 [any fire?] ──Yes──→ Claude produces CHATGPT_TASK_BRIEF_batchN.md
        ↓                       ↓
        No              User copies brief to ChatGPT
        ↓                       ↓
Claude outputs              ChatGPT runs Mamey
CDSW next paths          → returns batch zip
                                ↓
                         User uploads to Claude
                                ↓
                         Loop continues
```

---

## §1 — Trigger conditions

Claude evaluates these at the **end of every session** in which the workbook is modified. If any condition is true, Claude produces a task brief BEFORE the CDSW next-paths list.

| ID | Condition | Source sheet | Task emitted |
|---|---|---|---|
| T1 | ≥3 strains have `assembly_bp` = empty | A2_Strain_Registry | Task B: assembly stats CSV |
| T2 | ≥5 GOOD or MODERATE assembly strains have `final_state = SCAN_SUMMARY_ONLY` | D1_RGGMCI_All_Strains + A2 | Task C: full RGGMCI packages |
| T3 | Any H2 row has `assigned_platform` containing "ChatGPT" and `status = OPEN` | H2_Gap_Queue | Mirror the H2 gap as a task |
| T4 | Any G2 row has `primary_role = type_strain_pending` | G2_Validation_Roles | Task A: new Mamey run for that strain |
| T5 | User says "run more strains", "what does ChatGPT need", or similar intent | — | Task A with recommended accessions |
| T6 | Batch just merged, ≥2 known-chemistry type strains still missing from G2 | G2 cross-referenced with benchmark table | Task A for next priority strains |

**Suppression:** Claude does NOT emit a brief if all conditions are false, or if the user explicitly says "not now" / "skip handoff". A brief is never emitted mid-session — only at the end.

---

## §2 — Brief format specification

Claude uses `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md` to produce a filled brief. The brief is always:

- Named: `CHATGPT_TASK_BRIEF_batch{{N}}_{{YYYY-MM-DD}}.md`  
- Self-contained: ChatGPT needs no additional context to execute it  
- Versioned: includes current workbook filename, strain count, BGC count  
- Closed-loop: ends with "Claude will merge automatically on receipt"

The brief is presented as a downloadable file in the Claude response. The user copies it to ChatGPT.

---

## §3 — ChatGPT return format

ChatGPT returns a single zip containing:

```
Streptomyces_benchmark_project_master_vN_after_batchN.xlsx
Streptomyces_benchmark_batchN_summary_vN.md
Streptomyces_benchmark_batchN_summary_vN.csv
[per-strain package zips — optional]
```

The master xlsx must have all existing strains intact plus new strains appended. Claude validates this on receipt.

---

## §4 — Claude merge procedure (on receipt)

1. Read `H3_Schema_Version` — confirm ≤ current schema version.
2. Filter new strains from `BGC_Master` (strains not already in B1).
3. Map columns to B1 schema (see `docs/WORKBOOK_SCHEMA.md` §Column specs).
4. Apply heuristic ab_auto / af_auto / novelty_auto scoring (0–20 cap).
5. Build A2, B4, C1–C4, D1, F1, G2 rows.
6. If RGGMCI `FLBR grade = STRONG`: add D3 entry.
7. If strain has known chemistry: add G1 literature rows; assign G2 `benchmark_retrospective_validation` role.
8. Update A1 (strain count, BGC count, last_updated).
9. Update A4 for new strains.
10. Append A3 run manifest row.
11. Append H1 handoff log row.
12. Save as `SID-XXX_master_v1_0_Claude_filled_{{N+1}}.xlsx`.

---

## §5 — Schema validation before handoff (both directions)

Before any platform hands off the workbook, run:

```bash
python mamey/workbook_schema_check.py path/to/workbook.xlsx
```

A `PASS` result is required before handing off. Known gaps (e.g. empty B4 scan columns for benchmark strains) are acceptable if documented in H2_Gap_Queue.

---

## §6 — Handoff log entries (H1)

Every handoff — in either direction — appends one row to `H1_Handoff_Log`:

| Column | Value |
|---|---|
| date | YYYY-MM-DD |
| platform | `Claude` or `ChatGPT` |
| direction | `benchmark_batch_merge` / `auto_score_fill` / `assembly_stats_fill` / etc. |
| strains_affected | comma-separated short IDs |
| sheets_modified | comma-separated sheet codes |
| file_sha256 | SHA-256 of the xlsx being handed off (optional but recommended) |
| validation_result | `PASS` / `PASS_WITH_KNOWN_GAPS` / `FAIL` |
| notes | one-sentence summary |

---

## §7 — Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-06-08 | Initial protocol; 6 trigger conditions; template-based brief generation |
