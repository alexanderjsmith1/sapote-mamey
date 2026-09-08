# Master Strain Workbook — Canonical Schema (FROZEN, v1.1)
**STATUS: FROZEN 2026-06-09.** This is the canonical master strain workbook schema. Frozen after the provisional round-trip validated the KCB/MIBiG provenance gate three ways (reject / exempt / satisfiable) and demonstrated it on regenerated output (127 source-verified MIBIG_REFERENCE_LINE rows, 348 honest UNRESOLVED). Future changes are append-only per the forward-compatibility contract; structural changes require a v2 (which must still read v1).
*DEPLOYED (v1.1, frozen 2026-06-09). Defines the frozen, cross-strain master schema; per-strain (§57) and custom workbooks are intentionally NOT frozen. This contract is live — `mamey/workbook_schema_check.py` validates against it (SCHEMA_VERSION = "v1.1"). Its content is also reflected in docs/WORKBOOK_SCHEMA.md.*

## Scope of the freeze
- **FROZEN:** the master strain workbook — the cross-strain artifact handed between Claude and Mamey, merged by host. This document.
- **NOT frozen:** per-strain Sapote workbooks (AS-XXX style, monolith §57 namespace) and one-off custom user deliverables. They evolve independently.

## Forward-compatibility contract (the archival guarantee)
1. **Sheet codes are append-only & permanent.** A2, B1, B4, etc. never change meaning or get renumbered. v2 adds B10+, never repurposes a frozen code.
2. **Columns are append-only within a sheet.** v2 may ADD columns; it must never rename, reorder-by-meaning, or delete a frozen column. Readers locate columns by header name, not position.
3. **v2 MUST read v1.** A v2 reader accepts a v1 workbook by sheet code, ignoring columns it does not recognize rather than rejecting. A v1 reader encountering v2 extra columns ignores them. This is what lets a student's v1 workbook be reanalyzed by a future Claude with no context.
4. **Self-identifying.** Every master carries `workbook_type = MASTER_STRAIN_WORKBOOK` and `schema_version` (H3) so any tool/gate distinguishes a frozen master from a per-strain/custom file without guessing.

## Structural fixes applied BEFORE freeze (cannot be fixed by append-only later)
- **FIX-1 — scan summaries → structured integers.** The current `Strain_Master` prose columns (`CCTT_summary`="T43-HAL:7, T43-NUC:2…", `Resistance_summary`="9 total hits; 4 T1 BGCs", etc.) become numeric fields in **B4_Cross_Strain_Scans** (strain × scan-count). Prose retained ONLY as an optional `*_summary_text` human-readable extra. Removes the permanent parsing tax.
- **FIX-2 — de-glue top-lead projection.** `Top_BGC/Top_products/Top_AB_auto/...` leave `A2_Strain_Registry`; top-lead info is derived by joining to B1/Top_Leads (or lands in C3_Lead_Tier_Summary). A2 = pure identity/assembly/status.
- **FIX-3 — remove redundant/staging sheets.** `Host_Metadata` (subset of A2) folded into A2. `New_Strains_Summary`/`New_Top_Leads` folded into A2/B1 via a `batch` + `status` column (no parallel staging sheets).

## Canonical sheet set (frozen)

### Group A — Registry & meta
| Code | Sheet | Purpose | Owner | Key | Rows |
|---|---|---|---|---|---|
| A1 | A1_Dashboard | type marker, schema_version, strain/BGC counts, generated date | Auto | — | fixed |
| A2 | A2_Strain_Registry | per-strain identity, host/source, assembly stats, tier, status, batch | Both | strain | 1/strain |
| A3 | A3_Run_Manifest | per Mamey run: date, version, input, output, SHA | Runner | run_id | 1/run |
| A4 | A4_Completeness_Audit | per-strain: which sheets/fields populated | Auto | strain | 1/strain |

### Group B — BGC inventory, scans, class views
| Code | Sheet | Purpose | Owner | Key | Rows |
|---|---|---|---|---|---|
| B1 | B1_BGC_Master | one row per BGC: coords, products, boundary, arch, KCB, CCTT, scores | Mamey | strain+BGC_ID | 1/BGC |
| B2 | B2_Product_Class_Matrix | strain × product-class count | Mamey | strain | 1/strain |
| B3 | B3_Known_Cluster_Matrix | strain × KCB-top-hit count | Mamey | strain | 1/strain |
| B4 | B4_Cross_Strain_Scans | **strain × scan-count INTEGERS** (T43-* CCTT, CGAD, bldA/TTA, resistance tiers, RG-GMCI, FLBR, UMED, EFLS, PHO) — FIX-1 target | Mamey | strain | 1/strain |
| B5 | B5_Strict_Marker_Calls | one row per marker call (family, call, contig, loci, coords) — already normalized, keep as-is | Mamey | strain+BGC_ID+marker | 1/call |
| B6 | B6_Protein_Marker_Hits | one row per protein hit (locus, gene, product, sec_met_domain, aSDomain) — keep as-is | Mamey | strain+locus_tag | 1/hit |
| B7 | B7_External_HMMER_Worklist | BGCs needing external HMMER/domtblout, with recommended test | Mamey | strain+BGC_ID | 1/item |
| **B8** | **B8_Top100_CrossStrain** | ranked VIEW over B1 (top 100 by Sapote priority) + grouped-frequency block | Sapote | strain+BGC_ID | ≤100 |
| **B9** | **B9_Top_PKS_BGCs** | ranked VIEW over B1 (polyketide filter) + KCB-MIBiG provenance cols + grouped-frequency | Sapote | strain+BGC_ID | ≤50 |
| **B10** | **B10_Nucleoside_RareClass** | rare-class enumeration (all hits, hit_level, rarity stats) | Sapote | strain+BGC_ID/strain-level | all hits |
| **B11** | **B11_RareClass_Template** | reusable rare-class contract (phosphonate/enediyne/carbapenem) | Sapote | strain+BGC_ID | all hits |
| **B12** | **B12_Top_Halogenation_BGCs** | ranked VIEW over B1 (halogenation: label + T43-HAL tiers) + grouped-frequency | Sapote | strain+BGC_ID | ≤50 |

### Group C — Leads
| Code | Sheet | Purpose | Owner | Key | Rows |
|---|---|---|---|---|---|
| C1 | C1_DAPR_Antibacterial | ranked AB leads across strains | Sapote | strain+BGC_ID | 1/lead |
| C2 | C2_DAPR_Antifungal | ranked AF leads across strains | Sapote | strain+BGC_ID | 1/lead |
| C3 | C3_Lead_Tier_Summary | per-strain top AB/AF lead, tier (absorbs FIX-2 top-lead fields) | Sapote | strain | 1/strain |

### Group D — Rescue
| Code | Sheet | Purpose | Owner | Key | Rows |
|---|---|---|---|---|---|
| D1 | D1_RGGMCI_All_Strains | per-strain pair counts, promoted groups, state | Mamey | strain | 1/strain |
| D2 | D2_RGGMCI_Top_Pairs | top HIGH pairs per strain | Mamey | strain+pair_id | ~10/strain |
| D3 | D3_RGGMCI_Promoted | promoted rescue groups (CONFIDENCE-ranked) | Sapote | group_id | 1/group |
| **D4** | **D4_Rescue_Usefulness** | rescue groups ranked by DOWNSTREAM POTENTIAL, saccharide-excluded (NOT confidence) | Sapote | strain+rescue_group_id | 1/group |

### Group F/G/H — Ecology, literature, ops
| Code | Sheet | Purpose | Owner | Key | Rows |
|---|---|---|---|---|---|
| F1 | F1_Ecology_Readiness | per-strain taxonomy, source, habitat, readiness | Both | strain | 1/strain |
| F2 | F2_Regulatory_TFBS | TFBS hits with TF family, target, score | Mamey | strain+hit | 1/hit |
| G1 | G1_Literature_Index | per-BGC citation entries (Bert-Mode Verified only) | Sapote | citation_id | 1/cite |
| G2 | G2_Validation_Roles | per-strain validation assignment | Sapote | strain | 1/strain |
| H1 | H1_Handoff_Log | platform handoff events: who/when/SHA/validation result | Both | event_id | 1/event |
| H2 | H2_Gap_Queue | outstanding gaps, priority, required input | Both | gap_id | 1/gap |
| H3 | H3_Schema_Version | schema_version, workbook_type, freeze date, forward-compat note | Auto | — | fixed |

## Cross-cutting conventions (frozen)
- **Grouped-frequency block** on every class-view sheet (B5–B9): count + denominator + % at global / host / genus / family scope; descriptive only (small-N + assembly-tier caveat, never a significance claim).
- **Dynamic scope_note** per class sheet: states active grouping + N for the merge that produced it ("moss isolates, N=8, 47 BGCs").
- **Provenance columns** wherever a compound/MIBiG identity appears (B6 + any view): closest_product_provenance, source_kcb_file, source_kcb_locator (identifiers only, no verbatim text), parse_confidence, denominator_type; untraceable → UNRESOLVED / blank.
- **Objective vs interpretive split:** B8–B12 views are mechanical re-derivable projections of B1; interpretive scoring (D4 usefulness, mechanism hypotheses) is fenced and labelled exploratory.
- **Claim-safety:** compounds candidate/predicted; KCB source-derived similarity; no PMIDs/DOIs unless Bert-Mode Verified; markers = disambiguation targets unless external HMMER.
- **Merge contract:** append-only by strain+BGC_ID; schema-validated on receipt; stop on WORKBOOK_SCHEMA_CONFLICT.

## Release-gate (scoped to master only)
Gate fails ONLY if an artifact identifying as `workbook_type=MASTER_STRAIN_WORKBOOK` does not conform to the codes/columns above. Per-strain (§57) and custom artifacts are exempt.

---

# KCB/MIBiG Provenance Patch (agreed via provisional round-trip, 2026-06-09)

**Core rule:** if a sheet carries a parsed product name or MIBiG accession, provenance is part of the value, not optional metadata. Surfaced by the v9.4 category-deliverables test: claim-safe wording and zero BGC/score fabrication held across 18 categories, but parsed `Closest_Candidate_KCB_Product` / `Closest_MIBiG_Accession` values were populated without machine-checkable provenance — an audit gap (genuine source-derived vs model inference is indistinguishable without it).

## Trigger fields (canonical — see Addition 2)
A sheet containing any of: `closest_product`, `Closest_Candidate_KCB_Product`, `closest_mibig_accession`, `Closest_MIBiG_Accession`, `candidate_known_product`, `candidate_mibig_accession` MUST also carry the required provenance fields below.

## Required provenance fields
`closest_product_provenance`, `source_kcb_file`, `source_kcb_locator`, `kcb_hit_rank`, `denominator_type`, `parse_confidence`, `needs_manual_kcb_check`, `product_claim_ceiling`.

## Optional bounded convenience field
`source_kcb_excerpt` — optional, must be short, must NOT be required for pass/fail, must NOT reproduce full KnownClusterBlast/MIBiG text blocks. Provenance is established by locator fields, not copied prose. (This preserves the no-verbatim-reproduction rule.)

## Allowed values
- `closest_product_provenance`: KCB_TEXT_EXACT | MIBIG_REFERENCE_LINE | KCB_TOP_FIELD | ANTISMASH_GBK_FEATURE | DERIVED_LOOKUP | UNRESOLVED | NOT_APPLICABLE
- `source_kcb_file`: path to source file | `self:KCB_top` (value from master's own KCB_top) | `self:<sheet>:<column>` | NOT_APPLICABLE | UNRESOLVED
- `source_kcb_locator`: e.g. `row=<id>` | `BGC_ID=<id>;hit_rank=<n>` | `region=<id>;knownclusterblast_hit=<n>` | `GBK=<file>;feature=<id>` | `self:KCB_top` | UNRESOLVED
- `denominator_type`: query_CDS_count | reference_cluster_gene_count | both_reported | unknown | not_applicable
- `parse_confidence`: HIGH | MEDIUM | LOW | UNRESOLVED | NOT_APPLICABLE
- `needs_manual_kcb_check`: yes | no
- `product_claim_ceiling`: source-derived similarity anchor only | candidate family-level similarity only | candidate product-level similarity, manual check required | unresolved; do not use product name | not applicable

## Validation — all failures emit `WORKBOOK_SCHEMA_CONFLICT` with a sub-reason
- `KCB_PROVENANCE_COLUMNS_MISSING` — parsed fields present but a required provenance column is absent.
- `KCB_PRODUCT_PROVENANCE_MISSING` — product field non-empty, `closest_product_provenance` blank.
- `KCB_ACCESSION_PROVENANCE_MISSING` — accession non-empty, provenance blank. *Carve-out:* if provenance = `KCB_TOP_FIELD`, `source_kcb_file = self:KCB_top` is valid.
- `KCB_PARSE_CONFIDENCE_MISSING` — parsed fields populated, `parse_confidence` blank.
- `KCB_PRODUCT_CLAIM_CEILING_MISSING` — parsed fields populated, `product_claim_ceiling` blank.
- `KCB_UNRESOLVED_NOT_FLAGGED` — provenance = UNRESOLVED but `needs_manual_kcb_check != yes`.
- `KCB_DERIVED_LOOKUP_NOT_FLAGGED` — provenance = DERIVED_LOOKUP but `needs_manual_kcb_check != yes`.
- `KCB_LOCATOR_MISSING` — provenance = KCB_TEXT_EXACT / MIBIG_REFERENCE_LINE / KCB_TOP_FIELD / ANTISMASH_GBK_FEATURE but `source_kcb_locator` blank. (For KCB_TOP_FIELD, `self:KCB_top` is valid.)
- **`KCB_MANUAL_CHECK_FLAG_MISSING`** (Addition 1) — any parsed product/accession field populated and `needs_manual_kcb_check` is blank, missing, or not one of {yes, no}. Prevents a silent blank escaping the gate; if provenance is unresolved, must be `yes`.
- **`KCB_PRODUCT_FIELD_NONCANONICAL`** (Addition 2) — a column semantically carrying a parsed product/closest-known-product/candidate-compound/MIBiG/reference-cluster accession uses a non-canonical name (e.g. `nearest_known_compound`, `best_product_match`, `probable_product`, `reference_product_name`) instead of a registered canonical trigger name. Future canonical names may be added but MUST be registered in the schema before use. Prevents bypassing the gate by renaming columns.

## Required agent behavior
If provenance cannot be supplied: leave product/accession blank or mark unresolved, and set `closest_product_provenance=UNRESOLVED`, `source_kcb_file=UNRESOLVED`, `source_kcb_locator=UNRESOLVED`, `parse_confidence=UNRESOLVED`, `needs_manual_kcb_check=yes`, `product_claim_ceiling=unresolved; do not use product name`.
If the value comes from the master's own `KCB_top`: `closest_product_provenance=KCB_TOP_FIELD`, `source_kcb_file=self:KCB_top`, `source_kcb_locator=self:KCB_top`, `parse_confidence=HIGH|MEDIUM`, `needs_manual_kcb_check=no` only if the field itself supports the exact parsed value, `product_claim_ceiling=source-derived similarity anchor only`.

## Disposition of the v9.4 provisional category workbook
Useful category strategy test · claim-safety language test PASSED · score/BGC preservation PASSED · **KCB/MIBiG provenance INCOMPLETE** · NOT manuscript-ready for product/accession mappings (do not use the parsed product/accession values until provenance is added).

## Amendment — build -q (2026-06-14): A3_Run_Manifest + `antismash_profile`

`A3_Run_Manifest` gains an `antismash_profile` column at position 5 (after `mode`). It records the
antiSMASH hmmdetection strictness used for the run (`strict|relaxed|loose|unknown`), so cross-run
pooling stays comparable (see `docs/ANTISMASH_PROFILE.md` and `tools/check_antismash_profile.py`).
Default `unknown`. The schema validator auto-derives required columns from the builder, so it now
requires this column. Workbooks built before -q lack it and will fail validation — rebuild to migrate.
