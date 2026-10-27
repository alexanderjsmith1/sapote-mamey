# Choose a Sapote-Mamey task

Find the result you want in the table, open its guide and supply its inputs. Replace bracketed values with real paths and identities. Check the [release manifest](../RELEASE_MANIFEST.md)
and the JSON routes' `baseline` block for their recorded source version.

New here? Start with [Start with your file](READER_START_HERE.md). The [JSON routes](USER_TASK_ROUTER.json) list the same task names, inputs and completion limits for assistants. They grant no permission and do not replace the guide or the CLI source. Assistants read `AGENTS.md` before choosing a route.

| Task | Example request | You need | Guide |
|---|---|---|---|
| First analysis | Extract and validate one strain from this antiSMASH result ZIP. | antiSMASH ZIP; strain metadata; output folder | [First analysis](reader/01_FIRST_RUN.md) |
| Read your results | Explain this package, its issue log and missing evidence. | existing package with its manifest | [Read your results](reader/03_READ_RESULTS.md) |
| Evidence to report | Make these figures and give me short findings and Methods facts. | packages or evidence; question and figure list; output folder; public or private scope | [Evidence to report](EVIDENCE_TO_REPORT.md) |
| Mode B card | Author and verify this locus under the named profile. | validated package; full locus identity; profile; evidence | [Mode B card](MODEB_PROFILE_MATRIX.md) |
| Strain slides builder | Build the main strain deck and its region-gene-table companion. | validated package; strain ID; sources JSON; new output folder and tag | [Strain slides builder](STRAIN_SLIDES.md) |
| Figure rendering | Render this figure set from the package into another folder. | package; figure set; renderer inputs | [Figure rendering](FIGURES_START_HERE.md) |
| Companion tools | Plan this comparison from these inputs and existing results. | inputs and references; resource limits; tool versions | [Companion tools](COMPANION_TOOL_GUIDE.md) |
| Stored BLASTp evidence | Inspect and reuse saved BLASTp results for these queries. | raw stored results; query mapping; database, settings and date | [Stored BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md) |
| Recover a failed step | Diagnose the failed stage and give a recovery for this run. | run log; status or manifest; input hashes; prior settings | [Recover a failed step](reader/04_RECOVERY_AND_LIMITS.md) |
| Pairwise protein comparison | Compare proteins in these two antiSMASH result ZIPs. | query and reference ZIPs with translated CDS; a working alignment backend; new output folder; optional genome FASTAs | [Pairwise protein comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md) |
| Interactive reader widgets | Build an interactive reader from this package. | package or run folder, or Complete_Package ZIP with manifest; new output folder | [Interactive reader widgets](WIDGET_DELIVERABLES.md) |
| Portable handoff builder | Package this result and its region files for another session. | package with its validation and hashes; optional original antiSMASH ZIP; new ZIP path | [Portable handoff builder](FILES_STORAGE_AND_HANDOFF.md) |
| Project catalog | Register or verify package locations in this project root. | project root; package paths; catalog and manifest hashes when verifying | [Project catalog](PROJECT_CATALOG.md) |
| Private project handoff | Prepare or open a private multi-package handoff. | project root and catalog; package, config and registry files; new archive path, or source archive with its SHA-256; empty import folder when importing | [Private project handoff](PROJECT_CATALOG.md) |
| Project portfolio binding | Check this pointer config and its project registry without running an analysis. | project root; `sapote_project_portfolio_v1` config; contained `sapote_project_registry_v1` JSON; receipt destination if writing | [Project portfolio binding](PROJECT_CATALOG.md) |
| Privacy and evidence metadata validation | Check this privacy profile and evidence TSV as metadata. | `sapote_privacy_profile_v1` JSON; strain evidence registry TSV | [Privacy and evidence metadata validation](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) |

## What each task returns

| Task | Returns | Watch for |
|---|---|---|
| First analysis | inventory, package, validation results, list of requested outputs | `--workbook-strict` fails if the workbook is missing; extraction is not interpretation |
| Read your results | explanation and evidence gaps | read what exists before rerunning |
| Evidence to report | figures, data and scripts, captions, findings, Methods facts, open states | needs no Mode B card; does not approve publication |
| Mode B card | authored card, verifier result, open questions | emit and verify with the same contract; a structural pass is not acceptance |
| Strain slides builder | main PPTX, gene-table PPTX, assets, build receipt | structure gallery needs matching assets, not a tag; annotations are shortened |
| Figure rendering | figures, renderer receipts, page check | can update package integrity records; render from a working copy |
| Companion tools | work order, input/output contract, readiness gaps | read the companion protocol and preflight first; online submission needs a go-ahead |
| Stored BLASTp evidence | per-channel evidence with provenance | keep missing, failed and no-hit apart; no new live search |
| Recover a failed step | failed stage, kept attempt, next action | do not overwrite failures or rerun unrelated stages |
| Pairwise protein comparison | directional per-query best-hit CSV, summary, backend/ANI status | needs both source ZIPs; no-hit is not absence; no complete-proteome, function, compound or taxonomy claim |
| Interactive reader widgets | `OPEN_WIDGETS.html`, seven pages, data, manifest, handoff templates | `PASS` is a render status; empty views and partial refreshes are possible |
| Portable handoff builder | handoff ZIP, `HANDOFF_README.txt`, region count | with no region GBKs it still writes a package-only ZIP |
| Project catalog | catalog, manifest-location report | `verify` can create a missing root or empty catalog; unregistered runs are not found |
| Private project handoff | private ZIP or review folder, catalog, provenance | may include unlisted files and omit external evidence; export refuses an occupied destination; import can be partial; not disclosure approval or a backup |
| Project portfolio binding | binding JSON on stdout, optional `portfolio_binding.json` | default writes nothing; the optional write can replace a receipt and follows symlinks; counts include `NOT_TESTED` |
| Privacy and evidence metadata validation | status, availability summary, open lineage issues | separate from the project-registry schema; `PASS` checks recorded parent links and cycles, but does not verify sources or prove activity or identity |

## Rules for every task

Work from the bundle folder that holds `mamey_run.py` and `pyproject.toml`; an installed `mamey` command may be a different version. Set up with [installation](INSTALL.md) and [prerequisites](PREREQUISITES.md), adding only the extras the task needs. A code ZIP, an antiSMASH result ZIP and a Complete_Package ZIP are different inputs.

Keep original inputs unchanged and record their hashes and versions. Show any single locus as `strain / full node-or-contig / region / BGC alias`; a bare alias can select a locus within one package but does not replace its full reported identity. Missing, failed, not run and tested no-hit are four different states.

To run the pipeline, use the bundle launcher and the workflow in `AGENTS.md`. Document or code review alone does not authorize installation or execution. Follow the current task scope. A structural check passing is not proof of production or activity. Similarity is not compound identity;
capacity is not production; untested is not negative.

## When a request runs into trouble

- A channel or dependency is missing: name it and carry on with the work that does not need it.
- A command fails: keep the actual error and find which stage failed.
- A linked example is old: use the current CLI and named schema.
- A structure gallery is wanted: supply matching structure assets and check the gallery counts in the output, rather than changing only the tag.
