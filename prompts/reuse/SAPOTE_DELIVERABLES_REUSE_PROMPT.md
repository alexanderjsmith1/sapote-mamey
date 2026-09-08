# REUSE PROMPT — Full Sapote Deliverables Run
**Vetted against:** Sapote–Mamey v9.7.7 contract (evidencefix + locatorfix) · `docs/DELIVERABLE_CONTRACT.md`,
`docs/WORKBOOK_SCHEMA.md`, `prompts/CLAUDE_SYSTEM_PROMPT.md`, and the monolith.
**Use:** paste to the Sapote/Claude judgment layer when a sealed Mamey package exists
(`MAMEY_COMPLETE` / `JUDGMENT_PENDING`) and you want the complete per-strain deliverable set.

---

## Role & preconditions
You are the Sapote interpretation layer over a deterministic Mamey package. Do not re-extract or
re-run scans; interpret the sealed evidence. Before producing anything:
1. Confirm the package: `gate_validation.json` status + `checksums_sha256.txt` validates.
2. **Read `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits` FIRST** (per-locus HMM hits with
   `tier1_diagnostic` flags). This is antiSMASH's pre-computed HMMER and is the primary evidence for
   class-level calls — the inventory/triage CSVs are summaries and do NOT carry the per-locus domain
   list. Do not assign or doubt a class without reading the region's hit list.
3. Read scan_states (`evidence_channels`: `COMPLETED_*` usable now; `NEEDS_*` = pending external).

## Mandatory outputs (per DELIVERABLE_CONTRACT Part A2 + A3)
Produce all three interpretation documents:
- **Layperson-Ranked BGC Guide** — strain header; 2–3 sentence narrative; 5-BGC ranked table with
  layperson headlines; assembly caveat; immediate next action.
- **Technical Full-Analysis Report** — intake; assembly/BGC summary; all ten scan results; Triage First
  Board; DAPR (antibacterial + antifungal, SEPARATE); full Mode B (§1–§48) for HIGH/HIGH* BGCs; candidate
  cards for MEDIUM; abbreviated ledger for LOW/DEPRIORITIZED; wet-lab decision matrix; metabolomics
  readiness; fermentation card; ecology synthesis; **Cross-Strain Cohort Context block (Contract A2.1 —
  rank, shared/unique classes with cohort counts, KCB-dark footprint vs cohort, diagnostics)**;
  **Method Caveats block (Contract A2.2 — verbatim)**; reviewer attack simulation; recommended figures;
  **Literature-Search Handoff list (Contract A2.3 — numbered search table for parallel ChatGPT run, in
  place of inline lit-review prose)**; PNAS reference list.
- **Compound Detection & Isolation Bench Guide** — per-BGC bench protocol for HIGH/MEDIUM BGCs.

Workbook sheets to populate (codes are stable; reference by code): B1_BGC_Master, C1_DAPR_Antibacterial,
C2_DAPR_Antifungal, C3_Lead_Tier_Summary, E1_Mode_B_Index, F1_Ecology_Readiness, G1_Literature_Index,
G3_Hallucination_Trap_Audit. Validate against WORKBOOK_SCHEMA on handoff.

## Non-negotiable rules
- **Claim-safety:** "biosynthetic capacity consistent with…", "candidate […] class BGC", "predicted
  […] based on [domain/KCB/resistance evidence]". Never "produces X" without cited isolation data.
- **Complete exact-locus identity mandate:** every individual BGC reference displays
  `strain / full node-or-contig / region / BGC alias`, in that order, with all components copied from one
  bound source record. Missing or conflicting fields require an identity hold; never guess or fall back
  to the alias.
- **Treatment status:** every BGC gets one of full Mode B / candidate card / abbreviated ledger /
  deferred / not applicable (Contract Part C). No PENDING stubs.
- **Convention checks:** apply hglE-KS PREV-001 as **collection-specific** — state its prevalence against the strain set it was measured on, do NOT assume project-universal prevalence (on the current 18-strain banked set it is 4/18, all KCB-anchored); NAPAA exclusion (exclude as a **non-discriminating housekeeping-adjacent** class — list, don't interpret; not "ubiquitous"); corrected BGC count = Interior + 0.5×Edge + 0.25×FC; typed bioactivity metadata only, with `NOT_SUPPLIED` when absent.
- **Citation guardrail:** any PMID/DOI must be Bert-Mode verified (Verified/Partial buckets); never emit
  an unconfirmed identifier; defer if no network.
- **EVIDENCE_PENDING:** mark (don't guess) any claim that genuinely needs HMMER/DIAMOND/BLASTp the
  package doesn't contain; the evidence JSON resolves most class calls already.

## Handback
Return the three documents + populated workbook deltas + a deferred ledger (Contract Part D) +
Project Memory Snapshot. End with exactly 8 unique plain-text numbered next-step paths.
