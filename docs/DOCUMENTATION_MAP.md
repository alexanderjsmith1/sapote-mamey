# Find the right document

Start with [the file you have](READER_START_HERE.md), then follow one focused reader guide below. The short guides own the compact recipes; the longer walkthrough and result-reading references remain available for detail.

| Your task | Maintained entry point |
|---|---|
| Prepare inputs and an environment | [Inputs and setup](reader/02_INPUTS_AND_SETUP.md) |
| Extract one supplied antiSMASH ZIP | [Your first extraction](reader/01_FIRST_RUN.md) |
| Choose an output to request | [Deliverable menu](DELIVERABLE_MENU.md) |
| Understand a saved result and its evidence gaps | [Read one saved package](reader/03_READ_RESULTS.md), [Glossary](GLOSSARY.md) |
| Understand how evidence becomes a claim | [Evidence and interpretation white paper](INGEST_AND_PRINCIPLES_WHITEPAPER.md) |
| Recover an incomplete attempt | [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md) |
| Look up a specific error | [Troubleshooting](COMMON_MISTAKES.md) |
| Reopen, move or archive results | [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md) |
| Understand an optional tool | [Companion Tool Guide](COMPANION_TOOL_GUIDE.md), then [actual run contracts](COMPANION_RUN_CONTRACTS.md) |
| Request the builder for strain and gene-table decks | [Strain slides builder](STRAIN_SLIDES.md) |
| Use roster/dossier/cohort reader tools | [Multi-Cohort Comparison Toolkit](../deliverable_tools/README.md) |
| Recover BiG-SCAPE reader outputs | [Reader recovery and exact binding](../tools/BIGSCAPE_READER_RECOVERY.md) |
| Reuse governed document templates | [Token-light document factory](TOKEN_LIGHT_DOCUMENT_FACTORY.md) |
| Compare gene-cluster families across a cohort | [BiG-SCAPE cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md), [troubleshooting](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md) |
| See actual offline examples | [Type Strain walkthroughs](TYPE_STRAIN_WALKTHROUGHS.md) |
| Find a specialist workflow | [Current Docs Index](../CURRENT_DOCS_INDEX.md) |
| Look up a command | [Generated command catalog](COMMAND_CATALOG.generated.md), then source-compatible help and the command's own write contract |

The [human and machine task router](USER_TASK_ROUTER.md) pairs request names with inputs, outputs and completion limits. The [examples index](../examples/README.md) distinguishes fixtures, illustrative prose and retained historical records. A familiar tool name or generated catalog grouping does not establish read-only behavior or successful installation.

## Why similar titles exist

START_HERE and HOW_TO_USE are routing pages. WORKFLOW_GUIDE explains stage boundaries. READER_START_HERE selects the file-based route. The short reader guides hold the compact first-extraction, setup, saved-result and recovery instructions. The Master Walkthrough is the detailed first-run reference, including the assistant request; READING_YOUR_RESULTS and COMMON_MISTAKES provide deeper field and troubleshooting explanations. GUIDE/02_Quick_Guide is a compact/advanced reference. The root-level docs/QUICK_GUIDE is a preserved superseded document. The older worked example is retired to docs/history; TYPE_STRAIN_WALKTHROUGHS holds the recorded worked cases.

Historical version numbers in a title do not by themselves prove a document is obsolete: some named contracts remain referenced by current code. Check inbound references and ownership before moving or deleting one. Generated command/capability catalogs should be refreshed through their generator during the appropriate maintenance step, not edited as prose to manufacture agreement.

## For documentation maintainers

The checks below help maintain entry points and pointers. Open the details for the check you need; readers following a workflow can continue in the task guides above.

<details>
<summary>Maintenance rules and static-check scope</summary>

## Maintenance rules

Do not bulk-move or delete documents. Replace misleading onboarding text in place. Mark an older worked example with an explicit historical notice rather than deleting it. Classification is navigation triage, not a claim that every scientific statement was independently validated. Specialist scientific and historical claims need scoped reviews against their implementations and evidence.

## Onboarding-funnel maintenance check

```bash
python tools/check_onboarding_funnel.py --root '<selected-bundle>'
```

The default check reads root-level Markdown entry points and compares the `AGENTS.md`/`CLAUDE.md` twins byte for byte. It does not import the engine or run `start`. Root-only, case-sensitive filename globs select existing doors; nested specialist guides and differently cased names are outside that roster. Missing canonical twins fail, but not every other intended door is required to exist. Preserve the independently intended entry-point list alongside the printed checked names (`tools/check_onboarding_funnel.py`).

For ordinary doors, a substring `python mamey_run.py start` **or** `AGENTS.md` anywhere in the first 12 lines satisfies the check. `README.md` is scanned in full. Comments, negated instructions and a self-reference can satisfy these literals; the checker does not verify an actual redirect, noncircular destination or reader-visible command. A PASS is this literal/twin invariant, not proof that a human or LLM can follow the route successfully. Review actual entry-point text and links in context; keep the canonical twins synchronized when changing them.

Optional `--run-start` executes the selected runner with the current Python interpreter as `start --no-doctor`, up to 180 seconds, and requires exit 0 plus the `python mamey_run.py` idiom in stdout. It omits doctor and is a subprocess operation, not the default static check or proof that the full setup/workflow completed. Select that operation only within the authorized execution scope; preserve full stdout/stderr, actual interpreter/runner identity and result independently. The helper's normal report has no input hashes or persisted receipt. Normal check failures return 1; unexpected file-reading errors can instead raise without a complete report. Record incomplete states rather than inferring acceptance from output alone.

## Checking documented command names

Maintainers can use `python tools/check_command_pointers.py` to find some stale command names before adopting a documentation patch. It scans the bundle root derived from the script's location, not a caller-selected documentation or staged-patch directory. It builds the core parser's command set and also permits a fixed add-on command list (empty at present); an allowed add-on pointer would not prove the add-on is installed.

Treat this as a narrow pointer check. The pattern recognizes only a backtick immediately followed by lowercase `mamey`, one literal space and an alphabetic command token. Shell-fenced commands on their own lines, `python mamey_run.py ...`, different case/spacing and command options are outside that predicate. The scan considers lowercase `.md`, `.txt`, `.py`, `.html` and `.rst` filename suffixes, skips paths containing `/.git` or `__pycache__` and every file named `check_command_pointers.py`. It does not verify arguments, inputs, installed tools, write effects or successful execution. Review a flagged historical example in context; preserve its dated record instead of deleting it merely to clear the check.

Unreadable files/directories are reported and make the normal check return 1, as do matched names outside the allow-set. However, file decoding ignores invalid UTF-8 bytes rather than treating them as unreadable. A normal return 0 means no disallowed token or recorded read failure was found in that selected scope; an empty readable scope can also satisfy it. The tool does not emit inspected-file counts, input hashes or a coverage receipt. Preserve the command, exact bundle/source identity and intended document roster, and verify source-compatible help for each command actually used. Parser/import failures can prevent the normal report; retain that as an incomplete check (`tools/check_command_pointers.py`).

## Checking brace characters in entry names

For a selected tree, maintainers can run `python tools/check_no_brace_paths.py /path/to/tree`; omitting the root selects the bundle containing the script. The check enumerates descendant file and directory entries through `tools/_safe_walk.py` and tests each entry's own name for `{` or `}`. It does not examine the selected root's name or its ancestor names, file contents, shell commands or whether an entry belongs in a distributable bundle. A brace-named child directory is reported, but a brace appearing only in the selected root is outside this predicate.

Normal exit 0 reports the enumerated path count with no matching brace names or reported traversal errors. Exit 1 reports a brace finding or incomplete traversal; exit 2 refuses a zero-entry readable/missing tree. That empty/missing-root refusal is narrower than the script's older 0/1-only introductory description. Counts include directory entries, not just files, and are a pathname denominator rather than content/readability coverage. A directory symlink's name is included but its target descendants are not followed by the underlying walk; referenced external trees are not certified.

Retain the selected root, source version/hash, console outcome and intended tree inventory with the check. No JSON/hash manifest is written automatically. A clean name scan does not validate shell expansion, archive containment, symlink safety, file contents or cut readiness, and it does not authorize moving or deleting evidence (`tools/check_no_brace_paths.py`; `tools/_safe_walk.py`).

## Checking regex interpolation in maintained code

`python tools/check_regex_interpolation.py --root /path/to/selected/code --json` checks selected source text for a specific alternation-binding pattern; it does not execute that code. Without `--root`, its `mamey`, `tools` and `tests` roots are relative to the current working directory. Directory roots discover lowercase `*.py`; an explicitly selected file is parsed regardless of suffix. Paths containing configured cache/vendor/build components are excluded. Preserve the intended source roster and exact input/source hashes with the report.

The checker models f-strings and string/name `+` concatenation, resolving bare names from string-constant assignments found anywhere in the same file. It compares regex parse trees with and without a group around a top-level alternation. This is not lexical-scope or control-flow resolution: same-name assignments from different scopes can be combined, and f-string conversion/format specifiers are not modeled. Percent-formatting, `.format()`, dynamic/imported values and some indirect regex contexts lie outside its coverage. Inspect the real composition before adopting a suggested wrapper (`tools/check_regex_interpolation.py`).

Read its coverage fields as partial static reach. `files_scanned` counts selected files before syntax parsing; a syntax-invalid file is skipped without a corresponding error/omission field. Invalid UTF-8 is replaced, unresolved parts are counted but do not themselves fail, and compositions whose regex parse fails produce no finding. Thus a normal exit 0 can coexist with unresolved or syntax-skipped code. Exit 1 means a new finding; missing roots or zero selected files return 2. Non-strict mode permits exact-path allowlisted findings; `--strict` ignores that allowlist. JSON reports findings and counts, not source hashes, executed-test outcomes or complete regex correctness. File/read or unexpected parser failures can instead interrupt the command; retain such a check as incomplete (`tools/check_regex_interpolation.py`).

## Generated catalog limits

The workflow/receipt catalog group includes explicit maintenance actions, and its owning generator now calls out command-specific write boundaries. For example, `ingest-receipts` writes the judgment store and can reconcile a master workbook. Treat each command's source-backed input/write contract as controlling; group placement is not an immutability guarantee. The generated page and its count/optional-command metadata come from `tools/gen_command_catalog.py`. See [catalog maintenance](CATALOG_MAINTENANCE.md) and the paired [maintenance inventory](MAINTENANCE_INVENTORY.generated.md) for owners, regeneration rules and explicit review holds.

</details>
