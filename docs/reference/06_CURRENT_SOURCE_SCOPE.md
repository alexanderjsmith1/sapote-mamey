# Check tools: what a PASS does not cover

Use this page when a check tool says PASS or exits 0 and you need to know what it did not check.
Each section names a tool, its command and what it does not check. If the page and the tool disagree,
the tool's source code is right. Scientific interpretation is yours to make with the project lead.

Two rules apply everywhere. A PASS is a software check, not scientific acceptance. Cite each locus as
strain / full node-or-contig / region / BGC alias; matching an alias alone does not check the contig or region.

Where to look instead:
[reference index](00_README.md) ·
[tools reference](../user_guides/tools_reference.md) ·
[task router](../USER_TASK_ROUTER.md) ·
[glossary](../GLOSSARY.md) ·
[custom privacy tiers](../CUSTOM_PRIVACY_TIERS.md).

<a id="volume-i-section-66-standing-rule-selection-scope-and-policy-conflict"></a>
## Scores and rules that changed

- **NAPAA and hglE.** NAPAA (non-alpha poly-amino acids) and hglE-KS (a heterocyst-glycolipid-type ketosynthase) are defined in the [glossary](../GLOSSARY.md). `mamey/data/rules_registry.json` marks NAPAA neutral and hglE-KS noted. Both are
  nonblocking in the registry. Saccharide is a lead-blocking exclusion. `mamey/scoring.py` still has an
  own-product fallback for hglE-KS: when no registry rule matched and no CCTT trigger fired on the BGC, an hglE
  product label sets the `hglE-KS-PREV-001` standing rule. That caps the tier at the bottom tier and withholds
  `corrected_rank`; raw scores are kept.
- **Assembly quality.** `mamey/assembly.py` gives a weighted count and 70/45/20/UNKNOWN labels. These are
  engineering diagnostics. Keep raw counts and boundary state beside them.
- **RG-GMCI score labels.** RG-GMCI is defined in the [glossary](../GLOSSARY.md). Reference-row scores use 14/9 thresholds. Pair rollups add support and
  geometry terms before applying thresholds and gates. Read the final verdict and its evidence; a HIGH
  label identifies a candidate link and does not establish a physical contig join.
- **Version stamps.** `tools/sync_version.py` updates version lines in the references. It does not re-check
  the formulas under them.

<a id="plumbing-part-1-current-cli-contracts"></a>
## Command-line behavior

- Run modes: `gold`, plus the deprecated `standard` alias. `smoke` is gone. Gold extracts evidence; it does
  not author Mode B cards.
- `--antismash-profile` defaults to `auto` and reads strictness from the archive. A disagreement is reported
  as `PROFILE_MISMATCH` and the run continues with your value.
- The main full-mode JSON walker refuses a member above 80,000,000 bytes. Other JSON and GBK readers
  have independent caps and switches. `--json-evidence off` stops the main walker; GBK Pfam extraction
  still runs. `run --json-evidence` defaults to `bounded`; `--capped-session` forces `off`. The separate record pass still reads eligible, readable JSON for KCB percent and other record evidence; inspect its status for missing, held or unreadable input.
- Privacy defaults to PRIVATE unless you supply an exact public roster or override. A strain-ID prefix grants nothing.
  See [custom privacy tiers](../CUSTOM_PRIVACY_TIERS.md).
- `validate` separates extraction completeness from judgment completeness. A `MAMEY_COMPLETE` result
  with exit 0 does not certify authored cards; read the judgment state too.

<a id="plumbing-part-2-master-writer-and-retained-values"></a>
<a id="plumbing-part-4-gene-exports-and-package-integrity"></a>
<a id="plumbing-part-5-brief-profiles-display-labels-and-boundary-payloads"></a>
<a id="plumbing-part-7-stored-depth-receipt-admission-and-legacy-readiness"></a>
## Workbook, package and brief writers

- The master writer adds a header column for an unfamiliar key; it does not drop it.
- A brief status of `COMPLETE` means the main brief returned. Optional figure families can still have been
  skipped. Check the files on disk.
- Re-ingesting a Mode B card replaces the card and upserts that alias's layperson and fermentation
  sections. Legacy duplicate sections are consolidated; other sections are retained.

<a id="aggregate-figure-rendering-selection-writes-and-completion"></a>
## Rendering every figure

Copy the package first and run on the copy; see [figures start here](../FIGURES_START_HERE.md).
`python mamey_run.py render-all-figures --package reviews/EXAMPLE-copy/package` runs five sets by default: smoke, brief, locus-maps,
figure-suite and domain-level. `--all` adds cohort-class and mamey-native. `--include` wins over `--all`;
`--exclude` removes sets.

- Any errored or unknown set gives `FAIL` and exit 1. Later sets still run unless you pass `--fail-fast`.
- Skipped sets give `PASS_WITH_SKIPS`, even when every set skipped. An empty set list gives `PASS`.
  Read the per-set results, not the exit code.

<a id="combined-v7-and-mode-b-report-builder"></a>
<a id="refreshable-exact-identity-report-selection-and-publication-routes"></a>
<a id="refreshable-report-evidence-admission-profiles-channels-and-mode-b"></a>
## Report builders

`python3 tools/build_combined_bgc_report.py --job-spec path/to/job-spec.json --source-root ID=/actual/source/root --out-root reviews/EXAMPLE-combined` composes
an existing report packet with V7 report sections and Mode B sections (see the [glossary](../GLOSSARY.md) for Mode B). It does not rerun BLASTp or write missing sections.
An excluded job returns `EXCLUDED_NO_OUTPUT` and exit 3. A built draft returns exit 0; check `status`
in its JSON.
A built dossier reads `DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED`. `python3 -m mamey.bgc_report_builder` is the
refreshable exact-identity report.

<a id="input-manifests-and-zip-preflight-scopes"></a>
## Input manifests and ZIP checks

`python3 tools/input_manifest.py --label EXAMPLE --out reviews/EXAMPLE-inputs --inputs path/to/input.zip --denominator path/to/keys.txt` hashes each input and writes
`<label>_INPUT_MANIFEST.tsv` and `<label>_COVERAGE_REPORT.md`.

- Exit 3 means an expected key was not consumed. Extra keys are listed but do not change the exit.
- With no `--denominator`, or an empty one, it exits 0. That is no coverage check at all.
- Keys come from file names. Basename mode can merge different files into one key.

`tools/preflight_zip_hygiene.py` checks a path's declared ceiling first, even below the global 5 MiB
limit and for `.whl`, `.xlsx` or `.pdf` members. Unlisted members use the global limit and its
`registry_inventory`/suffix exemptions. The directory checker `tools/zip_hygiene_allowlist.py` accepts
files up to its default 5 MiB limit before consulting its allowlist for larger files, and exits 2 for
a violation. Its PASS does not enforce a smaller declared path ceiling. Keep the two checks distinct.

<a id="phylogeny-preflight-local-probes-and-conditional-checks"></a>
<a id="phylogeny-postflight-lexical-checks-and-unmeasured-evidence"></a>
## Tree checks

```bash
python3 tools/phylo_postflight.py '<treefile>' --outgroup '<token>' \
  --genomes-dir '<input-dir>' --scope family --json '<receipt.json>'
```

- It reads a finished tree. It does not build, reroot or draw one.
- `--json` must be a fresh path that is not an input. An existing file, the tree itself or a file inside `--genomes-dir` is refused with `OUTPUT_REFUSED` and exit 2 before any check runs.
- `--outgroup` is a substring match on tip names. Keep an exact tip list elsewhere.
- Each check prints one row: `ok` (pass), `~` (warning) or `FAIL`. A last line counts them, for example
  `--- 4 pass / 1 warn / 0 FAIL ---`. Fix every `FAIL` before you publish the tree.
- P5 needs at least five ingroup branch lengths and warns above five times the median.
- P6 counts top-level `.fna` files only. Zero files gives a P6 WARN. Warnings still exit 0; read the row.
- Only FAIL rows give exit 1. Warnings come with exit 0.

<a id="16s-store-defect-validation-and-additive-merge-screening"></a>
## 16S store checks

`tools/phylo_16s_validate_db.py --db <store>` runs two data-quality screens. Exit 0 means no selected
defect; exit 1 means at least one; bad input gives 2. `REVIEW_NEEDED` rows do not set the defect flag, so
read them separately. A missing `metadata_source` column is a defect. A blank value on a row carrying selected metadata counts as unknown provenance; a row with no selected metadata does not trigger that particular count.

<a id="cross-strain-denominator-and-conservation-audit-coverage"></a>
## Cross-strain denominators

`python3 tools/cross_strain_denominator_audit.py path/to/cohort-workbook.xlsx` scans selected `N/M` tokens on four cross-strain sheets. It applies a bounded detector, accepts selected registry/BGC totals and reports some ambiguous tokens separately for review. Compare the relevant unit and roster yourself. Substitute real bound paths in these examples, quote spaces and select fresh authorized output folders.

- It reads cached cell values. It does not recalculate formulas.
- A workbook with none of the four sheets passes.
- With no BGC inventory sheet, a `1/0` token can pass.
- It accepts either the strain total or the BGC total for any token.

<a id="finished-text-citation-hygiene-and-strict-source-disclosure"></a>
## Citation and disclosure checks

```bash
python3 tools/deliverable_citation_audit.py '<file-or-dir>' --strict --json --out '<audit.json>'
python3 tools/strict_source_disclosure_audit.py '<staging-tree>' --json
```

The citation audit checks locator patterns in `.md`, `.markdown` and `.txt` files. It does not read DOCX
or PDF, and it does not check the full four-part locus identity. `--strict` exits 1 only for BLOCK findings.

<a id="receipt-timestamps-and-monolith-freshness-gates"></a>
<a id="tool-inventory-concept-search-and-static-connection-evidence"></a>
<a id="configured-suite-receipts-two-owners-and-different-contracts"></a>
<a id="separate-manifestschema-drift-screen"></a>
<a id="find-a-current-contract"></a>
## Docs and inventory checks

`python3 tools/check_dangling_refs.py --scope all --strict-paths` checks that paths named in docs exist.
The generated tool catalog guesses a tool's interface from its source text; a comment can make a tool
look like a CLI. Two different suite-receipt formats exist; check which tool wrote a receipt before
comparing them.

## Scan-level limits worth knowing

- **Self-resistance confidence.** `HIGH_CLASS_CONCORDANT` can be set by a class-concordant group that is
  not the diagnostic group.
- **CNBU** (class-normalized biosynthetic units: region length divided by the expected length for the class). Missing, nonnumeric and explicit zero inputs can all appear as `0.0`. Inspect the bound input field and report unavailable or invalid length separately; the output zero alone identifies neither a measured biological span nor its missingness cause.
- **Region span fallback.** When a record has no stored original bounds, the span comes from the last
  region, protocluster or candidate-cluster feature, not their union.
- **External scan pack.** Several pack rows derive from stored counts or flags. Check the per-scan
  producer before treating a pack label as a record of completed execution.

Read the raw fields behind these labels. Ask the project lead before you change a confidence, length or
coordinate rule.
