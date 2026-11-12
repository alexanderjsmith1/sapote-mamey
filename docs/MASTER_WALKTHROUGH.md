# Ask an assistant to run your first analysis

This page is for having a coding assistant turn one antiSMASH result ZIP into a
package for you. To run the commands yourself, follow
[Your first run](reader/01_FIRST_RUN.md). To read a saved `Complete_Package.zip`, use
[Read one saved package](reader/03_READ_RESULTS.md). Terms are in the [glossary](GLOSSARY.md).

## Route A: ask your assistant to run it

Give your assistant the program folder and your antiSMASH result ZIP. Use this
request, replacing `EXAMPLE` with your strain name:

> Read AGENTS.md, inspect my EXAMPLE antiSMASH ZIP, run Mamey and validate the
> package. Show me where to open the workbook and explain any warnings.
> Keep the original input and use a new output folder.

Check the answer yourself. The assistant should show you three things:

- the `run` exit code and the `status` it printed;
- the `validate` output, with its exit code;
- the path of the sealed `_Complete_Package.zip`, if produced, or the failure and
  missing artifact. Identify the exact extracted package or copy that was validated;
  do not assume a validation of a different copy proves the ZIP has the same bytes.

[Your first run](reader/01_FIRST_RUN.md#4-check-that-the-run-worked) says what each
exit code and status means. `validate` updates `package_status.json` inside the
package, so ask for a copy to be validated if the original bytes must stay unchanged.

If the assistant cannot run Python or reach the files, run the commands yourself
on a computer that can.

## Route B: run the commands yourself

Follow [Your first run](reader/01_FIRST_RUN.md).

## What next

If present, open `runs/EXAMPLE/package/OPEN_ME_FIRST.html`; otherwise inspect the
issue log and available package files. In either case, use
[Read one saved package](reader/03_READ_RESULTS.md). If something failed, use
[Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md). To move a result, see
[Save and move a result](FILES_STORAGE_AND_HANDOFF.md). For a figure, a comparison or a
Mode B card, pick a question in [Choose a task](USER_TASK_ROUTER.md).
