# Patch Spec — Sapote-Mamey v9.7.136 Citation-Compact Mode

**Target base:** Sapote-Mamey v9.7.135  
**Patch name:** v9.7.136 — citation-compact output budget  
**Patch type:** output/reporting efficiency + citation-ledger validation  
**Engine impact:** no biosynthetic scoring change  
**Primary goal:** reduce token waste in assistant-facing and report-facing outputs while increasing citation/evidence density.

---

## 1. Problem

Sapote-Mamey reports and chat handbacks can spend too many tokens repeating the same claim-ceiling / genome-mining caveat in every BGC card, table row, lead paragraph, and report section.

This hurts the actual user goal:

- less room for evidence;
- fewer citations per output;
- more repeated boilerplate;
- more token pressure in ChatGPT/Claude;
- harder merge work across chats.

The system already has claim-safety internally. What is missing is a compact output profile that separates:

1. **internal safety state** — validators, safe-claim fields, uncertainty flags; from
2. **reader-facing prose** — one global caveat plus dense evidence/citation tables.

---

## 2. Design Principle

Do **not** remove claim-safety.

Instead:

- keep claim-safety fields internally;
- emit one global BGC caveat per report/package;
- move repeated safe-claim prose into structured columns;
- require a citation/evidence basis for priority leads;
- write a machine-readable citation ledger;
- make assistant handbacks delta-first and file-first.

---

## 3. New Mode

Introduce a report/output profile named:

```text
citation-compact
```

CLI spelling:

```bash
--token-budget citation-compact
```

This flag is wired into `mamey run` in the runtime patch. The profile name is stable.

---

## 4. Required Behavior

Citation-compact mode must:

1. emit `GLOBAL_BGC_CAVEAT` once per report/package;
2. suppress repeated claim-ceiling paragraphs from individual BGC cards;
3. retain compact safety columns:
   - `claim_scope`
   - `evidence_basis`
   - `citation_basis`
   - `uncertainty_flags`
   - `next_experiment`
4. write:
   - `Citation_Ledger.csv`
   - `Citation_Ledger.json`
5. require citation basis for priority leads:
   - `EXCEPTIONAL`
   - `HIGH`
   - optionally top-N `MEDIUM`
6. mark missing citation coverage as `citation_needed`, never invent references;
7. preserve all existing score/triage behavior.

---


## 4b. Literature Search Work Orders

When a citation is missing, citation-compact mode must not invent it. Instead it emits:

- `citation_compact/Literature_Search_WorkOrder.md`
- `citation_compact/Literature_Search_WorkOrder.json`

These files are designed for a separate web/literature ChatGPT session. Each task includes the strain, BGC, locus, candidate class, evidence basis, exact citation need, search instruction, required output format, and a do-not-infer rule.


## 5. Out of Scope

This patch does **not** change:

- AB/AF scoring;
- BGC ranking;
- cassette calls;
- KCB parsing;
- RG-GMCI;
- MIBiG matching;
- edge/interior correction;
- assembly QC.

This is an output and validation-layer patch.

---

## 6. Files Added or Modified in This Proposal

Added:

- `mamey/citation_compact.py`
- `schemas/citation_ledger_v1.schema.json`
- `schemas/lead_record_citation_compact_v1.schema.json`
- `schemas/literature_search_workorder_v1.schema.json`
- `templates/citation_compact/technical_report.md`
- `templates/citation_compact/bench_guide.md`
- `templates/citation_compact/layperson_guide.md`
- `templates/citation_compact/lead_table.md`
- `docs/CITATION_COMPACT_MODE.md`
- `docs/patch_notes/PORT_PLAN_v9.7.136_FROM_MAMEY_v1.7.2.md`
- `tests/test_citation_compact_v97136.py`
- `tests/test_citation_compact_runtime_v97136.py`

Modified:

- `mamey/cli.py`
- `docs/DELIVERABLE_CONTRACT.md`

---

## 7. Acceptance Tests

Minimum acceptance tests:

1. priority lead without `citation_basis` fails validation;
2. priority lead with `citation_basis` passes validation;
3. `Citation_Ledger.csv` and `.json` preserve required fields;
4. report text with zero or one global caveat passes;
5. report text with repeated global caveat fails;
6. compact templates do not contain repeated claim-ceiling boilerplate;
7. compact templates include `Citation_Ledger` or citation-ledger placeholder;
8. `mamey run --token-budget citation-compact` is accepted by the CLI parser;
9. package emission writes `Citation_Ledger.csv/json` and compact technical/bench/layperson reports.

---

## 8. Release Recommendation

Use v9.7.135 as the stable base.

Cut this as:

```text
v9.7.136 — citation-compact output budget
```

Do not backport into v9.7.135.
