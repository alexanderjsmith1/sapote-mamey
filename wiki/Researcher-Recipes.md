# Researcher Recipes

*Current to bundle v9.7.405 · engine Mamey 1.9.145. Authored by Codex (Wiki Revision 03, 2026-08-31) against v9.7.395; admitted to the bundle wiki at v9.7.405 by the Claude Code patch lane after a currency pass. Documentation only — confers no scientific, release, or publication authority; class-level hypotheses, judgment deferred.*


Run commands from the extracted bundle root. Paths below are generic examples. Replace them with governed local paths; do not copy development-workspace paths into a project or public document.

## Recipe 1 — first successful run

### Inputs

- A Python environment satisfying the bundle requirement, Python 3.12 or later.
- One raw antiSMASH output ZIP: `inputs/reference-isolate-001_antismash.zip`.
- A stable public-safe strain label and explicit taxonomy, source, and source-provenance values.
- A writable output root such as `runs/`.

### Command

```bash
python mamey_run.py doctor
python mamey_run.py inspect inputs/reference-isolate-001_antismash.zip
python mamey_run.py run \
  --strain reference-isolate-001 \
  --display-name "Reference isolate 001" \
  --input-zip inputs/reference-isolate-001_antismash.zip \
  --taxonomy "Genus species" \
  --source "deposited sample metadata" \
  --source-provenance table \
  --mode gold \
  --json-evidence bounded \
  --outdir runs
python mamey_run.py validate runs/reference-isolate-001/package
python mamey_run.py explain runs/reference-isolate-001/package
```

Omit `--release` unless a governed privacy profile or a deliberately more restrictive setting requires it. Do not add `doctor --probe-transports` to an offline first run; that option is explicitly networked.

### Outputs

- `runs/reference-isolate-001/package/` with `manifest.json`, `checksums_sha256.txt`, `gate_validation.json`, numbered outputs, and package receipts.
- A sealed `*_Complete_Package.zip` under the strain run directory.
- `runs/HANDBACK.json`, which points to the sealed deliverable.
- Plain-language output from `explain`; it does not rewrite the extraction.

### Expected typed states

- `doctor`: `DOCTOR: ALL CLEAR` or `DOCTOR: PASS with ... warning(s)`; any blocking issue must be fixed before the run.
- `inspect`: exit 0, at least one antiSMASH region GBK, and a recognized raw antiSMASH input shape.
- `run`: terminal `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES`; `VALIDATION_FAIL` is a stop.
- `validate`: `MAMEY_COMPLETE` when deterministic extraction is complete and judgment remains pending, or `PASS` after the applicable completeness conditions pass. Check `checksum_integrity` separately.
- `package_status`: normally `MAMEY_COMPLETE`; recovery states remain distinct.

### Common failure

`inspect` reports that the ZIP contains no region GBKs. This usually means the input is a raw assembly or another ZIP type, not an antiSMASH result. Do not force the run; produce a valid antiSMASH output ZIP first.

### What this result does not establish

A successful first run does not establish compound identity, expression, production, bioactivity, novelty, causal phenotype linkage, completed Mode B judgment, public-release suitability, owner acceptance, or publication readiness.

## Recipe 2 — one-strain run with deliberate metadata

### Inputs

- One ZIP already accepted by `inspect`.
- A stable strain label that is not merely a convenience filename.
- Taxonomy, source, and provenance values whose evidence strength is known.
- Optional typed bioactivity JSON or privacy profile only when those governed inputs actually exist.

### Command

```bash
python mamey_run.py run \
  --strain reference-isolate-002 \
  --display-name "Genus species reference-isolate-002" \
  --input-zip inputs/reference-isolate-002_antismash.zip \
  --taxonomy "Genus species" \
  --source "culture collection record" \
  --source-provenance accession \
  --mode gold \
  --json-evidence bounded \
  --outdir project_runs
python mamey_run.py validate project_runs/reference-isolate-002/package
```

Use `--json-evidence off` when JSON processing must be deliberately disabled. Use `full` only after checking the size refusal documented by command help. The choice changes evidence availability, not biology.

### Outputs

- One per-strain package directory.
- One sealed per-strain package ZIP.
- A manifest recording the run mode, metadata, evidence mode, version, and package inventory.
- Optional nonblocking enrichments and issue records when their dependencies are available.

### Expected typed states

- `MAMEY_COMPLETE`: extraction and package gates completed for the recorded input.
- `MAMEY_COMPLETE_WITH_ISSUES`: the package completed, but `issue_count` and `issues` require review.
- `VALIDATION_FAIL` or `MAMEY_FAILED`: do not begin post-seal interpretation.
- `JUDGMENT_PENDING` inside the gold-completeness dimension is expected for a fresh extraction package.

### Common failure

Supplying a database accession as the strain identity without deliberately enabling the accession-label compatibility option can be refused or upgraded from archive metadata. Treat accession, organism name, and local strain identity as different fields; do not silently collapse them.

### What this result does not establish

Explicit metadata improves provenance but does not prove the stated host, habitat, phenotype, or activity belongs to any individual locus. Strain-level context cannot be localized without separate evidence.

## Recipe 3 — small batch of up to about three strains

### Inputs

- Two or three antiSMASH ZIPs, each already checked with `inspect`.
- Pipe-separated taxonomy and source lists aligned to the ZIP order.
- One provenance enum shared by the batch. In v9.7.395, the help text describes pipe-separated provenance, but the parser accepts only one of `accession`, `table`, `filename`, or `asserted`.
- A shared output directory.
- An optional master workbook path for cross-strain accumulation.

### Command

```bash
python mamey_run.py run \
  --strains \
    inputs/reference-isolate-001_antismash.zip \
    inputs/reference-isolate-002_antismash.zip \
  --taxonomy "Genus species|Genus species" \
  --source "collection record A|collection record B" \
  --source-provenance table \
  --mode gold \
  --json-evidence bounded \
  --outdir runs \
  --master project_master.xlsx
```

The batch path resolves strain identifiers from archive content or filenames and suffixes collisions rather than overwriting an earlier result. Confirm the resolved identities printed by the command.

### Outputs

- One `runs/<resolved-strain>/package/` directory and sealed package ZIP per input.
- `runs/HANDBACK.json` listing the primary sealed deliverables.
- `project_master.xlsx` when workbook creation succeeds.
- Best-effort cross-strain figure outputs for multi-strain runs; these never replace per-strain package validation.

### Expected typed states

- A result object per strain, each with its own terminal status.
- Batch exit 0 only when every result is a recognized terminal success.
- Optional cross-strain figure steps may report `SKIPPED` without invalidating already sealed per-strain packages.
- Workbook failures become issues and may be blocking only when `--require-workbook` is used.

### Common failure

Trying `--source-provenance "table|asserted"` is rejected by the v9.7.395 parser even though its help text describes a pipe-separated batch form. Use one truthful shared value, or split inputs with different provenance states into separate runs. A shorter taxonomy or source list falls back to `not verified` or `not supplied`; fix the alignment and use a new governed output root if the recorded metadata is unacceptable.

### What this result does not establish

A successful batch does not establish a scientifically valid cohort, comparable antiSMASH settings, harmonized evidence availability, a shared biological denominator, or cross-strain causal conclusions.

## Recipe 4 — validate a package

### Inputs

- An unpacked package directory, not the sealed ZIP itself.
- The bundle version intended to validate that package.
- Permission to update mutable status receipts inside the package.

### Command

```bash
python mamey_run.py validate runs/reference-isolate-001/package
```

For a workbook-content gate that changes the exit code on workbook failure:

```bash
python mamey_run.py validate \
  --workbook-strict \
  runs/reference-isolate-001/package
```

### Outputs

- JSON on standard output containing file-presence, checksum, RG-GMCI, reporting, exclusion, depth, and package-status results.
- A `WORKBOOK_CONTENT` result on standard output.
- An updated mutable `package_status.json` receipt.

### Expected typed states

- Validator `MAMEY_COMPLETE` or `PASS`: command exits 0.
- Validator `FAIL`: command exits nonzero.
- Package recovery status: `MAMEY_COMPLETE`, `RECOVERY_VALIDATED`, `RECOVERY_NEEDED`, or `PARTIAL_FAILED`.
- Workbook state: `PASS`, `SKIP`, or a non-pass state; it blocks only under `--workbook-strict`.

Read validator status and recovery status together. `RECOVERY_VALIDATED` means the recovered object passed its applicable checks; it does not rewrite history as an uninterrupted run.

### Common failure

Pointing `validate` at the sealed ZIP or at the parent run directory instead of the unpacked `package/` directory produces missing-file failures. Resolve the exact package directory before diagnosing content.

### What this result does not establish

Validation proves only the implemented package gates for the exact bytes inspected. It does not prove interpretation quality, biological truth, experimental validity, owner acceptance, integration, release, or publication readiness.

## Recipe 5 — post-seal Mode B start

### Inputs

- A package that currently validates.
- A normalized CSV or TSV inventory with `strain`, `bgc`, `full_node` or `node`, and `region` columns. Every row must form `strain / full node-or-contig / region / BGC alias`.
- One or more configured evidence roots and, when available, a curated evidence-index TSV with explicit freshness states.
- An additive output directory outside score-bearing extraction files.

The package's numbered inventory is not automatically a valid `modeb-availability` input in v9.7.395 because its shipped header shape lacks the required normalized strain and lowercase identity fields. Build or use an explicit normalized crosswalk; do not guess missing fields.

### Command

```bash
python mamey_run.py modeb-availability \
  --inventory project/per_bgc_inventory.tsv \
  --source-root package=runs/reference-isolate-001/package \
  --evidence-index project/curated_evidence.tsv \
  --out project/modeb_availability
python mamey_run.py mode-b \
  --package runs/reference-isolate-001/package \
  --top-n 10 \
  --outdir project/mode_b_native
```

Omit `--evidence-index` when no curated index exists; absence then remains `UNVERIFIED` or another typed state. Do not fabricate `CURRENT` from timestamps or filenames.

### Outputs

- Availability: evidence observations, per-locus availability, per-strain availability, section plan, summary Markdown, and `modeb_availability_manifest.json`.
- Native Mode B: top-lead Markdown and CSV plus `Mode_B_Coverage_Receipt.json`.
- Separate per-locus writing, promotion, work, binding, freshness, section-support, and coverage states.

### Expected typed states

- Binding: `EXACT_LOCUS`, `ALIAS_BOUND`, `STRAIN_ONLY`, `UNBOUND`, or `ABSENT`.
- Writing: `PASS_FOR_GAP_AWARE_AUTHORING`, `HOLD_IDENTITY_UNRESOLVED`, or `HOLD_MISSING_GENE_LEVEL_SOURCE`.
- Promotion: `HOLD_BLASTP_UNAVAILABLE_OR_UNBOUND`, `HOLD_BLASTP_FRESHNESS_UNVERIFIED`, or `ELIGIBLE_FOR_SEPARATE_INTERPRETIVE_REVIEW`.
- Section plan: `EVIDENCE_AVAILABLE_REQUIRES_INTERPRETATION`, `CONTEXT_ONLY_DO_NOT_LOCALIZE`, or `WRITE_EXPLICIT_GAP_OR_HOLD`.
- Native coverage: `FULL_NATIVE_MODEB_COVERAGE`, `PARTIAL_NATIVE_MODEB_COVERAGE`, `PARTIAL_TOPN_MODEB_COVERAGE`, `TOPN_NATIVE_MODEB_COVERAGE`, or `INVENTORY_UNKNOWN_MODEB_COVERAGE`.

Treat native `mode-b` output as generated top-lead material, not as an automatically finished current 48-section card. Current full Mode B still requires the current contract, exact identity, evidence-channel separation, authoring, and verification.

### Common failure

Using `modeb-availability --package ...` fails because that option does not exist in v9.7.395. The command requires `--inventory` and `--out`; evidence enters through repeatable `--source-root` and `--evidence-index` options.

### What this result does not establish

Availability `PASS`, an eligible promotion gate, native coverage, or a generated card does not establish correct interpretation, compound identity, novelty, production, activity, experimental adjudication, owner acceptance, release, or publication readiness.

## Recipe 6 — Figure Factory Next preflight and refusal

### Inputs

- A metrics TSV under a configured external data root.
- Required columns: `identity`, `channel`, `metric`, `numerator`, `denominator`, and `denominator_key`.
- Exactly one `aggregate_metrics` input with a relative logical locator and exact SHA-256.
- An explicit exclusion policy that matches at least one input row, plus a nonblank exclusion reason state.
- The optional figures dependencies, including Matplotlib.

### Command

```bash
python mamey_run.py doctor
python tools/figure_factory_next.py --help
python tools/figure_factory_next.py \
  --config project/figure_factory_next.json
```

Preflight the data before the final command: verify the recorded SHA-256, relative locator containment, required headers, unique identity/channel/metric/denominator-key rows, integer values, `0 <= numerator <= denominator`, `denominator > 0`, exclusion matches, and at least one eligible row after exclusion.

### Outputs

- `figure_factory_next.png`
- `figure_factory_next.svg`
- `figure_factory_next_data.tsv`
- `figure_factory_next_exclusions.tsv`
- `figure_factory_next_receipt.json`

### Expected typed states

- Success receipt: `PASS_PORTABLE_PROTOTYPE`.
- Authority state: `PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED`.
- Excluded rows: `AUDIT_ONLY_EXCLUDED_FROM_RENDER_AND_DENOMINATOR` in the audit-only table.
- Refusal in v9.7.395: nonzero exit with a specific exception reason. The tool does not currently emit a typed `OUTPUT_REFUSED` receipt.

Refusal reasons include schema mismatch, missing external root or input, absolute or escaping locator, missing or mismatched SHA-256, malformed or duplicate metric rows, invalid denominators, absent or drifting exclusion policy, no eligible rows, missing figure dependency, and an excluded-identity render leak.

### Common failure

Leaving a placeholder SHA-256 or naming an excluded identity that no longer appears in the input causes a fail-closed refusal. Update the content receipt or policy only after reviewing the new bytes and identity set; do not weaken the check.

### What this result does not establish

The figure and receipt establish bounded rendering provenance and evidence-coverage arithmetic. They do not establish scientific correctness, biological absence, similarity identity, production, activity, owner acceptance, integration, release, or publication readiness.

## Recipe 7 — missing optional evidence or tools

### Inputs

- A bundle-local environment.
- A valid package or normalized Mode B inventory.
- A clear distinction between a required core dependency, an optional Python library, an external dataset, an external companion tool, and an online evidence channel.

### Command

```bash
python mamey_run.py doctor --companions
python mamey_run.py modeb-availability \
  --inventory project/per_bgc_inventory.tsv \
  --source-root package=runs/reference-isolate-001/package \
  --out project/modeb_availability
```

Do not add `--probe-transports` unless network use is explicitly authorized. `--companions` is an offline presence probe; missing companion tools are optional and do not change the core doctor's pass/fail result.

### Outputs

- Doctor rows distinguishing required failures from optional warnings and detected-not-bundled companions.
- Availability tables that record each missing, unbound, strain-only, stale, or freshness-unverified evidence channel explicitly.
- A section plan that preserves gaps rather than filling them from another channel.

### Expected typed states

- Doctor: `PASS with ... warning(s)` when only optional items are absent.
- Evidence binding: `ABSENT`, `UNBOUND`, `STRAIN_ONLY`, `ALIAS_BOUND`, or `EXACT_LOCUS`.
- Work routing: `NEEDS_EVIDENCE_ASSEMBLY`, `GAP_AWARE_REVIEW_CANDIDATE`, or `EVIDENCE_RICH_REVIEW_CANDIDATE`.
- Missing external dataset: dependent sections are `NOT MEASURED` or carry an explicit gap/hold, never an empty-result biological conclusion.
- Missing optional figure tools: extraction remains valid; only the optional rendering path is unavailable.

### Common failure

Treating a doctor's optional warning as a failed extraction, or treating an absent evidence channel as proof of novelty or biological absence. Preserve the typed state and acquire or bind the missing source when it is required for the intended claim.

### What this result does not establish

A core doctor pass does not prove optional analyses are available. Conversely, a missing optional tool or dataset does not negate a valid package and does not establish a biological negative.

## Recipe 8 — resume and recovery

### Inputs

- An exact unpacked package directory.
- Its manifest, checksum file, gate validation, package-status receipt, judgment register, and any recovery markers.
- A new additive path for the workflow ledger.

### Command

```bash
python mamey_run.py validate runs/reference-isolate-001/package
python mamey_run.py resume \
  --json \
  runs/reference-isolate-001/package
python mamey_run.py workflow \
  --package runs/reference-isolate-001/package \
  --json \
  --ledger-out project/resume/reference-isolate-001_WORKFLOW_LEDGER.md
```

Use `workflow --strict` only when a nonzero exit is desired for every incomplete mandatory workflow step. The non-strict view is useful for orientation because pending downstream work is normal immediately after extraction.

### Outputs

- Validation JSON and an updated `package_status.json`.
- Resume JSON containing package identity, `done`, `pending`, `next_up`, evidence-routing context, and strict-report runnability.
- A workflow ledger with ordered W0–W10 states and receipts at the explicit additive path.

### Expected typed states

- Package: `MAMEY_COMPLETE`, `RECOVERY_VALIDATED`, `RECOVERY_NEEDED`, or `PARTIAL_FAILED`.
- Workflow step: `PASS`, `PENDING`, `BLOCKED`, or `N/A`.
- Resume progress: per-item `COMPLETE` or `PENDING`, plus `strict_runnable` true or false and named missing sections.
- `RECOVERY_VALIDATED` retains merge semantics `validated_recovery_not_uninterrupted`.

### Common failure

Running `resume` first and treating its briefing as a package-integrity check. `resume` reduces existing artifacts; it does not replace checksum or validation gates. Validate first, and stop on `RECOVERY_NEEDED`, `PARTIAL_FAILED`, checksum failure, or validator failure.

### What this result does not establish

A reconstructed briefing or workflow ledger does not prove that prior interpretation was correct, that a recovered run was uninterrupted, that pending evidence exists elsewhere, or that any deliverable is accepted, integrated, released, or publication-ready.

## Exact-locus inventory example

An individual row must be able to display the complete identity. For example:

`reference-isolate-001 / NODE_7_length_50000_cov_20.5 / region001 / BGC001`

The normalized table may store those values in separate `strain`, `full_node`, `region`, and `bgc` columns. If any field is unavailable, the row is held; no recipe authorizes a fallback to the alias alone.
