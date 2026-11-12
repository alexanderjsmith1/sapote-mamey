# Current Docs Index — v9.7.465 · engine 1.9.181 · build 20261110v97465a

Each listed entry starts with its status. The status is `current` (follow it for new work), `reference` (background, specifications or dated examples; check current code before relying on a number) or `experimental` (report-only, not a release gate).

Check historical status first: a page under `docs/history/`, or one whose first lines say historical, retired, deprecated or superseded, is not current even if another page links to it or an index entry has drifted. Otherwise, `current` entries designate the maintained routes. For an unlisted page, check its first lines and the declared scope of the maintained page that links to it; a link alone does not validate its contents.

## Start here

Terms such as BGC (biosynthetic gene cluster) and Mode B are defined in the [Glossary](docs/GLOSSARY.md). A `Complete_Package.zip` is the saved result of a run; see [Start with your file](docs/READER_START_HERE.md).

- `current` [Start with your file](docs/READER_START_HERE.md): tells you whether you have the software, an antiSMASH ZIP or a saved result.
- `current` [Installation](docs/INSTALL.md), [prerequisites](docs/PREREQUISITES.md) and [external assets](docs/EXTERNAL_DATA.md): set up the program and the separately supplied data.
- `current` [Inputs and setup](docs/reader/02_INPUTS_AND_SETUP.md): the program, input and output folders for your task.
- `current` [Your first run](docs/reader/01_FIRST_RUN.md): extract and check one antiSMASH ZIP. This is the recommended first-run route.
- `current` [Read one saved package](docs/reader/03_READ_RESULTS.md): find the region list, workbook and issue log in a result. [Reading your results](docs/READING_YOUR_RESULTS.md) explains selected result fields and evidence states.
- `current` [Recover a run](docs/reader/04_RECOVERY_AND_LIMITS.md): what to do when a command fails or a run is incomplete. [Troubleshooting](docs/COMMON_MISTAKES.md) lists common mistakes.
- `current` [Choose a task](docs/USER_TASK_ROUTER.md): pick a task and see its inputs and guide. [Choose the next command](docs/user_guides/CHOOSE_NEXT_COMMAND.md) gives a working command line for the specialist commands.
- `current` [Find the right document](docs/DOCUMENTATION_MAP.md): a short table from what you want to do to the page to open.
- `current` [Quick Guide](docs/GUIDE/02_Quick_Guide.md) and [User manual](docs/GUIDE/01_User_Manual.md): a command map and the manual's table of contents. Both link to the pages above instead of restating them.
- `current` [Ask an assistant to run it](docs/MASTER_WALKTHROUGH.md): the request to give a coding assistant for a first analysis, and what to check in its answer.
- `current` [Data home](docs/DATA_HOME.md): where results live, the inbox route into the Strain Master, how to find data before making any, and the self-check.
- `current` [Files, storage and handoff](docs/FILES_STORAGE_AND_HANDOFF.md): save a package or move it to another computer.
- `current` [Command catalog](docs/COMMAND_CATALOG.generated.md) and [deliverable menu](docs/DELIVERABLE_MENU.md): generated lists of commands and of what the program can produce.

## Guides by task

- `current` [Make and review figures](docs/FIGURES_START_HERE.md) and [Evidence to report](docs/EVIDENCE_TO_REPORT.md): figures, captions and short findings and Methods facts.
- `current` [Read locus maps, tables and protein PCoA comparisons](docs/LOCUS_AND_PCOA_TOOLS.md).
- `current` [Figure house rules](docs/FIGURE_HOUSE_RULES.md): the rules every figure meets (format, caption and methods, page wording, material labels, provenance) and what checks each one.
- `current` [Aggregate evidence-coverage figures](docs/FIGURE_FACTORY_NEXT.md) and [figure preflight](wiki/Figure-Factory-Preflight-and-Methods-Manual.md):
  actual input contracts, output sidecars and renderer-specific limits.
- `current` [Bioassay Figure Factory](docs/BIOASSAY_FIGURE_FACTORY.md): typed plate, material, replicate,
  target, time-point, control, exclusion, and R-rendering contract.
- `current` [R figure workflows](docs/R_FIGURE_WORKFLOWS.md): current ggplot2/ggtree renderer map and the
  admitted bioassay-to-tree path.
- `current` [Strain slides](docs/STRAIN_SLIDES.md): one deck per strain from a sources file. Each deck has the complete region inventory and gene tables. Selected region slides (with explicit omission rules) carry the gap-rescue map, gene strip, GECCO, RG-GMCI two-proof, BiG-SCAPE and BLASTp lines, GECCO-only candidates and a gene-table appendix. The deck also has protein PCoA panels per strain.
- `current` [BLASTp evidence](docs/ONLINE_BLASTP_PROTOCOL.md): existing results first (rollups to reservoir; trove to package overlay; HitTable to workbook), optional live submission.
- `current` [BiG-SCAPE cohort walkthrough](docs/BIGSCAPE_COHORT_WALKTHROUGH.md) and [troubleshooting](docs/troubleshooting/BIGSCAPE_TROUBLESHOOTING.md): stage region files, run a cohort, inspect family verdicts and figures.
- `current` [BiG-SCAPE cohort networks and comparator context](docs/BIGSCAPE_COHORT_NETWORK_GUIDE.md): exact-identity cohort tables, evidence badges and citations, overmerged-region component metrics, interactive/static figures, and additive batch report enrichment.
- `current` [antiSMASH strictness and pooling](docs/ANTISMASH_PROFILE.md): recorded profile evidence, mismatch states and the selected-package pooling guard.
- `current` [antiSMASH web submission](docs/ANTISMASH_WEB_SUBMISSION_SOP.md): the procedure for sending reference genomes to the public antiSMASH server; light-touch queue rule, loose with all 11 features, no email, one authorized batch at a time.
- `current` [Local 16S database](docs/LOCAL_16S_DATABASE.md): build the NCBI 16S type-strain BLAST database fully or for chosen genera, the optional SQLite store, and the shared lookup every 16S tool uses.
- `current` [Isolate neighborhood panel](docs/NEIGHBOUR_PANEL_16S_TYGS.md): one isolate's genome panel from its 16S BLAST hits on complete genomes, the NCBI genome table (`datasets`) and its TYGS closest type strains (`tools/neighbour_panel_candidates.py`; check with `tools/check_tygs_coverage.py`).
- `current` [Green-algal and cyanobacterial phylogeny](docs/PHYLO_ALGAL_CYANO_WORKFLOW.md): lineage-specific planning and evidence holds.
- `current` [Phylogenetic workflow](docs/PHYLO_AUTOPILOT_WORKFLOW.md), [placement](docs/PHYLO_PLACEMENT_WORKFLOW.md),
  and [companion tools](docs/LLM_COMPANION_TOOL_PROTOCOL.md): inputs, resource scope and run receipts.
- `current` [Companion Tool Guide](docs/COMPANION_TOOL_GUIDE.md): standalone use, inputs/outputs and integration roles.
- `current` [Companion class evidence](docs/COMPANION_CLASS_EVIDENCE.md): optional GECCO, the metabolomics bridge and the explicit non-KS policy. External reader outputs, source binding and class-level interpretation.
- `current` [TriMap runs](docs/TRIMAP_RUNS.md): TriMap and t-SNE installation, smoke test, the numba threading-layer crash, duplicate points and the settings to reuse.
- `current` [Optional pairwise comparison](sapote_addons/README_OFFLINE_ANALYSIS.md) and
  [optional hooks](docs/OPTIONAL_HOOKS.md): specialized capabilities with their own setup.
- `current` [Optional Barrnap](docs/BARRNAP.md): rRNA recipe versus execution, version/model checks and external setup.
- `current` [Multi-Cohort Comparison Toolkit](deliverable_tools/README.md): named roster/dossier/cohort tools, per-tool dependencies and writes.
- `current` [Project catalog and private handoff](docs/PROJECT_CATALOG.md): manifest-bound package locations, write behavior and partial-archive/import recovery.
- `current` [Deliverable queue](docs/DELIVERABLE_QUEUE.md): discovery states, package mutations, resume binding and per-strain recovery.
- `current` [Deliverable request templates](deliverables/README.md): supplied inputs, complete identity, bounded authoring and conversion contracts.
- `current` [Master workbook validation](docs/WORKBOOK_VALIDATION.md): deployed schema, fast/full scope, roster/hash checks and retained freeze discrepancies.
- `current` [Manuscript revision workflow](docs/MANUSCRIPT_REVISION_WORKFLOW.md): notes, reviewer findings and answers in one
  Word ledger; asks-only rounds; staged edits checked, applied and logged with `tools/manuscript_revision.py`.
- `current` [Evidence freshness](docs/EVIDENCE_FRESHNESS.md): check retained SHA-256 pins and declared dependency edges with `tools/evidence_freshness.py`; it writes only the receipt you name.
- `current` [Working with an assistant](docs/ASSISTANT_USER_GUIDE.md): choose inputs, task scope, evidence and completion criteria.
- `current` [Offline paper reference audit](docs/PAPER_REFERENCE_AUDIT.md): DOCX citation/reference and figure/table callout keys; parsing holds remain visible; no network or document edits.
- `experimental` [Experimental dominated diagnostic report](docs/DOMINATED_DIAGNOSTIC.md): report-only thresholds and calibration hold.

- `current` [Make reports from a saved package](docs/POSTSEAL_READERS.md): make a report or prepare another analysis from an extracted package. Some commands write into the package.
- `current` [HTML readers: which tool builds which page](docs/HTML_TEMPLATE_READERS.md): each HTML template, its builder and where the output goes.
- `current` [Citation-compact reports](docs/CITATION_COMPACT_READERS.md): the optional `--token-budget citation-compact` output and how to read it.
- `current` [Cohort-bank publication and recovery](docs/COHORT_BANK_TRANSACTIONS.md): merge one package into a cohort bank and recover an interrupted write.
- `current` [Companion setup, scanner HMMs, protein input and BLASTp checkpoints](docs/447_COMPANION_RETRIEVAL_CONTROLS.md): four setup and retrieval tasks that sit beside the main pipeline.
- `current` [Companion run contracts](docs/COMPANION_RUN_CONTRACTS.md): what the planner, runner and placement steps read and write.
- `current` [Reading bundle identity, manifests and checksums](docs/BUNDLE_METADATA_READERS.md): verify a bundle against a trusted release hash.
- `current` [Standalone delivery audit](docs/STANDALONE_DELIVERY_AUDIT.md): check that an HTML or SVG delivery folder or ZIP matches its file-and-hash list and loads nothing from outside it.
- `current` [Find a missing input](docs/COMPANION_FILES.md): where to get a genome, reference file or optional program.
- `current` [Find a helper tool](docs/user_guides/tools_reference.md): choose a task, then open its guide.
- `current` [Compare a fungal isolate with references](docs/PHYLO_FUNGAL_WORKFLOW.md): fungal markers or genome orthologs for placement.
- `current` [Browse a package with widgets](docs/WIDGET_DELIVERABLES.md): linked offline HTML pages from a package.

## Mode B cards

A Mode B card is a written evidence review of one region. Start with the hub.

- `current` [Mode B guide index](docs/MODE_B_DOCUMENT_INDEX.md): find the Mode B guide you need.
- `current` [Mode B authoring](wiki/Mode-B.md): use the selected machine-readable
  profile and its emitted template; legacy section counts do not replace a named current profile.
- `current` [Mode B contract current50 v2](docs/MODEB_CURRENT50_V2_CONTRACT.md): the 50-section card with GECCO (§22), reference-guided rescue evidence and candidate partner contigs (§26), literature with relevance (§48–§49) and the data evidence table last (§50); `emit-modeb-template --contract current50_v2` and `verify-modeb --contract current50_v2`.
- `current` [Mode B expanded locus](docs/MODEB_EXPANDED_LOCUS.md): independently source-bound CDS inventories and bounded supported-anchor context; use `--require-expanded-locus` for an expanded work order. Core membership remains separate.
- `current` [Mode B gap-rescue reader](docs/MODEB_GAP_RESCUE_READER.md): supplied rescue context and existence checks; this does not adopt rescued genes into a locus.
- `current` [Mode B evidence availability and writing](docs/MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md): pre-authoring inventory, typed binding/freshness states, planner limits and the independently reviewed finished-card evidence matrix.
- `current` [Mode B profiles](docs/MODEB_PROFILE_MATRIX.md): which card is which (scaffold, candidate, finished §1–§48, opt-in current50 v2), with each profile's producer, verifier and the status it can claim. "Full Mode B" means the selected finished profile.
- `current` [Mode B user walkthrough](docs/MODE_B_USER_WALKTHROUGH.md): profile boundaries and commands for the default 48-section card and the 50-section `current50_v2` card.
- `reference` [Mode B exemplar reader guide](docs/reference/modeb_exemplars/README.md): historical class sketches and a 48-section format reference. Use the example register to identify their scope; their locus-specific evidence and old pass labels do not validate a current 50-section finished card.

## Tool and contract pages

Use these guides for specialized tools, commands and input and output contracts.

- `experimental` [Optional RiPPER plan/import adapter](docs/RIPPER_OPTIONAL_ADAPTER.md): standalone `tools/ripper_adapter.py` subcommands for planning RiPP precursor searches and importing their results. It is not part of `mamey_run.py`.

### Trees and phylogeny

- `experimental` [ClusterBlast-derived phylogeny candidate ledger](docs/CLUSTERBLAST_PHYLO_CANDIDATES.md)
- `experimental` [BGC-machinery domain-tree contract](docs/DOMAIN_TREE_CONTRACT.md): candidate interface only; it builds no tree.
- `current` [Bounded GToTree panel selection](docs/GTOTREE_PANEL_SELECTION.md)
- `current` [Outgroup generator + right-sized reference sets (outgroup_registry.py, phylo_refset.py)](docs/OUTGROUP_AND_REFSET_WORKFLOW.md)
- `current` [PKS ketosynthase-tree option guide](docs/PKS_KS_TREE_OPTIONS.md)
- `current` [RiPP tree and sequence-network option guide](docs/RIPP_TREE_OPTIONS.md)
- `current` [Phylogenetic workflow gate guide](docs/WORKFLOW_GATES_GUIDE.md)

### Figures and maps

- `current` [F13 BGC domain-count PCA source-artwork contract](docs/F13_BGC_DOMAIN_PCA.md)
- `current` [Locus-map review contract](docs/LOCUS_MAP_REVIEW_CONTRACT.md)
- `current` [Locus map v8](docs/LOCUS_MAP_V8.md)
- `current` [Screening exploration with ggplot2](docs/SCREENING_EXPLORATION_R.md)
- `current` [Strain BiG-SCAPE report and figure labels](docs/STRAIN_BIGSCAPE_REPORT.md)

### Mode B and BGC reports

- `current` [BGC functional logic workup](docs/BGC_FUNCTIONAL_LOGIC_WORKUP.md)
- `current` [Definitive BGC prioritization ranker](docs/DEFINITIVE_BGC_RANKER.md)
- `current` [Enzyme neighborhood explorer](docs/ENZYME_NEIGHBORHOODS.md)
- `current` [FA6 — Mode B card exporter (modeb-export)](docs/MODEB_EXPORT_HOOK.md)
- `current` [Mode B gene-first exploration](docs/MODEB_GENE_FIRST_EXPLORATION.md)
- `reference` [Mode B status vocabulary](docs/MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md)
- `current` [Strain-level BGC logic reports](docs/STRAIN_LEVEL_BGC_LOGIC.md)
- `current` [Two-stage modular BGC reports](docs/TWO_STAGE_MODULAR_BGC_REPORTS.md)
- `current` [Make a quick per-BGC overview with `report-card`](docs/PER_BGC_REPORT_CARD_SPEC.md)
- `current` [Cohort protein comparison contract for Mode B](docs/COHORT_PROTEIN_COMPARISON_MODEB_CONTRACT.md)
- `current` [Reporting v2 — per-gene MIBiG convergence & structured antiSMASH tables](docs/reporting_v2_mibig_convergence.md)
- `current` [RG-GMCI complementary-rescue atlas](docs/RGGMCI_RESCUE_ATLAS.md)

### Finding and checking clusters

- `current` [Clear Match Finder](docs/CLEAR_MATCH_FINDER.md)
- `current` [cluster_completeness — reference-dependent homology coverage](docs/CLUSTER_COMPLETENESS.md): scores coverage against a reference panel. It cannot tell a missing gene from an assembly gap.
- `current` [cluster_discovery — candidate assembly lookup from marker-protein similarities](docs/CLUSTER_DISCOVERY.md)
- `current` [cluster_gene_compare — gene-by-gene homology comparison](docs/CLUSTER_GENE_COMPARE.md)
- `current` [cluster_relate — relationship tree + distance matrix from homologous clusters](docs/CLUSTER_RELATE.md)
- `current` [extract_cluster — find a marker-co-occurrence candidate region in a raw genome](docs/EXTRACT_CLUSTER.md)
- `current` [fetch_reference_cluster — write a reference or cohort cluster as a GenBank file](docs/FETCH_REFERENCE_CLUSTER.md)
- `current` [scope_cluster — scope an over-merged antiSMASH region to a selected source-bound protocluster](docs/SCOPE_CLUSTER.md)
- `current` [Exact-bound reference-BGC structural validator](docs/REFERENCE_BGC_STRUCTURAL_VALIDATOR.md)
- `experimental` [Gene evidence disagreement review candidate](docs/EVIDENCE_DISAGREEMENTS_CANDIDATE.md)
- `current` [Whole-genome chitin/GlcNAc reference-capacity evaluation](docs/CHITIN_REFERENCE_EVALUATION.md)

### Activity data, privacy and workspaces

- `current` [Optional external AB/AF activity-prediction channel](docs/AB_AF_EXTERNAL_ACTIVITY_CHANNEL.md)
- `current` [Bioactivity Metadata Contract](docs/BIOACTIVITY_METADATA_CONTRACT.md)
- `current` [Bioassay activity-channel workflow — where it sits](docs/BIOASSAY_ACTIVITY_CHANNEL_WORKFLOW.md)
- `current` [Cohort pack interface (external, operator-supplied, Git-ignored)](docs/COHORT_PACK_INTERFACE.md)
- `current` [Portable evidence-workspace interface](docs/PORTABLE_EVIDENCE_WORKSPACE.md)
- `current` [Portable strain privacy and evidence registry](docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md)
- `current` [Prevalence workflow — where it sits](docs/PREVALENCE_WORKFLOW.md)
- `current` [Portable project data home](docs/PROJECT_DATA_HOME.md)
- `current` [Literature atlas current-evidence refresh](docs/LITERATURE_ATLAS_CURRENT_EVIDENCE_REFRESH.md)

## Reference

- `current` [Guide navigation](docs/GUIDE/00_README.md): which guides are operational and which are dated.
- `reference` [Engine reference](docs/reference/00_README.md): equations and rules. Check current code and named schemas for numerical behavior.
- `reference` [Limits of each check tool](docs/reference/06_CURRENT_SOURCE_SCOPE.md): what a PASS from each tool does not check.
- `reference` [Methods technical appendix](docs/reference/METHODS_TECHNICAL_APPENDIX.md): parameters and failure-state meanings that affect Methods text.
- `current` [Methods implementation template](docs/templates/MANUSCRIPT_METHODS_IMPLEMENTATION_TEMPLATE.md) and
  [reporting checklist](docs/METHODS_REPORTING_CHECKLIST.md): manuscript authoring aids; their presence does not assert that a study or module was run.
- `reference` [Examples index](examples/README.md): fixtures and illustrative or historical evidence.
- `reference` [Resources](resources/README.md) and [validation records](validation/README.md): data purpose, consumers and historical evidence boundaries.
- `reference` [JGI public reference context](docs/SMC_PUBLIC_REFERENCE_CONTEXT.md): IMG-ABC provenance and optional manual references; automated retrieval is not implemented.

[History](docs/history/README.md) and the [changelog](CHANGELOG.md) hold old records. Commands, counts and results in them are not instructions. [RELEASES_LOG](RELEASES_LOG.md) is a partial table of build stamps.

## Maintainers

Users do not need these pages. Maintainers and coding assistants do.

- `current` [Task routes as JSON](docs/USER_TASK_ROUTER.json): the same routes as Choose a task, with detailed input and output rules, for assistants.
- `current` [AGENTS](AGENTS.md): the shared coding-assistant contract. `CLAUDE.md` is a generated copy for Claude. Other assistants need `AGENTS.md` through their own instruction mechanism.
- `current` [Assistant governance](docs/ASSISTANT_GOVERNANCE.md) and [runtime profiles](docs/ASSISTANT_RUNTIME_PROFILES.md): scope, permissions, conflict rules and environment limits.
- `current` [Catalog reading and maintenance](docs/CATALOG_MAINTENANCE.md): generated owners and check scope.
- `current` [Maintenance inventory](docs/MAINTENANCE_INVENTORY.generated.md): scoped owners for commands, optional tools, generated files and documents. [Machine records](docs/MAINTENANCE_INVENTORY.generated.json) use the same source declarations.
- `current` [Structured domain/motif sidecar readers](docs/STRUCTURED_DOMAIN_MOTIF_EXTENSION.md): source admission, partial-output recovery and receipt scope.
- `current` [Figure owner-review workflow](docs/FIGURE_OWNER_REVIEW_WORKFLOW.md)
- `current` [Figure Factory owner-review queue](docs/FIGURE_REVIEW_WORKFLOW.md)
- `current` [Owner-kept Figure Factory inputs](docs/OWNER_KEPT_FIGURE_INPUTS.md)
- `current` [Sapote Markdown authoring contract](docs/SAPOTE_MARKDOWN_AUTHORING_CONTRACT.md)
- `current` [Sapote-Mamey report theme](docs/SAPOTE_REPORT_THEME.md)
- `current` [Sapote-Mamey Naming Contract](docs/PROJECT_NAMING.md)
- `current` [Token-light Sapote document factory](docs/TOKEN_LIGHT_DOCUMENT_FACTORY.md)
- `current` [Tool database inspection](docs/TOOL_DATABASE_INSPECTION.md): inspect one frozen tool-database manifest with `tool-database-inspect`.
- `current` [NPBDetect prediction guard](docs/NPBDETECT_ADAPTER_GUARD.md): local NPBDetect results are recorded only as out-of-domain or failed, with no AB/AF probability, and held.
- `reference` [Large-reference source scope](docs/development/LARGE_REFERENCE_SOURCE_SCOPE.md): developer-facing; where the large reference documents differ from the current code.
- `reference` [Methods implementation source map](docs/development/METHODS_IMPLEMENTATION_SOURCE_MAP.md): developer-facing; checked against current implementation and test paths.
- `current` [Figure Factory guides](docs/figure_factory/README.md): the aggregate rendering guide, the preflight manual, optional gallery tools and a progress-dashboard pattern.

Update links when the owning workflow changes. Keep generated command, capability, version and release files under their generators. A version-stamp update is not a content review.
