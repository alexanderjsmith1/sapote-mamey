# Find the right document

Choose a guide for the file or task in front of you. Start with
[the file you have](READER_START_HERE.md) if you are unsure what it is.

| You want to | Open |
|---|---|
| Set up and extract an antiSMASH ZIP | [Inputs and setup](reader/02_INPUTS_AND_SETUP.md), then [First run](reader/01_FIRST_RUN.md) |
| Read a saved result | [Read results](reader/03_READ_RESULTS.md) |
| Fix an incomplete run or an error | [Recovery](reader/04_RECOVERY_AND_LIMITS.md), then [Troubleshooting](COMMON_MISTAKES.md) |
| Save or transfer a package | [Files and storage](FILES_STORAGE_AND_HANDOFF.md) |
| Choose a tool, figure, report or comparison | [Task router](USER_TASK_ROUTER.md) and [Companion tools](COMPANION_TOOL_GUIDE.md) |
| Look up a term or command | [Glossary](GLOSSARY.md) or [Command catalog](COMMAND_CATALOG.generated.md) |
| Read a worked example | [Type-strain examples](TYPE_STRAIN_WALKTHROUGHS.md) |

The [Master Walkthrough](MASTER_WALKTHROUGH.md) connects the main steps.
[Reading your results](READING_YOUR_RESULTS.md) explains individual output fields.
The [Current Docs Index](../CURRENT_DOCS_INDEX.md) lists specialist guides.

## For documentation maintainers

Update misleading instructions in place and preserve earlier evidence.
Use the generator for a generated catalog; [catalog maintenance](CATALOG_MAINTENANCE.md)
identifies the relevant scripts. Keep the `AGENTS.md` and `CLAUDE.md` twins synchronized.
Walk the examples after changing them.

<details>
<summary>Run the static documentation checks</summary>

Run these from the selected program folder and its Python environment.

### Entry points

```bash
python tools/check_onboarding_funnel.py
```

This compares the canonical twins and checks routing text in root-level entry
pages. Read its listed page names: the check uses literal text and excludes
nested guides. Add `--root` only to check a different bundle folder.

### Command names

```bash
python tools/check_command_pointers.py
```

This scans the bundle containing the script for a specific inline
`mamey <subcommand>` pattern. It checks the command token against the parser.
Python command examples, options and input requirements need their own walk.
Read errors are failures; parser/import errors can stop the report.

### Brace characters in names

```bash
python tools/check_no_brace_paths.py
```

This checks descendant file and directory names for braces and prints the count.
A missing or empty tree is refused. The root's own name and descendants reached
through directory symlinks are outside this check. Supply a root argument only
when checking another tree.

### Regex interpolation

```bash
python tools/check_regex_interpolation.py
```

This checks Python files under `mamey`, `tools` and `tests` relative to the current
folder for a specific alternation-binding error. Read the unresolved-interpolation
count even after PASS. Syntax-skipped files and unresolved expressions require
separate inspection. Add `--json` when another program needs a JSON report;
`--strict` also treats allowlisted findings as failures.

Keep the selected source version, commands and complete output with your review.
For exact discovery and exclusion rules, read the named checker. Historical
examples can contain old commands; preserve their history and correct the current
route that sends readers to them.

</details>

<a id="why-similar-titles-exist"></a>
<a id="maintenance-rules"></a>
<a id="onboarding-funnel-maintenance-check"></a>
<a id="checking-documented-command-names"></a>
<a id="checking-brace-characters-in-entry-names"></a>
<a id="checking-regex-interpolation-in-maintained-code"></a>
<a id="generated-catalog-limits"></a>
