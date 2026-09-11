# SOP-15 — Cross-Chat Merge and Patch Handoff

## Purpose

This SOP lets multiple ChatGPT/Claude chats work on Sapote/Mamey without losing state or accidentally overwriting each other.

## Patch packet requirements

Every patch packet should contain:

- README,
- patch brief,
- apply order,
- diffs,
- modified files,
- tests,
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
7. whether it can merge before cut.

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
2. Patches should include tests.
3. Apply order should be explicit.
4. Other-chat findings should be reconciled before candidate cut.
5. Signed base should remain identifiable.
