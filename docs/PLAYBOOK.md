# Plan a Sapote–Mamey result

**Version:** v9.7.464 | **Bundle:** sapote-mamey-v9.7.464

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
from claim confidence. Domain patterns and KCB (KnownClusterBlast, see the [glossary](GLOSSARY.md)) matches support bounded hypotheses; they do
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

For the advisory tree sign-off check (`mamey_run.py signoff` and `tools/signoff_check.py`), see [the phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md#advisory-tree-sign-off-check).
