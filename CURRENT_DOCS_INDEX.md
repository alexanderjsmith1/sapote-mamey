# Current Docs Index — v9.7.459 · engine 1.9.177 · build 20261027v97459a

Each listed entry starts with its status. The status is `current` (follow it for new work), `reference` (background, specifications or dated examples; check current code before relying on a number) or `experimental` (report-only, not a release gate). An unlisted page may be current or historical; check its banner and the [maintenance inventory](docs/MAINTENANCE_INVENTORY.generated.md).

## Start with what you have

- `current` **Choose your starting file:** [Start with your file](docs/READER_START_HERE.md)
  distinguishes software, antiSMASH input and a saved result.
- `current` **Prepare inputs and the environment:** [Inputs and setup](docs/reader/02_INPUTS_AND_SETUP.md)
  identifies the program, input and output locations and the prerequisites for your selected task.
- `current` **Extract one supplied antiSMASH ZIP:** [Your first extraction](docs/reader/01_FIRST_RUN.md)
  gives the compact recipe and separate package/workbook checks. The
  [Master Walkthrough](docs/MASTER_WALKTHROUGH.md) remains the longer reference for assistant requests and options.
- `current` **Read an existing Complete_Package ZIP:** [Read one saved package](docs/reader/03_READ_RESULTS.md)
  starts with saved evidence before considering a rerun; [Reading your results](docs/READING_YOUR_RESULTS.md)
  explains the fields in more detail.
- `current` **Recover an incomplete attempt:** [Recovery and limits](docs/reader/04_RECOVERY_AND_LIMITS.md)
  preserves the attempt and routes by symptom.
- **Another task:** use [Choose a task](docs/USER_TASK_ROUTER.md) to find its inputs and owning guide.

Use the [Quick Guide](docs/GUIDE/02_Quick_Guide.md) as a compact command reference after choosing
your route. For a figure handoff, start with [Make and review figures](docs/FIGURES_START_HERE.md),
then use [Evidence to report](docs/EVIDENCE_TO_REPORT.md) for captions and short findings/Methods facts.
[AGENTS](AGENTS.md) is the shared coding-assistant contract; generated `CLAUDE.md` supports Claude discovery.
Other assistants need AGENTS through their supported instruction mechanism.

- `current` [Data home](docs/DATA_HOME.md): where results live, the inbox route into the Strain Master, how to find data before making any, and the self-check.
- `current` [Choose a task](docs/USER_TASK_ROUTER.md): named human requests, required inputs, owning guides and completion evidence; [JSON routes](docs/USER_TASK_ROUTER.json) for assistants.

## Operating guides

- `current` [Citation-compact report readers](docs/CITATION_COMPACT_READERS.md): template substitutions, citation preservation, sequential writes and structural QA limits.

- `current` [HTML template readers](docs/HTML_TEMPLATE_READERS.md): owning builders, browser/server routes, output writes and recovery boundaries.
- `current` [Structured domain/motif sidecar readers](docs/STRUCTURED_DOMAIN_MOTIF_EXTENSION.md): source admission, partial-output recovery and receipt scope.

- `current` [Use the large Sapote reference guides](docs/GUIDE/07_LARGE_REFERENCE_ENTRY.md): navigation, version differences and historical/deprecated sections.

- `current` [Bundle metadata and integrity readers](docs/BUNDLE_METADATA_READERS.md): versions, checksum/membership scope, accretion baseline and required-artifact holds.

- `current` [Immutable package readers](docs/POSTSEAL_READERS.md): external report destinations and source-bound BiG-SCAPE staging.
- `current` [Companion provisioning and retrieval controls](docs/447_COMPANION_RETRIEVAL_CONTROLS.md): clone installations, scanner subsets, optional R, protein input admission and RID checkpoints.
- `current` [Cohort bank transactions](docs/COHORT_BANK_TRANSACTIONS.md): schema admission, coherent readers and explicit interrupted-write recovery.

- `current` [Companion Tool Guide](docs/COMPANION_TOOL_GUIDE.md): standalone use, inputs/outputs and integration roles.
- `reference` [JGI public reference context](docs/SMC_PUBLIC_REFERENCE_CONTEXT.md): historical IMG-ABC provenance and optional manual SMC references; automated retrieval is not implemented.
- `current` [Companion run contracts](docs/COMPANION_RUN_CONTRACTS.md): planner, runner and placement receipts and writes.
- `current` [Multi-Cohort Comparison Toolkit](deliverable_tools/README.md): named roster/dossier/cohort tools, per-tool dependencies and writes.
- `current` [Examples index](examples/README.md): fixtures and illustrative or historical evidence, with current source contracts.
- `current` [Project catalog and private handoff](docs/PROJECT_CATALOG.md): manifest-bound package locations, write behavior and partial-archive/import recovery.
- `current` [Deliverable queue](docs/DELIVERABLE_QUEUE.md): discovery states, package mutations, resume binding and per-strain recovery.
- `current` [Deliverable request templates](deliverables/README.md): supplied inputs, complete identity, bounded authoring and conversion contracts.
- `current` [Catalog reading and maintenance](docs/CATALOG_MAINTENANCE.md): generated owners, check scope and source-help limitations.
- `current` [Maintenance inventory](docs/MAINTENANCE_INVENTORY.generated.md): scoped command, optional-tool, generated-surface and document owners; explicit review holds and rebuild rules. [Machine records](docs/MAINTENANCE_INVENTORY.generated.json) use the same source declarations.
- `current` [Master workbook validation](docs/WORKBOOK_VALIDATION.md): deployed schema, fast/full scope, roster/hash checks and retained freeze discrepancies.

- `current` [Optional Barrnap](docs/BARRNAP.md): rRNA recipe versus execution, version/model checks and external setup.

- `current` [Runtime profiles](docs/ASSISTANT_RUNTIME_PROFILES.md): environment-dependent limits and migration from hosted sessions.

- `current` [Working with an assistant](docs/ASSISTANT_USER_GUIDE.md): choose inputs, task scope, evidence and completion criteria.
- `current` [Assistant governance](docs/ASSISTANT_GOVERNANCE.md): scope, permissions and conflict rules for project workflows.

- `current` [Installation](docs/INSTALL.md), [prerequisites](docs/PREREQUISITES.md), and
  [external assets](docs/EXTERNAL_DATA.md): environment setup and separately supplied data.
- `current` [User manual](docs/GUIDE/01_User_Manual.md): running analyses and reading outputs.
- `current` [Command catalog](docs/COMMAND_CATALOG.generated.md) and [deliverable menu](docs/DELIVERABLE_MENU.md):
  generated command and capability navigation. The menu is maintained by the deliverables registry.
- `current` [Glossary](docs/GLOSSARY.md): canonical reader-facing terms.
- `current` [Methods implementation template](docs/templates/MANUSCRIPT_METHODS_IMPLEMENTATION_TEMPLATE.md) and
  [reporting checklist](docs/METHODS_REPORTING_CHECKLIST.md): prospective, claim-safe manuscript authoring aids;
  their presence does not assert that a study or module was run.
- `current` [Manuscript revision workflow](docs/MANUSCRIPT_REVISION_WORKFLOW.md): notes, reviewer findings and answers in one
  Word ledger; asks-only rounds; staged edits checked, applied and logged with `tools/manuscript_revision.py`.
- `current` [Mode B authoring](wiki/Mode-B-Gene-First-and-48-Section-Manual.md): use the selected machine-readable
  profile and its emitted template; legacy section counts do not replace a named current profile.
- `current` [Mode B contract current50 v2](docs/MODEB_CURRENT50_V2_CONTRACT.md): the 50-section card with GECCO (§22), the contigs rescued into the BGC (§26), literature with relevance (§48–§49) and the data evidence table last (§50); `emit-modeb-template --contract current50_v2` and `verify-modeb --contract current50_v2`.
- `current` [Mode B expanded locus](docs/MODEB_EXPANDED_LOCUS.md): independently source-bound CDS inventories and bounded supported-anchor context; use `--require-expanded-locus` for an expanded work order. Core membership remains separate.
- `current` [Mode B gap-rescue reader](docs/MODEB_GAP_RESCUE_READER.md): supplied rescue context and existence checks; this does not adopt rescued genes into a locus.
- `current` [Mode B evidence availability and writing](docs/MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md): pre-authoring inventory, typed binding/freshness states, planner limits and the independently reviewed finished-card evidence matrix.
- `current` [Mode B profiles](docs/MODEB_PROFILE_MATRIX.md): which card is which (scaffold, candidate, finished §1–§48, opt-in current50 v2), with each profile's producer, verifier and the status it can claim. "Full Mode B" means the selected finished profile.
- `current` [Mode B user walkthrough](docs/MODE_B_USER_WALKTHROUGH.md): actual profile boundaries, commands and all 50 requirements.
- `reference` [Mode B exemplar reader guide](docs/reference/modeb_exemplars/README.md): historical class sketches and a 48-section format reference. Use the example register to identify their scope; their locus-specific evidence and old pass labels do not validate a current 50-section finished card.
- `current` [BLASTp evidence](docs/ONLINE_BLASTP_PROTOCOL.md): existing results first (rollups to reservoir; trove to package overlay; HitTable to workbook), optional live submission.
- `current` [antiSMASH strictness and pooling](docs/ANTISMASH_PROFILE.md): recorded profile evidence, mismatch states and the selected-package pooling guard.
- `current` [antiSMASH web submission](docs/ANTISMASH_WEB_SUBMISSION_SOP.md): the procedure for sending reference genomes to the public antiSMASH server; light-touch queue rule, loose with all 11 features, no email, one authorized batch at a time.
- `current` [BiG-SCAPE cohort walkthrough](docs/BIGSCAPE_COHORT_WALKTHROUGH.md) and [troubleshooting](docs/troubleshooting/BIGSCAPE_TROUBLESHOOTING.md): stage region files, run a cohort, inspect family verdicts and figures.
- `current` [BiG-SCAPE cohort networks and comparator context](docs/BIGSCAPE_COHORT_NETWORK_GUIDE.md): exact-identity cohort tables, evidence badges and citations, overmerged-region component metrics, interactive/static figures, and additive batch report enrichment.
- `current` [Strain slides](docs/STRAIN_SLIDES.md): one deck per strain from a sources file. Each deck has the complete region inventory and gene tables. Selected region slides (with explicit omission rules) carry the gap-rescue map, gene strip, GECCO, RG-GMCI two-proof, BiG-SCAPE and BLASTp lines, GECCO-only candidates and a gene-table appendix. The deck also has protein PCoA panels per strain.
- `current` [Local 16S database](docs/LOCAL_16S_DATABASE.md): build the NCBI 16S type-strain BLAST database fully or for chosen genera, the optional SQLite store, and the shared lookup every 16S tool uses.
- `current` [Isolate neighborhood panel](docs/NEIGHBOUR_PANEL_16S_TYGS.md): one isolate's genome panel from its 16S BLAST hits on complete genomes, the NCBI genome table (`datasets`) and its TYGS closest type strains (`tools/neighbour_panel_candidates.py`; check with `tools/check_tygs_coverage.py`).
- `current` [Phylogenetic workflow](docs/PHYLO_AUTOPILOT_WORKFLOW.md), [placement](docs/PHYLO_PLACEMENT_WORKFLOW.md),
  and [companion tools](docs/LLM_COMPANION_TOOL_PROTOCOL.md): inputs, resource scope and run receipts.
- `current` [Figure house rules](docs/FIGURE_HOUSE_RULES.md): the rules every figure meets (format, caption and methods, page wording, material labels, provenance) and what checks each one.
- `current` [Aggregate evidence-coverage figures](docs/FIGURE_FACTORY_NEXT.md) and [figure preflight](wiki/Figure-Factory-Preflight-and-Methods-Manual.md):
  actual input contracts, output sidecars and renderer-specific limits.
- `current` [Bioassay Figure Factory](docs/BIOASSAY_FIGURE_FACTORY.md): typed plate, material, replicate,
  target, time-point, control, exclusion, and R-rendering contract.
- `current` [R figure workflows](docs/R_FIGURE_WORKFLOWS.md): current ggplot2/ggtree renderer map and the
  admitted bioassay-to-tree path.
- `current` [Optional pairwise comparison](sapote_addons/README_OFFLINE_ANALYSIS.md) and
  [optional hooks](docs/OPTIONAL_HOOKS.md): specialized capabilities with their own setup.
- `current` [Resources](resources/README.md) and [validation records](validation/README.md): data purpose,
  consumers and historical evidence boundaries.

The [Master Walkthrough](docs/MASTER_WALKTHROUGH.md) connects installation to validated outputs;
[prerequisites](docs/PREREQUISITES.md) distinguish Python extras, external tools and datasets.

## Tool and contract pages

- `experimental` [Optional RiPPER plan/import adapter](docs/RIPPER_OPTIONAL_ADAPTER.md): isolated precursor-candidate planning and operator-supplied TSV admission; no live execution route or upstream compatibility claim.

Use these guides for specialized tools, commands and input/output contracts.

- `current` [Optional external AB/AF activity-prediction channel](docs/AB_AF_EXTERNAL_ACTIVITY_CHANNEL.md)
- `current` [BGC functional logic workup](docs/BGC_FUNCTIONAL_LOGIC_WORKUP.md)
- `current` [Bioactivity Metadata Contract](docs/BIOACTIVITY_METADATA_CONTRACT.md)
- `current` [Bioassay activity-channel workflow — where it sits](docs/BIOASSAY_ACTIVITY_CHANNEL_WORKFLOW.md)
- `current` [Whole-genome chitin/GlcNAc reference-capacity evaluation](docs/CHITIN_REFERENCE_EVALUATION.md)
- `current` [Clear Match Finder](docs/CLEAR_MATCH_FINDER.md)
- `current` [cluster_completeness — assembly truncation vs biological absence](docs/CLUSTER_COMPLETENESS.md)
- `current` [cluster_discovery — candidate assembly lookup from marker-protein similarities](docs/CLUSTER_DISCOVERY.md)
- `current` [cluster_gene_compare — gene-by-gene BGC comparison as a real deliverable](docs/CLUSTER_GENE_COMPARE.md)
- `current` [cluster_relate — relationship tree + distance matrix from homologous clusters](docs/CLUSTER_RELATE.md)
- `current` [ClusterBlast-derived phylogeny candidate ledger](docs/CLUSTERBLAST_PHYLO_CANDIDATES.md)
- `current` [Cohort pack interface (external, operator-supplied, Git-ignored)](docs/COHORT_PACK_INTERFACE.md)
- `current` [Cohort protein comparison contract for Mode B](docs/COHORT_PROTEIN_COMPARISON_MODEB_CONTRACT.md)
- `current` [Definitive BGC prioritization ranker](docs/DEFINITIVE_BGC_RANKER.md)
- `current` [BGC-machinery domain-tree contract](docs/DOMAIN_TREE_CONTRACT.md)
- `current` [Enzyme neighborhood explorer](docs/ENZYME_NEIGHBORHOODS.md)
- `experimental` [Gene evidence disagreement review candidate](docs/EVIDENCE_DISAGREEMENTS_CANDIDATE.md)
- `current` [extract_cluster — bring a raw genome into the pipeline](docs/EXTRACT_CLUSTER.md)
- `current` [F13 BGC domain-count PCA source-artwork contract](docs/F13_BGC_DOMAIN_PCA.md)
- `current` [fetch_reference_cluster — reference/cohort cluster GBKs, as a shared step](docs/FETCH_REFERENCE_CLUSTER.md)
- `current` [Figure owner-review workflow](docs/FIGURE_OWNER_REVIEW_WORKFLOW.md)
- `current` [Figure Factory owner-review queue](docs/FIGURE_REVIEW_WORKFLOW.md)
- `current` [Bounded GToTree panel selection](docs/GTOTREE_PANEL_SELECTION.md)
- `current` [Literature atlas current-evidence refresh](docs/LITERATURE_ATLAS_CURRENT_EVIDENCE_REFRESH.md)
- `current` [Locus-map review contract](docs/LOCUS_MAP_REVIEW_CONTRACT.md)
- `current` [Locus map v8](docs/LOCUS_MAP_V8.md)
- `current` [FA6 — Mode B card exporter (modeb-export)](docs/MODEB_EXPORT_HOOK.md)
- `current` [Mode B gene-first exploration](docs/MODEB_GENE_FIRST_EXPLORATION.md)
- `reference` [Ratified Mode B status vocabulary](docs/MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md)
- `current` [NPBDetect non-admissible prediction guard](docs/NPBDETECT_ADAPTER_GUARD.md): local NPBDetect model IDs permit only OUT_OF_DOMAIN/FAILED with null AB/AF probabilities and HOLD; preserved upstream audit notes do not grant admission.
- `current` [Outgroup generator + right-sized reference sets (outgroup_registry.py, phylo_refset.py)](docs/OUTGROUP_AND_REFSET_WORKFLOW.md)
- `current` [Owner-kept Figure Factory inputs](docs/OWNER_KEPT_FIGURE_INPUTS.md)
- `reference` [Spec — Cohesive Per-BGC Report (L0–L3) + Comparison Matrix](docs/PER_BGC_REPORT_CARD_SPEC.md)
- `current` [EPA-ng placement and phylogeny troubleshooting](docs/PHYLO_TROUBLESHOOTING.md)
- `current` [PKS ketosynthase-tree option guide](docs/PKS_KS_TREE_OPTIONS.md)
- `current` [Portable evidence-workspace interface](docs/PORTABLE_EVIDENCE_WORKSPACE.md)
- `current` [Portable strain privacy and evidence registry](docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md)
- `current` [Prevalence workflow — where it sits](docs/PREVALENCE_WORKFLOW.md)
- `current` [Portable project data home](docs/PROJECT_DATA_HOME.md)
- `current` [Sapote-Mamey Naming Contract](docs/PROJECT_NAMING.md)
- `current` [Exact-bound reference-BGC structural validator](docs/REFERENCE_BGC_STRUCTURAL_VALIDATOR.md)
- `current` [Reporting v2 — per-gene MIBiG convergence & structured antiSMASH tables](docs/reporting_v2_mibig_convergence.md)
- `current` [RG-GMCI complementary-rescue atlas](docs/RGGMCI_RESCUE_ATLAS.md)
- `current` [RiPP tree and sequence-network option guide](docs/RIPP_TREE_OPTIONS.md)
- `current` [Sapote Markdown authoring contract](docs/SAPOTE_MARKDOWN_AUTHORING_CONTRACT.md)
- `current` [Sapote-Mamey report theme](docs/SAPOTE_REPORT_THEME.md)
- `current` [scope_cluster — scope an over-merged antiSMASH region to its true protocluster](docs/SCOPE_CLUSTER.md)
- `current` [Screening exploration with ggplot2](docs/SCREENING_EXPLORATION_R.md)
- `current` [Standalone delivery audit](docs/STANDALONE_DELIVERY_AUDIT.md): checks that an HTML/SVG delivery folder or ZIP matches its file-and-hash list and loads nothing from outside it.
- `current` [Strain BiG-SCAPE report and figure labels](docs/STRAIN_BIGSCAPE_REPORT.md)
- `current` [Strain-level BGC logic reports](docs/STRAIN_LEVEL_BGC_LOGIC.md)
- `current` [Token-light Sapote document factory](docs/TOKEN_LIGHT_DOCUMENT_FACTORY.md)
- `current` [Read only tool database inspection](docs/TOOL_DATABASE_INSPECTION.md)
- `current` [Two-stage modular BGC reports](docs/TWO_STAGE_MODULAR_BGC_REPORTS.md)
- `current` [Phylogenetic workflow gate guide](docs/WORKFLOW_GATES_GUIDE.md)

- `current` [Offline paper reference audit](docs/PAPER_REFERENCE_AUDIT.md): DOCX citation/reference and figure/table callout keys; parsing holds remain visible; no network or document edits.

## Reference, development and history

[Guide navigation](docs/GUIDE/00_README.md) distinguishes the operational guides from the dated
Encyclopedia and newsletter.

[Version-specific reference notes](docs/reference/06_CURRENT_SOURCE_SCOPE.md) explain equations, rule differences and figure limitations.
[Engine reference](docs/reference/00_README.md) and [Encyclopedia currency](docs/history/wiki_encyclopedia/Encyclopedia-Currency.md)
record reference scope. Consult current code and named schemas for numerical behavior.
[Methods technical appendix](docs/reference/METHODS_TECHNICAL_APPENDIX.md) records release-sensitive
parameters and failure-state semantics. The developer-facing
[implementation source map](docs/development/METHODS_IMPLEMENTATION_SOURCE_MAP.md) is regression-tested
against current implementation and test paths.
[Figure repair records](docs/figure_factory/README.md) and `docs/patch_notes/` are engineering records, not an alternative user setup sequence.

[History](docs/history/README.md) and the [changelog](CHANGELOG.md) preserve dated decisions. The changelog is the
complete per-cut record. [RELEASES_LOG](RELEASES_LOG.md) is a partial build-stamp table (see its header). Historical commands, counts, results and proposed features in those records
are not current operating instructions. `docs/QUICK_GUIDE.md` is superseded by the Quick Guide above;
`docs/user_guides/comprehensive_glossary.md` and `sapote_mamey_wheel_glossary.md` now point to their
history copies in `docs/history/retired_458/user_guides/`.
`docs/user_guides/` also contains tool and mathematical references alongside the human
entry guides linked below. The former cross-chat documentation protocol is archived under `docs/history/`.

## Maintaining this index

Update links when the owning workflow changes. Keep generated command, capability, version and
release surfaces under their existing generators. Review document content before claiming currency;
do not turn a version-stamp update into a claim of a full content review.

## Practical help

- `current` [Find the right document](docs/DOCUMENTATION_MAP.md)
- `current` [Troubleshooting](docs/COMMON_MISTAKES.md)
- `current` [Files, storage and handoff](docs/FILES_STORAGE_AND_HANDOFF.md)

## Diagnostic screening

- `experimental` [Experimental dominated diagnostic report](docs/DOMINATED_DIAGNOSTIC.md) — report-only thresholds and calibration hold.

- `current` [Optional GECCO, metabolomics bridge and explicit non-KS policy](docs/COMPANION_CLASS_EVIDENCE.md) — external reader outputs, source binding and class-level interpretation.

## Human entry guides

- `current` [Read an existing result](docs/user_guides/READ_EXISTING_RESULT.md).
- `current` [Start a first run](docs/user_guides/FIRST_RUN_ORIENTATION.md).
- `current` [Troubleshoot and maintain a workflow](docs/user_guides/WORKFLOW_RECOVERY.md).
- `current` [Read locus maps, tables and protein PCoA comparisons](docs/LOCUS_AND_PCOA_TOOLS.md).
- `current` [Choose the next command](docs/user_guides/CHOOSE_NEXT_COMMAND.md).

The [BiG-SCAPE cohort network guide](docs/BIGSCAPE_COHORT_NETWORK_GUIDE.md) gives the class reading limits that accompany the generated vocabulary.
