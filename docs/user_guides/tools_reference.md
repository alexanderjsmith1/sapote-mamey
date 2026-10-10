# Sapote–Mamey Tools Directory Reference

Before any `doctor` example below, read the [write-probe boundary](../INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


**Current navigation baseline: bundle v9.7.447 · engine 1.9.172 · build 20261003v97447a.** Execution receipts below retain their original versions; source inspection does not renew them.

> **The per-script inventory that used to live here has been retired, not lost.**
> It is now generated, not hand-maintained:
>
> | What you want | Where it lives now | How it stays current |
> |---|---|---|
> | Every script in `tools/` + its docstring | [`docs/TOOLS_INVENTORY.generated.md`](../TOOLS_INVENTORY.generated.md) | `tools/gen_tools_inventory.py`; `--check` verifies sync |
> | Every `mamey_run.py` subcommand | [`docs/COMMAND_CATALOG.generated.md`](../COMMAND_CATALOG.generated.md) | `tools/gen_command_catalog.py`; `--check` fails the build when stale |
> | External tools (antiSMASH, BiG-SCAPE, IQ-TREE, GToTree, BLAST+, SPAdes) | [`docs/EXTERNAL_TOOL_INVENTORY.md`](../EXTERNAL_TOOL_INVENTORY.md) | manual, versions + citations |
>
> The inventories are generated from their owning sources. Read their current headers instead of copying counts into this page. A successful generator check establishes synchronization, not runtime correctness or scientific validity.
>
> **Do not re-add a manual script list here.** Check the generated inventory *before* writing a
> new tool, as its own header instructs.

## What remains in this file

Section 15 is the maintained request/command route. Section 14 and Sections 16 onward are historical execution/development records: their versioned incidents, fixes and card counts are not current work orders or permission to change biological reports. Read the owning current code/profile before reusing any older command or applying an incident-specific repair. These records document observed behavior at their stated versions, not current runtime guarantees.

---

## Section 14: Live Tools Verification — What Actually Runs

> **Currency note (added 2026-09-14):** the verification receipts in this section were recorded
> against **bundle v9.7.241 on 2026-07-09** and have **not** been re-executed since. They are
> retained as a historical receipt of what ran at that version, not as a claim about the current baseline.
> Re-running this matrix is tracked as an open item; until then, treat the "Confirmed" column as
> "confirmed at v9.7.241".


*Commands verified to run successfully in bundle v9.7.241, 2026-07-09. All outputs are from real execution against the teicoplanin calibration package.*

### Verified command matrix

| Command | Input | Output | Confirmed |
|---|---|---|---|
| `python mamey_run.py doctor` | (no input) | Dependency/permission pre-flight report | ✅ 18.8s total |
| `python mamey_run.py inspect <zip>` | antiSMASH ZIP | Pre-run preview: region count, GBK contents | ✅ |
| `python mamey_run.py run --mode gold` | antiSMASH ZIP | Sealed package, 26 figures, compiled report | ✅ 18.8s wall |
| `python mamey_run.py validate <pkg>` | Sealed package | JSON gate report: file_presence, checksums, rggmci | ✅ MAMEY_COMPLETE |
| `python mamey_run.py list-bgcs <pkg> --json` | Sealed package | JSON BGC inventory with all scores | ✅ |
| `python mamey_run.py emit-modeb-template --bgc BGC001` | Sealed package + BGC ID | §1–§30 template with gene table pre-filled | ✅ 109 lines |
| `python mamey_run.py render-all-figures <pkg>` | Sealed package | 5 figure modules, 26 figures total | ✅ |
| `python mamey_run.py workflow <pkg> --json` | Sealed package | W0–W10 gate status with receipts | ✅ W0-W2 PASS |
| `tools/preflight_zip_hygiene.py <zip>` | antiSMASH ZIP | Clean/dirty assessment | ✅ OK |
| `tools/gen_marker_catalog.py --check` | (live patterns) | Drift check: 14 tables in sync | ✅ |
| `tools/sapote_workflow.py <pkg>` | Sealed package | W0–W10 ledger markdown | ✅ 3/11 PASS |
| `tools/claim_safety_linter.py <md>` | Markdown file | Finding list with line annotations | ✅ 2 findings |

### Tools that require additional arguments (not run but syntax verified)

**`tools/check_deliverable_suite.py`** — requires `--manifest MANIFEST` (a filled `DELIVERABLE_MANIFEST_*.md`). Not runnable until the deliverable manifest has been generated and filled.

**`tools/assembly_qc_check.py`** — takes `--snapshot` or `--banked-dir`, not `--package`. Call with a cohort bank directory, not directly with a package.

**`tools/sapote_md_preflight.py`** — requires both `input_md` and `output_md` positional arguments (writes a preflight-processed copy to output).

**`tools/build_workbook.py --full`** — requires `--banked-dir` (a cohort bank populated by `ingest_package.py`). Cannot run on a single package directly.

### Tools output format notes

**`python mamey_run.py workflow --json`** — produces the same content as the markdown output but machine-readable. The status values are: `PASS`, `PENDING`, `BLOCKED`, `N_A`. The `receipt` field contains the specific artifact reference (file name + size + content summary) that confirmed the PASS, or the blocking reason.

**`python mamey_run.py list-bgcs --json`** — produces a JSON array, one object per BGC. The array is directly usable by downstream tools. The `--axis` flag selects sort order (`rank`, `ab`, `af`, `novelty`); `--top N` limits output count.

**`python mamey_run.py emit-modeb-template`** — the output goes to stdout by default; redirect to a file for authoring. The template includes a pre-filled gene table from `gene_context.jsonl`, the BGC's scores from the triage board, and the over-merge warning when applicable.

**`python mamey_run.py render-all-figures`** — non-blocking per module. If one module fails (e.g. domain-level fails because deep_data.json is empty), the others continue. The summary at the end reports per-module results.

**`tools/gen_tools_inventory.py`** — writes the full tools inventory to `docs/TOOLS_INVENTORY.generated.md`, injects a compact `name — summary` list into the generated block of `docs/BUNDLE_CAPABILITIES.md`, and also outputs "wrote inventory: N tools" to stdout. The inventory is a structured markdown table of all tools/scripts with docstrings extracted. For a connection-aware review, run `python tools/gen_tools_inventory.py --connections --format tsv --output tool_connections.tsv`. That audit reports current tool-file hashes, heuristically detected interface, lexical source/CLI/test/doc/manifest reference files, inferred lifecycle, personal-path/external-contact markers and two wiring scores. It covers only direct tools files; selected historical-directory filtering is incomplete, and no dependency, call or test is executed. See [catalog maintenance](../CATALOG_MAINTENANCE.md) for mode, mutation and snapshot limits. The scores measure wiring and operational support only; they do not measure scientific value, correctness, acceptance, or release readiness. The marker columns are review cues, not proof that a default is unsafe or that external contact occurs.

---

## Section 15: Current task routes and bounded examples

For `list-bgcs`, use [quick-list selection and full inventory](../READING_YOUR_RESULTS.md#quick-list-selection-and-full-inventory): current axes are `rank`, `ab` and `af`; default exclusions and `--top` make a selected view. Use `--include-dropped` when the task requires all admitted board rows. Historical option/output descriptions below or above retain their original receipt scope.

Use [Choose a task](../USER_TASK_ROUTER.md) for inputs, outputs and completion limits, and the generated command catalog for command names, aliases and summary help. Use the owning command’s current `--help` for flags. Historical commands in Section 14 are receipts, not current copy/paste instructions.

For source-ZIP comparison use [offline pairwise comparison](../../sapote_addons/README_OFFLINE_ANALYSIS.md); a sealed package directory is not its protein input. For a browser reader use [interactive widgets](../WIDGET_DELIVERABLES.md), whose render status does not validate the package. To transfer reviewed evidence use [portable handoff](../FILES_STORAGE_AND_HANDOFF.md#use-the-portable-handoff-builder-deliberately), checking actual region-file counts. Each route has a separate output and recovery contract.

### Strain slides builder

Request the **Sapote-Mamey Strain slides builder**. It creates the main strain deck and a separate region-gene-table PowerPoint. Follow [Strain slides](../STRAIN_SLIDES.md) for the sources JSON, optional channels, output files and .447 versus v2n/.448 boundary.

```bash
python tools/strain_slides.py template > XS-001_sources.json
# Fill the sources file with real strain/package bindings and absolute optional paths.
python tools/strain_slides.py build --sources XS-001_sources.json --out decks/new_build --tag review1
```

### Combined V7 + Mode B report builder

Request the **Sapote-Mamey combined V7 + Mode B report builder** for composing an existing exact-current predecessor packet with retained scientific text and structured overlays. Read [its complete selected input/output contract](../reference/06_CURRENT_SOURCE_SCOPE.md#combined-v7-and-mode-b-report-builder) before preparing the job JSON. It requires ten source roles, explicit identity/hash bindings and a fresh destination; it does not create missing evidence or render Word/PDF. Exclusion can return exit0 with no output, and a built draft can retain scientific holds.

### Mode B authoring

Replace all placeholders. The BGC alias is a local selector within a source-bound package; the authored file must preserve `strain / full node-or-contig / region / BGC alias`.

```bash
python mamey_run.py emit-modeb-template --package '<package>' --bgc '<alias>' --contract current50_v2 --out '<new-template.md>'
# Author the emitted template from admitted evidence before verification.
python mamey_run.py verify-modeb '<authored-card.md>' --package '<package>' --bgc '<alias>' --contract current50_v2
```

Choose the profile explicitly: .447 accepts `full48` (default) or `current50_v2` for these commands. Carry the same contract through emission and verification. The verifier requires the authored file as a positional argument. See [profile matrix](../MODEB_PROFILE_MATRIX.md) and [expanded locus](../MODEB_EXPANDED_LOCUS.md) for work-order-specific requirements. A template or structure pass is not a finished scientific interpretation.

### Selected package figures

```bash
python mamey_run.py render-figures --package '<working-package-copy>' --figure-set standard --outdir '<external-output-folder>'
```

This selects one figure set and supplies an external image destination. The .447 CLI can still refresh integrity files in the supplied package; use a working copy and retain the original. See [post-seal boundaries](../POSTSEAL_READERS.md#commands-that-still-author-package-data-in-447). Read [Figure rendering](../FIGURES_START_HERE.md) for prerequisite evidence and renderer limits. Capped extraction can defer figures; a renderer success does not prove every desired figure was available or visually reviewed.

### Registry-ID duplicate screen

Request `tools/check_registry_ids_unique.py` for exact extracted duplicates within selected JSON/CSV files. Read [input admission, per-file scope and recovery](../REGISTRY_JSON_CSV_PARITY_NOTE_v9.7.141.md#registry-id-checker-scope): “unique (0 IDs)” can omit invalid/missing entries, and separately clean files do not prove population or field parity. Keep original registry evidence and bind the actual inputs/result before using the count.

### Input manifest and release ZIP preflight

Use the **input manifest and coverage builder** for selected file hashes and a separately reviewed key denominator. Use ZIP hygiene for software-release packaging names/sizes. Read [their exact scope and recovery](../reference/06_CURRENT_SOURCE_SCOPE.md#input-manifests-and-zip-preflight-scopes): neither check proves analysis consumption, full cohort identity, payload validity or release acceptance. Historical antiSMASH ZIP examples above do not turn release hygiene into intake validation.

### 16S store defect validator and merge screen

Request these by their separate names when auditing a closed 16S store. The validator reports selected metadata/genus defects; the merge screen produces an additive alignment screen with merge acceptance held. Read [inputs, outputs and recovery](../reference/06_CURRENT_SOURCE_SCOPE.md#16s-store-defect-validation-and-additive-merge-screening) before interpreting exit0 or publishing reports.

### Denominator and evidence-conservation audits

Request these checks for cached workbook ratio tokens or two selected JSON evidence files respectively. Their PASS states have different units and explicit unexercised coverage. See [their commands, receipts and recovery](../reference/06_CURRENT_SOURCE_SCOPE.md#cross-strain-denominator-and-conservation-audit-coverage); neither saves a full provenance receipt or validates every claim/locus.

### Finished-text citations and source disclosure

Request the **finished-text citation hygiene audit** for selected Markdown/text, and the **strict source-disclosure compatibility check** for Python/test disclosure scope. They have different input and completion contracts. Read [selection, status, output and recovery](../reference/06_CURRENT_SOURCE_SCOPE.md#finished-text-citation-hygiene-and-strict-source-disclosure): neither proves factual source support, exact full-locus binding, rendered-page QA or release acceptance.

### Public-workbook disclosure audit

Request `tools/audit_public_cut.py` for a selected merged-master Excel candidate, with its preserved private source and allowed/held roster when available. This is a cached-cell/schema-name pattern guard, not the code-tree release auditor or a bundle-version validator. Read [public-workbook scope and recovery](../CUSTOM_PRIVACY_TIERS.md#public-workbook-audit-limits) before interpreting `CLEAN`, selecting report/scrub destinations or sharing the diagnostic report. No default `CLEAN` result proves full roster admission, formula/object disclosure review or release permission.

### Local Markdown target check

Request `tools/check_md_links.py` for simple local links in explicitly selected Markdown files. Read [input discovery, link syntax and hook limits](../CATALOG_MAINTENANCE.md#markdown-link-checks-and-hook-scope): zero problems does not validate missing requested inputs, heading fragments, reference-style links, relocation, figure coverage or rendered navigation. Keep source Markdown intact and retain the actual checked-file list and result; a quiet optional hook is not execution evidence.

### Markdown preflight and advisory text lint

Request the **Markdown render preflight** by name for table-routing and selected
raw-value checks. Use separate input/output paths; choose fresh output,
appendix and QA destinations outside the source evidence:

```bash
python tools/sapote_md_preflight.py '<input.md>' '<processed.md>' --profile boss --appendix-md '<wide-tables.md>' --qa-json '<preflight.json>'
```

The `boss` profile routes detected pipe-table blocks exceeding six columns or
118 characters per line by default. `technical` retains those tables. Detection
is a line heuristic, without Markdown fence or escaped-pipe parsing. The helper
does not render or inspect a PDF, prove page fit, check full document structure,
or validate scientific content. Its body output is written even when it returns
1 for selected forbidden raw-value strings. Exit 0/QA PASS means no such string
was found in the processed body; routed tables can still contain them. Review
and retain the appendix separately. If `--appendix-md` is omitted, routed table
content is not saved by the CLI. QA JSON is also optional. Output, appendix and
QA writes are separate publications, so a failure can leave a mixed set. Verify
all requested outputs and their hashes after a retry or interruption.

Request the **advisory professionalism linter** for selected interpretive text:

```bash
python tools/professionalism_linter.py '<text.md>' --json
```

This reads text and emits warnings; it does not edit the input or certify its
claims. Exit 1 means findings, and exit 0 means no findings among the files it
successfully read. Unreadable files are currently reported to stderr and skipped;
an entirely unreadable request can return 0 with `{}`. Confirm every requested
file was read and retain stderr before calling the check clean. Blank lines,
headings and blockquotes are skipped; table rows skip the denominator rule.
Code fences are not parsed. Same-line evidence words or backticks can suppress
warnings without establishing factual support. Independently verify citations,
full locus identity, denominators and producer completion evidence.

### Silent-success exit inventory

Request the **silent-success exit inventory** when reviewing selected Python
guard paths. It reads source text and emits a classified console report; it does
not run the reviewed code or repair files. Select the source root and scope:

```bash
python tools/silent_exit_audit.py --root '<source-root>' --scope hooks tools
```

Default scope is `hooks` under the current directory. Only `.py` files under the
selected scopes are considered; `__pycache__` directories are skipped. Confirm
the requested directories exist and retain the exact source roster/hashes with
the console report. Missing directories or an empty scope can produce zero files
and exit 0. A Python syntax error is silently omitted, while that filename still
contributes to the reported file count; an unreadable file can raise an error.
The reported denominator is files encountered, not verified parse coverage.

Exit 0 is the default even when REVIEW rows exist. `--ceiling N` returns 1 only
when the total REVIEW count exceeds N. `--class REVIEW` filters displayed rows;
it does not redefine that count. No JSON or saved-receipt option is provided.
Capture the console output and command exit separately in a fresh receipt.

Classes are lexical review suggestions, not verified path contracts. In
particular, FAIL_OPEN does not establish that a guard's actual fail-open behavior
is appropriate. The scanner recognizes selected constant success exits under
`if`/`except` blocks; it does not prove all execution paths or computed returns.
Emitter recognition is name-based and treats calls named `write` as visible
output, even if they only write a file. A later or conditional emitter anywhere
in an enclosing branch can also suppress a genuinely silent exit. Inspect the
actual branch and helper behavior before accepting either a finding or an empty
report. A low count or ratchet pass does not establish complete recovery,
operator-visible diagnostics or runtime correctness.

### Caption-band helper

Request the **caption-band helper** for an existing raster plot and an authored
Markdown caption. Use a fresh writable figure destination outside source evidence:

```bash
python tools/caption_band.py '<plot.png>' '<caption.md>' --outdir '<new-figure-directory>'
```

This creates `<stem>_with_caption.png`, `<stem>_with_caption.pdf` and
`<stem>_CAPTION.md`; `_plot_only` is removed from the input stem. Different input
names can therefore map to the same outputs. Without `--outdir`, outputs go beside
the source plot. Existing names can be replaced, and the three writes are not one
transaction. After a failure or retry, verify every requested output and its hash;
a retained earlier image or sidecar is not proof of current completion.

The sidecar is copied verbatim unless it already occupies the selected sidecar
path. The band strips selected Markdown marks and link targets and removes blank
lines; it is not a verbatim Markdown rendering. Empty caption text becomes the
placeholder `(caption)`. The helper checks selected prohibited wording in those
flattened lines, not the original plot text, methods schema, source-data bindings,
scientific accuracy or caption completeness. Retain those checks and provenance
in separate receipts. It does not create a `_plot_only` source image.

The PDF wraps the raster canvas; it is not a vector export. Saving 300-DPI
metadata does not establish adequate resolution at the intended publication
size. Inspect the actual image/PDF for legibility and clipping before delivery.
Banned caption wording returns exit 2. Other input, dependency or save failures
can raise exceptions; missing Pillow currently exits through a string
`SystemExit`, rather than the documented exit 2. Preserve diagnostics and the
actual exit code instead of assuming every refusal shares one status.

### Patch-queue composition screen

Request `tools/patch_queue_composition_audit.py` for advisory screening of file drops and diff compatibility against a selected base. Read [composition-screen scope](../PATCH_WORKSPACE_LAYOUT.md#optional-composition-screen-scope) before interpreting counts, skipped checks or a zero exit. It does not validate an ordered composed candidate or authorize applying a queue.

### Patch-pool card inventory (`parked_card_audit.py`)

```bash
python tools/parked_card_audit.py '<versioned-patch-pool>' --sealed-tree '<reviewed-bundle-tree>' --current-version 447 --ttl 2 --all
```

Use the actual reviewed cut number. This inventories immediate card directories and top-level `.patch`/`.diff` files in pools whose directory names contain `9.7.N`. Nested patch copies are excluded. Nonexistent pool selections and unversioned pools can contribute no rows without failing; record the selected pool/card roster independently. `--all` expands printed rows, not validation scope.

Statuses are screening heuristics. `FOLDED` means at least 60% of distinctive added lines occur as substrings in every existing in-scope target, or a new-file target merely exists. It does not compare complete patch content or context. Deletion-only changes and additions shorter than six stripped characters can be `FOLDED` without checking their intended effect. An unrelated existing new file or matching text in a comment can also satisfy the heuristic. Missing modify targets are skipped; a card with no admitted targets is `OUT_OF_SCOPE`. Confirm intended additions, deletions, exact paths and provenance separately before treating a card as integrated (`tools/parked_card_audit.py:76–162`).

When presence is insufficient, the helper runs native `patch -p1 --dry-run --fuzz=0` with a 60-second timeout to distinguish `PARKED` from `DRIFTED`; it does not apply the patch. Only review trusted patches: target paths are joined to the tree without containment admission, so absolute/traversal targets are not safely restricted to that tree. `DRIFTED` is always flagged; `PARKED` is flagged at the selected TTL or for a contradicting FOLDED marker. `EMPTY`, `FOLDED` and `OUT_OF_SCOPE` alone are unflagged. These states require their own review rather than relying on the final clean message.

The test guard checks filename/target presence for `PARKED`/`DRIFTED` engine-code cards, not test execution, coverage or results. `--no-require-tests` disables that presence guard. Exit 2 means flagged cards or an undetermined current version; exit 0 means no flags in the admitted inventory. Neither proves complete integration. Capture the command, exact inputs/hashes, complete printed roster and independent resolution records; the helper does not save a structured hash-bound receipt (`tools/parked_card_audit.py:202–313`).

### Onboarding entry-point check

Request `tools/check_onboarding_funnel.py` for the selected bundle's static root-door/twin check. Read [literal admission and optional runtime scope](../DOCUMENTATION_MAP.md#onboarding-funnel-maintenance-check) before treating PASS as a usable route or selecting `--run-start`. Preserve the intended entry-point roster and actual results.

### Module-inventory gate

Request `tools/check_module_accretion.py` for module membership and changelog-justification screening. Read [baseline ownership and write limits](../RELEASE_CHECKLIST_v9.md#module-inventory-gate-and-manifest-ownership) before interpreting zero additions or selecting `--write`. Keep full module identities, expected inventory and source/hash validation separate.

### Manifest/schema-drift screen

Request `tools/check_schema_drift.py` for its selected recorded-version/key-set/companion checks before a separately authorized merge. Read [schema and skipped-comparison limits](../batches/batch22_multi_strain_comparative_claims.md#separate-manifestschema-drift-screen) and supply an independently required workflow version. “No drift” does not prove complete schema, source provenance or merge acceptance.

### Handback-format and instruction-drift screens

Request `tools/check_chatgpt_next_paths.py HANDOFF.md` only when the selected handoff deliberately uses its legacy format. It requires 3–8 consecutive numbered items, with a final SAVE STATE saved/link-shaped confirmation or FAILED statement. Current user/task instructions govern whether next actions are useful; do not pad a routine answer to satisfy this formatter. It checks the last numbered-list-looking block, including lines in code fences. Blank lines preserve a block, while wrapped nonblank continuation lines split it; a later numbered bibliography can become the selected block (`tools/check_chatgpt_next_paths.py:24–35,45–72`).

A PASS is lexical. A missing link target, a SAVE STATE FAILED statement or even “SAVE STATE not saved” plus a link-shaped string can pass. The helper neither resolves the checkpoint nor verifies any write. Confirm actual saved/failed state, output path and hash independently. Duplicate detection compares six leading normalized tokens; it is not a review of feasibility or distinct outcomes. Exit 0 means this format passed, 1 means format errors, and 2 means the selected input is not a regular file. No receipt is persisted by the checker.

Request `tools/audit_chatgpt_nextpaths_drift.py ROOT --json` for the separate selected-surface lexical regression check. It reads only explicitly named paths and the `prompts/reuse/` and `docs/modules/` prefixes, restricted to `.md`, `.txt` and `.json`. Relative path selection is case-sensitive. Symlinked entries and `.git` directories are skipped. Review the reported considered/selected counts against your intended current surface roster: these counts do not prove every required document exists. Zero selected files is REFUSED (exit 2), matched rules FAIL (1), and selected files without matches PASS (0) (`tools/audit_chatgpt_nextpaths_drift.py:20–82,85–115`).

Rules operate per line. A quoted or negated forbidden phrase can trigger FAIL, while synonyms or a phrase split across lines can evade detection. Python-emitted wording and historical surfaces are outside this selection. Missing roots or unreadable/invalid-UTF-8 selected files raise exceptions rather than producing a complete typed audit receipt. `--json` prints a report to stdout; preserve it externally with the command, selected roster and input hashes. Treat PASS as evidence for these exact lexical rules, then review actual instruction consistency and generated owners separately.

### Workflow status

```bash
python mamey_run.py workflow --package '<package>' --json --ledger-out '<external-ledger.md>'
```

The explicit ledger destination preserves the source package. `--strict` applies the workflow's mandatory-step gate; it does not certify scientific validity. Review per-step receipts and holds. For first extraction follow [Your first analysis](../MASTER_WALKTHROUGH.md); for existing packages follow [Read your results](../READING_YOUR_RESULTS.md).

**compile-report `--pdf` publication artwork.** The PDF path validates every figure at the declared
7.2-inch double-column width before writing render Markdown. Live-text SVG is preserved through vector
PDF conversion when `cairosvg`, `rsvg-convert`, or `inkscape` is available. Only if vector conversion is
unavailable may the compiler make a native-width raster fallback, which must still provide at least 300
effective DPI. Existing PNG thumbnails that would be enlarged are refused with
`FIGURE_EFFECTIVE_DPI_INSUFFICIENT`; metadata DPI and PDF-derived screenshots do not satisfy the gate.
This fail-closed check prevents a standalone screen PNG from becoming blurred publication artwork.
Install `cairosvg` via the render extra so the vector-preserving path is available wherever the compiled
PDF is built:

```bash
pip install '.[render]'   # cairosvg — also folded into '.[all]'
```

---

*v2 additions: Sections 14–15 (live verification, quick reference card) · Bundle v9.7.241 · 2026-07-09*

---

## Historical development records

The following sections retain their original version scopes. For current tasks use Section 15 and the linked owning guides; historical remediation text applies only to its original incident and sources.

## Section 16: New Tools (v9.7.243–246)

### `tools/file_atlas.py` — describe every Python file from the source

**Current use:** the description and v9.7.246 counts below are historical. Use the [current atlas scope](../ARTIFACT_MAP_LIMITS.md#generated-file-atlas): the scan covers selected Python paths, and import/CLI/test associations are heuristics. The tool scans the extracted bundle containing its own script, rather than a source root selected by the working directory; it has no `--root` flag. Output destinations are ordinary supplied paths. To preserve bundled/generated evidence, create a separate output directory beforehand and select distinct, new files:

```bash
python tools/file_atlas.py --out ../review_output/atlas_new.csv \
  --md ../review_output/atlas_new.md
```

Do not point either output at source code, historical evidence or the other output. Equal or aliased `--out`/`--md` paths are not refused: Markdown can replace the CSV while the command exits zero. Publication is sequential and directly replacing, with no group rollback or input/output hash receipt. Retain a partial result after a later failure; rerun into new paths and inspect both current files. `--orphans` takes precedence over both output flags and prints candidates without writing either file. Invoke the reporting and file-writing forms separately when both are needed.

**Added:** v9.7.243. Built for the Bunny Hop Audit Game (`debugging_modules/BUNNY_HOP_AUDIT_GAME.md`): "you cannot audit what you cannot see."

Walks `mamey/` and `tools/` with `ast` and emits one row per file. Nothing is inferred and no list is hardcoded — every column is read from the real tree.

**Columns:** `path`, `loc`, `summary` (first docstring line), `n_defs`, `n_classes`, `imports_internal` (fan-out), `imported_by` (fan-in), `cli_verbs` (subcommands registered in this file), `test_refs` (test files naming this module), `orphan`.

**The `orphan` column is the interesting one.** A module that nothing imports, that no CLI verb reaches, and that no test names, is a candidate for the audit's REDUNDANCY inspector — or for the defect class this project keeps hitting, where **a capability exists and nothing invokes it** (see Development Issues Compendium, Group 14).

```bash
python3 tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md
python3 tools/file_atlas.py --orphans     # just the orphan list, for the bunny-hop roll
```

| Flag | Effect |
|---|---|
| `--out PATH` | CSV output path |
| `--md PATH` | Markdown summary path |
| `--orphans` | Print orphan candidates only; no files written |

**Live receipt on bundle v9.7.246:**

```
280 files under mamey/ and tools/
74,981 total lines
35 orphan candidates (no importer, no CLI verb, no test)
57 files no test names at all
```

**Highest fan-in (from `docs/FILE_ATLAS.md`) — change these carefully:**

| File | Imported by | LOC |
|---|---:|---:|
| `tools/_wbio.py` | 38 | 125 |
| `mamey/models.py` | 13 | 397 |
| `mamey/crosswalk.py` | 11 | 238 |
| `mamey/antismash_evidence.py` | 9 | 1,233 |
| `mamey/figure_policy.py` | 8 | 56 |
| `mamey/source_scans.py` | 8 | 1,733 |
| `mamey/_gbk_shim.py` | 7 | 139 |
| `mamey/modeb_structure_gate.py` | 7 | 1,036 |

Both `_wbio.py` (38 importers, 1 test before v9.7.243) and `crosswalk.py` (fan-in 11) were subsequently hardened — the atlas identified them as the highest-risk files, and the audit went there next. This is the tool doing its job.

**Known limitation, found and fixed before shipping:** the first pass called `verify_release_identity.py` an orphan. It is invoked by `tools/release.sh`, which the AST scanner did not read. Shell and gate-registry invocations now count. Orphan count dropped 42 → 35. The lesson generalises: an AST scan sees Python imports, not shell invocations, not YAML, not a `gate_registry.tsv` row.

**Output artifacts:** `docs/FILE_ATLAS.csv` (machine-readable, one row per file) and `docs/FILE_ATLAS.md` (four sections: Highest fan-in · Largest files · Orphan candidates · Every file).

---

### `tools/check_monolith_freshness.py` — keep the parent design doc's anchor honest

**Added:** v9.7.243, WIRED (registered in `tools/gate_registry.tsv`).

`docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` is the parent design controller, referenced by 20 files including `prompts/CLAUDE_SYSTEM_PROMPT.md`. It is deliberately **not** bumped every patch — its content is reviewed at checkpoints. That convention is sound. What is not sound is the anchor line drifting silently: at v9.7.242 the monolith still claimed to be vetted against v9.7.6 and stated `current bundle 9.7.57 / engine 1.9.64` — **185 cuts of drift, with no signal.**

**The gate does not demand a re-read. It demands that the monolith state, truthfully, how far behind it is.**

**Four checks:**
1. The monolith exists and names a `vetted against` bundle version.
2. The `current bundle X / engine Y` parenthetical, if present, matches the live `pyproject.toml` / `BUILD_STAMP`.
3. The drift (live bundle patch − vetted patch) is reported, and fails above `--max-drift`.
4. **No retired doctrine is present** — assembly tiers 66/50/33, per-BGC BSL-2 flagging, AS_SCRUB, the PUBLIC/PRIVATE figure divider. These are decisions the project has explicitly reversed, and a fresh chat reads the monolith first.

```bash
python3 tools/check_monolith_freshness.py                # default max-drift
python3 tools/check_monolith_freshness.py --max-drift 10
python3 tools/check_monolith_freshness.py --quiet
```

| Exit | Meaning |
|---|---|
| 0 | Fresh enough and doctrinally current |
| 1 | Stale anchor or retired doctrine present |
| 2 | Monolith missing |

**Live receipt on bundle v9.7.246:**

```
monolith: vetted v9.7.242 | live v9.7.246 | drift 4 patches | 450,214 chars
check_monolith_freshness: PASS (anchor honest, no retired doctrine)
```

**Negation awareness.** The gate false-positived on its own first run, flagging a freshly written "no per-BGC BSL-2 flagging" as an assertion of the doctrine it denies. A negation-aware window was added — the same lesson the v9.7.233 novelty lint learned. It still fails on a genuine assertion (`GOOD >= 66%`).

---

## Section 17: Gate Additions (v9.7.246–.256)

### `PHANTOM_LOCUS` — release-blocking referent validation

Not a standalone tool: a lint inside `mamey/modeb_structure_gate.py`, reachable through `python mamey_run.py verify-modeb` and `authored_verify`.

**What it asks:** does every `ctgN_M` locus tag cited in this Mode B card exist in **this strain's own CDS table**?

**Why it exists:** the §4 authoring template hardcoded a real per-gene BLASTp result from *Amycolatopsis* sp. NPDC004378, which was templated verbatim into 74 cards across two strains — asserting a specific BLASTp outcome for strains on which no BLASTp had been run. Every existing guard passed those cards. None of them asked whether the cited gene existed. (Full account: Development Issues Compendium, Group 13.)

**How to invoke:**

```bash
python mamey_run.py verify-modeb '<authored-card.md>' --package '<sealed_pkg>' --bgc '<alias>' --contract full48    # loads known_loci automatically
```

`authored_verify` globs `<pkg>/*_cds_table.csv` and `<pkg>/cds_table.csv` to build `bgc_context["known_loci"]`. Without a sealed package there is no CDS table, and **the lint is silent** — it cannot judge what it cannot see, and a false accusation of fabrication is worse than none.

**Severity:** ERROR. Added to `_READINESS_BLOCKING` alongside `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`, and `FACT_MISMATCH`. A card citing a foreign locus cannot reach `EVIDENCE_MATRIX_VALIDATED` and therefore cannot be presented.

**Verified against the real AS-XXX package:** 758 loci loaded; `ctg12_71` not among them; the leaked sentence raises ERROR and drops `readiness_state` to `DRAFT`. A card citing that strain's real loci passes clean.

**Operational consequence:** the 74 already-authored cards are not repaired by the fix. Re-run `verify-modeb` against them with a sealed package and every one will flag. **Every §4 and §16 paragraph containing `ctg12_71` should be deleted, not reworded** — there is no BLASTp result to reword.

### `LOCUS_BGC_MISMATCH` — real locus cited under the wrong BGC (v9.7.256)

Sibling of `PHANTOM_LOCUS` in `mamey/modeb_structure_gate.py`, reached through `verify-modeb` / `authored_verify`. Where `PHANTOM_LOCUS` asks *does this gene exist in this strain at all*, `LOCUS_BGC_MISMATCH` asks *does this gene, which does exist, belong to the BGC it is cited under*.

**What it asks:** for a `ctgN_M` that is a real member of this strain's CDS table, is it cited under its home BGC, or co-cited under a different BGC it does not belong to?

**Why it exists:** the AS-XXX BGC006/BGC010 leak class — templated boilerplate carried from one BGC's session into another's card attributes a real gene to the wrong cluster. The gene is real (so `PHANTOM_LOCUS` stays silent), but the attribution is fabricated. `authored_verify` builds per-BGC membership so the lint can tell a real gene cited under the wrong BGC from a correctly-placed one.

**Severity:** ERROR → the card drops to `DRAFT` (Section 18) and cannot be presented. It is **not** a member of the four-code `_READINESS_BLOCKING` set; it blocks via the any-ERROR path.

### `PANEL_ABSENT_CLAIM` — per-gene BLASTp result asserted for a BGC with no panel (v9.7.256)

Sibling lint (same file / entry points). Guards the independent-homology channel against fabricated results.

**What it asks:** does the card state a per-gene BLASTp outcome for a BGC that has **no BLASTp panel** in this package?

**Why it exists:** a BLASTp result for a BGC whose panel was never built is a fabricated observation (the same AS-XXX BGC006 class). `authored_verify` records which BGCs actually have a panel so the lint can flag a per-gene claim on a BGC with none.

**Keys on panel *selection*, not returned alignments (residual gap, stated):** a standard run builds a selection FASTA for *every* BGC, so this lint does **not** catch a fabricated per-gene result on a BGC that has a panel selection but was never actually run (reproduced on `S_erythraea` BGC017). The residual gap is "asserted result vs actual returned alignments"; a future gate closing it should extend `PANEL_ABSENT_CLAIM` to require a results artifact, not add a new gate.

**Severity:** ERROR → `DRAFT`; blocks via the any-ERROR path, not a `_READINESS_BLOCKING` member.

---

## Section 18: Card Readiness State Machine

Documented here because `verify-modeb` reports it and no other section covers it. Source: `mamey/modeb_structure_gate.py:readiness_state`.

```python
_READINESS_BLOCKING = {"NOVELTY_CONTRADICTION", "INTERNAL_CONTRADICTION", "FACT_MISMATCH",
                       "PHANTOM_LOCUS"}


def readiness_state(findings, quality_tier: Optional[str] = None) -> str:
    """Return a mechanical validation state, never an owner/release state.

    Character/depth diagnostics and deterministic lints cannot confer scientific
    acceptance, integration, rendering approval, release approval, or publication approval.
    """
    findings = list(findings or [])
    if any(f.get("severity") == "ERROR" for f in findings):
        return "DRAFT"
    if quality_tier in (None, "STUB", "UNKNOWN"):
        return "DRAFT"
    if {f.get("code") for f in findings} & _READINESS_BLOCKING:
        return "STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS"
    return "EVIDENCE_MATRIX_VALIDATED"
```

| State | Meaning | May be presented? |
|---|---|---|
| `DRAFT` | Any ERROR finding, **or** the card is a STUB / depth-unverified | No |
| `STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS` | Depth is adequate, but a correctness check fails (one of the four blocking codes) | No |
| `EVIDENCE_MATRIX_VALIDATED` | Depth adequate **and** no correctness block | Mechanically clear; presentation still needs owner judgment |

**Only `EVIDENCE_MATRIX_VALIDATED` should flow into user-facing documents.** This is the mechanical presentation gate, not a release or scientific-acceptance state (the function's own docstring says so). A card that is structurally complete, adequately deep, and claim-safe can still be `STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS` rather than `EVIDENCE_MATRIX_VALIDATED` — because a fact in it contradicts the package, or a locus in it belongs to another organism.

Note the asymmetry: an ERROR-severity finding drops a card all the way to `DRAFT`; a blocking *code* at WARN severity holds it at `STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS`. `PHANTOM_LOCUS` is emitted at ERROR severity, so a phantom locus produces `DRAFT`.

---

## Section 19: BLASTp toolchain + release-qa (v9.7.247–.260, CLI synced v9.7.260)

The independent per-gene homology channel and its ingest/iterate commands, plus the release gate. These are `mamey` subcommands (not `tools/` scripts); descriptions are from the registered CLI (`mamey <cmd> --help`), verified against the tree at v9.7.260.

**§4 authoring — offline path preferred (v9.7.260).** A Mode B lead card's §4 is authored *after* the BLASTp panel exists, but there are two ways to produce the same `<BGC>_online_blastp.csv` panel and the offline one avoids live polling:

- **token-friendly / offline (preferred when results are in hand):** if NCBI BLAST has already been run, ingest the hit-table with zero network via `python mamey_run.py ingest-blastp` — no RID poll, no ~1–2 min/query wait.
- **live:** `python mamey_run.py blastp-online` submits to NCBI and polls; use only when no pre-run results exist.

With no results at all, the honest read is "antiSMASH Pfam, unverified" — never fabricate (see `PANEL_ABSENT_CLAIM` / `PHANTOM_LOCUS`, Section 17).

**`python mamey_run.py bgc-blastp-panel`** — Export up to two representative translated proteins per BGC as chunked FASTA files for manual BLASTP. The panel *selection* is what downstream gates read to decide a BGC "has a panel" (`PANEL_ABSENT_CLAIM`).

**`python mamey_run.py blastp-online`** — Per-gene NCBI web BLASTp for a BGC (independent homology channel; fail-closed if biopython/network absent — actionable message, not a traceback). Its banner now points at the offline `ingest-blastp` route to skip live polling.

**`python mamey_run.py blastp-ebi`** — EBI fallback BLASTp transport (no nr; DB-tagged provenance;
coverage-preserving XML path). Live submission requires a valid EBI contact email plus
`--confirm-public-sequence-upload`; the sequence count and SHA-256 receipt print before transport.

**`python mamey_run.py blastp-round`** — Plan/run a phased strain BLASTp round (full top-N + 1 per remaining BGC).

**`python mamey_run.py blastp-followup`** — Parse NCBI BLASTP Hit Table / XML2 results and make the next iterative, residue-safe BLASTP queue files.

**`python mamey_run.py ingest-blastp`** — Ingest an NCBI BLASTp HitTable CSV (+ optional Alignment XML) into a master workbook's `B5_BLASTp_Hits` sheet; with `--package`, mirrors the panel to `<package>/blastp_online/<BGC>_online_blastp.csv`. This is the offline, zero-network path.

**`python mamey_run.py modeb-blastp`** — Emit per-BGC BLASTP FASTA batches from the panel manifest (Mode B §16 automation).

**`python mamey_run.py hmm-adjudicate`** — Ordered HMM domain readout for a BGC (intrinsic structure; offline tie-breaker that complements BLASTp when it disagrees with the antiSMASH call).

**`python mamey_run.py release-qa`** — Run release QA gates: Legacy Feature Matrix + Dual-LLM Handoff Receipt.

*Batch rule (v9.7.252): a submission closes on protein count OR a 30,000-aa `RESIDUE_BUDGET`, whichever hits first; `MAX_BATCH` stays 30 and `DEFAULT_BATCH` is 10 (the courteous default used when the caller omits `batch_size`); giants (>2,500 aa) run solo; `SUBMIT_GAP_S` spaces submissions.*

*Mode B referent lints (v9.7.246/.256): `PHANTOM_LOCUS` (locus not in this strain's CDS table), `LOCUS_BGC_MISMATCH` (real locus cited under the wrong BGC), `PANEL_ABSENT_CLAIM` (per-gene BLASTp result asserted for a BGC with no panel). All ERROR-severity → `DRAFT`. Full detail in Section 17.*

*Section 19 added v9.7.260; command descriptions from the registered `mamey <cmd> --help`.*

---

## Section 20: New post-seal subcommands & deliverables (v9.7.338)

Twelve sign-off-gated capabilities that consume an **already-sealed package** (or a directory of
them) and emit an extra deliverable. Like `render-figures` / `cohort-figures` / `ingest-receipts`,
every one is post-seal and non-blocking: it reads facts the engine already computed and **never
re-runs the engine, moves a score, or touches a published tier**. Non-scoring unless noted;
capacity-level, judgment deferred.

```bash
# --- CROSS-STRAIN LEDGERS ---
python mamey_run.py cohort-leads    --runs-dir <runs_dir> [--out COHORT_PRIORITY_LEADS.csv]   # union Exceptional+High leads → one ranked CSV
python mamey_run.py cohort-assemble --runs-dir <runs_dir> [--out COHORT_MASTER.csv] [--xlsx]  # many sealed packages → one master table (+ siblings)

# --- EVIDENCE / FALSE-POSITIVE LAYER ---
python mamey_run.py comparator-coverage <package> [--cohort-runs-dir <runs_dir>] [--out <dir>]  # two-denominator MIBiG comparator coverage (report-only)
                                                                     # standalone: python -m mamey.mibig_comparator_coverage <package_dir> [--cohort-runs-dir <dir>]

# --- ANTIFUNGAL + INTERPRETIVE DELIVERABLES ---
python mamey_run.py af-dossier   <root> [--out DIR] [--activity-table CSV] [--depth N]  # AF leads x optional measured Candida activity (report-only)
python mamey_run.py good-guesses <root> [--out DIR] [--pdf] [--docx] [--depth N]       # claim-safe interpretive priors (solid/rare/remarkable/notable/interesting)
                                                                          # standalone: python -m mamey.good_guesses <ROOT|package_dir> --out <DIR> --pdf --docx

# --- DOCUMENT + FIGURE EXPORT ---
python mamey_run.py modeb-export <card.md|mode_b/> [--outdir DIR] [--format docx|pdf|both]  # authored Mode B card → .docx + .pdf (reportlab)
python -m mamey.kcb_locusmap --zip <zip> --contig <NODE> --out-dir <dir> \
    --strain-id <ID> --bgc-id BGC### [--products "..."] [--top-n 6]           # offline KCB comparative locus map (PNG/SVG + data.csv)
                                                                              # or: --kcb-txt <knownclusterblast.txt> --out-dir <dir> --stem BGC###

# --- COUNT / NOVELTY / REFERENCE (advisory) ---
python mamey_run.py domain-reference  --package <pkg> [--out DIR]             # bundled Mode-B domain-reference dictionary
python mamey_run.py realistic-count   --package <pkg> [--out DIR]             # honest corrected BGC-count denominator
python mamey_run.py novelty-shortlist --package <pkg> [--top 30] [--out DIR]  # composite multi-signal novelty shortlist

# --- ANALYSIS QC + MODE-B INTERPRETATION GATES ---
python mamey_run.py signoff [tree.treefile ...] [--minutes N]                          # "would a master's student sign off?" tree QC (advisory, exit 0)
python mamey_run.py verify-modeb '<authored-card.md>' --package '<pkg>' --bgc '<alias>' --contract full48 --interp  # add WARN-only INTERP_* judgment checks to verify-modeb
                                                                           # strict authoring gate: python -m mamey.modeb_interp_gate <card.md> [--strict]
```

**Notes.**
- **`comparator-coverage`** emits `<STRAIN>_3b_comparator_coverage.csv` + `_summary.json` in a sibling output directory by default (or `--out <dir>`). It is the
  false-positive killer: a named-MIBiG-family "lead" that survives only one of the two coverage
  denominators is exposed as low-specificity rather than surfaced. Report-only in .338 — its scoring
  wire (suppression-only, guard-gated) is a future sign-off-gated change and is NOT active.
- **`good-guesses`** writes `GOOD_GUESSES.{md,csv}` (+ `.docx` / `.pdf` on request). Each notable BGC
  gets ONE best claim-safe read, a tag (solid / rare / remarkable / notable / interesting), a
  confidence, and the resolving experiment; a per-page claim-safety footer is included.
- **`modeb-export`** — `reportlab` (PDF) is a core dependency in `pyproject.toml`, installed by `pip install -e .`;
  `python-docx` is only in the `documents` / `all` extras, so the DOCX path degrades gracefully
  (`SKIPPED_NO_DOCX`) rather than failing when it is unavailable.
- **`figures kcb-locusmap`** degrades to a clear message + non-zero exit (never a traceback) when
  matplotlib is absent; it reads only a sealed input ZIP (or an extracted txt) and cannot fail a run.
- **`verify-modeb --interp`** only *adds* WARN-severity `INTERP_*` findings — the structure gate's
  PASS/FAIL and exit code are unchanged (a card can be green and still show interp warnings).

**Non-feature .338 changes reflected here:** the **§4 Mode-B evidence gate now bites (MB-01)** (the
evidence-grid check is enforcing, not advisory), the **NAPAA standing rule now follows the registry
(RG-01)** (driven by `rules_registry.json`, not a hardcoded pattern — same behaviour, single source),
and the redaction wording is corrected (E2E-03): AS-series strains are PUBLIC by default (PI decision
2026-07-06), fail-safe PRIVATE only for AJS- / PENDING- / unrecognized shapes.

---

*v3 additions: Sections 16–18 (file_atlas, check_monolith_freshness, PHANTOM_LOCUS gate, readiness state machine) · Bundle v9.7.246 · 2026-07-09*
*v4 additions: Section 17 extended with `LOCUS_BGC_MISMATCH` + `PANEL_ABSENT_CLAIM` (v9.7.256); Section 19 (BLASTp toolchain + release-qa, offline-preferred §4); header CLI-synced · Bundle v9.7.260 · 2026-07-11*
*v5 additions: Section 20 (twelve new post-seal subcommands & deliverables) · v9.7.338*

## Suite-receipt verification and recovery

External receipt verification and candidate-local suite recording use distinct schemas, digests and completion contracts. Read [current receipt scope](../reference/06_CURRENT_SOURCE_SCOPE.md#configured-suite-receipts-two-owners-and-different-contracts) before reusing a receipt or rerunning its producer. Receipt acceptance binds selected supplied evidence; it does not independently certify the full collected test roster or final archive. The recorder’s `run` action executes the slow/network suite and replaces local approval/log state.
