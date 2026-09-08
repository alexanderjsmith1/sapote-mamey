# Sapote–Mamey Tools Directory Reference
## Complete Inventory of tools/ Scripts
**Bundle v9.7.263 · Engine 1.9.111** *(subcommand CLI synced v9.7.262 — includes compile-report `--pdf` / `--allow-unfilled-pdf`; the tools/ script inventory below retains its last-verified stamp)*
Hamilton, Ontario

*Sourced from: direct inspection of `tools/` directory, module docstrings via `python3 -c "import ast"` extraction, `docs/HOW_TO_USE.md`, `docs/RELEASE_CHECKLIST_v9.md`. 107 scripts inventoried.*

---

## Section 1: Primary Workflow Tools

These are the scripts the standard operating procedure uses directly.

**`mamey_intake.py`** — One-step cohort intake. Combines `ingest_package.py` + `build_workbook.py --full` in sequence. Takes `--packages <dir>` (parent of package directories), `--banked-dir <dir>`, `--workbook <out.xlsx>`. The recommended first step after running `mamey run` for a cohort. Source: `tools/mamey_intake.py`.

**`ingest_package.py`** — Ingests one sealed Mamey package into the cohort bank. Writes `bgc_data.json`, `deep_data.json`, `gene_data.json` into `--banked-dir`. Takes `--package <pkg>`, `--ww <WWxxxxxxxx>` (accession), `--merge` flag. Works with or without `--ww` depending on release tier. Source: `tools/ingest_package.py`.

**`build_workbook.py`** — Builds the master cross-strain workbook from the banked cohort. `--full` runs the complete pipeline: deep-data bank → marker bank → `build_master` → cross-strain overlays → DAPR boards → D5/Activity_Ref → Lead_Board. Takes `--workbook <out.xlsx>`, `--banked-dir <dir>`. Source: `tools/build_workbook.py`.

**`build_master.py`** — The internal master workbook writer called by `build_workbook.py --full`. Writes A1–A4, B1–B4, and related sheets from the banked cohort. Do not call directly — use `build_workbook.py` which orchestrates it correctly. Source: `tools/build_master.py`.

**`sapote_workflow.py`** — W0–W10 Sapote workflow gate driver. `--strict` exits non-zero if any mandatory step is incomplete. `--json` outputs machine-readable status. The official gate for verifying judgment layer completeness before delivery. Source: `mamey/sapote_workflow.py` (also mirrored in tools). Source: `tools/sapote_workflow.py`.

**`sapote_judgment_receipt.py`** — Flips `gold_completeness` from asserted to verified in the package manifest. Reads the completed deliverable manifest and validates all 13 items. Exits 0 only when judgment is genuinely complete. Source: `tools/sapote_judgment_receipt.py`.

**`check_deliverable_suite.py`** — Validates the 13-item per-strain deliverable contract. Reads `DELIVERABLE_MANIFEST_<strain>.md`; fails closed on unfilled items, under-justified items, and JUDGMENT_PENDING gold gate violations. Source: `tools/check_deliverable_suite.py`.

**`claim_safety_linter.py`** — Scans Sapote interpretive text for claim-safety violations: production claims, structure assertions, per-BGC bioactivity claims. Returns violations with line numbers. Invoked by `mamey write-narrative` (exit 3 on violation) and available standalone. Source: `tools/claim_safety_linter.py`.

---

## Section 2: Figure Generation Tools

**`build_figures.py`** — Cohort-level figure generation from the banked data. Calls the per-strain and cohort figure modules. Takes `--banked-dir`, `--out <figure_dir>`, `--strains` (optional filter). Source: `tools/build_figures.py`.

**`build_cross_strain_figures.py`** — Cross-strain figure set: class prevalence, BGC distribution, habitat comparisons. Source: `tools/build_cross_strain_figures.py`.

**`build_master_figures.py`** — Master workbook–sourced figure set. Reads directly from the `*.xlsx` master workbook sheets. Source: `tools/build_master_figures.py`.

**`build_master_figure_atlas.py`** — Produces the boss-ready figure atlas PDF from the master workbook. Source: `tools/build_master_figure_atlas.py`.

**`build_overview_figures.py`** — Project-level overview figures: cohort size, assembly tier distribution, lead tier distribution. Source: `tools/build_overview_figures.py`.

**`build_panel_figure.py`** — Configurable multi-panel figure builder. Takes a YAML layout spec. Source: `tools/build_panel_figure.py`.

**`build_subset_panel.py`** — Panel figure for a subset of strains (e.g. top leads, one habitat). Source: `tools/build_subset_panel.py`.

**`build_cohort_html.py`** — Builds the browsable BGC atlas HTML from cohort data. Source: `tools/build_cohort_html.py`.

**`build_thesis_diagrams.py`** / **`build_thesis_vignettes.py`** — Thesis-chapter-ready figure generation. Source: `tools/build_thesis_*.py`.

**`build_workflow_figure.py`** — Schematic diagram of the Sapote-Mamey pipeline workflow. Source: `tools/build_workflow_figure.py`.

**`build_validation_panel.py`** — Validation control figure set (known compound recovery, class calibration). Source: `tools/build_validation_panel.py`.

**`build_punchcard.py`** — Punchcard-style BGC presence/absence visualization across the cohort. Source: `tools/build_punchcard.py`.

**`plot_examples.py`** — Reference plotting examples using the figure-ready tidy CSVs: fragmentation-loss gradient, class prevalence, class×strain heatmap. Source: `tools/plot_examples.py`.

---

## Section 3: BGC Analysis and Scoring

**`build_dapr_rescue_sheets.py`** — Deterministic builder for C1/C2 DAPR sheets and the D5 Fragment_Rescue_Tiers sheet. Regenerates the `Activity_Ref` column from the DAPR class framework citation map. Idempotent — preserves judgment columns (Rank, AN_Score, WL_Score, Rationale). Source: `tools/build_dapr_rescue_sheets.py`.

**`build_lead_tiers.py`** — Computes lead tier assignments across the cohort. Source: `tools/build_lead_tiers.py`.

**`build_lead_detail.py`** — Per-lead detail compilation for the Lead_Board sheet. Source: `tools/build_lead_detail.py`.

**`build_priority_leads.py`** — Priority lead selection and ranking logic. Source: `tools/build_priority_leads.py`.

**`build_genelevel_triage.py`** — Gene-level triage board (individual CDS, not just BGC level). Source: `tools/build_genelevel_triage.py`.

**`lead_board.py`** — Lead_Board sheet builder with RG-GMCI rescue flags and Mode B verdict fold. Source: `tools/lead_board.py`.

**`apply_dapr_boards.py`** — Applies DAPR board content to a master workbook. Source: `tools/apply_dapr_boards.py`.

**`render_dapr_boards.py`** — Renders DAPR boards as formatted output. Source: `tools/render_dapr_boards.py`.

**`build_saccharide_triage.py`** — Splits saccharide regions into CANDIDATE_PRODUCT / UNCHARACTERIZED_STANDALONE / TAILORING / MACHINERY categories. Writes the Saccharide_Triage sheet. Source: `tools/build_saccharide_triage.py`.

**`build_size_profile.py`** — BGC size profile by class. Source: `tools/build_size_profile.py`.

**`dark_gene_scan.py`** — Scans for genes with no Pfam annotation ("dark genes") within BGCs. Dark genes in a core locus are novelty signals. Source: `tools/dark_gene_scan.py`.

**`scan_cctt_class_compat.py`** — Verifies CCTT trigger–class compatibility across the cohort. Source: `tools/scan_cctt_class_compat.py`.

**`reclass_check.py`** — Checks for BGCs that scored above a lead threshold under one class but would score differently under a corrected class assignment. Source: `tools/reclass_check.py`.

**`kcb_confidence.py`** — KCB confidence score computation and reporting. Source: `tools/kcb_confidence.py`.

---

## Section 4: Cross-Strain and Cohort Analysis

**`cohort_blastp_driver.py`** — Drives multi-BGC BLASTp campaigns across a scoped set of BGCs (leads / modular / all). `--plan-only` prints scale before running. Receipt is the overlay file on disk, not the exit code. Source: `tools/cohort_blastp_driver.py`.

**`build_cohort_precompute.py`** — Precomputes the cohort-wide domain matrix and prevalence statistics. Source: `tools/build_cohort_precompute.py`.

**`build_domain_matrix.py`** — Builds the strain × domain count matrix. Input to gold figures F11 (clustermap). Source: `tools/build_domain_matrix.py`.

**`build_normalization_matrix.py`** — Builds the fragmentation-robust normalization matrix (ectoine+NAPAA denominator). Source: `tools/build_normalization_matrix.py`.

**`build_family_map.py`** — BGC family mapping across the cohort (pan-genome family assignment). Source: `tools/build_family_map.py`.

**`build_pangenome.py`** — Pan-genome construction from BGC protein sets. Source: `tools/build_pangenome.py`.

**`build_gcf_tags.py`** — Gene Cluster Family (GCF) tag assignment. Source: `tools/build_gcf_tags.py`.

**`cross_strain_denominator_audit.py`** — Audits cross-strain comparison denominators for fragmentation sensitivity. Reports the correlation table from HOW_TO_USE §Fragmentation-Robust Normalization. Source: `tools/cross_strain_denominator_audit.py`.

**`cohort_scoring_version_gate.py`** — Verifies that all strains in the cohort were scored under the same engine version. Version-mixed cohorts require a re-score before cross-strain comparisons. Source: `tools/cohort_scoring_version_gate.py`.

**`rggmci_cohort_rollup.py`** — Rolls up RG-GMCI evidence across the cohort. Ranks by subject-tiling verdict (COMPLEMENTARY_SPLIT > TERMINUS_TRUNCATION > MIXED > INSUFFICIENT). Source: `tools/rggmci_cohort_rollup.py`.

**`add_xstrain_sheets.py`** — Adds cross-strain overlay sheets to the master workbook: `Cross_Strain_Class_Prevalence`, `Cross_Strain_Findings`, `Strain_Cohort_Context`. Called by `build_workbook.py --full`. Source: `tools/add_xstrain_sheets.py`.

**`cohort_concordance_summary.py`** — Summary of reference-BGC concordance across the cohort. Source: `tools/cohort_concordance_summary.py`.

**`rare_motif.py`** → `mamey/rare_motif.py` — Cross-strain rare BGC motif detection (see module listing).

---

## Section 5: BLASTp Campaign Management

**`blastp_campaign.py`** — High-level BLASTp campaign orchestrator. Manages batch submission, polling, and result collection across multiple BGCs. Source: `tools/blastp_campaign.py`.

**`build_bgc_markers.py`** — Builds BGC marker sets for the BLASTp priority queue. Source: `tools/build_bgc_markers.py`.

**`round_ledger.py`** — Tracks BLASTp round submissions and results for reproducibility. RID (Request ID) ledger that allows re-fetching results within the 24-hour RID lifetime. Source: `tools/round_ledger.py`.

**`run_directed_pks_study.py`** — Directed PKS/NRPS study runner for focused BLASTp of megasynthase domains. Source: `tools/run_directed_pks_study.py`.

**`edge_fasta_export.py`** — Exports FASTA files for Edge and Full-contig BGC proteins (priority for BLASTp when assembly is POOR/VERY_POOR). Source: `tools/edge_fasta_export.py`.

---

## Section 6: Ecology and Regulatory Analysis

**`build_chitinase_screen.py`** — Computes fragmentation-robust chitinase prevalence: `chit_per_unit = chitinase / (ectoine + NAPAA)`. Flags outliers (|z| > 1.3), marks `no_norm_ref` when denominator is absent. Source: `tools/build_chitinase_screen.py`.

**`build_tfbs_profile.py`** — Builds the TFBS_Profile sheet: per-strain regulator-family counts + per-Mbp density, sorted by SARP density. Source: `tools/build_tfbs_profile.py`.

**`mamey_habitat_map.py`** — Maps strains to their habitat classification (bee, wasp, moss, attine, marine, benchmark). Source: `tools/mamey_habitat_map.py`.

**`topology_scan.py`** — Scans BGC gene topology (orientation, spacing, cluster compactness). Source: `tools/topology_scan.py`.

**`build_causemap.py`** — Builds the causal map of habitat → chemistry → evidence chains. Source: `tools/build_causemap.py`.

**`build_metabolomics_readiness.py`** — Per-strain metabolomics readiness scoring: predicted masses, extraction handles, detection windows. Source: `tools/build_metabolomics_readiness.py`.

**`gene_topology.py`** — Per-gene topology analysis (synteny, orientation relative to BGC). Source: `tools/gene_topology.py`.

---

## Section 7: Release and Quality Assurance

**`make_public_tier.sh`** — Cuts the public tier (SID-public) from the MERGED-PRIVATE scaffold. Runs the full pytest suite in the staged tier, refuses to zip on any failure. Scrubs `__pycache__`, `*.pyc`, `.pytest_cache` before checksum+zip. Source: `tools/make_public_tier.sh`.

**`sync_version.py`** — Synchronises version strings across all tracked files. `--check` validates consistency; `--apply` updates all files to the current version. **Critical:** regex must use `[a-z]*` suffix to handle letter-suffix versions (see ISSUES VERSYNC-1). Source: `tools/sync_version.py`.

**`redact_public_tier.py`** — Scrubs AS-/AJS-/PENDING- strain IDs from a directory tree for public tier release. Idempotent (scrubbing already-scrubbed output produces no further changes). Source: `tools/redact_public_tier.py`.

**`check_tier_parity.py`** — Verifies that all four release tiers have identical registry files, identical pytest pass rates, zero cache files, and zero AS-strain ID leaks. Required before tag/push. Source: `tools/check_tier_parity.py`.

**`verify_release_identity.py`** — Verifies bundle identity: checksums, version strings, file manifest. Source: `tools/verify_release_identity.py`.

**`verify_tier_derivation.py`** — Verifies that each tier was correctly derived from the scaffold (no extra files, no missing files, correct redactions). Source: `tools/verify_tier_derivation.py`.

**`run_chatgpt_surrogate_gate.py`** — The surrogate gate: runs 22 pytest files and reports PASS/FAIL with timing. The fast pre-validation gate before full suite. Source: `tools/run_chatgpt_surrogate_gate.py`.

**`release.sh`** — Full release script: runs tier parity check, surrogate gate, full pytest, builds tiers, computes checksums, emits the release manifest. Source: `tools/release.sh`.

**`build_all_deliverables.sh`** — Builds the complete deliverable set for a strain from a sealed package. Source: `tools/build_all_deliverables.sh`.

**`emit_release_sums.sh`** — Emits SHA-256 checksums for all release files. Source: `tools/emit_release_sums.sh`.

**`log_release.py`** — Logs a release event to the release history. Source: `tools/log_release.py`.

**`gen_release_manifest.py`** — Generates `RELEASE_MANIFEST.md` from the current bundle state. Source: `tools/gen_release_manifest.py`.

---

## Section 8: Audit and Validation

**`audit_public_cut.py`** — Audits a public-tier cut for AS-strain ID leaks, stale version strings, and disallowed content. Source: `tools/audit_public_cut.py`.

**`audit_chatgpt_nextpaths_drift.py`** — Checks whether ChatGPT handback responses are correctly providing exactly 8 next-paths. Source: `tools/audit_chatgpt_nextpaths_drift.py`.

**`bunny_hop_audit_game.py`** — Not a standalone script — the Bunny Hop game is documented in `docs/BUNNY_HOP_AUDIT_GAME.md` and triggered conversationally. Source: trigger phrase "bunny hop."

**`evidence_conservation_audit.py`** — Audits the evidence conservation property: checks that every BGC in the input appears in every downstream output. Catches silent drops during merges or workbook builds. Source: `tools/evidence_conservation_audit.py`.

**`compilation_gate.py`** — Gate that verifies the compiled report is complete before delivery. Source: `tools/compilation_gate.py`.

**`session_checklist.py`** — Generates the per-session checklist for a strain analysis session. Source: `tools/session_checklist.py`.

**`workflow_status.py`** — Reports the current workflow status for a strain (which W-steps are PASS/PENDING/BLOCKED). Source: `tools/workflow_status.py`.

**`mamey_package_qa_v2.py`** — Package QA check v2: validates all required files, checksums, and schema compliance against the current frozen schema. Source: `tools/mamey_package_qa_v2.py`.

**`check_antismash_profile.py`** — Validates an antiSMASH ZIP against the expected profile (version, JSON presence, KCB text present). Source: `tools/check_antismash_profile.py`.

**`preflight_zip_hygiene.py`** — Pre-flight check for antiSMASH ZIPs: macOS resource forks, nested ZIPs, minimal file set. Source: `tools/preflight_zip_hygiene.py`.

**`sapote_md_preflight.py`** — Pre-flight check for Sapote-authored Markdown files before PDF rendering: bare BGC IDs, double section breaks, overclaims, stale placeholders. Source: `tools/sapote_md_preflight.py`.

---

## Section 9: Schema and Registry Management

**`workflow_status.py`** — Reports A4_Completeness_Audit status for a master workbook. Source: tools directory.

**`schema_deployed_audit.py`** — Compares the WORKBOOK_SCHEMA.md definition against the actual deployed columns in a master workbook. Reports MATCHED / MAPPED / SCHEMA-ONLY / DEPLOYED-ONLY per sheet. Source: `tools/schema_deployed_audit.py`.

**`regen_modeb_contract_docs.py`** — Regenerates the Mode B contract documentation from `modeb_full30_corrective_contract.json`. `--check` enforces no drift between the JSON and derived docs in CI. Source: `tools/regen_modeb_contract_docs.py`.

**`build_id_resolver.py`** — Builds the `node_citation_map.json` (BGC ID → NODE · region locator) for a package. Source: `tools/build_id_resolver.py`.

**`locator_reconciliation.py`** — Reconciles BGC locators across multiple sessions/versions of the same package. Source: `tools/locator_reconciliation.py`.

**`check_registry_ids_unique.py`** — Validates that all BGC IDs in the cassette/marker registry are unique. Source: `tools/check_registry_ids_unique.py`.

**`check_schema_drift.py`** — Detects schema drift between the code and the deployed workbook. Source: `tools/check_schema_drift.py`.

**`check_provenance_columns.py`** — Validates that all provenance/citation-ledger columns are correctly populated. Source: `tools/check_provenance_columns.py`.

**`check_dangling_refs.py`** — Checks for references to BGC IDs or strain IDs that do not exist in the current package/workbook. Source: `tools/check_dangling_refs.py`.

**`check_module_accretion.py`** — Tracks the history of when each mamey/ module was added. Prevents unintentional module removal between cuts. Source: `tools/check_module_accretion.py`.

**`check_no_brace_paths.py`** — Validates that no `{variable}` brace-path expressions appear unresolved in generated deliverables. Source: `tools/check_no_brace_paths.py`.

**`check_duplicate_dict_keys.py`** — Checks JSON files for duplicate keys (which Python's json.loads silently ignores, taking the last value). Source: `tools/check_duplicate_dict_keys.py`.

**`check_chatgpt_next_paths.py`** — Validates that ChatGPT handback text includes exactly 8 next-paths. Source: `tools/check_chatgpt_next_paths.py`.

**`gen_marker_catalog.py`** — Regenerates `docs/MARKER_CATALOG.generated.md` and `docs/MARKER_CATALOG.generated.json` from the live pattern tables in `mamey/source_scans.py`. `--check` verifies the on-disk catalog matches the live tables. Run in CI to prevent catalog drift. Source: `tools/gen_marker_catalog.py`.

**`gen_tools_inventory.py`** — Generates a machine-readable inventory of all tools/ scripts. Source: `tools/gen_tools_inventory.py`.

**`gen_user_catalog.py`** — Generates the user-facing catalog of available deliverables. Source: `tools/gen_user_catalog.py`.

---

## Section 10: Data Export and Literature

**`export_figure_ready.py`** — Exports the master workbook as tidy CSVs for downstream plotting. Produces `figure_ready/` folder: `strain_summary.csv`, `bgc_inventory.csv`, `bgc_class_long.csv`, `class_by_strain.csv`, `class_prevalence.csv`, `diagnostics_long.csv`, `cross_strain_findings.csv` + `DATA_DICTIONARY.md`. Column names and types are versioned with the bundle. Source: `tools/export_figure_ready.py`.

**`build_deep_data.py`** — Extracts deep workbook sheet data (Gene_NRPS_PKS_Substrates, Gene_Active_Sites, Gene_RiPP_Cores, BGC_Class_Predictions) from banked packages. Tags `Source = GBK-offline` vs `bounded-json` per field. Reports `OFFLINE-LIMITED` for strains that need re-running for fine sheet data. Source: `tools/build_deep_data.py`.

**`arts_ingest.py`** — Ingests ARTS (Antibiotic Resistance Target Seeker) output alongside Mamey packages. Source: `tools/arts_ingest.py`.

**`hub_merge.py`** — Hub-level merge of multiple sub-project workbooks into a master project workbook. Source: `tools/hub_merge.py`.

**`merge_workbooks.py`** — Merges two or more master workbooks without duplicating strains. Uses the `workbook_dedup.py` idempotent append mechanism. Source: `tools/merge_workbooks.py`.

**`build_card_workbook.py`** — Builds a per-BGC analysis card workbook (one sheet per lead BGC). Source: `tools/build_card_workbook.py`.

**`build_chat_export.py`** — Exports session chat history in a format suitable for archiving. Source: `tools/build_chat_export.py`.

---

## Section 11: Specialist and Research Tools

**`build_reconstruction.py`** — Fragment-rescue reconstruction builder: integrates RG-GMCI HIGH pairs into reconstructed cluster groups. Source: `tools/build_reconstruction.py`.

**`fragment_concordance_scorer.py`** — Scores RG-GMCI fragment pair concordance using the subject-tiling criterion. Source: `tools/fragment_concordance_scorer.py`.

**`run_efls_rewire.py`** — Runs the EFLS (Edge-Flank Linkage Scoring) rewire pass. Source: `tools/run_efls_rewire.py`.

**`build_wetlab_matrix.py`** — Builds the Wet-Lab Decision Matrix deliverable. Source: `tools/build_wetlab_matrix.py`.

**`build_modeb_deepdive.py`** — Batch Mode B deep-dive builder. Takes `--targets <ID>:BGC04,<ID>:BGC13` or reads from `cohort/modeb_verdicts.csv`. Source: `tools/build_modeb_deepdive.py`.

**`run_comparator_antismash_ingest.py`** — Runs antiSMASH comparator ingest for benchmark/validation strains. Source: `tools/run_comparator_antismash_ingest.py`.

**`backfill_reference_signatures.py`** — Backfills MIBiG reference signatures for BGCs that were processed before the reference index was complete. Source: `tools/backfill_reference_signatures.py`.

**`seed_reference_library.py`** — Seeds the curated reference BGC library from MIBiG and validated accessions. Source: `tools/seed_reference_library.py`.

**`build_first_pass_scans.py`** — Standalone first-pass scan runner (without running the full engine). Source: `tools/build_first_pass_scans.py`.

**`reference_panel_ledger.py`** — Maintains the reference panel ledger (known-compound positive controls and their expected outputs). Source: `tools/reference_panel_ledger.py`.

**`cluster_alignment.py`** — Aligns BGC protein sets across strains for comparative analysis. Source: `tools/cluster_alignment.py`.

**`comparative_pairs.py`** → `mamey/comparative_pairs.py` — see module listing.

**`build_finer_from_gbk.py`** — Extracts fine workbook sheet data (Gene_NRPS_PKS_Substrates, Gene_Active_Sites, BGC_Class_Predictions) directly from region GBKs without needing bounded-mode JSON. Source: `tools/build_finer_from_gbk.py`.

**`reclass_discriminating_domains.json`** — Registry of domain combinations that discriminate between antiSMASH class calls (e.g., CDPS vs ent-CDPS, ranthipeptide vs mycofactocin). Read by `reclass_check.py`. Source: `tools/reclass_discriminating_domains.json`.

**`gate_registry.tsv`** — Machine-readable registry of all pipeline gates with their descriptions, source modules, and test coverage status. Source: `tools/gate_registry.tsv`.

**`test_synthetic_ids.txt`** — Synthetic strain ID list for testing the release guard (unpublished ID detection). Source: `tools/test_synthetic_ids.txt`.

---

## Section 12: Document Generation

**`md_to_docx.sh`** — Converts Markdown to DOCX via pandoc. Used for deliverable document generation. Source: `tools/md_to_docx.sh`.

**`md_to_pdf.sh`** — Converts Markdown to PDF via pandoc + xelatex. The authorised PDF path — do not use wkhtmltopdf. Source: `tools/md_to_pdf.sh`.

**`render_bootstrap_contract.py`** — Renders the bootstrap contract (session start document) for a new analysis chat. Source: `tools/render_bootstrap_contract.py`.

**`build_chat_export.py`** — Archives session content in a structured format. Source: `tools/build_chat_export.py`.

---

## Section 13: Validation Helpers

**`assembly_qc_check.py`** — Assembly quality control check: GC%, N50, contig count, contamination flags. Standalone version of the assembly_sanity_check logic. Source: `tools/assembly_qc_check.py`.

**`check_tier_parity.py`** — Cross-tier parity check. See Section 7. Source: `tools/check_tier_parity.py`.

**`intake_harness.py`** — Test harness for the antiSMASH intake pipeline. Runs a batch of antiSMASH ZIPs through intake and validates outputs. Source: `tools/intake_harness.py`.

**`reference_bgc_structural_validator.py`** — Exact-bound structural measurement of a locally curated reference-BGC panel. This deterministic operator tool reports locus size, feature counts, and scoped detector observations; it does not perform biological validation and does not emit one row per gene. Source: `tools/reference_bgc_structural_validator.py`.

**`validate_timing_receipt_parity.py`** — Validates that run_phase_receipts.jsonl contains timing entries for every phase in the expected sequence. Source: `tools/validate_timing_receipt_parity.py`.

**`encyclopedia_reground_check.py`** — Checks that the Encyclopedia (03_Technical_Manual_Encyclopedia.html) cross-references remain valid after source changes. Source: `tools/encyclopedia_reground_check.py`.

**`SLIM_KERNEL_PATCHES_v1.9.7.md`** — Patch notes for the Slim Kernel → Execution Slice transition, v1.9.7 series. Source: `tools/SLIM_KERNEL_PATCHES_v1.9.7.md`.

---

*Source: direct directory listing of `tools/` plus docstring extraction. 107 scripts inventoried. Compiled 2026-07-09 · bundle v9.7.241.*

---

## Section 14: Live Tools Verification — What Actually Runs

*Commands verified to run successfully in bundle v9.7.241, 2026-07-09. All outputs are from real execution against the teicoplanin calibration package.*

### Verified command matrix

| Command | Input | Output | Confirmed |
|---|---|---|---|
| `mamey doctor` | (no input) | Dependency/permission pre-flight report | ✅ 18.8s total |
| `mamey inspect <zip>` | antiSMASH ZIP | Pre-run preview: region count, GBK contents | ✅ |
| `mamey run --mode gold` | antiSMASH ZIP | Sealed package, 26 figures, compiled report | ✅ 18.8s wall |
| `mamey validate <pkg>` | Sealed package | JSON gate report: file_presence, checksums, rggmci | ✅ MAMEY_COMPLETE |
| `mamey list-bgcs <pkg> --json` | Sealed package | JSON BGC inventory with all scores | ✅ |
| `mamey emit-modeb-template --bgc BGC001` | Sealed package + BGC ID | §1–§30 template with gene table pre-filled | ✅ 109 lines |
| `mamey render-all-figures <pkg>` | Sealed package | 5 figure modules, 26 figures total | ✅ |
| `mamey workflow <pkg> --json` | Sealed package | W0–W10 gate status with receipts | ✅ W0-W2 PASS |
| `tools/preflight_zip_hygiene.py <zip>` | antiSMASH ZIP | Clean/dirty assessment | ✅ OK |
| `tools/gen_marker_catalog.py --check` | (live patterns) | Drift check: 14 tables in sync | ✅ |
| `tools/sapote_workflow.py <pkg>` | Sealed package | W0–W10 ledger markdown | ✅ 3/11 PASS |
| `tools/claim_safety_linter.py <md>` | Markdown file | Finding list with line annotations | ✅ 2 findings |

### Tools that require additional arguments (not run but syntax verified)

**`tools/check_deliverable_suite.py`** — requires `--manifest MANIFEST` (a filled `DELIVERABLE_MANIFEST_*.md`). Not runnable until the deliverable manifest has been generated and filled.

**`tools/assembly_qc_check.py`** — takes `--snapshot` or `--banked-dir`, not `--package`. Call with a cohort bank directory, not directly with a package.

**`tools/sapote_md_preflight.py`** — requires both `input_md` and `output_md` positional arguments (writes a preflight-processed copy to output).

**`tools/build_workbook.py --full`** — requires `--banked-dir` (a cohort bank populated by `ingest_package.py`). Cannot run on a single package directly.

### Tools output format notes

**`mamey workflow --json`** — produces the same content as the markdown output but machine-readable. The status values are: `PASS`, `PENDING`, `BLOCKED`, `N_A`. The `receipt` field contains the specific artifact reference (file name + size + content summary) that confirmed the PASS, or the blocking reason.

**`mamey list-bgcs --json`** — produces a JSON array, one object per BGC. The array is directly usable by downstream tools. The `--axis` flag selects sort order (`rank`, `ab`, `af`, `novelty`); `--top N` limits output count.

**`mamey emit-modeb-template`** — the output goes to stdout by default; redirect to a file for authoring. The template includes a pre-filled gene table from `gene_context.jsonl`, the BGC's scores from the triage board, and the over-merge warning when applicable.

**`mamey render-all-figures`** — non-blocking per module. If one module fails (e.g. domain-level fails because deep_data.json is empty), the others continue. The summary at the end reports per-module results.

**`tools/gen_tools_inventory.py`** — writes a tools inventory to `SESSION_START_MANIFEST.md` and also outputs "wrote inventory: N tools" to stdout. The inventory is a structured markdown table of all tools/scripts with docstrings extracted. For a connection-aware review, run `python tools/gen_tools_inventory.py --connections --format tsv --output tool_connections.tsv`. That audit reports exact source hashes, executable interface, source/CLI consumers, tests, path-filtered non-historical documentation references, manifest membership, declared lifecycle, personal-path literals, external-contact markers, and two transparent evidence scores. The scores measure wiring and operational support only; they do not measure scientific value, correctness, acceptance, or release readiness. The marker columns are review cues, not proof that a default is unsafe or that external contact occurs.

---

## Section 15: Tools Quick Reference Card

For field use — the most common tools and their essential flags.

```bash
# --- BEFORE A RUN ---
mamey doctor                               # pre-flight: Python, deps, permissions
preflight_zip_hygiene.py <zip>             # check for macOS artifacts, oversized files
mamey inspect <zip>                        # preview: region count, organism, GBK structure

# --- RUN ---
python -m mamey run \
  --input-zip <zip> --strain <ID> \
  --taxonomy "Genus sp." --source "host, location" \
  --release PUBLIC|PRIVATE \
  --mode gold --json-evidence bounded \
  --outdir runs/

# --- VALIDATE ---
mamey validate runs/<ID>/package           # → MAMEY_COMPLETE or MAMEY_COMPLETE_WITH_ISSUES

# --- FIGURES ---
mamey render-all-figures --package <pkg>   # run if --capped-session suppressed figures

# --- EXPLORE OUTPUTS ---
mamey list-bgcs <pkg> --json              # BGC inventory with all scores
mamey list-bgcs <pkg> --axis af --top 5  # top 5 by antifungal score
mamey explain <pkg>                        # narrative walkthrough

# --- MODE B ---
mamey emit-modeb-template \
  --package <pkg> --bgc BGC001 > BGC001_card.md    # emit §1–§30 skeleton
mamey verify-modeb --package <pkg> --bgc BGC001    # validate authored card

# --- WORKFLOW GATE ---
mamey workflow --package <pkg>             # W0–W10 markdown ledger
mamey workflow --package <pkg> --json     # W0–W10 machine-readable
mamey workflow --package <pkg> --strict   # exit non-zero if any mandatory step incomplete

# --- COMPILE ---
mamey compile-report --package <pkg>       # auto-compile report
mamey compile-report --package <pkg> --strict  # exit non-zero if SAPOTE slots open
mamey compile-report --package <pkg> --pdf  # also render Boss-Ready PDF via md_to_pdf.sh (refuses on unfilled slots)
mamey compile-report --package <pkg> --pdf --allow-unfilled-pdf  # render the PDF even with unfilled slots (skeleton)

# --- BANK AND BUILD ---
tools/ingest_package.py \
  --package <pkg> --ww WWGP0000000 \
  --merge --banked-dir cohort/

tools/build_workbook.py \
  --workbook project_master.xlsx \
  --banked-dir cohort/ --full

# --- RELEASE ---
tools/gen_marker_catalog.py --check       # verify catalog matches source
tools/sync_version.py --check             # verify version strings consistent
tools/preflight_zip_hygiene.py <zip>      # clean release check
tools/check_tier_parity.py --tiers-dir . # all-tier parity gate
tools/claim_safety_linter.py <md>        # check claim safety in narrative text
```

**compile-report `--pdf` publication artwork.** The PDF path validates every figure at the declared
7.2-inch double-column width before writing render Markdown. Live-text SVG is preserved through vector
PDF conversion when `cairosvg`, `rsvg-convert`, or `inkscape` is available. Only if vector conversion is
unavailable may the compiler make a native-width raster fallback, which must still provide at least 300
effective DPI. Existing PNG thumbnails that would be enlarged are refused with
`FIGURE_EFFECTIVE_DPI_INSUFFICIENT`; metadata DPI and PDF-derived screenshots do not satisfy the gate.
This fail-closed check prevents a standalone screen PNG from becoming blurred publication artwork.
Install `cairosvg` via the render extra so the vector-preserving path is available wherever the compiled
PDF is built:

```bash
pip install '.[render]'   # cairosvg — also folded into '.[all]'
```

---

*v2 additions: Sections 14–15 (live verification, quick reference card) · Bundle v9.7.241 · 2026-07-09*

---

## Section 16: New Tools (v9.7.243–246)

### `tools/file_atlas.py` — describe every Python file from the source

**Added:** v9.7.243. Built for the Bunny Hop Audit Game (`games/BUNNY_HOP_AUDIT_GAME.md`): "you cannot audit what you cannot see."

Walks `mamey/` and `tools/` with `ast` and emits one row per file. Nothing is inferred and no list is hardcoded — every column is read from the real tree.

**Columns:** `path`, `loc`, `summary` (first docstring line), `n_defs`, `n_classes`, `imports_internal` (fan-out), `imported_by` (fan-in), `cli_verbs` (subcommands registered in this file), `test_refs` (test files naming this module), `orphan`.

**The `orphan` column is the interesting one.** A module that nothing imports, that no CLI verb reaches, and that no test names, is a candidate for the audit's REDUNDANCY inspector — or for the defect class this project keeps hitting, where **a capability exists and nothing invokes it** (see Development Issues Compendium, Group 14).

```bash
python3 tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md
python3 tools/file_atlas.py --orphans     # just the orphan list, for the bunny-hop roll
```

| Flag | Effect |
|---|---|
| `--out PATH` | CSV output path |
| `--md PATH` | Markdown summary path |
| `--orphans` | Print orphan candidates only; no files written |

**Live receipt on bundle v9.7.246:**

```
280 files under mamey/ and tools/
74,981 total lines
35 orphan candidates (no importer, no CLI verb, no test)
57 files no test names at all
```

**Highest fan-in (from `docs/FILE_ATLAS.md`) — change these carefully:**

| File | Imported by | LOC |
|---|---:|---:|
| `tools/_wbio.py` | 38 | 125 |
| `mamey/models.py` | 13 | 397 |
| `mamey/crosswalk.py` | 11 | 238 |
| `mamey/antismash_evidence.py` | 9 | 1,233 |
| `mamey/figure_policy.py` | 8 | 56 |
| `mamey/source_scans.py` | 8 | 1,733 |
| `mamey/_gbk_shim.py` | 7 | 139 |
| `mamey/modeb_structure_gate.py` | 7 | 1,036 |

Both `_wbio.py` (38 importers, 1 test before v9.7.243) and `crosswalk.py` (fan-in 11) were subsequently hardened — the atlas identified them as the highest-risk files, and the audit went there next. This is the tool doing its job.

**Known limitation, found and fixed before shipping:** the first pass called `verify_release_identity.py` an orphan. It is invoked by `release.sh`, which the AST scanner did not read. Shell and gate-registry invocations now count. Orphan count dropped 42 → 35. The lesson generalises: an AST scan sees Python imports, not shell invocations, not YAML, not a `gate_registry.tsv` row.

**Output artifacts:** `docs/FILE_ATLAS.csv` (machine-readable, one row per file) and `docs/FILE_ATLAS.md` (four sections: Highest fan-in · Largest files · Orphan candidates · Every file).

---

### `tools/check_monolith_freshness.py` — keep the parent design doc's anchor honest

**Added:** v9.7.243, WIRED (registered in `tools/gate_registry.tsv`).

`docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` is the parent design controller, referenced by 20 files including `prompts/CLAUDE_SYSTEM_PROMPT.md`. It is deliberately **not** bumped every patch — its content is reviewed at checkpoints. That convention is sound. What is not sound is the anchor line drifting silently: at v9.7.242 the monolith still claimed to be vetted against v9.7.6 and stated `current bundle 9.7.57 / engine 1.9.64` — **185 cuts of drift, with no signal.**

**The gate does not demand a re-read. It demands that the monolith state, truthfully, how far behind it is.**

**Four checks:**
1. The monolith exists and names a `vetted against` bundle version.
2. The `current bundle X / engine Y` parenthetical, if present, matches the live `pyproject.toml` / `BUILD_STAMP`.
3. The drift (live bundle patch − vetted patch) is reported, and fails above `--max-drift`.
4. **No retired doctrine is present** — assembly tiers 66/50/33, per-BGC BSL-2 flagging, AS_SCRUB, the PUBLIC/PRIVATE figure divider. These are decisions the project has explicitly reversed, and a fresh chat reads the monolith first.

```bash
python3 tools/check_monolith_freshness.py                # default max-drift
python3 tools/check_monolith_freshness.py --max-drift 10
python3 tools/check_monolith_freshness.py --quiet
```

| Exit | Meaning |
|---|---|
| 0 | Fresh enough and doctrinally current |
| 1 | Stale anchor or retired doctrine present |
| 2 | Monolith missing |

**Live receipt on bundle v9.7.246:**

```
monolith: vetted v9.7.242 | live v9.7.246 | drift 4 patches | 450,214 chars
check_monolith_freshness: PASS (anchor honest, no retired doctrine)
```

**Negation awareness.** The gate false-positived on its own first run, flagging a freshly written "no per-BGC BSL-2 flagging" as an assertion of the doctrine it denies. A negation-aware window was added — the same lesson the v9.7.233 novelty lint learned. It still fails on a genuine assertion (`GOOD >= 66%`).

---

## Section 17: Gate Additions (v9.7.246–.256)

### `PHANTOM_LOCUS` — release-blocking referent validation

Not a standalone tool: a lint inside `mamey/modeb_structure_gate.py`, reachable through `mamey verify-modeb` and `authored_verify`.

**What it asks:** does every `ctgN_M` locus tag cited in this Mode B card exist in **this strain's own CDS table**?

**Why it exists:** the §4 authoring template hardcoded a real per-gene BLASTp result from *Amycolatopsis* sp. NPDC004378, which was templated verbatim into 74 cards across two strains — asserting a specific BLASTp outcome for strains on which no BLASTp had been run. Every existing guard passed those cards. None of them asked whether the cited gene existed. (Full account: Development Issues Compendium, Group 13.)

**How to invoke:**

```bash
mamey verify-modeb --package <sealed_pkg> --bgc BGC001    # loads known_loci automatically
```

`authored_verify` globs `<pkg>/*_cds_table.csv` and `<pkg>/cds_table.csv` to build `bgc_context["known_loci"]`. Without a sealed package there is no CDS table, and **the lint is silent** — it cannot judge what it cannot see, and a false accusation of fabrication is worse than none.

**Severity:** ERROR. Added to `_READINESS_BLOCKING` alongside `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`, and `FACT_MISMATCH`. A card citing a foreign locus cannot reach `RELEASE_READY` and therefore cannot be presented.

**Verified against the real AS-XXX package:** 758 loci loaded; `ctg12_71` not among them; the leaked sentence raises ERROR and drops `readiness_state` below `RELEASE_READY`. A card citing that strain's real loci passes clean.

**Operational consequence:** the 74 already-authored cards are not repaired by the fix. Re-run `verify-modeb` against them with a sealed package and every one will flag. **Every §4 and §16 paragraph containing `ctg12_71` should be deleted, not reworded** — there is no BLASTp result to reword.

### `LOCUS_BGC_MISMATCH` — real locus cited under the wrong BGC (v9.7.256)

Sibling of `PHANTOM_LOCUS` in `mamey/modeb_structure_gate.py`, reached through `verify-modeb` / `authored_verify`. Where `PHANTOM_LOCUS` asks *does this gene exist in this strain at all*, `LOCUS_BGC_MISMATCH` asks *does this gene, which does exist, belong to the BGC it is cited under*.

**What it asks:** for a `ctgN_M` that is a real member of this strain's CDS table, is it cited under its home BGC, or co-cited under a different BGC it does not belong to?

**Why it exists:** the AS-XXX BGC006/BGC010 leak class — templated boilerplate carried from one BGC's session into another's card attributes a real gene to the wrong cluster. The gene is real (so `PHANTOM_LOCUS` stays silent), but the attribution is fabricated. `authored_verify` builds per-BGC membership so the lint can tell a real gene cited under the wrong BGC from a correctly-placed one.

**Severity:** ERROR → the card drops to `DRAFT` (Section 18) and cannot be presented. It is **not** a member of the four-code `_READINESS_BLOCKING` set; it blocks via the any-ERROR path.

### `PANEL_ABSENT_CLAIM` — per-gene BLASTp result asserted for a BGC with no panel (v9.7.256)

Sibling lint (same file / entry points). Guards the independent-homology channel against fabricated results.

**What it asks:** does the card state a per-gene BLASTp outcome for a BGC that has **no BLASTp panel** in this package?

**Why it exists:** a BLASTp result for a BGC whose panel was never built is a fabricated observation (the same AS-XXX BGC006 class). `authored_verify` records which BGCs actually have a panel so the lint can flag a per-gene claim on a BGC with none.

**Keys on panel *selection*, not returned alignments (residual gap, stated):** a standard run builds a selection FASTA for *every* BGC, so this lint does **not** catch a fabricated per-gene result on a BGC that has a panel selection but was never actually run (reproduced on `S_erythraea` BGC017). The residual gap is "asserted result vs actual returned alignments"; a future gate closing it should extend `PANEL_ABSENT_CLAIM` to require a results artifact, not add a new gate.

**Severity:** ERROR → `DRAFT`; blocks via the any-ERROR path, not a `_READINESS_BLOCKING` member.

---

## Section 18: Card Readiness State Machine

Documented here because `verify-modeb` reports it and no other section covers it. Source: `mamey/modeb_structure_gate.py:readiness_state`.

```python
_READINESS_BLOCKING = {"NOVELTY_CONTRADICTION", "INTERNAL_CONTRADICTION",
                       "FACT_MISMATCH", "PHANTOM_LOCUS"}

def readiness_state(findings, quality_tier=None):
    if any(f["severity"] == "ERROR" for f in findings):   return "DRAFT"
    if quality_tier in (None, "STUB", "UNKNOWN"):          return "DRAFT"
    if {f["code"] for f in findings} & _READINESS_BLOCKING: return "VERIFIED"
    return "RELEASE_READY"
```

| State | Meaning | May be presented? |
|---|---|---|
| `DRAFT` | Any ERROR finding, **or** the card is a STUB / depth-unverified | No |
| `VERIFIED` | Depth is adequate, but a correctness check fails (one of the four blocking codes) | No |
| `RELEASE_READY` | Depth adequate **and** no correctness block | Yes |

**Only `RELEASE_READY` should flow into user-facing documents.** This is the presentation gate. A card that is structurally complete, adequately deep, and claim-safe can still be `VERIFIED` rather than `RELEASE_READY` — because a fact in it contradicts the package, or a locus in it belongs to another organism.

Note the asymmetry: an ERROR-severity finding drops a card all the way to `DRAFT`; a blocking *code* at WARN severity holds it at `VERIFIED`. `PHANTOM_LOCUS` is emitted at ERROR severity, so a phantom locus produces `DRAFT`.

---

## Section 19: BLASTp toolchain + release-qa (v9.7.247–.260, CLI synced v9.7.260)

The independent per-gene homology channel and its ingest/iterate commands, plus the release gate. These are `mamey` subcommands (not `tools/` scripts); descriptions are from the registered CLI (`mamey <cmd> --help`), verified against the tree at v9.7.260.

**§4 authoring — offline path preferred (v9.7.260).** A Mode B lead card's §4 is authored *after* the BLASTp panel exists, but there are two ways to produce the same `<BGC>_online_blastp.csv` panel and the offline one avoids live polling:

- **token-friendly / offline (preferred when results are in hand):** if NCBI BLAST has already been run, ingest the hit-table with zero network via `mamey ingest-blastp` — no RID poll, no ~1–2 min/query wait.
- **live:** `mamey blastp-online` submits to NCBI and polls; use only when no pre-run results exist.

With no results at all, the honest read is "antiSMASH Pfam, unverified" — never fabricate (see `PANEL_ABSENT_CLAIM` / `PHANTOM_LOCUS`, Section 17).

**`mamey bgc-blastp-panel`** — Export up to two representative translated proteins per BGC as chunked FASTA files for manual BLASTP. The panel *selection* is what downstream gates read to decide a BGC "has a panel" (`PANEL_ABSENT_CLAIM`).

**`mamey blastp-online`** — Per-gene NCBI web BLASTp for a BGC (independent homology channel; fail-closed if biopython/network absent — actionable message, not a traceback). Its banner now points at the offline `ingest-blastp` route to skip live polling.

**`mamey blastp-ebi`** — EBI fallback BLASTp transport (no nr; DB-tagged provenance; coverage-preserving XML path).

**`mamey blastp-round`** — Plan/run a phased strain BLASTp round (full top-N + 1 per remaining BGC).

**`mamey blastp-followup`** — Parse NCBI BLASTP Hit Table / XML2 results and make the next iterative, residue-safe BLASTP queue files.

**`mamey ingest-blastp`** — Ingest an NCBI BLASTp HitTable CSV (+ optional Alignment XML) into a master workbook's `B5_BLASTp_Hits` sheet; with `--package`, mirrors the panel to `<package>/blastp_online/<BGC>_online_blastp.csv`. This is the offline, zero-network path.

**`mamey modeb-blastp`** — Emit per-BGC BLASTP FASTA batches from the panel manifest (Mode B §16 automation).

**`mamey hmm-adjudicate`** — Ordered HMM domain readout for a BGC (intrinsic structure; offline tie-breaker that complements BLASTp when it disagrees with the antiSMASH call).

**`mamey release-qa`** — Run release QA gates: Legacy Feature Matrix + Dual-LLM Handoff Receipt.

*Batch rule (v9.7.252): a submission closes on protein count OR a 30,000-aa `RESIDUE_BUDGET`, whichever hits first; `MAX_BATCH` stays 30 and `DEFAULT_BATCH` is 10 (the courteous default used when the caller omits `batch_size`); giants (>2,500 aa) run solo; `SUBMIT_GAP_S` spaces submissions.*

*Mode B referent lints (v9.7.246/.256): `PHANTOM_LOCUS` (locus not in this strain's CDS table), `LOCUS_BGC_MISMATCH` (real locus cited under the wrong BGC), `PANEL_ABSENT_CLAIM` (per-gene BLASTp result asserted for a BGC with no panel). All ERROR-severity → `DRAFT`. Full detail in Section 17.*

*Section 19 added v9.7.260; command descriptions from the registered `mamey <cmd> --help`.*

---

## Section 20: New post-seal subcommands & deliverables (v9.7.338)

Twelve sign-off-gated capabilities that consume an **already-sealed package** (or a directory of
them) and emit an extra deliverable. Like `render-figures` / `cohort-figures` / `ingest-receipts`,
every one is post-seal and non-blocking: it reads facts the engine already computed and **never
re-runs the engine, moves a score, or touches a published tier**. Non-scoring unless noted;
capacity-level, judgment deferred.

```bash
# --- CROSS-STRAIN LEDGERS ---
mamey cohort-leads    --runs-dir <runs_dir> [--out COHORT_PRIORITY_LEADS.csv]   # union Exceptional+High leads → one ranked CSV
mamey cohort-assemble --runs-dir <runs_dir> [--out COHORT_MASTER.csv] [--xlsx]  # many sealed packages → one master table (+ siblings)

# --- EVIDENCE / FALSE-POSITIVE LAYER ---
mamey comparator-coverage <package> [--cohort-runs-dir <runs_dir>]  # two-denominator MIBiG comparator coverage (report-only)
                                                                     # standalone: python -m mamey.mibig_comparator_coverage <package_dir> [--cohort-runs-dir <dir>]

# --- ANTIFUNGAL + INTERPRETIVE DELIVERABLES ---
mamey af-dossier   <root> [--out DIR] [--activity-table CSV] [--depth N]  # AF leads x optional measured Candida activity (report-only)
mamey good-guesses <root> [--out DIR] [--pdf] [--docx] [--depth N]       # claim-safe interpretive priors (solid/rare/remarkable/notable/interesting)
                                                                          # standalone: python -m mamey.good_guesses <ROOT|package_dir> --out <DIR> --pdf --docx

# --- DOCUMENT + FIGURE EXPORT ---
mamey modeb-export <card.md|mode_b/> [--outdir DIR] [--format docx|pdf|both]  # authored Mode B card → .docx + .pdf (reportlab)
python -m mamey.kcb_locusmap --zip <zip> --contig <NODE> --out-dir <dir> \
    --strain-id <ID> --bgc-id BGC### [--products "..."] [--top-n 6]           # offline KCB comparative locus map (PNG/SVG + data.csv)
                                                                              # or: --kcb-txt <knownclusterblast.txt> --out-dir <dir> --stem BGC###

# --- COUNT / NOVELTY / REFERENCE (advisory) ---
mamey domain-reference  --package <pkg> [--out FILE]            # bundled Mode-B domain-reference dictionary
mamey realistic-count   --package <pkg> [--out FILE]            # honest corrected BGC-count denominator
mamey novelty-shortlist --package <pkg> [--top 30] [--out FILE]  # composite multi-signal novelty shortlist

# --- ANALYSIS QC + MODE-B INTERPRETATION GATES ---
mamey signoff [tree.treefile ...] [--minutes N]                          # "would a master's student sign off?" tree QC (advisory, exit 0)
mamey verify-modeb --package <pkg> --bgc BGC### --interp [--interp-strict]  # add WARN-only INTERP_* judgment checks to verify-modeb
                                                                           # strict authoring gate: python -m mamey.modeb_interp_gate <card.md> [--strict]
```

**Notes.**
- **`comparator-coverage`** emits `<STRAIN>_3b_comparator_coverage.csv` + `_summary.json`. It is the
  false-positive killer: a named-MIBiG-family "lead" that survives only one of the two coverage
  denominators is exposed as low-specificity rather than surfaced. Report-only in .338 — its scoring
  wire (suppression-only, guard-gated) is a future sign-off-gated change and is NOT active.
- **`good-guesses`** writes `GOOD_GUESSES.{md,csv}` (+ `.docx` / `.pdf` on request). Each notable BGC
  gets ONE best claim-safe read, a tag (solid / rare / remarkable / notable / interesting), a
  confidence, and the resolving experiment; a per-page claim-safety footer is included.
- **`modeb-export`** — `reportlab` (PDF) is vendored in `Tools/wheelhouse`; `python-docx` is not, so the
  DOCX path degrades gracefully (`SKIPPED_NO_DOCX`) rather than failing when it is unavailable.
- **`figures kcb-locusmap`** degrades to a clear message + non-zero exit (never a traceback) when
  matplotlib is absent; it reads only a sealed input ZIP (or an extracted txt) and cannot fail a run.
- **`verify-modeb --interp`** only *adds* WARN-severity `INTERP_*` findings — the structure gate's
  PASS/FAIL and exit code are unchanged (a card can be green and still show interp warnings).

**Non-feature .338 changes reflected here:** the **§4 Mode-B evidence gate now bites (MB-01)** (the
evidence-grid check is enforcing, not advisory), the **NAPAA standing rule now follows the registry
(RG-01)** (driven by `rules_registry.json`, not a hardcoded pattern — same behaviour, single source),
and the redaction wording is corrected (E2E-03): AS-series strains are PUBLIC by default (PI decision
2026-07-06), fail-safe PRIVATE only for AJS- / PENDING- / unrecognized shapes.

---

*v3 additions: Sections 16–18 (file_atlas, check_monolith_freshness, PHANTOM_LOCUS gate, readiness state machine) · Bundle v9.7.246 · 2026-07-09*
*v4 additions: Section 17 extended with `LOCUS_BGC_MISMATCH` + `PANEL_ABSENT_CLAIM` (v9.7.256); Section 19 (BLASTp toolchain + release-qa, offline-preferred §4); header CLI-synced · Bundle v9.7.260 · 2026-07-11*
*v5 additions: Section 20 (twelve new post-seal subcommands & deliverables) · v9.7.338*
