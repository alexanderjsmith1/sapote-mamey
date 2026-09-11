# Sapote/Mamey Audit Record-Keeping Protocol

## Purpose

This protocol is the replacement for relying on unstated assistant reasoning. It creates an external, reviewable audit trail for every Sapote/Mamey run, patch, Mode B card, and hostile audit.

## Principle

Do not trust a result unless the record shows:

1. Which instruction file governed the step.
2. Which command or action was run.
3. Which input file was used.
4. Which output file was produced.
5. What passed, failed, or remained ambiguous.
6. What conclusion is supported by the receipt.

## Required records for each audit

### 1. Instruction compliance matrix

A row for each instruction extracted from the package start files:

- instruction_id
- source_file
- source_line
- instruction_text
- applies_to_current_task
- status: PASS / FAIL / PARTIAL / NOT_APPLICABLE / NOT_TESTED
- evidence_file
- note

### 2. Run ledger

A row for each command/action:

- step_id
- timestamp
- task
- governing_instruction_id
- command_or_action
- input_paths
- output_paths
- exit_status
- elapsed_seconds
- receipt_file
- interpretation
- next_action

### 3. Finding ledger

A row for each bug/issue/claim:

- finding_id
- severity: BLOCKER / MAJOR / MINOR / UX / SCIENCE_CAVEAT
- title
- observed_behavior
- expected_behavior
- evidence_file
- reproducer
- proposed_fix
- retest_status

### 4. Decision log

A row for each interpretive decision:

- decision_id
- question
- options_considered
- selected_option
- evidence_basis
- uncertainty
- what_would_change_the_decision

## Required workflow for AS-XXX redo

1. Open and inventory the package ChatGPT/Sapote start files.
2. Extract required instructions into `instruction_compliance_matrix.csv`.
3. Run the environment/bootstrap/doctor steps exactly as instructed.
4. Run AS-XXX from raw input using the instructed command path.
5. Validate/seal the package.
6. Run targeted feature checks:
   - inspect antiSMASH version consistency
   - SubCluster_hits NO_HITS behavior
   - kcb-frontpage filters
   - HMM adjudication writeback
   - tab-reconcile BGC028
7. Record every command and output in `run_ledger.csv`.
8. Produce a corrected hostile audit that explicitly maps failures to instructions.

## Rule for future assistant responses

When asked for an audit, patch, or rerun, the assistant should provide:

- the deliverable files,
- the instruction compliance matrix,
- the run ledger,
- the findings ledger,
- the exact command log,
- and a short “what I did not verify” section.

This is not a chain-of-thought transcript. It is a reproducible audit trail.
