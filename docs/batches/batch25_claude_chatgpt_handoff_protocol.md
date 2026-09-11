# Claude ↔ ChatGPT Handoff Protocol
**When and how to trigger a ChatGPT task, and how the loop closes**

**v9.7.149a** | Source: `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md` v1.1 | Last updated: 2026-06-29

---

## The division of labour

| Platform | Role | Writes |
|----------|------|--------|
| **Claude (Sapote tier)** | Judgment, scoring, ecology, literature, hallucination-trap audit | C1–C4, D3, E1–E4, F1–F3, G1–G3 workbook sheets; Mode B cards; ecology synthesis |
| **ChatGPT (Mamey tier)** | Extraction, assembly stats, RGGMCI computation | A2 (assembly stats), A3, B1–B4, D1–D2 workbook sheets |

The master workbook is the shared contract. Both platforms validate schema on receipt and log every write to H1_Handoff_Log before handing back.

---

## The trigger loop

```
User uploads batch ZIP
       ↓
Claude merges → produces filled_N+1.xlsx
       ↓
Claude evaluates trigger conditions (see below)
       ↓
[any fire?] → Claude produces CHATGPT_TASK_BRIEF_batchN.md
       ↓               ↓
      No         User copies brief to ChatGPT
       ↓               ↓
Claude outputs    ChatGPT runs Mamey
CDSW next paths  → returns batch ZIP
                        ↓
               User uploads to Claude
                        ↓
               Loop continues
```

---

## Trigger conditions

Claude evaluates these at the **end of every session** in which the workbook is modified. A brief is produced BEFORE the CDSW next-paths list if any condition is true.

| ID | Condition | Source sheet | Task emitted |
|----|-----------|-------------|-------------|
| T1 | ≥3 strains have `assembly_bp` = empty | A2_Strain_Registry | Task B: assembly stats CSV |
| T2 | ≥5 GOOD/MODERATE strains have `final_state = SCAN_SUMMARY_ONLY` | D1_RGGMCI_All_Strains + A2 | Task C: full RGGMCI packages |
| T3 | Any H2 row has `assigned_platform = ChatGPT` and `status = OPEN` | H2_Gap_Queue | Mirror the H2 gap as a task |
| T4 | Any G2 row has `primary_role = type_strain_pending` | G2_Validation_Roles | Task A: new Mamey run |
| T5 | User says "run more strains" / "what does ChatGPT need" | — | Task A with recommended accessions |
| T6 | Batch just merged, ≥2 known-chemistry type strains missing from G2 | G2 vs benchmark table | Task A for next priority strains |

**Suppression:** Claude does NOT emit a brief if all conditions are false, or if the user says "not now" / "skip handoff". A brief is never emitted mid-session — only at session end.

---

## Brief format

Claude uses `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md` to produce a filled brief. Every brief is:

- **Named:** `CHATGPT_TASK_BRIEF_batch{{N}}_{{YYYY-MM-DD}}.md`
- **Self-contained:** ChatGPT needs no additional context to execute it
- **Versioned:** includes current workbook filename, strain count, BGC count
- **Closed-loop:** ends with "Claude will merge automatically on receipt"

The brief is presented as a downloadable file. The user copies it to ChatGPT.

---

## ChatGPT return format

ChatGPT returns a single ZIP containing:

```
Streptomyces_benchmark_project_master_vN_after_batchN.xlsx
Streptomyces_benchmark_batchN_summary_vN.md
Streptomyces_benchmark_batchN_summary_vN.csv
[per-strain package ZIPs — optional]
```

The master xlsx must have all existing strains intact plus new strains appended. Claude validates this on receipt.

---

## Claude merge procedure (on receipt of ChatGPT return)

When the ChatGPT ZIP arrives:

1. Read `H3_Schema_Version` — confirm ≤ current schema version
2. Filter new strains from `BGC_Master` (strains not already in B1)
3. Map columns to B1 schema (see `docs/WORKBOOK_SCHEMA.md`)
4. Apply heuristic ab_auto / af_auto / novelty_auto scoring (0–20 cap)
5. Build A2, B4, C1–C4, D1, F1, G2 rows
6. If RGGMCI `FLBR grade = STRONG` → add D3 entry
7. If strain has known chemistry → add G1 literature rows; assign G2 `benchmark_retrospective_validation` role
8. Update A1 (strain count, BGC count, last_updated)
9. Update A4 for new strains
10. Append A3 run manifest row
11. Append H1 handoff log row
12. Save as `SID-XXX_master_v1_0_Claude_filled_{{N+1}}.xlsx`

---

## Schema validation (both directions, mandatory)

Before any platform hands off the workbook:

```bash
python mamey/workbook_schema_check.py path/to/workbook.xlsx
```

`PASS` required before handoff. Known gaps (e.g. empty B4 scan columns for benchmark strains) are acceptable if documented in H2_Gap_Queue with reason and completion path.

---

## Handoff log entries (H1)

Every handoff — in either direction — appends one row to `H1_Handoff_Log`:

| Column | Value |
|--------|-------|
| date | YYYY-MM-DD |
| platform | `Claude` or `ChatGPT` |
| direction | e.g. `benchmark_batch_merge` / `auto_score_fill` / `assembly_stats_fill` |
| strains_affected | comma-separated short IDs |
| sheets_modified | comma-separated sheet codes |
| file_sha256 | SHA-256 of xlsx being handed off (recommended) |
| validation_result | `PASS` / `PASS_WITH_KNOWN_GAPS` / `FAIL` |
| notes | one-sentence summary |

---

## Literature handoffs

Literature work orders (ChatGPT Bert Mode sessions) follow a different protocol — see `chatgpt_lit_work_order_INSTRUCTIONS.md`. The Bert Mode literature handoff is not the same as the Mamey batch handoff:

| Type | Goes to | Returns |
|------|---------|---------|
| **Mamey batch** | ChatGPT with code execution | Workbook ZIP + per-strain packages |
| **Literature verification** | ChatGPT with web browsing | PMID/DOI/author verification table |

Do not mix the two. A literature work order is not a task brief; a task brief does not trigger literature verification.

---

## CDSW next-paths rule

**Claude (Sapote, non-ChatGPT):** 3–6 genuinely different next paths at the end of every substantive response.

**ChatGPT (Mamey tier):** Exactly 8 unique next paths, numbered 1–8, for every substantive response or handback. No fewer, no more, no duplicates. A ChatGPT handback with <8 paths, >8 paths, duplicate paths, or no paths is non-conformant and must be regenerated.

---

## Quick checklist before handing off to ChatGPT

- [ ] Trigger condition genuinely fires (not suppressed)
- [ ] Task brief generated from template (not ad hoc)
- [ ] Brief is self-contained (ChatGPT needs no prior context)
- [ ] Workbook schema-validated before handoff
- [ ] H1 log entry ready to append on receipt

---

## See also

- **Authoritative source:** `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`
- **Task brief template:** `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md`
- **Schema check:** `python mamey/workbook_schema_check.py`
- **Literature work orders:** `chatgpt_lit_work_order_INSTRUCTIONS.md`
- **CDSW protocol:** session start manifest `docs/BUNDLE_CAPABILITIES.md`
