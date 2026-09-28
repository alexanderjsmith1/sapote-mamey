# Current Docs Index — v9.7.444 · engine 1.9.171 · build 20260929v97444a

Start with [README](README.md), then [Your first analysis](docs/MASTER_WALKTHROUGH.md).
For an existing package use [Read your results](docs/READING_YOUR_RESULTS.md).
The [Quick Guide](docs/GUIDE/02_Quick_Guide.md) is the compact and advanced command reference. [AGENTS](AGENTS.md) is the canonical portable coding-assistant contract. Its
generated `CLAUDE.md` copy supports Claude discovery; other assistants must be directed to AGENTS
or receive it through their supported instruction mechanism.

## Operating guides

- [Companion Tool Guide](docs/COMPANION_TOOL_GUIDE.md): standalone use, inputs/outputs and actual integration roles.

- [Runtime profiles](docs/ASSISTANT_RUNTIME_PROFILES.md): environment-dependent limits and migration from hosted sessions.

- [Working with an assistant](docs/ASSISTANT_USER_GUIDE.md): choose inputs, task scope, evidence and completion criteria.
- [Assistant governance](docs/ASSISTANT_GOVERNANCE.md): scope, permissions and conflict rules for project workflows.

- [Installation](docs/INSTALL.md), [prerequisites](docs/PREREQUISITES.md), and
  [external assets](docs/EXTERNAL_DATA.md): environment setup and separately supplied data.
- [User manual](docs/GUIDE/01_User_Manual.md): running analyses and reading outputs.
- [Command catalog](docs/COMMAND_CATALOG.generated.md) and [deliverable menu](docs/DELIVERABLE_MENU.md):
  generated command and capability navigation. The menu is maintained by the deliverables registry.
- [Glossary](docs/GLOSSARY.md): canonical reader-facing terms.
- [Methods implementation template](docs/templates/MANUSCRIPT_METHODS_IMPLEMENTATION_TEMPLATE.md) and
  [reporting checklist](docs/METHODS_REPORTING_CHECKLIST.md): prospective, claim-safe manuscript authoring aids;
  their presence does not assert that a study or module was run.
- [Mode B authoring](wiki/Mode-B-Gene-First-and-48-Section-Manual.md): use the selected machine-readable
  profile and its emitted template; legacy section counts do not replace a named current profile.
- [BLASTp evidence](docs/ONLINE_BLASTP_PROTOCOL.md): existing results first (rollups to reservoir; trove to package overlay; HitTable to workbook), optional live submission.
- [BiG-SCAPE cohort walkthrough](docs/BIGSCAPE_COHORT_WALKTHROUGH.md) and [troubleshooting](docs/troubleshooting/BIGSCAPE_TROUBLESHOOTING.md): stage region files, run a cohort, inspect family verdicts and figures.
- [BiG-SCAPE cohort networks and comparator context](docs/BIGSCAPE_COHORT_NETWORK_GUIDE.md): exact-identity cohort tables, evidence badges and citations, overmerged-region component metrics, interactive/static figures, and additive batch report enrichment.
- [Phylogenetic workflow](docs/PHYLO_AUTOPILOT_WORKFLOW.md), [placement](docs/PHYLO_PLACEMENT_WORKFLOW.md),
  and [companion tools](docs/LLM_COMPANION_TOOL_PROTOCOL.md): inputs, resource scope and run receipts.
- [Figure house rules](docs/FIGURE_HOUSE_RULES.md): the rules every figure meets (format, caption and methods, page wording, material labels, provenance) and what checks each one.
- [Figure rendering](docs/FIGURE_FACTORY_NEXT.md) and [figure preflight](wiki/Figure-Factory-Preflight-and-Methods-Manual.md):
  actual input contracts, output sidecars and renderer-specific limits.
- [Bioassay Figure Factory](docs/BIOASSAY_FIGURE_FACTORY.md): typed plate, material, replicate,
  target, time-point, control, exclusion, and R-rendering contract.
- [R figure workflows](docs/R_FIGURE_WORKFLOWS.md): current ggplot2/ggtree renderer map and the
  admitted bioassay-to-tree path.
- [Optional pairwise comparison](sapote_addons/README_OFFLINE_ANALYSIS.md) and
  [optional hooks](docs/OPTIONAL_HOOKS.md): specialized capabilities with their own setup.
- [Resources](resources/README.md) and [validation records](validation/README.md): data purpose,
  consumers and historical evidence boundaries.

The [Master Walkthrough](docs/MASTER_WALKTHROUGH.md) connects installation to validated outputs;
[prerequisites](docs/PREREQUISITES.md) distinguish Python extras, external tools and datasets.

## Tool and contract pages

These pages document shipped tools, commands and contracts. They were not linked from here before.

- [Optional external AB/AF activity-prediction channel](docs/AB_AF_EXTERNAL_ACTIVITY_CHANNEL.md)
- [BGC functional logic workup](docs/BGC_FUNCTIONAL_LOGIC_WORKUP.md)
- [Bioactivity Metadata Contract](docs/BIOACTIVITY_METADATA_CONTRACT.md)
- [Bioassay activity-channel workflow — where it sits](docs/BIOASSAY_ACTIVITY_CHANNEL_WORKFLOW.md)
- [Whole-genome chitin/GlcNAc reference-capacity evaluation](docs/CHITIN_REFERENCE_EVALUATION.md)
- [Clear Match Finder](docs/CLEAR_MATCH_FINDER.md)
- [cluster_completeness — assembly truncation vs biological absence](docs/CLUSTER_COMPLETENESS.md)
- [cluster_discovery — find strains carrying a BGC from a diagnostic marker](docs/CLUSTER_DISCOVERY.md)
- [cluster_gene_compare — gene-by-gene BGC comparison as a real deliverable](docs/CLUSTER_GENE_COMPARE.md)
- [cluster_relate — relationship tree + distance matrix from homologous clusters](docs/CLUSTER_RELATE.md)
- [ClusterBlast-derived phylogeny candidate ledger](docs/CLUSTERBLAST_PHYLO_CANDIDATES.md)
- [Cohort pack interface (external, operator-supplied, Git-ignored)](docs/COHORT_PACK_INTERFACE.md)
- [Cohort protein comparison contract for Mode B](docs/COHORT_PROTEIN_COMPARISON_MODEB_CONTRACT.md)
- [Definitive BGC prioritization ranker](docs/DEFINITIVE_BGC_RANKER.md)
- [BGC-machinery domain-tree contract](docs/DOMAIN_TREE_CONTRACT.md)
- [Enzyme neighborhood explorer](docs/ENZYME_NEIGHBORHOODS.md)
- [Gene evidence disagreement review candidate](docs/EVIDENCE_DISAGREEMENTS_CANDIDATE.md)
- [extract_cluster — bring a raw genome into the pipeline](docs/EXTRACT_CLUSTER.md)
- [F13 BGC domain-count PCA source-artwork contract](docs/F13_BGC_DOMAIN_PCA.md)
- [fetch_reference_cluster — reference/cohort cluster GBKs, as a shared step](docs/FETCH_REFERENCE_CLUSTER.md)
- [Figure owner-review workflow](docs/FIGURE_OWNER_REVIEW_WORKFLOW.md)
- [Figure Factory owner-review queue](docs/FIGURE_REVIEW_WORKFLOW.md)
- [Bounded GToTree panel selection](docs/GTOTREE_PANEL_SELECTION.md)
- [Lab Quest: governed optional local interface](docs/LAB_QUEST.md)
- [Literature atlas current-evidence refresh](docs/LITERATURE_ATLAS_CURRENT_EVIDENCE_REFRESH.md)
- [Locus-map review contract](docs/LOCUS_MAP_REVIEW_CONTRACT.md)
- [Locus map v8](docs/LOCUS_MAP_V8.md)
- [FA6 — Mode B card exporter (modeb-export)](docs/MODEB_EXPORT_HOOK.md)
- [Mode B gene-first exploration](docs/MODEB_GENE_FIRST_EXPLORATION.md)
- [RATIFIED status vocabulary — Sapote-Mamey Mode B (the Developer or User ratification 2026-08-21)](docs/MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md)
- [NPBDetect optional-adapter guard](docs/NPBDETECT_ADAPTER_GUARD.md)
- [Outgroup generator + right-sized reference sets (outgroup_registry.py, phylo_refset.py)](docs/OUTGROUP_AND_REFSET_WORKFLOW.md)
- [Owner-kept Figure Factory inputs](docs/OWNER_KEPT_FIGURE_INPUTS.md)
- [Spec — Cohesive Per-BGC Report (L0–L3) + Comparison Matrix](docs/PER_BGC_REPORT_CARD_SPEC.md)
- [TROUBLESHOOTING — EPA-ng placement + phylo tooling (Eggplant, 2026-09-06)](docs/PHYLO_TROUBLESHOOTING.md)
- [PKS ketosynthase-tree option guide](docs/PKS_KS_TREE_OPTIONS.md)
- [Portable evidence-workspace interface](docs/PORTABLE_EVIDENCE_WORKSPACE.md)
- [Portable strain privacy and evidence registry](docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md)
- [Prevalence workflow — where it sits](docs/PREVALENCE_WORKFLOW.md)
- [Portable project data home](docs/PROJECT_DATA_HOME.md)
- [Sapote-Mamey Naming Contract](docs/PROJECT_NAMING.md)
- [Exact-bound reference-BGC structural validator](docs/REFERENCE_BGC_STRUCTURAL_VALIDATOR.md)
- [Reporting v2 — per-gene MIBiG convergence & structured antiSMASH tables](docs/reporting_v2_mibig_convergence.md)
- [RG-GMCI complementary-rescue atlas](docs/RGGMCI_RESCUE_ATLAS.md)
- [RiPP tree and sequence-network option guide](docs/RIPP_TREE_OPTIONS.md)
- [Sapote Markdown authoring contract](docs/SAPOTE_MARKDOWN_AUTHORING_CONTRACT.md)
- [Sapote-Mamey report theme](docs/SAPOTE_REPORT_THEME.md)
- [scope_cluster — scope an over-merged antiSMASH region to its true protocluster](docs/SCOPE_CLUSTER.md)
- [Screening exploration with ggplot2](docs/SCREENING_EXPLORATION_R.md)
- [Strain BiG-SCAPE report + figure-label convention (v9.7.293)](docs/STRAIN_BIGSCAPE_REPORT.md)
- [Strain-level BGC logic reports](docs/STRAIN_LEVEL_BGC_LOGIC.md)
- [Token-light Sapote document factory](docs/TOKEN_LIGHT_DOCUMENT_FACTORY.md)
- [Read only tool database inspection](docs/TOOL_DATABASE_INSPECTION.md)
- [Two-stage modular BGC reports](docs/TWO_STAGE_MODULAR_BGC_REPORTS.md)
- [Phylogenetic workflow gate guide](docs/WORKFLOW_GATES_GUIDE.md)

## Reference, development and history

[Guide navigation](docs/GUIDE/00_README.md) distinguishes the operational guides from the dated
Encyclopedia and newsletter. A current bundle stamp identifies packaging; it does not prove that
every scientific statement or historical experiment was revalidated for that cut.

[Engine reference](docs/reference/00_README.md) and [Encyclopedia currency](wiki/Encyclopedia-Currency.md)
record reference scope. Consult current code and named schemas for numerical behavior.
[Methods technical appendix](docs/reference/METHODS_TECHNICAL_APPENDIX.md) records release-sensitive
parameters and failure-state semantics. The developer-facing
[implementation source map](docs/development/METHODS_IMPLEMENTATION_SOURCE_MAP.md) is regression-tested
against current implementation and test paths.
[Figure repair records](docs/figure_factory/README.md), `docs/working/`, `docs/release_planning/`,
and `docs/patch_notes/` are engineering records, not an alternative user setup sequence.

[History](docs/history/README.md) and the [changelog](CHANGELOG.md) preserve dated decisions. The changelog is the
complete per-cut record. [RELEASES_LOG](RELEASES_LOG.md) is a partial build-stamp table (see its header). Historical commands, counts, results and proposed features in those records
are not current operating instructions. `docs/QUICK_GUIDE.md` is superseded by the Quick Guide above;
`docs/user_guides/comprehensive_glossary.md` and `sapote_mamey_wheel_glossary.md` are retained snapshots.
`docs/user_guides/` now holds `operational_reference.md`, `tools_reference.md`, `sapote_kernel_guide.md`,
`development_issues_compendium.md`, the two math references, and those two retained glossary snapshots;
the former cross-chat documentation protocol is archived under `docs/history/`.

## Maintaining this index

Update links when the owning workflow changes. Keep generated command, capability, version and
release surfaces under their existing generators. Review document content before claiming currency;
do not turn a version-stamp update into a claim of a full content review.

## Practical help

- [Find the right document](docs/DOCUMENTATION_MAP.md)
- [Troubleshooting](docs/COMMON_MISTAKES.md)
- [Files, storage and handoff](docs/FILES_STORAGE_AND_HANDOFF.md)

- [Mode B user walkthrough](docs/MODE_B_USER_WALKTHROUGH.md): actual profile boundaries, commands and all 50 requirements.
