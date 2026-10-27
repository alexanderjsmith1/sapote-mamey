# Read an existing result


You can start from a result someone has already produced. You do not need to install Python to open the HTML entry page, workbook or tables. Keep the result package together and make a separate working copy for notes.

## Start with your question

Write one question before opening the ranked table. For example: which regions need closer gene-level review, or which evidence is missing for an interpretation? A question helps you choose useful evidence without treating a high score as an answer.

## Check what you received

Find the Complete_Package ZIP and the strain/run identity. Keep the original archive. Extract a copy and open `OPEN_ME_FIRST.html`. Check the strain/run, then follow the file that answers your question:

- **What happened during extraction?** Read `issue_log.md` and the entry-page status details.
- **What checks were saved?** Read `gate_validation.json`; `package_status.json` may hold a later, mutable status receipt.
- **Which region should I inspect?** Open the workbook, then the matching inventory and triage rows.

For an older entry page, follow the underlying files rather than relying on its badge alone.

Four questions have separate answers:

- Did the command finish?
- Did the package pass its encoded checks?
- Which evidence channels actually completed, within what scope?
- Has someone authored and reviewed the interpretation?

“Complete” in one place does not answer all four. A generated template or triage table can still need interpretation.

## Open the tables

Use the per-strain workbook to browse. Use the inventory table to establish the region and its boundary; use the triage board to understand why it was prioritized. Copy the complete identity from the same run before taking notes: **strain / full node-or-contig / region / BGC alias**. Ranks and aliases can change between runs.

For one selected row, record the observed value and where you found it, the interpretation it supports, and what remains unresolved. A reference match describes similarity under a particular method. It does not establish that the organism produces the reference compound. A routing score is not a measured assay result or a probability.

## Treat missing evidence precisely

Read a zero together with its channel status. A completed scan with no retained matches says that the operation found none within its recorded inputs and limits. An unavailable input, an incomplete parse or a failed operation cannot answer that same question. Keep the recorded state in your note, then decide whether the gap changes your interpretation.

If you need help, share the question, exact package/run identity, selected file or row, and the recorded issue. A manifest by itself does not transmit the evidence files it names. Review identifiers before sharing them.

## A short note you can write

**Question:** what am I trying to decide?

**Identity and source:** which exact record and run am I reading?

**Observed:** what does the source actually show?

**Interpretation and alternative:** what could explain it?

**Gap and next evidence:** what would distinguish the alternatives?

Save this note outside the preserved package. For a detailed explanation of each file and status, use the existing [READING_YOUR_RESULTS.md](../READING_YOUR_RESULTS.md). For a fault or missing file, use [COMMON_MISTAKES.md](../COMMON_MISTAKES.md).


