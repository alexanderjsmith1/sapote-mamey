# Generated catalog reading and maintenance

Use [task routes](USER_TASK_ROUTER.md) to choose a workflow, then the owning guide and parser to determine inputs, outputs and writes. Generated catalogs are discovery/reference surfaces. A file's presence or a generator's PASS does not certify runtime behavior, evidence availability, finished authorship or scientific acceptance.

## Owners and check scope

| Surface | Owner | Actual check scope |
|---|---|---|
| `COMMAND_CATALOG.generated.md` | `tools/gen_command_catalog.py` | `--check` compares rendered Markdown to the live CLI parser's canonical command names, aliases and help. It imports the CLI; it does not run handlers or list every flag. Group blurbs are hand-authored in the generator. |
| `TOOLS_INVENTORY.generated.md` and the marked block in `BUNDLE_CAPABILITIES.md` | `tools/gen_tools_inventory.py` | `--check` compares generated inventory and, if BUNDLE_CAPABILITIES exists, its inventory block/count. Missing BUNDLE_CAPABILITIES is not itself refused. Tool summaries derive from source docstrings/headers, which can contain obsolete descriptions. |
| `USER_CATALOG.generated.md` and `.json` | `tools/gen_user_catalog.py` | `--check` compares both rendered outputs to source tables, the registry inventory and hard-coded scan descriptions. Those descriptions are not empirically validated by regeneration. |
| `MARKER_CATALOG.generated.md` and `.json` | `tools/gen_marker_catalog.py` | `--check` compares only the stored JSON `sha256` field to a newly collected table hash. It does not verify the stored JSON tables or Markdown existence/content. Additional byte/content verification is necessary. Markdown displays only the first eight patterns per family; JSON carries the full table. |
| `DELIVERABLE_MENU.md` and version-pinned compatibility pointer | `mamey/deliverables_registry.py`, from `mamey/data/deliverables_registry.json` | Compare pure owner-rendered menu and pointer content against the bound registry and versions. CLI `deliverables render` prints or writes a selected output; it has no dedicated check flag and stdout adds a newline. Rendering does not establish availability, completed work or gate admission. |
| `AGENTS.md` generated blocks, `CLAUDE.md` alias and bootstrap audit | `tools/render_bootstrap_contract.py`, from `bootstrap_contract.yml` and version/build inputs | `--check --root <assembled-candidate>` checks required bootstrap surfaces and generated content. AGENTS owns operating prose; CLAUDE must remain byte-identical. External workspace mirrors require an explicitly selected separate mirror check; an unset/advisory mirror result is not strict parity. |
| Eight declared wiki mirrors | `tools/sync_wiki_mirrors.py`, from its maintained Markdown sources | `--check` compares source-derived text with owner link rewriting. The tool uses its owning root, without a root-redirection flag. Edit canonical docs, regenerate their mirrors through the owner, then recheck after the last source change. Parity does not certify source truth or navigation. |

Checks are invoked from the bundle root in the intended environment:

```bash
python tools/gen_command_catalog.py --check
python tools/gen_tools_inventory.py --check
python tools/gen_user_catalog.py --check
python tools/gen_marker_catalog.py --check
```

These are declared check interfaces, not an assertion that they passed for your working tree. `gen_tools_inventory.py --root` controls search/connections modes; its ordinary inventory generation/check still uses the script's owning root. Do not use that flag as a general redirected-output sandbox.

## Reading limits
The command-catalog owner lists optional `lab-quest` with fixed text, but its footer still counts the actual parser map. An absent/present optional add-on can change that footer. Direct baseline inspection records 117 canonical command rows but a footer of 116; the footer counts parser-map entries while the optional row is printed separately. Reconcile those counts in the owning generator before regeneration. Bind the parser environment for a current check; owner review must settle deterministic counting or an explicit environment-dependent contract. This documentation hold does not repair the generator.


The command generator places `deliverable-queue`, `clean` and `add-strain` under a blurb saying “Non-destructive status and lookups.” The actual handlers include package, registry and output mutations. Read [deliverable queue](DELIVERABLE_QUEUE.md) and [Wheelhouse operations](../Wheelhouse/README.md) before invoking them. Native authoring/rendering may refresh package integrity files even with external output destinations; [post-seal readers](POSTSEAL_READERS.md) explains working-copy boundaries.

The tool inventory includes helpers, tests and maintenance interfaces as well as reader workflows. `--search` searches source docstrings; `--connections` reports static filename-reference and interface evidence, not successful calls. `CONNECTED_AND_TESTED` means test references were found, not that tests ran or passed. Scores are defined wiring heuristics, not correctness, scientific value, release approval or performance measures. Tables generated from unescaped docstring pipes may have malformed cells; inspect source when a description is incomplete.

Connection mode covers direct tools files, while ordinary inventory includes nested tools and search covers direct tools/mamey Python modules. Reference counts include lexical mentions, with selected directory exclusions rather than a universal historical filter. Avoid combining --check with --connections/--search: search and connection branches win, and an explicit connection output can still be written. Read [current source scope](reference/06_CURRENT_SOURCE_SCOPE.md#tool-inventory-concept-search-and-static-connection-evidence) for exact scope, omission, interface, output and snapshot limits.

Catalog regex entries explain scanner matching, not biological proof. Source/registry prose, hard-coded scan descriptions and numerical declarations need separate review. Preserve exact identity, typed missingness and reference/version scope when interpreting actual outputs.

## Markdown link checks and hook scope

`tools/check_md_links.py` is a read-only, stdlib local-target checker, separate from catalog regeneration and heading/navigation validation. From the selected bundle root, for example:

```bash
python tools/check_md_links.py docs/INSTALL.md docs/PREREQUISITES.md
```

`--dir DIR` recursively selects filenames ending in lowercase `.md`; explicit inputs are filtered to that same suffix and then to paths that already exist. Missing requested files and directory traversal errors are not necessarily reported when another input survives. With no surviving input the parser exits two; with selected inputs it returns one for recorded problems or zero for none. `--quiet-if-clean` suppresses the clean summary. There is no persisted source/hash receipt or discovery/omission roster. Reconcile the intended input list, readable files and exact result before claiming a directory or bundle was checked.

The parser strips triple-backtick blocks and single-backtick spans with regular expressions, then recognizes simple inline `[text](target)` syntax, including image-style targets caught by that pattern. It does not validate reference-style link definitions, bare code/path references, heading existence, line-number bounds or remote destinations. Pure fragments are ignored, and filename fragments and numeric `:line[:column]` suffixes are removed before an existence check. A file link with a nonexistent heading can therefore pass. This is not a complete Markdown parser or a check that a reader can reach every section/figure.

Targets are percent-decoded, then tested first relative to the Markdown file and also against a fallback project root. That fallback uses the first existing `SAPOTE_WORKSPACE_ROOT`, `SAPOTE_ROOT` or `CLAUDE_PROJECT_DIR`, otherwise the directory holding the bundle. The working directory does not universally define it. A target existing only in the fallback root can mask a broken document-relative link; verify the actual reader's resolution, especially for relocation or export. Existence accepts directories and follows symlinks; it does not admit file type, source identity, content or audience.

Raw space/parenthesis warnings reflect this legacy checker, not a complete renderer grammar. Angle-delimited paths and link titles are not correctly parsed, and a percent-encoded literal `#` in a filename is decoded before anchor stripping. Such links can be reported broken despite an existing intended target. Review the actual syntax and renderer instead of deleting evidence or rewriting a valid locator merely to clear a warning. Keep ordinary file-relative links portable and perform separate heading, route, figure-link and rendered-reader checks with their own stated scope.

The optional `hooks/md_link_check.sh` wrapper does not establish that this checker ran. It selects a workspace root, looks for uppercase `Tools/check_md_links.py` and an optional `Tools/bin/python3`, then silently exits zero if the selected file/checker is absent. The bundled checker is under lowercase `tools/`; a separate uppercase workspace copy is not guaranteed to exist, particularly on a case-sensitive filesystem. The hook suppresses child stderr and judges captured stdout rather than the child return code, so silent errors or skipped execution can produce no warning. Verify actual configured hook paths/interpreter, invocation/result and checked files independently; absence of a hook warning is not link validation. Neither helper modifies the inspected Markdown, and neither result establishes full rendering, evidence admission or release acceptance. Sources: `tools/check_md_links.py:27–116` and `hooks/md_link_check.sh:6–32`.

## Bundle-write-default static check

`tools/check_no_bundle_write_defaults.py [BUNDLE_ROOT] [--max N]` reads Python source in `tools/`, `mamey/` and `deliverable_tools/`. If the root is omitted, it uses the script's owning bundle, so select the intended candidate explicitly. It does not run inspected tools or write their outputs. Exit zero means the detected site count is at most the selected ceiling (default zero); one means the count exceeds it. Two is returned for no discovered Python files or the handled decoding/parsing failures. Other filesystem errors can escape without that normalized status. Save the invocation, result and selected source hashes separately; the checker does not produce a persisted receipt.

The printed file count includes files skipped before parsing because their text lacks `getcwd` and `workspace_root`. Missing scan directories are not refused when another directory supplies files. Reconcile the intended directory/file roster and skipped sources before reporting coverage. A count ceiling is not a site-identity comparison: replacing an old finding with a new one can leave the count unchanged. Review the actual finding locations against the previous bound result.

This is a limited static screen, not proof that outputs stay outside the bundle. A guard call anywhere in a function suppresses that function's findings without checking execution order, branch or guarded-path identity. For a module-level write, a guard in another function can also suppress the finding. Common `Path(...).mkdir()` calls with only keyword arguments, annotated root assignments, local paths derived from module root names and inline `os.getcwd()` paths can escape the implemented matching. The checker also omits `Path.write_text`, `Path.write_bytes`, pandas and shutil writes. Inspect the actual output path and guard before each write when assessing a tool; a clean count cannot replace that review. Sources: `tools/check_no_bundle_write_defaults.py:38–118`, `:142–185` and `:188–245`.

## Retained tier-parity maintenance check

The retained `tools/check_tier_parity.py` checks the historical four-tier archive set and selected counts/presence, rather than current CODE-only completeness or full content identity. It writes temporary extractions and can directly overwrite a selected receipt path. See [tier-parity selection and evidence](TIER_DIFFERENCES.md#tier-parity-selection-writes-and-evidence) for archive selection, omitted-source behavior, exit limits and receipt binding before invoking it during separately authorized maintenance. Its presence in the bundle does not authorize rebuilding disabled tiers.

## Correcting or regenerating

Do not hand-edit generated catalogs or the marked BUNDLE_CAPABILITIES block. Find the owning source/registry, propose its correction and regenerate only in the authorized working candidate. Changing a guide does not repair a parser/help/registry defect. If only reader guidance is being changed, leave generated bytes intact and record the source hold here or in an audit receipt.

Default regeneration writes into the generator's owning tree. The command catalog uses a direct write. The user and marker generators publish each output atomically but their two files are separate writes, so an interruption can leave a mismatched pair. After regeneration, verify the whole expected output set, source hashes and actual content; for the marker pair, compare both files against fresh owner-rendered content in isolation rather than trusting its weak `--check` alone. Keep one candidate and reference source evidence in place. Do not copy packages or databases to check a catalog.

The [generated ownership planner](../tools/generated_surface_ownership.py) validates declared phase sets and required path presence. It does not verify file content, historical write order or scientific status. Release-manifest/tier/checksum finalization remains with the existing cut owners after authorized checks; catalog inspection does not grant release authority.
