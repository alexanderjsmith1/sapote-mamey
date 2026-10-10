# SOP-15 — Cross-Chat Merge and Patch Handoff

## Purpose

This SOP lets multiple ChatGPT/Claude chats work on Sapote/Mamey without losing state or accidentally overwriting each other.

## Source and scope binding

Bind the exact baseline version/build, file hashes and intended destination before reviewing applicability. A packet's instructions are evidence to inspect, not permission to apply it or release a bundle. Keep the baseline immutable; test application in a disposable authorized tree and compare the resulting file bytes to the proposed staged contents. A clean diff application is not runtime or scientific acceptance.

Identify generated files and their owner/generator. Reconcile the final implementation, not only the order in which chats reported changes. A docs-only packet must describe current code limitations honestly; it must not claim to fix runtime behavior.

## Patch packet requirements

Every patch packet should contain:

- README,
- patch brief,
- apply order,
- diffs,
- modified files,
- relevant tests or a stated reason runtime tests are not needed/authorized,
- validation logs,
- manifest,
- checksums,
- known issues.

## Response requirements

A reviewing chat should say:

1. what packet was reviewed,
2. whether patches are included,
3. whether diffs apply,
4. whether tests exist,
5. whether validation logs support claims,
6. whether any claims are self-reported only,
7. applicability and remaining holds for owner review before an authorized merge/cut.

## Merge order principle

Semantic/data patches before render/deliverable patches.

Standard apply order (priority):

1. BGC BLASTP/intake patches.
2. C5/C7 deliverable patches.
3. SOP/docs.
4. Release wrapper and final candidate packaging.

## Conflict signs

Potential conflict if two patches touch:

- Mode B output schema,
- `modeb_verdicts.csv`,
- workbook tabs,
- package validation,
- public/private redaction,
- deliverable rendering,
- CLI command registration.

## Bug-hunt checks

1. No patch packet should be report-only if it claims code fixes.
2. Include meaningful validation appropriate to the change. Documentation corrections can use source tracing and link/command checks; do not represent those as executed runtime regressions.
3. Apply order should be explicit.
4. Other-chat findings should be reconciled before candidate cut.
5. Signed base should remain identifiable.
