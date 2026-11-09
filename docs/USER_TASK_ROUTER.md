# Choose a Sapote-Mamey task

Find the result you want below. Each row lists the inputs you need and links to
the guide that shows how to make it. New users can start with
[Your first run](reader/01_FIRST_RUN.md) or [Read one saved package](reader/03_READ_RESULTS.md).

| Task | Example request | You need | Guide |
|---|---|---|---|
| First analysis | Extract and validate one strain from this antiSMASH result ZIP. | antiSMASH ZIP; strain name | [Your first run](reader/01_FIRST_RUN.md) |
| Read your results | Explain this package, its issue log and missing evidence. | existing package with its manifest | [Read one saved package](reader/03_READ_RESULTS.md) |
| Evidence to report | Make these figures and give me short findings and Methods facts. | packages or evidence; question and figure list; output folder; public or private scope | [Evidence to report](EVIDENCE_TO_REPORT.md) |
| Mode B card | Write an evidence review of one region and check it against a card profile (a named list of required sections). | validated package; full locus identity; profile; evidence | [Mode B card](MODEB_PROFILE_MATRIX.md) |
| Strain slides builder | Build the main strain deck and its region-gene-table companion. | validated package; strain ID; sources JSON; new output folder | [Strain slides builder](STRAIN_SLIDES.md) |
| Figure rendering | Render this figure set from the package into another folder. | package; figure set; renderer inputs | [Figure rendering](FIGURES_START_HERE.md) |
| Companion tools | Plan this comparison from these inputs and existing results. | inputs and references; resource limits; tool versions | [Companion tools](COMPANION_TOOL_GUIDE.md) |
| Fungal phylogeny | Review a fungal isolate against a selected reference scope. | source-bound records; question; reference and outgroup decisions; resource limits | [Fungal workflow](PHYLO_FUNGAL_WORKFLOW.md) |
| Green-algal or cyanobacterial phylogeny | Plan or review a comparison for the selected lineage. | source-bound records; lineage and compartment; reference and outgroup decisions; resource limits | [Green-algal and cyanobacterial workflow](PHYLO_ALGAL_CYANO_WORKFLOW.md) |
| Stored BLASTp evidence | Inspect and reuse saved BLASTp results for these queries. | raw stored results; query mapping; database, settings and date | [Stored BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md) |
| Choose a specialist command | Which command answers this question about my package, figures or ledgers? | existing package or saved evidence; new output folder | [Choose the next command](user_guides/CHOOSE_NEXT_COMMAND.md) |
| Recover a failed step | Diagnose the failed stage and give a recovery for this run. | run log; status or manifest; input hashes; prior settings | [Recover a run](reader/04_RECOVERY_AND_LIMITS.md) |
| Pairwise protein comparison | Compare proteins in these two antiSMASH result ZIPs. | query and reference ZIPs with translated CDS; a working alignment backend; new output folder; optional genome FASTAs | [Pairwise protein comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md) |
| Interactive reader widgets | Build an interactive reader from this package. | package or run folder, or Complete_Package ZIP with manifest; new output folder | [Interactive reader widgets](WIDGET_DELIVERABLES.md) |
| Share a package | Package this result and its region files for another computer. | package with its validation and hashes; original antiSMASH ZIP for the region files; new ZIP path | [Share a package](FILES_STORAGE_AND_HANDOFF.md#build-a-portable-zip) |
| Project catalog | Register or verify package locations in this project root. | project root; package paths; catalog and manifest hashes when verifying | [Project catalog](PROJECT_CATALOG.md) |
| Share a private project | Prepare or open a private archive that holds several packages. | project root and its catalog; the package files; new archive path, or a source archive with its SHA-256; empty import folder when importing | [Share a private project](PROJECT_CATALOG.md) |
| Add a project registry to an archive | Check a project registry file and save its hashes before sharing, without running an analysis. | project root; the portfolio config file; the project registry JSON it names | [Add a project registry](PROJECT_CATALOG.md#include-a-portfolio-registry-optional) |
| Check strain access and assay records | Check my access-tier file and assay record table. | privacy profile JSON; evidence registry TSV | [Set strain access and track assay records](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) |

## What each task returns

The linked guide names the output files and how to check them. A figure needs
its source data; a written card needs its evidence and the selected card profile.
Keep the input files and the results together when sharing a package.

## When a request runs into trouble

Use [Recovery](reader/04_RECOVERY_AND_LIMITS.md) for a failed command.
If an optional input is missing, choose a task that uses the evidence you have.
[Install](INSTALL.md) covers setup.

The [machine-readable task list](USER_TASK_ROUTER.json) includes the detailed
input and output rules. Its baseline names the source version the routes were built from. It does not certify that
every route was run. The [release manifest](../RELEASE_MANIFEST.md) names the installed version.
Coding assistants also use [AGENTS.md](../AGENTS.md).
