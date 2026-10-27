# Workflow guide: choose the next task

Choose your starting point:

- **I have a result package:** [read an existing result](user_guides/READ_EXISTING_RESULT.md), then choose the question you want it to answer.
- **I have an antiSMASH ZIP to process:** follow [the Master Walkthrough](MASTER_WALKTHROUGH.md).
- **I have a partial or confusing run:** use [Troubleshooting](COMMON_MISTAKES.md) before you choose a recovery action.

Use the stages below to find the next unfinished task. How much you can run depends on your environment and on the work you ask for.

| Stage | Start with | Finish when | Continue with |
|---|---|---|---|
| Prepare | Code and a compatible Python environment | You know the loaded version and the capabilities you need | Inspect one input |
| Inspect | Original antiSMASH result ZIP | Input contents and the metadata source are recorded | Explicit extraction settings |
| Extract | A known input and an output folder | The process exits and you keep its output and issue receipts | Validate and explain |
| Review package | A complete package and a question | You understand the saved statuses, relevant issues, evidence coverage and the inventory and triage rows you picked | An interpretation note tied to its source files |
| Interpret | Evidence from the source files for the chosen question | Others can review the claims, alternatives, uncertainty and references | Owner review and a specific follow-up |
| Extend | A defined evidence gap and the tools you may use | Results and their provenance are saved and tied to the correct input | Reassess the original question |
| Handoff | Complete saved artifacts | The recipient can find the files and verify the transferred bytes | Resume from the checkpoint |

You can run extraction and review fully offline with local inputs. A chat assistant can run the program only if its environment has the file access and tools it needs. A local command still has memory, time and disk limits. A model name or a fixed number of strains tells you nothing about capacity.

## Validation and recovery scope

`validate` can report a structurally complete package while gold interpretation is still `JUDGMENT_PENDING`. Workbook content checks only warn unless you pass `--workbook-strict`. `validate` also rewrites the package-status receipt, which is meant to change. To keep the original package bytes, validate a working copy. Read [the recovery states](COMMON_MISTAKES.md#a-validation-or-seal-command-returns-zero) before you treat a zero exit as complete evidence.

The intake harness's `--resume` skips an input only when its completion receipt matches the same input, settings and output tree. It does not resume an extraction partway through a phase. A verified skip reuses earlier evidence; it is not a new measurement. Keep failed and partial outputs. Diagnose them before you replace them in a new destination.

## Decide whether the package answers your question

Write down one observation with its file, field and recorded state. If that evidence answers your question, keep the note with the package identity. If it leaves competing explanations, name the one missing observation that would tell them apart. Then use the follow-up route below.

A package can be ready to read while interpretation is pending. A completed fragment-pair scan can correctly contain zero pairs within its recorded scope. A missing reference dataset is a gap, not a no-hit result. Read the status and input coverage alongside the rows. A positive count alone does not show that the inputs were complete.

A package is the starting point for interpretation. It does not replace the original antiSMASH archive. Later reparsing, parameter changes or more evidence extraction may need that archive. Keep it with its provenance.

## Select follow-up deliberately

Use [the companion-tool guide](COMPANION_TOOL_GUIDE.md) to understand optional searches, alignments, trees and figures. Before you run anything, state the question, the input identities, the destination and the compute scope. Also state any online submission you have permission for. Finishing an offline extraction does not mean optional online work should follow.

For practical problems use [Troubleshooting](COMMON_MISTAKES.md). For transferring or reopening results use [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md). For biological interpretation use [Reading your results](READING_YOUR_RESULTS.md).
