# Known limits of the check tools

Use this page when a check tool says PASS or exits 0 and you need to know what it did not check.
Each section names a tool, its command and the limits checked in the current source. Use the producing
code to resolve software behavior. Scientific interpretation and the choice of a canonical math reference
remain owner decisions.

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

- **NAPAA and hglE.** `mamey/data/rules_registry.json` marks NAPAA neutral and hglE-KS noted. Both are
  nonblocking. Saccharide is a lead-blocking exclusion. Older "three permanent exclusions" text is out of date.
- **Assembly quality.** `mamey/assembly.py` gives a weighted count and 70/45/20/UNKNOWN labels. These are
  engineering diagnostics. Keep raw counts and boundary state beside them.
- **RG-GMCI score labels.** Reference-row scores use 14/9 thresholds. Pair rollups add support and
  geometry terms before applying thresholds and gates. Read the final verdict and its evidence; a HIGH
  label identifies a candidate link and does not establish a physical contig join.
- **Version stamps.** `tools/sync_version.py` updates version lines in the references. It does not re-check
  the formulas under them.

<a id="plumbing-part-1-current-cli-contracts"></a>
## Command-line behavior that differs from the old plumbing reference

- Run modes: `gold`, plus the deprecated `standard` alias. `smoke` is gone. Gold extracts evidence; it does
  not author Mode B cards.
- `--antismash-profile` defaults to `auto` and reads strictness from the archive. A disagreement is reported
  as `PROFILE_MISMATCH` and the run continues with your value.
- The main full-mode JSON walker refuses a member above 80,000,000 bytes. Other JSON and GBK readers
  have independent caps and switches. `--json-evidence off` stops the main walker; GBK Pfam extraction
  still runs.
- Privacy defaults to PRIVATE unless you supply an exact public roster or override. An `AS` prefix grants nothing.
  See [custom privacy tiers](../CUSTOM_PRIVACY_TIERS.md).
- `validate` separates extraction completeness from judgment completeness. A `MAMEY_COMPLETE` result
  with exit 0 does not certify authored cards; read the judgment state too.

<a id="plumbing-part-2-master-writer-and-retained-values"></a>
<a id="plumbing-part-4-gene-exports-and-package-integrity"></a>
<a id="plumbing-part-5-brief-profiles-display-labels-and-boundary-payloads"></a>
<a id="plumbing-part-6-analysis-forward-and-package-entry-snapshots"></a>
<a id="plumbing-part-7-stored-depth-receipt-admission-and-legacy-readiness"></a>
<a id="card-ingestion-and-recovery-receipts"></a>
## Workbook, package and brief writers

- The master writer adds a header column for an unfamiliar key; it does not drop it.
- A brief status of `COMPLETE` means the main brief returned. Optional figure families can still have been
  skipped. Check the files on disk.
- Re-ingesting a Mode B card replaces the card and upserts that alias's layperson and fermentation
  sections. Legacy duplicate sections are consolidated; other sections are retained.

<a id="aggregate-figure-rendering-selection-writes-and-completion"></a>
## Rendering every figure

`mamey_run.py render-all-figures --package <package>` runs five sets by default: smoke, brief, locus-maps,
figure-suite and domain-level. `--all` adds cohort-class and mamey-native. `--include` wins over `--all`;
`--exclude` removes sets.

- Any errored or unknown set gives `FAIL` and exit 1. Later sets still run unless you pass `--fail-fast`.
- Skipped sets give `PASS_WITH_SKIPS`, even when every set skipped. An empty set list gives `PASS`.
  Read the per-set results, not the exit code.

<a id="combined-v7-and-mode-b-report-builder"></a>
<a id="refreshable-exact-identity-report-selection-and-publication-routes"></a>
<a id="refreshable-report-evidence-admission-profiles-channels-and-mode-b"></a>
## Report builders

`tools/build_combined_bgc_report.py --job-spec <spec> --source-root ID=/abs/path --out-root <dir>` composes
an existing report packet with V7 and Mode B sections. It does not rerun BLASTp or write missing sections.
An excluded job returns `EXCLUDED_NO_OUTPUT` and exit 3. A built draft returns exit 0; check `status`
in its JSON.
A built dossier reads `DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED`. `python3 -m mamey.bgc_report_builder` is the
refreshable exact-identity report.

<a id="input-manifests-and-zip-preflight-scopes"></a>
## Input manifests and ZIP checks

`python3 tools/input_manifest.py --label <name> --out <dir> --inputs <paths…> --denominator <keys.txt>` hashes each input and writes
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
- `--outgroup` is a substring match on tip names. Keep an exact tip list elsewhere.
- P5 needs at least five ingroup branch lengths and warns above five times the median.
- P6 counts top-level `.fna` files only. Zero files gives a P6 WARN. Warnings still exit 0; read the row.
- Only FAIL rows give exit 1. Warnings come with exit 0.

<a id="16s-store-defect-validation-and-additive-merge-screening"></a>
## 16S store checks

`tools/phylo_16s_validate_db.py --db <store>` runs two data-quality screens. Exit 0 means no selected
defect; exit 1 means at least one; bad input gives 2. `REVIEW_NEEDED` rows do not set the defect flag, so
read them separately. A missing `metadata_source` counts as a defect.

<a id="cross-strain-denominator-and-conservation-audit-coverage"></a>
## Cross-strain denominators

`python3 tools/cross_strain_denominator_audit.py '<cohort-workbook.xlsx>'` scans `N/M` tokens on four
cross-strain sheets and checks M against the strain-registry length.

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

<a id="volume-ii-b4-assembly-input-scope-independent-tier-fields-and-warning-limits"></a>
## Scan-level limits worth knowing

- **Self-resistance confidence.** `HIGH_CLASS_CONCORDANT` can be set by a class-concordant group that is
  not the diagnostic group.
- **CNBU.** A missing or non-numeric region length becomes 0 kb with no warning. That 0 means the
  length is missing. It is not a measured length of zero.
- **Region span fallback.** When a record has no stored original bounds, the span comes from the last
  region, protocluster or candidate-cluster feature, not their union.
- **External scan pack.** Several pack rows derive from stored counts or flags. Check the per-scan
  producer before treating a pack label as a record of completed execution.

Read the raw fields behind these labels. Changes to confidence, length or coordinate policy require
owner review.
