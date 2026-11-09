# Find the right document

Choose a guide for the file or task in front of you. If you are unsure what you have,
start with [the file you have](READER_START_HERE.md).

| You want to | Open |
|---|---|
| Install the program | [Install](INSTALL.md) |
| Set up and extract an antiSMASH ZIP | [Inputs and setup](reader/02_INPUTS_AND_SETUP.md), then [Your first run](reader/01_FIRST_RUN.md) |
| Read a saved result | [Read one saved package](reader/03_READ_RESULTS.md), then [Reading your results](READING_YOUR_RESULTS.md) for each field |
| Fix an incomplete run or an error | [Recover a run](reader/04_RECOVERY_AND_LIMITS.md), then [Troubleshooting](COMMON_MISTAKES.md) |
| Choose a task and see what it needs | [Choose a task](USER_TASK_ROUTER.md) |
| Choose a specialist command | [Choose the next command](user_guides/CHOOSE_NEXT_COMMAND.md) |
| Find a command or a term | [Command catalog](COMMAND_CATALOG.generated.md) or [Glossary](GLOSSARY.md) |
| Find a missing genome, reference or tool | [Find a missing input](COMPANION_FILES.md) |
| Write a Mode B card | [Mode B guide index](MODE_B_DOCUMENT_INDEX.md) |
| Use stored BLASTp results | [BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md) |
| Draw or check a figure | [Make and review figures](FIGURES_START_HERE.md) |
| Choose or run an optional companion tool | [Companion tools](COMPANION_TOOL_GUIDE.md) |
| Save or transfer a package | [Files and storage](FILES_STORAGE_AND_HANDOFF.md) |
| See recorded results from earlier runs | [Recorded public-genome walkthroughs](TYPE_STRAIN_WALKTHROUGHS.md). This is a record, not a recipe. |

The [Master Walkthrough](MASTER_WALKTHROUGH.md) connects the main steps.
The [Current Docs Index](../CURRENT_DOCS_INDEX.md) lists the specialist guides and says how to tell a current page from an old one.

## Maintainers

Fix wrong instructions in place. Rebuild a generated catalog with its generator;
[catalog maintenance](CATALOG_MAINTENANCE.md) names the scripts. `CLAUDE.md` is a generated
copy of `AGENTS.md` and must stay byte-identical. Walk the examples after you change them.

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
