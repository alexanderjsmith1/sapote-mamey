# Batch execution and continuation

Documented bundle: v9.7.435 / engine 1.9.167


A batch is an operational grouping of inputs, not a fixed biological or model limit. Start with one representative input and inspect measured runtime, memory, disk output and evidence gaps before selecting the next group. Do not infer the appropriate batch size from a historical “three strains” or “four to six strains” rule.

## Before the first run

Confirm the loaded program, actual runtime, input identities, metadata sources and writable destination. Keep original input ZIPs. Select evidence and rendering settings explicitly. State any online scope separately; offline extraction does not authorize searches.

## After each strain

Retain the exact command, exit status, package path, input hash, issue/validation receipts and file counts/bytes. Review extraction status, evidence coverage and interpretation separately. A source-scan label is not proof that every dependency or input was present. Do not manufacture completion by changing a status label manually.

## Continue or stop

If a run completed, preserve its package and proceed only while the environment can support the next input. If it failed, record the failure and diagnose it before retrying into a new destination. Do not assume extraction has a universal resumable checkpoint at every phase. Keep the per-strain packages independent; adding to a master workbook is a separate schema-sensitive action.

A combined ZIP is useful only when it serves the requested handoff. Count its added storage before duplicating already sealed per-strain archives. Save state and available transcripts at each substantive handoff, following the shared policy. Identify transcript gaps explicitly.

## Interpretation handoff

Provide complete packages and source-bound locators for the selected questions. Separate ranking from activity and similarity from identity. Choose the current named Mode B profile through [the current index](../../CURRENT_DOCS_INDEX.md); a historical section count does not define every present workflow. Interpretation can remain pending without obscuring a completed extraction.

See [Workflow Guide](../WORKFLOW_GUIDE.md), [Troubleshooting](../COMMON_MISTAKES.md) and [Files, storage and handoff](../FILES_STORAGE_AND_HANDOFF.md).
