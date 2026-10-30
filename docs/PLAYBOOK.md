# Plan a Sapote–Mamey result

**Version:** v9.7.461 | **Bundle:** sapote-mamey-v9.7.461

Choose the result you need, then use its maintained guide. If you already have a package,
read it before requesting another extraction. Keep the input path, question, permitted
output location and requested format together in your request.

The previous text is in [the historical Playbook](history/PLAYBOOK.md).

## Choose the next useful result

| You need | Start with | Result to inspect |
|---|---|---|
| A first extraction from an antiSMASH ZIP | [Your first analysis](MASTER_WALKTHROUGH.md) | Package, workbook, validation findings and recorded evidence gaps |
| An explanation of saved results | [Read your results](READING_YOUR_RESULTS.md) | The source inventory, issues and evidence supporting your question |
| Selected figures and short findings | [Evidence to report](EVIDENCE_TO_REPORT.md) and [figure routes](FIGURES_START_HERE.md) | Selected images with plotted data, captions, methods and review records |
| One authored Mode B card | [Profile matrix](MODEB_PROFILE_MATRIX.md), then [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md) | Authored card, selected-contract verification and unresolved evidence |
| A comparison across strains | [Choose a task](USER_TASK_ROUTER.md) and [companion tools](COMPANION_TOOL_GUIDE.md) | The named comparison's tables, provenance and completion evidence |
| A portable interactive reader | [Widget deliverables](WIDGET_DELIVERABLES.md) | Reader pages, source/count receipt and browser review |

For a selected command, check the [command catalog](COMMAND_CATALOG.generated.md) and its
owning guide. Interpretation formats, external analyses and other-model review are selected
work; the [shared assistant contract](../AGENTS.md) and [governance](ASSISTANT_GOVERNANCE.md)
keep that work within the request.

## Translate an older tier request

The older playbook used conversational tier names. Use the table to clarify the intended
result; these names are not CLI flags or automatic workbook selectors.

| Older request | Choose now |
|---|---|
| Tier 1: Mamey run | The first-analysis extraction and validation route |
| Tier 2: Sapote standard | A bounded interpretation of existing evidence; use the optional workbook plan below if requested |
| Tier 3: Sapote deep | The specific cards, figures or report the question needs, with a named card profile when applicable |
| Tier 4: Cross-strain | A named comparison with the authoritative strain roster and bound sources |
| Gene-by-gene or literature request | One complete locus identity and the admitted evidence for that question |
| Go deeper | One next question and its required evidence, rather than automatic production of the next tier |

A source observation and an interpretation serve different purposes. Retain the original
extraction, then bind each interpretation to its actual evidence. Keep lead priority separate
from claim confidence. Domain patterns and KCB matches support bounded hypotheses; they do
not by themselves establish product identity, activity or physical linkage. Display an
individual locus as **strain / full node-or-contig / region / BGC alias** from one bound record.
Missing evidence stays explicit.

## Optional five-sheet interpretation plan

If you select the old Tier 2 workbook format, these names can organize a manual deliverable.
No command writes these sheets.

| Sheet | Content to prepare |
|---|---|
| `S1_Sapote_Leads` | Source-bound lead observations, priority, claim confidence and a supported claim ceiling |
| `S2_Triage_Board` | The original triage values with separately identified interpretation columns |
| `S3_Deep_Analysis` | Selected loci's source observations and authored interpretation |
| `S4_Wetlab_Plan` | Only a separately requested follow-up plan, with its unresolved evidence and approval needs |
| `S5_Exec_Summary` | Main finding, assembly/evidence limits and one useful next action |

Keep a working workbook separate from original evidence. Agree on the selected loci and
sheets before authoring; a missing optional sheet does not redefine the requested task as
incomplete. A current Mode B card uses its selected profile, rather than this worksheet plan.

## Check and hand over what you selected

Return paths to the requested files, the checks actually performed, relevant evidence and
remaining holds. A template, saved completion label or a general self-check statement does
not replace the corresponding source review or verifier result. Keep source paths and
hashes with the result. Before a post-seal command, read its [write boundary](POSTSEAL_READERS.md);
an external destination alone does not establish that the source package remains unchanged.

### Current advisory sign-off selection

Use explicit current artifact paths when requesting sign-off review:

```bash
python mamey_run.py signoff '<tree.treefile>'
```

The bundle CLI exposes files and `--minutes` only. Use the direct helper when
selection requires its additional options:

```bash
python tools/signoff_check.py --root '<review-root>' --outgroup '<declared-tip-token>' '<tree.treefile>'
```

The helper accepts repeated/comma-separated outgroup terms; recognizing a label
is not approval of outgroup choice. Without explicit files, it walks the selected
root for case-sensitive `.treefile` names modified in the last 90 minutes by
default. Hidden directories and its named environment/database/reference pruning
list are excluded; `SIGNOFF_PRUNE_DIRS` adds exclusions. This is a selected recent
file sweep, not the authoritative artifact roster or proof of current-run input
binding. Record the exact files, hashes, source/run identities, scan window and
exclusions separately. Use explicit paths for required older or pruned artifacts.

The report checks regex-extracted labels and support-like text rather than fully
validating Newick structure, every numeric measurement or provenance. It does not
read ANI data, validate comparator downloads or make biological sign-off decisions.
Those are independent review requirements. No structured receipt or report file
is saved by the helper; retain console diagnostics with the selected input hashes.

Valid advisory invocations return 0 for issues, read failures, an incomplete walk
and no selected files. `--quiet-if-clean` can suppress the no-selection message or
caution notes when no issues were found. Silence is not a completed clean review.
The direct helper parses its options with argparse. `--help` prints usage and
exits 0. An unknown option, a missing value or a non-numeric `--minutes` exits 2.
Do not use its exit alone for input admission or completion. The bundle CLI has
its own parser and does not offer these extra helper options.
