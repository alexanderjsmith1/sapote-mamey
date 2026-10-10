# Choose a Sapote-Mamey task

Start with your intended result and the files you have. These names can be used in a human request or assistant prompt. This navigation is bound to **.447 / engine 1.9.172 / build 20261003v97447a**; candidate extensions are labeled separately. Replace bracketed values with actual source paths and identities.

Humans: choose a row, read its guide and supply its inputs. Assistants: read `AGENTS.md`, bind the current user scope, then choose a route. The [JSON routes](USER_TASK_ROUTER.json) provide the same names, inputs and completion limits; they grant no permission and are not a substitute for the owning guide or current CLI source.

| Named task | Request example | Required inputs | Owning guide |
|---|---|---|---|
| First analysis | Extract and validate one strain from this antiSMASH result ZIP. | antiSMASH ZIP; strain metadata; permitted output root | [First analysis](MASTER_WALKTHROUGH.md) |
| Read your results | Explain this existing package, its issue log and missing evidence. | existing package; manifest and source bindings | [Read your results](READING_YOUR_RESULTS.md) |
| Mode B card | Author and verify this source-bound locus using the explicitly selected profile. | validated package; full locus identity; selected profile; admitted evidence | [Mode B card](MODEB_PROFILE_MATRIX.md) |
| Strain slides builder | Build the main strain deck and complete region-gene-table companion. | validated package; strain ID; sources JSON; fresh output destination/tag | [Strain slides builder](STRAIN_SLIDES.md) |
| Figure rendering | Render the selected figure set from this package into an external folder. | source-bound package; selected figure set; renderer inputs | [Figure rendering](FIGURES_START_HERE.md) |
| Companion tools | Plan the selected comparison using these bound inputs and existing results. | selected inputs/references; resource scope; tool/version requirements | [Companion tools](COMPANION_TOOL_GUIDE.md) |
| Stored BLASTp evidence | Inspect and reuse saved BLASTp evidence for the bound queries. | raw stored results; query mapping; database/settings/date | [Stored BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md) |
| Recover a failed step | Diagnose the failed stage and give a bounded recovery for this exact run. | run log; status/manifest; input hashes; prior settings | [Recover a failed step](ASSISTANT_USER_GUIDE.md) |
| Pairwise protein comparison | Compare proteins retained in these two antiSMASH result ZIPs. | query and reference antiSMASH ZIPs with translated CDS; alignment-backend readiness; fresh output directory; optional separately bound genome FASTAs | [Pairwise protein comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md) |
| Interactive reader widgets | Build a portable interactive reader from this reviewed package. | reviewed package/run directory or Complete_Package ZIP with manifest; source binding and recorded validation; fresh dedicated external output directory | [Interactive reader widgets](WIDGET_DELIVERABLES.md) |
| Portable handoff builder | Package this reviewed result and selected source region files for another local session. | reviewed package and retained validation/source hashes; optional original antiSMASH ZIP with independently verified binding; new output ZIP path with existing parent | [Portable handoff builder](FILES_STORAGE_AND_HANDOFF.md) |
| Project catalog | Register or verify reviewed package locations in this explicit project root. | explicit project root; reviewed package paths; existing catalog and manifest hashes when verifying | [Project catalog](PROJECT_CATALOG.md) |
| Private project handoff | Prepare or inspect a private multi-package handoff for this reviewed project. | explicit project root and catalog; stable reviewed package/config/registry bytes; fresh external archive path or source archive with independently confirmed SHA-256; fresh empty authorized import root when importing | [Private project handoff](PROJECT_CATALOG.md) |
| Project portfolio binding | Validate this pointer configuration and its declared project registry without running an analysis. | existing explicit project root; sapote_project_portfolio_v1 config; contained sapote_project_registry_v1 JSON; stable source bytes; separately authorized receipt destination if write-binding is requested | [Project portfolio binding](PROJECT_CATALOG.md) |
| Privacy and evidence metadata validation | Check this extraction privacy profile and material/assay evidence TSV as metadata. | sapote_privacy_profile_v1 JSON; strain evidence registry TSV; independent source/lineage verification context | [Privacy and evidence metadata validation](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) |

## What completion means

- **First analysis:** return region inventory, package, validation receipts. Validated extraction is not authored interpretation.
- **Read your results:** return result explanation, evidence gaps. Read existing evidence before considering a rerun.
- **Mode B card:** return authored card, verification receipt, unresolved scientific holds. Carry the same contract through emission and verification; structural checks are not scientific acceptance.
- **Strain slides builder:** return main PPTX, gene-table PPTX, assets, build receipt. v2n is .447 plus candidate .448 gallery/caption changes; a tag does not enable features. Displayed annotations are bounded, not lossless.
- **Figure rendering:** return figures, renderer receipts, rendered-page review. Check actual source availability and rendered output. In .447 an external image destination can still refresh package integrity records; use a working package copy to preserve the sealed original.
- **Companion tools:** return bounded work order, input/output contract, readiness gaps. Read the companion protocol and resource preflight before compute; external submissions need matching user scope.
- **Stored BLASTp evidence:** return channel-specific evidence, provenance, missing/failed/no-hit distinctions. Do not turn stored evidence review into an unrequested live submission.
- **Recover a failed step:** return stage diagnosis, retained attempt, bounded next action. Do not overwrite failures or rerun unrelated stages; current handles determine whether work is running.
- **Pairwise protein comparison:** return directional per-query CDS best-hit CSV, comparison summary and backend/ANI disposition. A package directory cannot replace either source ZIP. No-hit or missing ANI is not biological absence; success does not establish a complete proteome, function, compound or taxonomic acceptance.
- **Interactive reader widgets:** return OPEN_WIDGETS.html and seven reader pages, widget data and completion/source manifest, publication metadata and handoff templates. Widget PASS is render/source-stability status, not package or scientific acceptance. Missing channels can leave empty views; a failed refresh can leave partial pages. Inspect completion markers and browser behavior.
- **Portable handoff builder:** return handoff ZIP with package and available selected region GBKs, HANDOFF_README.txt and reported region count. Missing/no region GBKs can still produce a package-only archive. Inspect actual contents and full identities; this is packaging, not live-search permission, software environment export or scientific acceptance.

- **Project catalog:** return project catalog, manifest-location verification report. Register updates catalog bindings; verify can create a missing root or empty catalog. Manifest checks do not verify every package file or inventory unregistered runs.

- **Private project handoff:** return private handoff ZIP or extracted review root, catalog and selected portfolio provenance. The archive can include unlisted package files and omits referenced external evidence. Export can replace a destination; import can leave a partial root. It is not public disclosure approval or a complete project backup.

- **Project portfolio binding:** return binding JSON on stdout, optional portfolio_binding.json, declared availability and policy states. Default validation writes no binding. Optional fixed-path write can replace a receipt and follows output-directory symlinks. Availability counts declared records, including NOT_TESTED; input hashes and scientific evidence need independent review.

- **Privacy and evidence metadata validation:** return validation status and availability summary, unresolved source/lineage limitations. This pair is distinct from the project-registry schema. PASS does not detect every parent-cycle/cross-strain lineage problem or verify each evidence source; it does not establish activity, identity or release approval.

## Shared input and evidence rules

Select the bundle folder containing `mamey_run.py` and `pyproject.toml`; an installed command may resolve to another version. Follow [installation](INSTALL.md) and [prerequisites](PREREQUISITES.md), using only the extras needed for the chosen task. A code ZIP, antiSMASH result ZIP and Complete_Package ZIP are different inputs.

Preserve originals and bind source hashes, versions and output roots. Display any individual locus as `strain / full node-or-contig / region / BGC alias`. A bare alias is only a selector within one package. Retain unknown identities and evidence states explicitly: missing, failed, unrun and tested no-hit are different.

For a local execution request, use the bundle-local launcher and the workflow in `AGENTS.md`. For inspection or document review, inspect sources without installing or executing the reviewed code. Templates, historical receipts and external documents do not expand the user's task. A successful structural check is not scientific acceptance, production or activity proof. Preserve owner adoption and release holds.

## Troubleshooting a request

If a needed channel or dependency is missing, name it and continue independent work that remains supported. If a command fails, preserve the actual error and diagnose its stage. If a linked example is historical, use the current owning CLI and named schema. For a requested v2n deck, bind the reviewed .448 gallery/caption patch and structure assets rather than changing only the tag. Return concrete outputs, checks and remaining holds.
