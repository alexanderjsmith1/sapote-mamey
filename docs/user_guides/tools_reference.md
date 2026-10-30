# Find a helper tool

Choose a task below, then open its guide for the inputs and command. For your
first antiSMASH ZIP, start with [Your first run](../reader/01_FIRST_RUN.md).

The [command catalog](../COMMAND_CATALOG.generated.md) lists launcher commands.
The [tools inventory](../TOOLS_INVENTORY.generated.md) lists helper scripts from
their source docstrings. The [external-tool inventory](../EXTERNAL_TOOL_INVENTORY.md)
covers separately installed programs. Check these lists before writing another helper.

Run commands from the selected bundle directory in your activated environment.
For the flags supported by that build, open the command's help:

```bash
python mamey_run.py --help
```

## Read or build a result

- **Open a saved package or select BGC rows:** [reading results](../READING_YOUR_RESULTS.md).
- **Make strain slides and gene tables:** [strain slides](../STRAIN_SLIDES.md).
- **Write a Mode B card:** [authoring walkthrough](../MODE_B_USER_WALKTHROUGH.md)
  and [profile choices](../MODEB_PROFILE_MATRIX.md).
- **Render package figures:** [figure entry point](../FIGURES_START_HERE.md).
- **Make interactive HTML:** [widgets](../WIDGET_DELIVERABLES.md).
- **Compare source ZIPs:** [offline pairwise comparison](../../sapote_addons/README_OFFLINE_ANALYSIS.md).
- **Transfer selected files:** [save and transfer results](../FILES_STORAGE_AND_HANDOFF.md).
- **Combine an existing V7 report and Mode B material:** [report-builder inputs](../reference/06_CURRENT_SOURCE_SCOPE.md#combined-v7-and-mode-b-report-builder).

A template is a starting file for writing. Keep the same selected profile during
emission and verification, and identify each locus as
**strain / full node-or-contig / region / BGC alias**.

## Check text, tables or source files

Choose the check for the file you actually have:

- **Markdown links:** [link-check scope](../CATALOG_MAINTENANCE.md#markdown-link-checks-and-hook-scope).
- **Citations and source disclosure:** [finished-text checks](../reference/06_CURRENT_SOURCE_SCOPE.md#finished-text-citation-hygiene-and-strict-source-disclosure).
- **Registry IDs:** [duplicate-check inputs](../REGISTRY_JSON_CSV_PARITY_NOTE_v9.7.141.md#registry-id-checker-scope).
- **Input hashes or software-release ZIP names:** [manifest and ZIP checks](../reference/06_CURRENT_SOURCE_SCOPE.md#input-manifests-and-zip-preflight-scopes).
- **Workbook ratios or evidence conservation:** [their separate checks](../reference/06_CURRENT_SOURCE_SCOPE.md#cross-strain-denominator-and-conservation-audit-coverage).
- **A public workbook candidate:** [disclosure audit](../CUSTOM_PRIVACY_TIERS.md#public-workbook-audit-limits).
- **An existing 16S store:** [defect and merge screens](../reference/06_CURRENT_SOURCE_SCOPE.md#16s-store-defect-validation-and-additive-merge-screening).

`sapote_md_preflight.py` processes Markdown into a separate file. If tables are
routed out of the body, supply an appendix destination so they are saved.
`professionalism_linter.py` reports text warnings; confirm that it read every
requested file, since unreadable files can be skipped. Neither replaces inspection
of the rendered document.

For software maintenance, `silent_exit_audit.py` scans selected Python source
for possible quiet-success paths. Review its matches in the source. Catalog generation and source-scanning commands belong in
a working checkout with separate diagnostic outputs.

## Suite-receipt verification and recovery

External receipt verification and local suite recording use different schemas.
Read [the receipt guide](../reference/06_CURRENT_SOURCE_SCOPE.md#configured-suite-receipts-two-owners-and-different-contracts)
before rerunning a producer: the recorder's `run` action executes the slow/network
suite and replaces local approval/log state.

## Earlier execution records

The [preserved tools-reference snapshot](../history/TOOLS_REFERENCE_v9_7_460.md)
contains the earlier verification matrix and development records. Use it to trace
an old result; use the current task guides above for commands.
