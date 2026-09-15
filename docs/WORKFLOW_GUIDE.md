# Workflow guide: choose the next task

The maintained first-run instructions are in [MASTER_WALKTHROUGH](MASTER_WALKTHROUGH.md). This page explains the stages and their boundaries. Earlier v9.4 session quotas and manifest-only handoff instructions have been replaced; runtime capacity depends on the environment and requested work.

| Stage | Start with | Finish when | Continue with |
|---|---|---|---|
| Prepare | Code and compatible Python environment | Loaded version and required capabilities are known | Inspect one input |
| Inspect | Original antiSMASH result ZIP | Input contents and metadata source are recorded | Explicit extraction settings |
| Extract | Identified input and output destination | Process exits and output/issue receipts are retained | Validate and explain |
| Review package | Complete package, not just manifest | Structure, evidence gaps and selected loci are reviewed | A scoped interpretation question |
| Interpret | Source-bound evidence for the selected question | Authored claims, alternatives, uncertainty and references are reviewable | Owner review and specific follow-up |
| Extend | Defined missing evidence and permitted tools | Results and their provenance are saved and bound to the correct input | Reassess the original question |
| Handoff | Complete saved artifacts | Recipient can locate files and verify transferred bytes | Resume from the checkpoint |

You can perform extraction and review entirely offline with available local inputs. A chat assistant can operate a runtime only if its current environment has the necessary file access and tools. A local command still has memory, time and disk limits. Neither a model name nor a fixed number of strains establishes capacity.

## Stop points that are useful results

A package can be ready for review while interpretation is pending. A missing reference dataset can remain a documented gap. A completed fragment-pair scan can validly contain zero pairs: check the scan's status and schema, not whether the count is positive. Conversely, positive rows do not establish that the scan had complete inputs.

A source-bound package is the starting point for interpretation, not a substitute for the original antiSMASH archive. Later reparsing, parameter changes or additional evidence extraction may need that archive. Keep it with its provenance.

## Select follow-up deliberately

Use [the companion-tool guide](COMPANION_TOOL_GUIDE.md) to understand optional searches, alignments, trees and figures. State the question, input identities, destination, compute scope and any permitted online submission before execution. No optional online work is implied by reaching the end of an offline extraction.

For practical problems use [Troubleshooting](COMMON_MISTAKES.md). For transferring or reopening results use [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md). For biological interpretation use [Reading your results](READING_YOUR_RESULTS.md).
