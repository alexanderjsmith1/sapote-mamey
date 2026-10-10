# Troubleshoot and maintain a workflow


## For the person using the results

Start with the symptom. Keep the exact command, final error and affected files. Record what you expected to see, what appeared instead, and whether an earlier stage completed. Preserve the failed attempt; it may contain the receipt needed to explain the problem.

Use [COMMON_MISTAKES.md](../COMMON_MISTAKES.md) to distinguish an input problem, an environment problem, incomplete evidence, a validation failure and a rendering problem. A missing optional tool does not mean every part of the program is unusable. A PDF that exists can still have unreadable pages; the underlying table may preserve the exact record while the layout is repaired.

When requesting help, include the loaded source version, operating system, Python version, input name/hash, output path, exit code and the relevant issue or validation receipt if one exists. Review sample identifiers and paths before sharing them.

Make recovery observable. “It ran again” is less useful than “the intended input records were recognized, the relevant gate passed, and these expected files were inspected.” Change one thing at a time and use a fresh destination for a replacement run.

## For the workflow maintainer

First identify the code and schema that own the affected behavior. Keep a source-bound reproduction and select tests at that boundary. A test import proves neither execution nor passing; a skipped integration case remains a gap. If a route is experimental, optional or sign-off-held, retain that status while improving its explanation.

Make command side effects explicit in user documentation. For example, `workflow` reports stage status but also writes a ledger. In this candidate, its default destination is inside the supplied package. It accepts an external destination:

```bash
python mamey_run.py workflow \
  --package '/your/actual/package' \
  --ledger-out '/your/existing/review-folder/workflow-ledger.md'
```

Use actual paths and a deliberately chosen review destination. The parent folder must exist; check that the ledger was written. `--json` changes the printed representation but still follows the ledger-writing path. `--strict` changes the exit condition for incomplete mandatory steps; it does not author the missing interpretation.

This example is checked against the parser and adapter by static inspection. The driver can also invoke verifier subprocesses. Its final close step always returns N/A, while the mandatory-step check requires PASS; even otherwise complete stages therefore leave `--strict` failing. Keep strict completion held until the closure evidence contract is repaired. This task has not run the complete driver or audited every nested verifier side effect.

## Keep the documentation roles visible

Human guides should explain the task, prerequisites, expected result and recovery in ordinary language. Developer reference should identify interfaces, schemas, compatibility and tests. Agent instructions should state scope, permissions, evidence handling and completion rules. A mixed page can route readers to these sections, but should not require a new researcher to read a coding-assistant contract to understand a result table.

Use a separate lifecycle label for current operating guidance, optional/experimental routes and dated history. A document title or bundle version does not establish that every example was revalidated. Keep generated inventories under their generators and link them to hand-written explanations.

