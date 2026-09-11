# Sapote-Mamey Master Workbook Schema v1.0 (v1.2 additions, 2026-06-11)

>
> **✓ MASTER-SCHEMA FROZEN (v1.1, 2026-06-09).** The canonical *master strain workbook* schema (cross-strain artifact handed Claude↔Mamey) is FROZEN in `MASTER_SCHEMA_FROZEN_v1_1.md`: sheets B5–B12 and D4, three pre-freeze structural fixes, the KCB/MIBiG provenance gate (validated 3 ways + round-trip), and the append-only forward-compatibility contract (v2 must read v1). Per-strain (§57) and custom workbooks are intentionally NOT frozen. Frozen after provisional round-trip validation.
>
> **Two independent schema namespaces — do not conflate.** This document is the **Mamey master-workbook schema (v1.0)**: the cross-strain workbook sheets (A–H groups below), validated by `workbook_schema_check.py`. It is distinct from the **Sapote Excel schema (v1.1)** referenced in monolith §57, which versions a different artifact — the per-analysis `CrypticClass_Triggers` / `Hallucination_Trap_Audit` judgment sheets (the "Class sub-grade" column). The two version numbers track separate schemas and advance independently.

## Purpose

This document defines the canonical sheet structure, column names, and validation rules for the project master workbook. Any platform (ChatGPT, Claude, user) that reads or writes the workbook MUST check this schema on receipt and before handoff.

## Related documents

- **Handoff protocol:** `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md` — when Claude auto-triggers a ChatGPT task brief, merge procedure, and schema validation rules.  
- **Claude system prompt:** `prompts/CLAUDE_SYSTEM_PROMPT.md` — paste into Claude settings; encodes standing rules and trigger conditions.  
- **ChatGPT task brief template:** `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md` — fill-in-the-blanks format Claude uses when emitting a task brief.  
- **Mamey CLI / workflow guide:** `docs/HOW_TO_USE.md` — how to run Mamey (CLI primary; ChatGPT standalone in `docs/standalone/`).

## Design principles

1. **Sheet codes are stable identifiers.** Every sheet has a code (A1, B2, etc.) that never changes. Platforms reference sheets by code, not by name.
2. **Columns are named exactly.** No synonyms. `Products` is always `Products`, never `Products/classes`.
3. **Empty cells mean "not yet computed."** Never fill with 0 or NULL unless the value is genuinely zero/null.
4. **Handoff validation is mandatory.** On receipt, the receiving platform checks: (a) all expected sheets exist, (b) column headers match, (c) row counts are consistent across sheets.

---

## Sheet index

### Section A — Project administration

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| A1 | `A1_Dashboard` | Project summary stats, version, strain count | Auto | Fixed |
| A2 | `A2_Strain_Registry` | One row per strain: identity, assembly, status, top leads | Both | 1/strain |
| A3 | `A3_Run_Manifest` | One row per Mamey run: date, version, input, output | Runner | 1/run |
| A4 | `A4_Completeness_Audit` | One row per strain: which sheets/fields are populated | Auto | 1/strain |

### Section B — BGC inventory (Tier 1 / Mamey extraction)

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| B1 | `B1_BGC_Master` | One row per BGC: coordinates, products, boundary, KCB, CCTT | Mamey | 1/BGC |
| B2 | `B2_Product_Class_Matrix` | Strain × product-class count matrix — **raw antiSMASH product counts, including standing-rule DROP classes (saccharide, NAPAA, hglE-KS, ectoine, redox-cofactor).** Use for inventory overview; do not use for lead-count claims without filtering. | Mamey | 1/strain |
| B3 | `B3_Known_Cluster_Matrix` | Strain × KCB-top-hit count matrix | Mamey | 1/strain |
| B4 | `B4_Cross_Strain_Scans` | Strain × scan totals (DasR, CCTT, CGAD, bldA, resistance) | Mamey | 1/strain |

### Section C — Judgment (Tier 2 / Sapote-slim)

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| C1 | `C1_DAPR_Antibacterial` | Ranked antibacterial leads across all strains | Sapote | 1/lead |
| C2 | `C2_DAPR_Antifungal` | Ranked antifungal leads across all strains | Sapote | 1/lead |
| C3 | `C3_Lead_Tier_Summary` | One row per strain: top AB lead, top AF lead, tier, band | Sapote | 1/strain |
| C4 | `C4_Strain_Decision_Table` | Sapote composite score, recommended role per strain | Sapote | 1/strain |

### Section D — RGGMCI and split-locus rescue

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| D1 | `D1_RGGMCI_All_Strains` | One row per strain: pair counts, promoted groups, state | Mamey | 1/strain |
| D2 | `D2_RGGMCI_Top_Pairs` | Top 10 HIGH pairs per strain (or top 50 for focal strains) | Mamey | ~10/strain |
| D3 | `D3_RGGMCI_Promoted` | Promoted rescue groups with evidence and claim ceiling | Sapote | 1/group |
| D5 | `Fragment_Rescue_Tiers` | One row per strain: assembly metrics + fragment-rescue tier (A–D) | Mamey | 1/strain |

### Section E — Deep analysis (Tier 3 / Sapote full / Mode B)

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| E1 | `E1_Mode_B_Index` | Which BGCs have full Mode B, link to per-strain sheets | Sapote | 1/BGC |
| E2 | `E2_Comparative_Pairs` | Ortholog/paralog pairs with protein %ID summary | Sapote | 1/pair |
| E3 | `E3_Megacluster_Registry` | BGCs >150 kb flagged for long-read confirmation | Mamey | 1/BGC |
| E4 | `E4_A_Domain_Summary` | NRPS A-domain specificities for Mode B BGCs | Sapote | 1/domain |

### Section F — Ecology and regulatory context

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| F1 | `F1_Ecology_Readiness` | Per-strain: taxonomy, source, habitat, readiness score | Both | 1/strain |
| F2 | `F2_Regulatory_TFBS` | TFBS hits with TF family, target, score | Mamey | 1/hit |
| F3 | `F3_Ecology_Theme_Board` | Cross-strain ecological themes (chitin, iron, etc.) | Sapote | 1/theme |

### Section G — Literature and validation

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| G1 | `G1_Literature_Index` | Per-BGC citation/evidence entries | Sapote | 1/citation |
| G2 | `G2_Validation_Roles` | Per-strain validation assignment for manuscript | Sapote | 1/strain |
| G3 | `G3_Hallucination_Trap_Audit` | Trap checks with disposition and evidence | Sapote | 1/trap |

### Section H — Handoff and audit

| Code | Sheet name | Purpose | Owner | Rows |
|---|---|---|---|---|
| H1 | `H1_Handoff_Log` | Platform handoff events with SHA-256 and validation | Both | 1/event |
| H2 | `H2_Gap_Queue` | Outstanding gaps with priority and required input | Both | 1/gap |
| H3 | `H3_Schema_Version` | Schema version, column definitions, change log | Fixed | Fixed |

---

## Column specifications for core sheets

> **Enforced spec:** the columns actually validated are defined in `mamey/workbook_schema_check.py` `REQUIRED_SHEETS` (reconciled to the deployed build, v1.2). The lists below are the original design reference; where they differ, the validator wins.

### A2_Strain_Registry

| Column | Type | Required | Source |
|---|---|---|---|
| strain | str | yes | Mamey |
| taxonomy | str | no | User/literature |
| ecology_source | str | no | User/literature |
| habitat | str | no | User (attine/bee/bryophyte/marine/benchmark) |
| assembly_bp | int | yes | Mamey |
| contigs | int | yes | Mamey |
| n50 | int | yes | Mamey |
| gc_pct | float | yes | Mamey |
| bgc_count | int | yes | Mamey |
| interior_pct | float | yes | Mamey |
| assembly_tier | str | yes | Mamey (GOOD/MODERATE/VERY_POOR) |
| workflow_version | str | yes | Mamey (e.g. "v1.9.7") |
| package_status | str | yes | Both (EXTRACTION_ONLY/JUDGMENT/MODE_B/COMPLETE) |
| top_ab_bgc | str | no | Sapote |
| top_ab_class | str | no | Sapote |
| ab_score | float | no | Sapote |
| ab_band | str | no | Sapote (Exceptional/Very_High/High/Medium/Exploratory) |
| top_af_bgc | str | no | Sapote |
| top_af_class | str | no | Sapote |
| af_score | float | no | Sapote |
| af_band | str | no | Sapote |
| rggmci_state | str | yes | Mamey |
| gap_next_action | str | no | Both |

### B1_BGC_Master

| Column | Type | Required | Source |
|---|---|---|---|
| strain | str | yes | Mamey |
| BGC_ID | str | yes | Mamey (BGC001, BGC002, ...) |
| contig | str | yes | Mamey |
| region | str | yes | Mamey (region001, region002, ...) |
| start | int | yes | Mamey |
| end | int | yes | Mamey |
| length_kb | float | yes | Mamey |
| products | str | yes | Mamey (semicolon-separated) |
| boundary | str | yes | Mamey (Interior/Edge/Full-contig) |
| arch | str | yes | Mamey (A/B/C/D/E) |
| kcb_top | str | yes | Mamey |
| kcb_score | float | yes | Mamey |
| kcb_proteins | int | yes | Mamey |
| cctt_triggers | str | no | Mamey |
| resistance_tier | str | no | Mamey |
| tta_tier | str | no | Mamey |
| ab_auto | float | no | Sapote-slim |
| af_auto | float | no | Sapote-slim |
| novelty_auto | float | no | Sapote-slim |
| lead_tier_auto | str | no | Mamey routing prior (Exceptional/High/Medium/Low/Inventory); Low and Inventory are class-gated below-Medium labels, not activity states |
| depth_floor | str | no | Sapote (full_mode_b/abbreviated/inventory_only) |

### C1_DAPR_Antibacterial / C2_DAPR_Antifungal  (schema v1.2 — reconciled to deployed columns)

**Hybrid sheet.** *Deterministic columns* are Mamey-regenerable (BGC data + framework lookup); *judgment columns* are the Sapote scoring/ranking overlay. The deterministic builder (`tools/build_dapr_rescue_sheets.py`) fills/refreshes the deterministic columns idempotently **without touching the judgment columns**.

| Column | Type | Required | Owner | Source |
|---|---|---|---|---|
| Rank | int | yes | Sapote | within-board ranking (judgment) |
| strain | str | yes | Mamey | strain id (values may be lab IDs, e.g. SID-XXX) |
| BGC_ID | str | yes | Mamey | BGC id (carry contig·region locator per §4 on first mention) |
| Product_Class | str | yes | Mamey | antiSMASH product class(es) |
| AN_Score | int | yes | Sapote | activity-association confidence (3 HIGH / 2 MED / 1 WATCH) |
| WL_Score | int | yes | Sapote | wet-lab priority (completeness + value) |
| Rationale | str | no | Sapote | evidence summary (judgment) |
| KCB_Provenance | str | yes | Mamey | KnownClusterBlast nearest cluster |
| Activity_Ref | str | yes | **Mamey (deterministic)** | framework citation lookup keyed on KCB compound → verification tag (VERIFIED / ROUTED-OUT / antifungal-adjacent), mirrored in `docs/DAPR_CLASS_FRAMEWORK.md` |

**Determinism:** `Activity_Ref` is a pure function of the KCB nearest compound via the framework citation map (embedded in the builder, documented in `DAPR_CLASS_FRAMEWORK.md`). Re-running the builder reproduces it exactly. The *selection and ranking* of board rows remains a Sapote judgment pass (class-level hypotheses; typed metadata does not add a score; cytotoxic-adjacent + siderophore classes routed out).

### E2_Comparative_Pairs

| Column | Type | Required | Source |
|---|---|---|---|
| pair_id | str | yes | e.g. "BGC011_BGC055" |
| strain_a | str | yes | |
| bgc_a | str | yes | |
| strain_b | str | yes | |
| bgc_b | str | yes | |
| length_a_kb | float | yes | |
| length_b_kb | float | yes | |
| products | str | yes | |
| subprogram_match | str | yes | e.g. "17/17" |
| mean_pct_id_core | float | yes | |
| mean_pct_id_all | float | yes | |
| a_domain_match | str | no | e.g. "7/7 identical Stachelhaus" |
| diverged_genes | str | no | |
| interpretation | str | yes | ortholog/paralog/unrelated |

---

## Handoff protocol

### Sender (platform completing work)

1. Populate all sheets relevant to the work done
2. Update A4_Completeness_Audit for affected strains
3. Add row to H1_Handoff_Log: date, platform, SHA-256 of xlsx, sheets modified
4. Validate: no orphan strains (every strain in A2 must appear in B1, B2, B4)
5. Export xlsx and provide to user

### Receiver (platform starting work)

1. Open xlsx, read H3_Schema_Version — confirm compatible
2. Read H1_Handoff_Log — identify what was last modified
3. Validate: A2 row count = B2 row count = B4 row count = D1 row count
4. Read A4_Completeness_Audit — identify gaps to fill
5. Proceed with assigned work

### User checkpoint

The user can verify workbook health by checking:
- A1_Dashboard: strain count, BGC count match expectations
- A4_Completeness_Audit: which strains have which sections populated
- H1_Handoff_Log: audit trail of who did what when

---

## Versioning

This is Schema v1.0. Changes to column names or sheet codes require a version bump in H3_Schema_Version. Adding new sheets uses the next available code in the appropriate section.

### Schema v1.2 additions (2026-06-11)

Append-only changes, forward-compatible (v1.1 readers ignore the new column/sheet):

1. **`C1/C2_DAPR` gain `Activity_Ref`** — a deterministic column (framework citation lookup keyed on the KCB nearest compound; see the reconciled C1/C2 spec above). Mamey-regenerable; the rank/score columns remain Sapote judgment.
2. **`Fragment_Rescue_Tiers`** — new fully-deterministic sheet (spec below).
3. **Cross-strain overlay sheets recognized:** `Cross_Strain_Class_Prevalence`, `Cross_Strain_Findings`, `Strain_Cohort_Context` are now schema-acknowledged overlay sheets (un-coded; emitted by the cross-strain builder). They were previously pending fold-in.

Deterministic regeneration of items (1) and (2) is provided by `tools/build_dapr_rescue_sheets.py`. The framework citation map is the single source of truth for `Activity_Ref` and is mirrored in `docs/DAPR_CLASS_FRAMEWORK.md`.

### Fragment_Rescue_Tiers (code D5; schema v1.2 — deterministic)

Fully deterministic from assembly/scan metrics with fixed tier thresholds. Regenerated by `tools/build_dapr_rescue_sheets.py`.

| Column | Type | Required | Source |
|---|---|---|---|
| Tier | str (A–D) | yes | tier rule below |
| strain | str | yes | strain id |
| Assembly | str | yes | GOOD/MOD/POOR (N50 ≥ 1 Mb / ≥ 100 kb / else) |
| Contigs | int | yes | assembly contig count |
| N50 | int | yes | assembly N50 (bp) |
| Frag_Loss | float | yes | raw − corrected BGC count |
| EFLS_Pairs | int | yes | fragment-linkage recovery candidates (≈0 in closed genomes) |
| RG_GMCI_HIGH | int | yes | reference-anchored recovery candidates |
| FLBR_Megasynth | int | yes | genome-wide megasynthase census (NOT a fragmentation metric) |
| Recommendation | str | yes | tier-derived re-sequencing guidance |

**Tier thresholds (locked):** `A` if N50 ≥ 1,000,000; else `D` if EFLS_Pairs < 20; else `B` if EFLS_Pairs ≥ 600; else `C`.

---

## Platform-specific notes

### ChatGPT (Mamey runner)
- Populates: A2 (partial), A3, B1–B4, D1–D2
- Has Biopython: can run source-derived scans directly
- Limitation: cannot do protein-level comparison without explicit FASTA extraction

### Claude (Sapote runner)
- Populates: A2 (judgment fields), C1–C4, D3, E1–E4, F1–F3, G1–G3
- Has shim: can parse GBK from antiSMASH ZIPs for protein comparison
- Limitation: no Biopython, no network for BLAST

### User
- Populates: A2 (taxonomy, ecology, habitat), F1 (metadata)
- Validates: A4 completeness, H1 handoff log
- Decides: which strains get Mode B, which go to Zenodo

---

## Schema-vs-deployed status (v1.2 audit, 2026-06-11)

Generated by `tools/schema_deployed_audit.py` (full report: `docs/SCHEMA_DEPLOYED_AUDIT.md`).
Of 29 coded sheets: **12 MATCHED**, **1 MAPPED**, **16 SCHEMA-ONLY**; 14 deployed sheets are detail/overlay sheets outside the coded index.

**MATCHED (built):** A1, A2, A4, B1, B2, B3, B4, C1, C2, D1, D2, D5.

**MAPPED (name to reconcile):** F2_Regulatory_TFBS ⇐ deployed `TFBS_Motifs`.

**SCHEMA-ONLY → BUILD next (deterministic / seedable):** E3_Megacluster_Registry (from B1, BGCs >150 kb), G1_Literature_Index (seed from `Lit_Verification_*`), H3_Schema_Version (fixed metadata).

**SCHEMA-ONLY → DEFERRED (Sapote judgment / per-analysis / on-demand):** A3, C3, C4, D3, E1, E2, E4, F1, F3, G2, G3, H1, H2.

**DEPLOYED-ONLY (recognized detail/overlay, not yet coded):** About; BGC_Scan_Profile, BGC_Domain_Architecture, BGC_Class_Predictions; Gene_NRPS_PKS_Substrates, Gene_Active_Sites, Gene_RiPP_Cores, Gene_Domain_Hits; TFBS_Motifs (→F2); Cross_Strain_Compare; TIGRFAM_Check; Strain_Catalog; Cross_Strain_Class_Prevalence, Cross_Strain_Findings, Strain_Cohort_Context.

**Naming reconciled (2026-06-11):** the strain key + taxonomy columns are now generic `strain`/`taxonomy` across all sheets (lab-specific `SID`/`Organism` retired from the schema; strain-ID *values* like `SID-XXX` remain as identifiers). Core validator reconciled to the deployed columns (2026-06-11): `workbook_schema_check.py` REQUIRED_SHEETS now describes the 27 built sheets exactly and **PASSES** (0 missing / 0 extra / 0 column errors). The 16 deferred coded sheets moved to OPTIONAL_SHEETS (documented, not required). The idealized column lists in 'Column specifications' below are retained as the design reference where they differ from the enforced deployed spec. Pick one canonical naming and align either the builder or the schema column specs. This is why the core validator reports column_errors even though the v1.2 deterministic checks pass.
