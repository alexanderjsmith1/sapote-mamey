# Current Docs Index — v9.7.428 · engine 1.9.163 · build 20260911v97428a

Start with [README](README.md) for the program and [Quick Guide](docs/GUIDE/02_Quick_Guide.md)
for a first run. [AGENTS](AGENTS.md) is the canonical portable coding-assistant contract. Its
generated `CLAUDE.md` copy supports Claude discovery; other assistants must be directed to AGENTS
or receive it through their supported instruction mechanism.

## Operating guides

- [Installation](docs/INSTALL.md), [prerequisites](docs/PREREQUISITES.md), and
  [external assets](docs/EXTERNAL_DATA.md): environment setup and separately supplied data.
- [User manual](docs/GUIDE/01_User_Manual.md): running analyses and reading outputs.
- [Command catalog](docs/COMMAND_CATALOG.generated.md) and [deliverable menu](docs/DELIVERABLE_MENU.md):
  generated command and capability navigation. The menu is maintained by the deliverables registry.
- [Glossary](docs/GLOSSARY.md): canonical reader-facing terms.
- [Mode B authoring](wiki/Mode-B-Gene-First-and-48-Section-Manual.md): use the selected machine-readable
  profile and its emitted template; legacy section counts do not replace a named current profile.
- [BLASTp evidence](docs/ONLINE_BLASTP_PROTOCOL.md): existing results first, optional live submission.
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

## Maintaining this index

Update links when the owning workflow changes. Keep generated command, capability, version and
release surfaces under their existing generators. Review document content before claiming currency;
do not turn a version-stamp update into a claim of a full content review.
