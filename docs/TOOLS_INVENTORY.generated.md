# Tools Inventory (generated)

**309 tools** in `tools/`. Generated from each tool's docstring by `tools/gen_tools_inventory.py` — do not edit by hand. Check this list BEFORE writing a new tool.

> **This is the INTERNAL script catalog** (the `tools/` helpers shipped with the engine). For the **external tool stack** the workflow depends on — antiSMASH, BiG-SCAPE, IQ-TREE, GToTree, BLAST+, SPAdes and their versions/citations — see `docs/EXTERNAL_TOOL_INVENTORY.md`.

| Tool | What it does |
|---|---|
| `_console.py` | the single owner of direct terminal emission for tools/ and deliverable_tools/. |
| `_safe_walk.py` | shared directory-walk helper that surfaces permission errors instead of |
| `_wbio.py` | Shared atomic workbook I/O for the secondary-sheet builders. |
| `add_xstrain_sheets.py` | Append or refresh the three deterministic cross-strain workbook sheets. |
| `ani_caption_check.py` | Check that a caption/table names ANI versus AAI honestly and flags boundary values. |
| `antismash_bigscape_join.py` | antismash_bigscape_join.py -- reconcile antiSMASH per-BGC output with BiG-SCAPE GCF families. |
| `apply_dapr_boards.py` | re-apply the Sapote-layer DAPR judgment boards (C1/C2) to a workbook. |
| `archive_leak_scan.py` | private-ID leak guard for the *contents* of committed archives. |
| `arts_ingest.py` | ARTS2 → per-BGC self-resistance signal (lead M7, validated against an admitted result fixture). |
| `assembly_qc_check.py` | deterministic assembly-QC gate (Mamey, runs before lead_board). |
| `audit_blastp_zero_alignment.py` | find fabricated tested-negatives in BLASTp evidence. |
| `audit_chatgpt_nextpaths_drift.py` | Audit high-risk ChatGPT/Mamey instruction surfaces for next-path drift. |
| `audit_documents_wheelhouse.py` | Fail-closed preflight for the governed documents add-on wheelhouse. |
| `audit_llm_companion_instructions.py` | Gate the LLM-facing BiG-SCAPE/GToTree instruction surface. |
| `audit_modeb_support_card.py` | Audit a Mode B support card and, optionally, its task progress ledger. |
| `audit_public_cut.py` | workbook-aware public-cut leak guard for merged-master Excel deliverables. |
| `backfill_reference_signatures.py` | Backfill architecture_signature + refresh observed markers/genus into the reference library from antiSMASH zi… |
| `bgc_alias_history.py` | which BGC id did this locus carry in the PRIOR run of the same strain? |
| `bgc_deliverable_pdf.py` | bgc_deliverable_pdf.py -- assemble a per-BGC deliverable PDF (cover + facts + figures + Mode B). |
| `bgc_figures.py` | bgc_figures.py -- per-BGC figure set for Sapote-Mamey deliverables. |
| `bgc_neighbor_layer.py` | build a SEPARATE labeled tree layer for shared-BGC / BLASTp-neighbor |
| `bgc_reconcile.py` | pre-authoring cross-channel evidence reconciliation ledger. |
| `bgc_reference_align.py` | bgc_reference_align.py -- align one BGC's proteins against characterized reference clusters |
| `bigscape_blastp_novelty.py` | Gene-level protein-homology context against a user-provisioned MIBiG GBK set. |
| `bigscape_combined_run.py` | Sapote-Mamey BiG-SCAPE combined-run tool |
| `bigscape_cross_strain.py` | Write a deterministic, qualified cross-strain BiG-SCAPE GCF table. |
| `bigscape_family_domains.py` | bigscape_family_domains.py |
| `bigscape_figure_labels.py` | bigscape_figure_labels.py -- canonical node-category labels/colours for BiG-SCAPE figures. |
| `bigscape_ingest_to_mamey.py` | bigscape_ingest_to_mamey.py -- write BiG-SCAPE GCF context INTO the Mamey layer. |
| `bigscape_known_novel.py` | Write qualified KNOWN/NOVEL GCF rows from one explicitly selected BiG-SCAPE run. |
| `bigscape_merge_anchors.py` | Validate qualified anchor/base rows, then atomically classify base GCFs. |
| `bigscape_mibig_anchors.py` | Emit qualified per-run, per-cutoff MIBiG anchoring edges. |
| `bigscape_mibig_batches.py` | split the MIBiG reference set into small, prokaryote-filtered |
| `bigscape_pipeline.py` | bigscape_pipeline.py -- one-command BiG-SCAPE GCF layer for a Mamey cohort. |
| `bigscape_prep.py` | stage antiSMASH region GBKs into a BiG-SCAPE input dir. |
| `bigslice_query.py` | bigslice_query.py -- BiG-SLiCE as a second, feature-based GCF opinion (complements BiG-SCAPE). |
| `bioassay_to_activity_channel.py` | emit MEASURED fraction-screen data as Sapote-Mamey |
| `blastp_campaign.py` | headless, resumable, checkpoint-first NCBI BLASTp campaign runner. |
| `blastp_channel_triage.py` | Command-line front door for the fail-closed BLASTp channel triage sidecar. |
| `blastp_coverage_wave.py` | measure BLASTp coverage gaps, stage a priority wave into isolated |
| `build_all_deliverables.sh` | regenerate default Sapote–Mamey deliverables from the banked cohort, |
| `build_bgc_markers.py` | (no docstring) |
| `build_card_workbook.py` | cross-strain card workbook. |
| `build_causemap.py` | chain-of-events / cause-effect diagrams (thesis-oriented). |
| `build_chat_export.py` | build_chat_export.py  (candidate patch P09) |
| `build_chitinase_screen.py` | add the Chitinase_Screen sheet to the master workbook. |
| `build_cohort_html.py` | one self-contained HTML analysis across sealed Mamey packages. |
| `build_cohort_precompute.py` | Part A: one cohort-wide table per fact-type (v9.7.224). |
| `build_combined_bgc_report.py` | Build one portable combined V7 + Mode B BGC dossier. |
| `build_cross_strain_figures.py` | CLI wrapper for mamey.cross_strain_figures. |
| `build_dapr_rescue_sheets.py` | deterministic (Mamey-layer) regeneration of the schema-v1.2 |
| `build_deep_data.py` | (no docstring) |
| `build_deliverable_menu_widget.py` | render the self-contained Deliverable Menu widget. |
| `build_domain_explorer.py` | Read-only projection of the existing architecture owner; no biological scans. |
| `build_domain_matrix.py` | cross-strain antiSMASH-HMM domain census (v9.7.221). |
| `build_domain_reference.py` | emit a per-package domain functional-context dictionary (DOMREF-01). |
| `build_domain_tree.py` | the ONLY sanctioned way to build a BGC-machinery domain tree (VGP-399). |
| `build_enzyme_neighborhoods.py` | Explicit local view builder; pins the adjacent bundled package. |
| `build_family_map.py` | lexicon growth) |
| `build_figure_review_queue.py` | Build a portable, paginated owner-review queue from a Figure Factory manifest. |
| `build_figures.py` | reproducible figure module for the Sapote-Mamey bundle. |
| `build_finer_from_gbk.py` | recover 3 of the 4 finer sheets from antiSMASH region GBKs, offline. |
| `build_first_pass_scans.py` | render the eight genome-wide First-Pass Scans into one cohesive |
| `build_gcf_tags.py` | map each BGC's KCB anchor to a curated GCF / product-family tag (Sapote annotation layer). |
| `build_genelevel_triage.py` | Mamey deterministic pre-pass that does the gene-level heavy |
| `build_id_resolver.py` | emit the BGC ID-resolver table for a banked cohort. |
| `build_inventory_table.py` | Improved BGC inventory deliverable: ONE document, two views of the same BGCs. |
| `build_lead_detail.py` | per-lead BGC detail extractor for the Sapote judgment layer. |
| `build_lead_tiers.py` | re-derive lead tiers with self-protection as an orthogonal second axis. |
| `build_master.py` | frozen cohort one-off. NOT the canonical master-workbook builder. |
| `build_master_figure_atlas.py` | DEPRECATED alias, retired v9.7.213-audit. |
| `build_master_figures.py` | Build boss-ready master figure atlas from a Sapote–Mamey workbook. |
| `build_metabolomics_readiness.py` | deterministic writer for the Metabolomics Readiness (MR) deliverable. |
| `build_mibig_index.py` | auto-extract a provenance-tagged architecture-signature INDEX from a |
| `build_mlsa.py` | 5-locus MLSA tree for a whole family's genome set, in one driver. |
| `build_modeb_deepdive.py` | gene-by-gene Mode B deep dives (Sapote deliverable). |
| `build_normalization_matrix.py` | fragmentation-robustness of BGC-class counts across a cohort. |
| `build_novelty_shortlist.py` | composite (multi-signal) novelty shortlist (advisory report). |
| `build_overview_figures.py` | two cohort-level overview figures for Sapote–Mamey. |
| `build_owner_kept_figure_inputs.py` | Build current-data tables and readiness receipts for owner-kept figures. |
| `build_panel_figure.py` | compose a labelled multi-panel figure from existing single-panel PNGs. |
| `build_pangenome.py` | cohort-level BGC family structure and novelty (pan-BGC-ome). |
| `build_pfam_desc_map.py` | extract Pfam NAME->{acc,desc} from a local Pfam-A.hmm into pfam_desc_map.json. |
| `build_phylo_panel.py` | Build a bounded, provenance-rich genome panel for GToTree. |
| `build_placement_ggtree_inputs.py` | the MISSING producer for tools/ggtree_placement.R. |
| `build_priority_leads.py` | highest-confidence lead shortlist across independent evidence axes. |
| `build_punchcard.py` | deterministic literature punch-card, generated IMMEDIATELY |
| `build_reconstruction.py` | clusterblast-scaffolded split-pathway reconstruction. |
| `build_saccharide_triage.py` | separate genuine saccharide products from glycosylation noise. |
| `build_saved_scan_states.py` | Portable extraction of saved package scan context. Never execute a scan. |
| `build_siderophore_atlas.py` | Bounded projection over pinned existing owner databases; never runs searches. |
| `build_size_profile.py` | per-strain BGC nucleotide content by class (Mamey standard module). |
| `build_subset_panel.py` | deterministic cross-cohort / cohort-subset panel (closes DLV-008; drives G2 & G6). |
| `build_tfbs_profile.py` | per-strain transcription-factor binding-site (TFBS) regulator profile. |
| `build_thesis_diagrams.py` | chain-of-events and cause-and-effect diagrams for the thesis chapter. |
| `build_thesis_vignettes.py` | worked thesis vignettes for the Class-A leads. |
| `build_tree.sh` | the ONLY sanctioned way to build a phylogenomic tree in this project. |
| `build_validation_panel.py` | corrected-vs-raw percentile scatter for the external-validation panel. |
| `build_wetlab_matrix.py` | deterministic writer for the Wet-Lab Decision Matrix (WLDM). |
| `build_workbook.py` | canonical master-workbook build orchestrator. |
| `build_workflow_figure.py` | Sapote-Mamey file-structure + data-flow diagram (manuscript Figure 1). |
| `calibration_run.py` | Run the portable Sapote-Mamey detector calibration panel. |
| `candidate_census.py` | file-count and debris census for a candidate cut tree. |
| `check_antismash_profile.py` | cross-profile pooling guard. |
| `check_bgc_naming.py` | portable enforcement of the AS-strain BGC node-naming rule. |
| `check_chatgpt_next_paths.py` | Check ChatGPT handbacks for exactly 8 unique next paths. |
| `check_command_pointers.py` | Phantom-command guard (patch 46). |
| `check_dangling_refs.py` | list references to `examples/<file>` OR tool/module names that don't |
| `check_deliverable_suite.py` | mechanical enforcement of the Sapote full-run deliverable contract. |
| `check_duplicate_dict_keys.py` | fail closed on NEW duplicate dict-literal keys. |
| `check_license_docs.py` | every file granted CC-BY-4.0 in LICENSE-DOCS.txt must actually ship. |
| `check_manifest_contract.py` | Validate a Mamey package against schemas/manifest_contract.json. |
| `check_md_links.py` | verify that local file links in Markdown actually resolve on disk. |
| `check_module_accretion.py` | the module-accretion gate (Round 4 Item 6). |
| `check_monolith_freshness.py` | the monolith is the parent design controller; keep its anchor honest. |
| `check_no_brace_paths.py` | fail if any shipped path contains a '{' or '}' (W2). |
| `check_onboarding_funnel.py` | One-door onboarding-funnel guard (CLAUDE_409_onboarding_funnel_guard). |
| `check_patch_lane.py` | validate patch-lane STRUCTURE and DISPOSITION. |
| `check_provenance_columns.py` | fail if a per-BGC table lacks its provenance anchor. |
| `check_regex_interpolation.py` | fail closed on regex patterns that interpolate an |
| `check_registry_ids_unique.py` | fail if registry inventory IDs collide. |
| `check_release_manifest.py` | verify the bundle's integrity artifacts against the tree itself. |
| `check_requirements_pyproject_sync.py` | freeze the requirements.txt <-> pyproject.toml core-dep drift. |
| `check_schema_drift.py` | check_schema_drift.py  (candidate patch G1) |
| `check_tier_parity.py` | fail-closed parity gate across the four release tiers. |
| `chitin_reference_eval.py` | tools/chitin_reference_eval.py -- operator front door for the whole-genome chitin/GlcNAc |
| `claim_safety_linter.py` | post-hoc claim-safety linter for Sapote interpretive text |
| `cluster_alignment.py` | reference-aligned homolog figures for split-pathway BGCs. |
| `cluster_brief.py` | one-command driver for the comparative chain → a consolidated brief. |
| `cluster_completeness.py` | is a truncated cluster incomplete by assembly, or by biology? |
| `cluster_discovery.py` | find strains carrying a BGC from a diagnostic marker gene. |
| `cluster_gene_compare.py` | gene-by-gene comparison of biosynthetic gene clusters. |
| `cluster_relate.py` | relationship tree + distance matrix from a set of homologous clusters. |
| `cohort_blastp_driver.py` | drive BLASTp + overlay ingest across a scoped set of BGCs. |
| `cohort_concordance_summary.py` | run the fragment-concordance scorer across a multi-strain ledger |
| `cohort_figure_prototypes.py` | Standalone CLI for the extended cohort figure suite (see mamey/cohort_figures_extended.py). |
| `cohort_next_evidence_actions.py` | Private, local next-evidence view. Existing registry reader owns SQLite access. |
| `cohort_scoring_version_gate.py` | fail-closed: a comparative build may only aggregate strains |
| `collapse_query_groups.py` | collapse_query_groups.py <pruned.nwk> <annotation.tsv> <out_prefix> |
| `comparator_discovery.py` | STEP 1 of discover -> download -> analyze (BB09 order). |
| `comparator_select.py` | pick a phylogenomic comparator genome by the 16S method. |
| `compilation_gate.py` | gate a strain compendium markdown/PDF before it can be called |
| `compile_figure_owner_review.py` | Compile human figure decisions into a deterministic, non-rendering action plan. |
| `cross_strain_denominator_audit.py` | fail-closed invariant on cohort-size denominators (v9.7.116). |
| `cut_audit.py` | reproducible sealed-cut audit + card rebase-verify harness. |
| `dark_gene_scan.py` | Dark-gene rescue scanner for edge/FC BGCs. |
| `deliverable_citation_audit.py` | pre-delivery §15 citation + provenance gate for FINISHED deliverables. |
| `determinism_fingerprint.py` | Run and compare the shipped deterministic-extraction control inventory. |
| `domain_phylo_rescue.py` | advisory catalytic-domain-phylogeny corroboration for split-pathway rescue. |
| `domain_prevalence.py` | cohort-wide domain-prevalence + host-filterable widget/figures (v9.7.413). |
| `domain_prevalence_widget.py` | domain_prevalence_widget.py (v9.7.413): host filter + single-strain drill-down + evidence + rare-loci + SVG e… |
| `edge_fasta_export.py` | Export a FASTA of edge-proximal genes for directed BLASTp. |
| `emit_release_sums.sh` | emit_release_sums.sh -- emit SHA256SUMS.txt over the cut tier zips at the release root (PC-04). |
| `encyclopedia_reground_check.py` | mechanize per-volume re-grounding of the Encyclopedia. |
| `evidence_bundle.py` | per-BGC evidence bundle assembled from a SEALED Mamey package (P360-001 / Idea D). |
| `evidence_conservation_audit.py` | finds the 'present in source, dropped in package' bug class. |
| `evidence_disagreements.py` | Run the local evidence review view using this extracted bundle's package. |
| `export_figure_ready.py` | emit tidy, figure-ready CSVs from a Sapote-Mamey master workbook. |
| `extract_cluster.py` | locate and extract a BGC from a RAW genome by its marker genes. |
| `extract_module_core_domains.py` | deterministic module-core aSDomain extractor (P358-003 Idea A.1). |
| `fetch_mibig_reference.py` | turn a MIBiG accession into a reference GBK from the PUBLIC repo. |
| `fetch_reference_cluster.py` | reconstruct a cluster GenBank from the BiG-SCAPE DB or NCBI. |
| `figure_check.py` | HARD pre-render gate for tree FIGURES (the render inputs), sibling to |
| `figure_factory_next.py` | Render receipt-bound aggregate evidence figures from an external data root. |
| `figure_methods.py` | reusable, versioned METHODS-CAPTION library for Sapote-Mamey figure tools. |
| `figure_readiness_board.py` | Report repair-spec binding and figure-receipt readiness states. |
| `file_atlas.py` | describe every Python file in the bundle, from the source, with receipts. |
| `finalize_public_archive.py` | Fail-closed, no-replace final archive transaction. |
| `find_asset.py` | locate a big/shared local asset BEFORE downloading or re-deriving it. |
| `fixture_inputs.py` | Content-preserving preparation of the one hash-bound synthetic test archive. |
| `fragment_concordance_scorer.py` | score a strain's observed BGC fragments against the reference panel. |
| `gate_mutation_probe.py` | Reproducibly answer whether a named test detects a minimal protection mutation. |
| `gen_command_catalog.py` | generate the task-oriented CLI command catalog (v9.7.405). |
| `gen_cut_receipt.py` | generate a cut receipt's file-delta from a machine checksum-diff. Generic. |
| `gen_figure_r_manifest.py` | derive FIGURE_R_MANIFEST.tsv from the Python figure sources. |
| `gen_marker_catalog.py` | generate the marker/cassette catalog FROM the regex backend (W9). |
| `gen_release_manifest.py` | regenerate the volatile fields of RELEASE_MANIFEST.md from live truth. |
| `gen_tier_doc.py` | generate the tier/release explainer FROM the release-state record. Generic. |
| `gen_tools_inventory.py` | list every tool, so nobody rebuilds one that exists (W22-adjacent). |
| `gen_user_catalog.py` | generate the USER-FACING cassette + scan catalogs (v9.7.86 B4). |
| `gene_assembly_line.py` | gene_assembly_line.py -- reliable PER-GENE NRPS/PKS assembly-line parser for antiSMASH region GBKs. |
| `gene_modeb_enrichment.py` | gene_modeb_enrichment.py -- gene-level assembly-line block for a Mode B card, floors enforced. |
| `gene_topology.py` | antiSMASH-style gene-arrow topology figures from antiSMASH region GBKs. |
| `generate_bgc_atlas.py` | browsable HTML atlas of one strain's BGC inventory (deliverable G1). |
| `generate_deliverables_menu.py` | Generate or verify the registry-backed Sapote-Mamey Diner Menu. |
| `generated_surface_ownership.py` | fail-closed, check-only cut-surface planner. |
| `graft_integrity.py` | Read-only metric checks and transactional gappa graft generation. |
| `gtotree_env.sh` | canonical environment for a GToTree/IQ-TREE phylogenomic run. |
| `harvest_16s.py` | assemble the 16S inputs for a per-genus EPA-ng placement, ALL FROM LOCAL DATA. |
| `hub_merge.py` | one-shot hub merge: ingest → schema-gate → normalize → merge → verify. |
| `ingest_blastp_rollups.py` | fold the per-strain DATED rollup CSVs into blastp.sqlite. |
| `ingest_package.py` | map a Mamey package into the cohort banked-JSON entries. |
| `ingest_swissprot_local.py` | fold the local SwissProt BLASTp CSVs into blastp.sqlite. |
| `input_manifest.py` | the "no wrong / no half files" guard (portable, stdlib only). |
| `intake_harness.py` | multi-strain intake for Sapote-Mamey with performance metrics. |
| `kcb_confidence.py` | extract antiSMASH's per-region KnownClusterBlast "Similarity Confidence" |
| `ks_burden_table.py` | Build a package-native KS-burden TSV and hash-bound receipt. |
| `lab_office_render.py` | the Lab Office "make-report" entry point (batch figure rendering). |
| `lead_board.py` | the per-strain ranked Lead Board (single source of truth). |
| `lead_propagation_gate.py` | does every triage-board lead reach every lead-listing surface? |
| `llm_trustworthiness.py` | "Is the LLM being trustworthy right now?"  (candidate module, v1 — F02 rework) |
| `locator_reconciliation.py` | verify a Mode B card's header fields match the canonical |
| `log_release.py` | append one row to RELEASES_LOG.md for the current build (idempotent). |
| `make_public_tier.sh` | cut a clean release tier from the working tree, deterministically. |
| `make_release_tarball.sh` | cut-time packaging artifact (v9.7.400, BC/Amber-fork proposal). |
| `mamey_habitat_map.py` | build the strain->habitat map L5/L6 need, store-backed. |
| `mamey_intake.py` | one-command intake for Mamey package outputs. |
| `mamey_package_qa_v2.py` | Mamey per-strain package completeness validator |
| `mamey_pipeline.py` | single-entry Lab Office pipeline (the "working program" cohesion piece). |
| `marker_candidate_search.py` | find NCBI comparator genomes for an AS strain by |
| `materialize_strain_data.py` | one-time staging tool for the canonical |
| `md_to_docx.sh` | Word deliverable via pandoc (no LaTeX required). |
| `md_to_pdf.sh` | md_to_pdf.sh IN.md OUT.pdf [boss|technical] |
| `merge_workbooks.py` | merge_workbooks.py  (candidate patch M1) |
| `mibig_neighborhoods.py` | cluster MIBiG reference domains of one family into "neighborhoods", pick one |
| `mlsa_outgroup_scan.py` | build the same MLSA panel rooted on several candidate |
| `modeb_card_diff.py` | Report current-package facts that would change a stored Mode B card. |
| `modeb_card_guard.py` | the check that would have caught 2026-08-17. |
| `modeb_evidence_gate.py` | deterministic Mode B evidence-governance gate (v9.7.354). |
| `npatlas_provision.py` | tools/npatlas_provision.py -- operator front door for user-provisioned NP Atlas ingestion |
| `nrps_substrate.py` | nrps_substrate.py -- predicted peptides + antibiotic-class signatures from A-domain substrates. |
| `outgroup_registry.py` | the "outgroup generator": genus -> a decided, reproducible outgroup. |
| `parked_card_audit.py` | flag patch-pool cards that silently fell out of the cut cadence. |
| `patch_packet_preflight.py` | Fail closed when a patch packet contains workspace, cache, or evidence bloat. |
| `patch_queue_composition_audit.py` | advisory pre-composition audit of a patch queue. |
| `phylo_autopilot.py` | one front door for "upload 16S and/or genomes -> gated trees". |
| `phylo_place.py` | reference-backbone phylogenetic PLACEMENT of query 16S (or protein) sequences. |
| `phylo_postflight.py` | validate a FINISHED tree before it becomes a figure. |
| `phylo_preflight.py` | validate a planned phylogenomic tree BEFORE spending CPU. |
| `phylo_refset.py` | build a RIGHT-SIZED, DE-DUPLICATED 16S reference set for phylogenetic placement. |
| `phylo_roster.py` | number the strains in a tree or panel, and edit them by number. |
| `pks_product_class.py` | pks_product_class.py -- predict polyketide product class from per-module reductive loops. |
| `placement_figure.py` | a paper-ready companion figure from a phylogenetic-placement grafted tree. |
| `placement_to_docx.py` | assemble phylogenetic-placement figures + their methods captions into a Word doc. |
| `plan_gtotree_iqtree.py` | Plan and inspect a bounded GToTree -> IQ-TREE workflow without running it. |
| `plot_examples.py` | reference figures built ONLY from the figure_ready/ tidy CSVs. |
| `preflight_zip_hygiene.py` | scan a built release ZIP for packaging-hygiene violations. |
| `prepare_biosynthetic_tree_inputs.py` | Prepare provenance-rich PKS/RiPP sequence pools without running a tree. |
| `preview_figure_components.py` | Write the static Figure Factory component gallery without network access. |
| `preview_figure_themes.py` | CLI wrapper for the portable Sapote-Mamey figure-theme gallery prototype. |
| `professionalism_linter.py` | post-hoc "professionalism" check for Sapote interpretive text |
| `project_catalog.py` | Operate the portable, hash-bound project catalog without the UI. |
| `prune_neighbors_from_tree.py` | pick each query strain's nearest reference |
| `public_release_audit.py` | FAIL-CLOSED audit of a tree destined for the public GitHub release. |
| `query_support_table.py` | query_support_table.py <placement_dir> <refpkg_dir> <out.tsv> |
| `rank_clusterblast_phylo_candidates.py` | Rank ClusterBlast-derived candidate comparator assemblies for phylogenomics. |
| `reaction_gap_board.py` | Build a private offline RG-GMCI review view using the retained semantic reader. |
| `realistic_bgc_count.py` | distinct-loci BGC count (advisory report). |
| `reclass_check.py` | antiSMASH label vs. diagnostic-domain discrepancy (lead L1). |
| `redact_public_tier.py` | CAS-safe SID + AS strain-identifier redaction for PUBLIC bundle tiers. |
| `reference_bgc_structural_validator.py` | Measure a curated, exact-bound reference-BGC panel with Mamey. |
| `reference_panel_ledger.py` | characterize the detection panel by separating OBSERVED from COMPUTED. |
| `regen_modeb_contract_docs.py` | regenerate Mode B contract docs from the JSON. |
| `register_compute_output.py` | the formal "register after running" step for heavy compute. |
| `relabel_and_render.py` | Relabel GToTree tip names from genome FASTA headers to a consistent |
| `release.sh` | single fail-closed build entrypoint for a Sapote-Mamey release (v9.7.97). |
| `release_cut.sh` | one-command, gate-enforced release cut. |
| `remediate_phantom_locus.py` | find and excise fabricated locus citations from authored Mode B cards. |
| `render_activity_lead_reports.py` | the Day-5-shaped activity-lead deliverable. |
| `render_all.py` | Render a built GToTree/IQ-TREE tree with publication-ready tip labels. |
| `render_bootstrap_contract.py` | Render/check assistant bootstrap docs from bootstrap_contract.yml. |
| `render_clean_tree.py` | Shared clean renderer for the GToTree 138-SCG core-genome ML trees. |
| `render_dapr_boards.py` | render the DAPR antibacterial/antifungal boards and the |
| `render_deliverable_pdf.py` | Compatibility CLI for the package-scoped ``mamey.markdown_pdf`` renderer. |
| `render_siderophore_atlas.py` | Render a pinned atlas snapshot into a standalone local evidence drawer. |
| `render_three_channel_evidence_matrix.py` | Render the static three-channel evidence matrix from generic JSON or TSV. |
| `repo_health.py` | one-command repo-health gate for the Sapote-Mamey bundle. |
| `reroot_postflight_receipt.py` | Reroot a Newick tree on one exact tip and emit a deterministic postflight receipt. |
| `rewrite_release_identity.py` | Rewrite cut-time bundle/build identity without platform-specific ``sed -i``. |
| `rggmci_cohort_rollup.py` | cross-strain RG-GMCI ranked rollup + confidence tiering (v9.7.117). |
| `round_ledger.py` | verify a Mode B card and append one audit row to the round ledger. |
| `run_chatgpt_surrogate_gate.py` | Fast ChatGPT surrogate release gate for Sapote--Mamey. |
| `run_comparator_antismash_ingest.py` | Run comparator antiSMASH/GBK ingest. |
| `run_directed_pks_study.py` | Run Directed PKS Study Mode from a source CDS CSV and JSON spec. |
| `run_efls_rewire.py` | Run EFLS Rewire from a Pre-Sapote Lite gene evidence table. |
| `run_planned_tree.py` | Execute an APPROVED GToTree -> IQ-TREE -> sign-off -> (optional) fastANI phylogenomics run. |
| `sapote_judgment_receipt.py` | write-back artifact that makes gold_completeness verifiable. |
| `sapote_md_preflight.py` | Preflight Markdown before PDF rendering. |
| `sapote_workflow.py` | CLI shim for the mandatory Sapote workflow driver. |
| `scan_cctt_class_compat.py` | cohort-wide CCTT-trigger vs product-class compatibility scan (N-05/A-04). |
| `scan_marker_census.py` | Emit a line-addressable census of registry-backed and inline scan markers. |
| `scan_prevalence.py` | cohort prevalence for mamey keyword-scan DBs (resistance/regulator/ |
| `scan_registry_parity.py` | Prove that registry-backed source scans match the literal fallback. |
| `schema_deployed_audit.py` | reconcile the coded sheets in WORKBOOK_SCHEMA.md against what the |
| `scope_cluster.py` | scope an over-merged antiSMASH region to its TRUE protocluster. |
| `seal_sweep.py` | seal_sweep.py  (candidate patch F10) |
| `seed_reference_library.py` | Seed mamey/data/reference_bgc_library.json from the validated reference set. |
| `session_checklist.py` | Render a session-close checklist from a governed, portable durability root. |
| `session_cost_audit.py` | where did a chat's tokens actually go? |
| `signoff_check.py` | the "would a master's student sign off?" gate, mechanised. |
| `strain_bigscape_report.py` | strain_bigscape_report.py -- per-strain BiG-SCAPE report as a standard Sapote-Mamey deliverable. |
| `strict_source_disclosure_audit.py` | COMPATIBILITY ENTRY POINT. Holds no policy. |
| `sync_version.py` | propagate the single source-of-truth version into restated files. |
| `test_reaction_gap_board.py` | (no docstring) |
| `tier_vocabulary.py` | the single owner of release-tier names, zip labels and aliases. |
| `topology_scan.py` | detect inverted (non-co-directional) BGC strand-block topology and |
| `tracked_file_policy.py` | Single source of truth for the tier tracked-file policy (NC-001/002/003). |
| `tree_bgc_overlay.py` | Hash-bound Figure Factory consumer for existing MLSA/GToTree IQ-TREE outputs. |
| `tree_heatmap_panel.py` | CLI front door for the tree-aligned heatmap panel (mamey.tree_heatmap_panel). |
| `tree_overlay_figure.py` | ONE tree, MANY overlay matrices. |
| `tree_sanity_check.py` | HARD pre-render gate. A tree must PASS this before it is rendered or shown. |
| `validate_portfolio_config.py` | Validate and bind a portable multi-strain project configuration to its project_registry.py |
| `validate_portfolio_registry.py` | Validate portable strain privacy and evidence registries without running Mamey. |
| `validate_timing_receipt_parity.py` | compare timing phases to run_phase_receipts.jsonl. |
| `verify_release_identity.py` | fail-closed release identity + LLM bootstrap freshness gate. |
| `verify_tier_derivation.py` | assert that a public tier is an exact redaction-view |
| `workflow_status.py` | Workflow status: where each strain sits in the pipeline. Emits a stage-matrix CSV + an SVG progress graphic. |
| `zip_hygiene_allowlist.py` | a checksum/path-bound allowlist for intentionally-large shipped files. Generic. |
| `../bootstrap.sh` | set up the Sapote-Mamey runtime + test deps in one command (W18). |

**Additional engine-internal CLI (in `mamey/`, not auto-inventoried):**

| Tool | What it does |
|---|---|
| `mamey/workbook_schema_check.py` | Workbook schema validator. Run: `python -m mamey.workbook_schema_check [--fast|--full] [--v12] <workbook.xlsx>`. Returns PASS/FAIL JSON; exit 0 = PASS. Lives in `mamey/` so not picked up here (C3 fix). |
