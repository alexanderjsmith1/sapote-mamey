# Master workbook schema

This page lists the sheets and columns of the master workbook. A master workbook is one `.xlsx` that holds many strains. `python mamey_run.py run ... --master <path>` creates it and adds each run to it. The page matches the builder (`mamey/master_workbook.py`, `CANONICAL_V1_HEADERS`) and the checker (`mamey/workbook_schema_check.py`). To check a workbook, follow [Master workbook validation](WORKBOOK_VALIDATION.md).

The schema version is v1.1. The sheet `H3_Schema_Version` carries the stamp. The frozen requirements are in [MASTER_SCHEMA_FROZEN_v1_1.md](MASTER_SCHEMA_FROZEN_v1_1.md). Terms are in the [glossary](GLOSSARY.md).

## Rules

1. Every sheet has a stable code (`A1`, `B2`, and so on). The code never changes.
2. Column names are exact. There are no synonyms.
3. A blank cell is not a zero. It can mean not supplied, not computed or held. Do not fill a blank with 0 or "inactive".
4. An assay column has four states: `+`, `−`, `n.t.` (not tested) and blank. Never turn one state into another. A strain with no test is not negative.
5. The checker compares headers by position and ignores case. Extra trailing columns are allowed.

## Sheet index

The checker requires the 26 sheets below. Header-only sheets pass. Each sheet is checked for presence and header order. The checker also compares data-row counts across the per-strain sheets and, outside fast mode, checks that `A2_Strain_Registry` and `B1_BGC_Master` hold the same strains; either mismatch sets FAIL (`mamey/workbook_schema_check.py:328-370`). It does not validate cell content or science.

| Code | Sheet | What it holds | Rows | Columns (in order) |
|---|---|---|---|---|
| A1 | `A1_Dashboard` | Strain count, BGC count and version summary. | fixed | not column-checked |
| A2 | `A2_Strain_Registry` | One row per strain: identity, assembly, status, top leads. | 1 per strain | `strain`, `taxonomy`, `ecology_source`, `habitat`, `assembly_bp`, `contigs`, `n50`, `gc_pct`, `bgc_count`, `interior_pct`, `assembly_tier`, `workflow_version`, `package_status`, `top_ab_bgc`, `top_ab_class`, `ab_score`, `ab_band`, `top_af_bgc`, `top_af_class`, `af_score`, `af_band`, `rggmci_state`, `gap_next_action`, `scope` |
| A3 | `A3_Run_Manifest` | One row per run: date, version, mode, input, issues. | 1 per run | `run_date`, `strain`, `version`, `mode`, `antismash_profile`, `input_zip`, `raw_bgcs`, `corrected_bgcs`, `issues`, `package_path` |
| A4 | `A4_Completeness_Audit` | Which sheets hold data for each strain. | 1 per strain | `strain`, `A2_registry`, `B1_bgc_master`, `B4_scans`, `C1_dapr_ab`, `C2_dapr_af`, `D1_rggmci`, `E1_mode_b`, `F1_ecology`, `overall`, `gap_action` |
| B1 | `B1_BGC_Master` | One row per BGC (biosynthetic gene cluster): locus, coordinates, products, KnownClusterBlast (KCB) hit, claim limits. | 1 per BGC | `strain`, `assembly_locator`, `contig`, `region`, `BGC_ID`, `start`, `end`, `length_kb`, `products`, `boundary`, `arch`, `kcb_top`, `kcb_score`, `kcb_evidence_state`, `kcb_proteins`, `cctt_triggers`, `resistance_tier`, `tta_tier`, `ab_auto`, `af_auto`, `novelty_auto`, `lead_tier_auto`, `depth_floor`, `closest_product_provenance`, `source_kcb_file`, `source_kcb_locator`, `kcb_hit_rank`, `denominator_type`, `parse_confidence`, `needs_manual_kcb_check`, `product_claim_ceiling`, `efls_status`, `flank_census_tier1`, `flank_census_tier2_todo`, `cross_contig_candidate_set`, `efls_claim_ceiling`, `dkp_rank`, `dkp_cdps_evidence`, `dkp_oxidase_homology`, `dkp_provenance`, `dkp_claim_ceiling`, `diagnostic_signal_score`, `evidence_weight_tier`, `claim_confidence`, `claim_ceiling`, `safe_claim`, `engine_version` |
| B2 | `B2_Product_Class_Matrix` | Strain by product-class counts. Raw antiSMASH counts, including classes the standing rules drop (saccharide, NAPAA, hglE-KS, ectoine, redox-cofactor). Filter before you make a lead-count claim. | 1 per strain | `strain`, `label_provenance`, `NRPS`, `NRPS-like`, `PKS`, `PKS-like`, `T1PKS`, `T2PKS`, `T3PKS`, `transAT-PKS`, `RiPP`, `terpene`, `carotenoid`, `saccharide`, `halogenated`, `lassopeptide`, `azole-containing-RiPP`, `lanthipeptide-class-i`, `lanthipeptide-class-ii`, `lanthipeptide-class-iii`, `NRP-metallophore`, `NI-siderophore`, `betalactone`, `fatty_acid`, `hglE-KS`, `NAPAA`, `RiPP-like`, `terpene-precursor`, `quinone_isoprenoid_chain`, `ectoine`, `butyrolactone`, `arylpolyene`, `RRE-containing`, `redox-cofactor`, `ranthipeptide`, `oligosaccharide`, `hydrogen-cyanide`, `aminopolycarboxylic-acid`, `HR-T2PKS`, `phosphonate`, `other`, `counts_reliability` |
| B3 | `B3_Known_Cluster_Matrix` | Strain by KCB top-hit matrix. One column per reference, so the width varies. | 1 per strain | one `strain` column, then one column per reference |
| B4 | `B4_Cross_Strain_Scans` | Per-strain scan totals. `KCB_status` is the run's `KCB_sweep` state: `PASS` (hits parsed), `NULL` (sources read, no hits) or `FAILED` (no source read, not a negative); `NOT_RECORDED` when the run carries no state. A workbook from an older bundle shows `PASS` for every strain. | 1 per strain | `strain`, `run_mode`, `KCB_status`, `RGGMCI_pairs`, `RGGMCI_HIGH`, `CCTT_triggers`, `CCTT_HAL`, `CCTT_LAN`, `CCTT_LASSO`, `CCTT_THA`, `CCTT_PHO`, `CCTT_ENE`, `CGAD_chitin`, `TFBS_DasR`, `TFBS_total`, `bldA_T4`, `resistance_T1`, `UMED_gaps`, `EFLS_pairs` |
| B6 | `B6_Compound_Reference` | Compound reference for each KCB-named compound. | 1 per BGC | `strain`, `BGC_ID`, `kcb_named_compound`, `kcb_score`, `resolved`, `npclassifier_pathway`, `npclassifier_class`, `mol_formula`, `exact_mass`, `m_plus_h`, `m_plus_na`, `inchikey`, `npaid`, `primary_doi`, `primary_pmid`, `primary_year`, `evidence_tier`, `claim_ceiling` |
| C1 | `C1_DAPR_Antibacterial` | Ranked antibacterial board. | 1 per lead | `strain`, `rank`, `assembly_locator`, `contig`, `BGC_ID`, `products`, `score`, `lead_tier`, `band`, `standing_rule`, `corrected_rank`, `kcb_top`, `kcb_score`, `boundary`, `arch`, `cctt`, `status_note`, `region`, then `Activity_Ref` when v1.2 is applied |
| C2 | `C2_DAPR_Antifungal` | Ranked antifungal board. | 1 per lead | `strain`, `rank`, `assembly_locator`, `contig`, `BGC_ID`, `products`, `score`, `lead_tier`, `band`, `standing_rule`, `corrected_rank`, `kcb_top`, `kcb_score`, `boundary`, `arch`, `cctt`, `status_note`, `region`, then `Activity_Ref` when v1.2 is applied |
| C3 | `C3_Lead_Tier_Summary` | Top antibacterial and antifungal lead per strain. | 1 per strain | `strain`, `top_ab_bgc`, `top_ab_products`, `ab_score`, `ab_band`, `top_af_bgc`, `top_af_products`, `af_score`, `af_band`, `sapote_composite`, `recommended_role` |
| C4 | `C4_Strain_Decision_Table` | Composite score and recommended role per strain. | 1 per strain | `sapote_rank`, `strain`, `sapote_score`, `bgc_count`, `assembly_tier`, `top_lead`, `top_kcb_score`, `rggmci_high`, `class_diversity`, `high_value_hits`, `rare_class_hits`, `recommended_role` |
| D1 | `D1_RGGMCI_All_Strains` | RG-GMCI (split-cluster signal) state per strain. | 1 per strain | `strain`, `contigs`, `review_required`, `final_state`, `promoted_grades`, `fragment_sets`, `promoted_bgcs`, `interpretation` |
| D2 | `D2_RGGMCI_Top_Pairs` | Top RG-GMCI pairs. | about 10 per strain | `strain`, `rank`, `bgc_a`, `bgc_b`, `rggmci_score`, `confidence`, `products_a`, `products_b`, `shared_references`, `interpretation` |
| D3 | `D3_RGGMCI_Promoted` | Promoted rescue groups, with evidence basis and claim ceiling. | 1 per group | `group_id`, `strain`, `grade`, `fragments`, `evidence_basis`, `claim_ceiling`, `chemistry_consequence`, `status` |
| E1 | `E1_Mode_B_Index` | Which BGCs have a Mode B card. | 1 per BGC | `strain`, `BGC_ID`, `length_kb`, `products`, `subprograms`, `mode_b_status`, `analysis_platform`, `date`, `report_file`, `layperson_summary`, `fermentation_note` |
| E2 | `E2_Comparative_Pairs` | BGC pairs across strains compared on banked product, domain and KCB-anchor signals. It runs no alignment and does not establish orthology or paralogy; `mean_pct_id_core` and `mean_pct_id_all` read `not_computed` (`mamey/comparative_pairs.py:12-23,144-145`). | 1 per pair | `pair_id`, `strain_a`, `bgc_a`, `strain_b`, `bgc_b`, `length_a_kb`, `length_b_kb`, `products`, `subprogram_match`, `mean_pct_id_core`, `mean_pct_id_all`, `a_domain_match`, `diverged_genes`, `interpretation` |
| E3 | `E3_Megacluster_Registry` | BGCs over 150 kb flagged for long-read confirmation. | 1 per BGC | `strain`, `BGC_ID`, `length_kb`, `boundary`, `products`, `kcb_top`, `kcb_score`, `long_read_status`, `notes` |
| E4 | `E4_A_Domain_Summary` | NRPS A-domain specificities for Mode B BGCs. | 1 per domain | `strain`, `BGC_ID`, `module_position`, `gene_locus_tag`, `stachelhaus_code`, `predicted_substrate`, `method`, `confidence`, `notes` |
| F1 | `F1_Ecology_Readiness` | Taxonomy, deposited source and readiness per strain. | 1 per strain | `strain`, `taxonomy`, `source`, `habitat`, `assembly_tier`, `bgc_count`, `ab_lead`, `af_lead`, `tfbs_hits`, `cctt_classes`, `readiness`, `route` |
| G1 | `G1_Literature_Index` | Literature entries per BGC. | 1 per citation | `strain`, `BGC_ID`, `track`, `citation`, `doi`, `evidence_purpose`, `verification_status` |
| G2 | `G2_Validation_Roles` | Manuscript role per strain. | 1 per strain | `strain`, `primary_role`, `manuscript_use` |
| H1 | `H1_Handoff_Log` | Handoff events with the workbook SHA-256. | 1 per event | `date`, `platform`, `direction`, `strains_affected`, `sheets_modified`, `file_sha256`, `validation_result`, `notes` |
| H2 | `H2_Gap_Queue` | Open gaps with the input each needs. | 1 per gap | `priority`, `gap_class`, `strains`, `required_input`, `next_action`, `assigned_platform`, `status` |
| H3 | `H3_Schema_Version` | Schema version stamp. | fixed | `Schema version`, `v1.1` |

## Columns that need a note

- **`contig`** (B1, C1, C2) is the full contig name as antiSMASH reports it. Nothing shortens it.
- **`assembly_locator`** (B1, C1, C2) is the contig first, with the BGC alias as a cross-reference. A single BGC is identified by `strain / full contig / region / BGC alias`. Take all four from the same row. C1 and C2 carry `region` as their last builder column, so all four come from one row there too (`mamey/master_workbook.py:233-234`). Rows written into an older master before that column existed have it blank.
- **`habitat`** and **`ecology_source`** (A2, F1) hold the isolation source text as deposited. They are not binned into categories. Blank means none was deposited.
- **`scope`** (A2) is `IN_SCOPE`, `OUT_OF_SCOPE` or `REVIEW`. It comes from the genus in `taxonomy`.
- **`assembly_tier`** (A2) is `GOOD`, `MODERATE`, `POOR`, `VERY_POOR` or `UNKNOWN`. The tier comes from the share of BGCs that sit in the interior of a contig: 70 percent or more is `GOOD`, 45 or more `MODERATE`, 20 or more `POOR`, and below 20 `VERY_POOR`. `UNKNOWN` means the share could not be computed.
- **`kcb_evidence_state`** (B1) says where the `kcb_*` values came from:
  - `KNOWNCLUSTERBLAST_OBSERVED`: a KnownClusterBlast hit was read.
  - `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`: the region's KnownClusterBlast text file was recognized as a no-hit report ("no hits" text, or empty "Significant hits:" and "Details:" sections) and no hit rows were parsed. The text is not checked against the JSON. The `kcb_*` fields stay empty, and no ClusterBlast hit is substituted. A missing or unreadable KnownClusterBlast file is not this state.
  - `CLUSTERBLAST_FALLBACK_OBSERVED`: the region had no KnownClusterBlast record of either kind, and a ClusterBlast record was read (`mamey/antismash_evidence.py:1849-1862`). Treat the hit as weaker evidence.
  - `UNKNOWN_KCB`: no record was found.
- **`kcb_score`** (B1, C1, C2) is the KnownClusterBlast cumulative BLAST score. It is not a percent. A similar reference is not an identical compound.
- **`lead_tier_auto`** (B1) and **`lead_tier`** (C1, C2) take one of `Exceptional`, `High`, `Medium`, `Low` or `Inventory`. `Low` and `Inventory` are routing labels for class-gated loci. They are not activity results.
- **`band`**, **`ab_band`** and **`af_band`** (C1, C2, A2, C3) are score bands. They rank candidates. They do not measure activity.

## Fragment_Rescue_Tiers (code D5)

This sheet is not in the 26 required sheets. `tools/build_dapr_rescue_sheets.py <master.xlsx>` builds it and rewrites the master in place. Copy the workbook first. The checker requires it only with `--v12`.

Columns, in order: `Tier`, `strain`, `Assembly`, `Contigs`, `N50`, `Frag_Loss`, `EFLS_Pairs`, `RG_GMCI_HIGH`, `FLBR_Megasynth`, `Recommendation`.

The tier rule is fixed:

| Tier | Condition |
|---|---|
| A | N50 of 1,000,000 or more |
| D | else, EFLS_Pairs below 20 |
| B | else, EFLS_Pairs of 600 or more |
| C | everything else |

The tool reads blank N50 and scan counts as zero. A blank input can therefore yield a tier. Check the inputs before you read a tier. `Assembly` is copied from A2 `assembly_tier`. It is not derived from N50.

## Activity_Ref on C1 and C2

The same tool adds or refreshes an `Activity_Ref` column at the end of C1 and C2. It looks up the KCB top hit in a fixed map (see [DAPR_CLASS_FRAMEWORK.md](DAPR_CLASS_FRAMEWORK.md)) and writes a tag such as `VERIFIED ...` or `ROUTED-OUT cytotoxic ...`. A tag is a literature pointer for the reference compound. It is not an activity result for your strain.

The tool refreshes a cell only when the KCB text and a mapped tag both exist. A blank or unmapped KCB leaves the old cell as it was. Compare retained tags with the current KCB text. The tool does not change rank, score or row selection.

## Other sheets

- **`B5_BLASTp_Hits`** holds ingested BLASTp hit rows (see [ONLINE_BLASTP_PROTOCOL.md](ONLINE_BLASTP_PROTOCOL.md)). It is optional. The checker checks it only when present. Columns: `strain`, `BGC_ID`, `contig`, `query_locus`, `query_len`, `hit_rank`, `subject_acc`, `subject_desc`, `sciname`, `pct_identity`, `positives_pct`, `align_len`, `mismatches`, `gap_opens`, `q_start`, `q_end`, `s_start`, `s_end`, `evalue`, `bitscore`, `subject_len`, `source`, `ingest_date`.
- **Cohort overlays**: `Cross_Strain_Class_Prevalence`, `Cross_Strain_Findings` and `Strain_Cohort_Context` come from the cross-strain builder. They are not coded sheets and the checker does not require them.
- **Optional coded sheets** the builder does not write: `F3_Ecology_Theme_Board` and `G3_Hallucination_Trap_Audit`. The checker allows them.

## Changing the schema

A change to a column name or a sheet code needs a new version in `H3_Schema_Version`. A new sheet takes the next free code in its group. Edit the builder first. This page and the checker follow it.
