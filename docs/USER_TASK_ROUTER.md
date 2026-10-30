# Choose a Sapote-Mamey task

Find the result you want below. Each row lists the inputs you need and links to
the guide that shows how to make it. New users can start with
[Your first run](reader/01_FIRST_RUN.md) or [Read a saved package](reader/03_READ_RESULTS.md).

| Task | Example request | You need | Guide |
|---|---|---|---|
| First analysis | Extract and validate one strain from this antiSMASH result ZIP. | antiSMASH ZIP; strain name | [First analysis](reader/01_FIRST_RUN.md) |
| Read your results | Explain this package, its issue log and missing evidence. | existing package with its manifest | [Read your results](reader/03_READ_RESULTS.md) |
| Evidence to report | Make these figures and give me short findings and Methods facts. | packages or evidence; question and figure list; output folder; public or private scope | [Evidence to report](EVIDENCE_TO_REPORT.md) |
| Mode B card | Author and verify this locus under the named profile. | validated package; full locus identity; profile; evidence | [Mode B card](MODEB_PROFILE_MATRIX.md) |
| Strain slides builder | Build the main strain deck and its region-gene-table companion. | validated package; strain ID; sources JSON; new output folder | [Strain slides builder](STRAIN_SLIDES.md) |
| Figure rendering | Render this figure set from the package into another folder. | package; figure set; renderer inputs | [Figure rendering](FIGURES_START_HERE.md) |
| Companion tools | Plan this comparison from these inputs and existing results. | inputs and references; resource limits; tool versions | [Companion tools](COMPANION_TOOL_GUIDE.md) |
| Stored BLASTp evidence | Inspect and reuse saved BLASTp results for these queries. | raw stored results; query mapping; database, settings and date | [Stored BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md) |
| Recover a failed step | Diagnose the failed stage and give a recovery for this run. | run log; status or manifest; input hashes; prior settings | [Recover a failed step](reader/04_RECOVERY_AND_LIMITS.md) |
| Pairwise protein comparison | Compare proteins in these two antiSMASH result ZIPs. | query and reference ZIPs with translated CDS; a working alignment backend; new output folder; optional genome FASTAs | [Pairwise protein comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md) |
| Interactive reader widgets | Build an interactive reader from this package. | package or run folder, or Complete_Package ZIP with manifest; new output folder | [Interactive reader widgets](WIDGET_DELIVERABLES.md) |
| Share a package | Package this result and its region files for another computer. | package with its validation and hashes; original antiSMASH ZIP for the region files; new ZIP path | [Share a package](FILES_STORAGE_AND_HANDOFF.md) |
| Project catalog | Register or verify package locations in this project root. | project root; package paths; catalog and manifest hashes when verifying | [Project catalog](PROJECT_CATALOG.md) |
| Share a private project | Prepare or open a private multi-package archive. | project root and catalog; package, config and registry files; new archive path, or source archive with its SHA-256; empty import folder when importing | [Share a private project](PROJECT_CATALOG.md) |
| Project portfolio binding | Check this pointer config and its project registry without running an analysis. | project root; `sapote_project_portfolio_v1` config; contained `sapote_project_registry_v1` JSON; receipt destination if writing | [Project portfolio binding](PROJECT_CATALOG.md) |
| Privacy and evidence metadata validation | Check this privacy profile and evidence TSV as metadata. | `sapote_privacy_profile_v1` JSON; strain evidence registry TSV | [Privacy and evidence metadata validation](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) |

## What each task returns

The linked guide names the output files and how to check them. A figure needs
its source data; a written card needs its evidence and the selected card profile.
Keep the input files and the results together when sharing a package.

## When a request runs into trouble

Use [Recovery](reader/04_RECOVERY_AND_LIMITS.md) for a failed command.
If an optional input is missing, choose a task that uses the evidence you have.
[Install](INSTALL.md) and [Prerequisites](PREREQUISITES.md) cover setup.

The [machine-readable task list](USER_TASK_ROUTER.json) includes the detailed
input and output rules. Its baseline records the sources used to build those routes;
check the [release manifest](../RELEASE_MANIFEST.md) for the installed bundle version.
Coding assistants also use [AGENTS.md](../AGENTS.md).
