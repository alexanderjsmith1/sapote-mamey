# Current Docs Index — v9.7.433 · engine 1.9.167 · build 20260917v97433c

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
- [Mode B authoring](wiki/Mode-B-Gene-First-and-48-Section-Manual.md): use the selected machine-readable
  profile and its emitted template; legacy section counts do not replace a named current profile.
- [BLASTp evidence](docs/ONLINE_BLASTP_PROTOCOL.md): existing results first, optional live submission.
- [BiG-SCAPE cohort walkthrough](docs/BIGSCAPE_COHORT_WALKTHROUGH.md) and [troubleshooting](docs/troubleshooting/BIGSCAPE_TROUBLESHOOTING.md): stage region files, run a cohort, inspect family verdicts and figures.
- [Phylogenetic workflow](docs/PHYLO_AUTOPILOT_WORKFLOW.md), [placement](docs/PHYLO_PLACEMENT_WORKFLOW.md),
  and [companion tools](docs/LLM_COMPANION_TOOL_PROTOCOL.md): inputs, resource scope and run receipts.
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

## Reference, development and history

[Guide navigation](docs/GUIDE/00_README.md) distinguishes the operational guides from the dated
Encyclopedia and newsletter. A current bundle stamp identifies packaging; it does not prove that
every scientific statement or historical experiment was revalidated for that cut.

[Engine reference](docs/reference/00_README.md) and [Encyclopedia currency](wiki/Encyclopedia-Currency.md)
record reference scope. Consult current code and named schemas for numerical behavior.
[Figure repair records](docs/figure_factory/README.md), `docs/working/`, `docs/release_planning/`,
and `docs/patch_notes/` are engineering records, not an alternative user setup sequence.

[History](docs/history/README.md), [release history](RELEASES_LOG.md), and [changelog](CHANGELOG.md)
preserve dated decisions. Historical commands, counts, results and proposed features in those records
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
