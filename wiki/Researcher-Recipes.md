# Researcher Recipes

Find task-based recipes with inputs, outputs and failure states.  
This page is for researchers running the bundle.

*Current to bundle v9.7.465 · engine Mamey 1.9.181.*

Each recipe gives inputs, the command, outputs, the states you should see, and the usual failure. None of these results establishes compound identity, production, activity, novelty or publication readiness; that is stated once here and not repeated.


Run commands from the extracted bundle root. Paths below are generic examples. Replace them with governed local paths; do not copy development-workspace paths into a project or public document.

Before any `doctor` command in these recipes, read the [write-probe boundary](../docs/INSTALL.md#doctor-scope-and-write-probe). If the probe folder is occupied, leave it intact and use an authorized working installation or resolve it with its owner.

## Recipes 1–4 — first run, metadata, small batch and validation

These recipes now live on one page each, so the steps are written once:

<a id="recipe-1--first-successful-run"></a>
<a id="recipe-2--one-strain-run-with-deliberate-metadata"></a>
<a id="recipe-4--validate-a-package"></a>
<a id="recipe-3--small-batch-of-up-to-about-three-strains"></a>

- **First run, with deliberate taxonomy and source:** [Your first run](../docs/reader/01_FIRST_RUN.md) covers `doctor`, `inspect`, `run` and `validate`, and how to fill `--taxonomy` and `--source`. [Inputs and setup](../docs/reader/02_INPUTS_AND_SETUP.md) covers what the placeholders refuse.
- **Validate or review a package:** [Read one saved package](../docs/reader/03_READ_RESULTS.md); [Recovery and limits](../docs/reader/04_RECOVERY_AND_LIMITS.md#status-values) lists the status values.
- **A folder of ZIPs:** the [batch guide](../docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md). Run one ZIP with the first-run page first.

## Recipe 5 — post-seal Mode B start

### Inputs

- A package that currently validates.
- For the optional availability route: a normalized CSV or TSV inventory with
  `strain`, `bgc`, `full_node` or `node`, and `region` columns forming the complete
  four-part identity. Native `mode-b` does not require that separate inventory.
- For that optional route, select evidence roots/indexes when available. Both
  options default to empty lists; neither is a universal parser requirement.
- An additive output directory outside score-bearing extraction files.

The package's numbered inventory is not automatically a valid `modeb-availability` input because its shipped header shape lacks the required normalized strain and lowercase identity fields. Build or use an explicit normalized crosswalk; do not guess missing fields.

### Commands

Optional evidence inventory (the normalized inventory belongs to this route):

```bash
python mamey_run.py modeb-availability \
  --inventory project/per_bgc_inventory.tsv \
  --source-root package=runs/reference-isolate-001/package \
  --evidence-index project/curated_evidence.tsv \
  --out project/modeb_availability
```

Native top-lead material, independently of that optional inventory:

```bash
python mamey_run.py mode-b \
  --package runs/reference-isolate-001/package \
  --top-n 10 \
  --outdir project/mode_b_native
```

Omit `--evidence-index` when no curated index exists; absence then remains `UNVERIFIED` or another typed state. Do not fabricate `CURRENT` from timestamps or filenames. Native `mode-b` is in the post-seal authoring allowlist and can refresh integrity records inside its supplied package even with an external output directory. Preserve the sealed original and use an identified working package copy when byte preservation is required; retain both source and candidate hashes. See [command-specific write boundaries](../docs/POSTSEAL_READERS.md).

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

Treat native `mode-b` output as generated top-lead material, not as an automatically finished current 48-section card. A finished card requires the selected current named profile, exact identity,
evidence-channel separation, authoring and verification.

### Common failure

Using `modeb-availability --package ...` fails because that option does not exist. The command requires `--inventory` and `--out`; evidence enters through repeatable `--source-root` and `--evidence-index` options.

## Recipe 6 — Figure Factory Next preflight and refusal

### Inputs

- A current `sapote.figure-factory-next.v2` JSON configuration. The aggregate renderer refuses v1.
- Exactly one `aggregate_metrics` TSV and one `cohort_manifest` TSV, each with a relative locator
  beneath `external_data_root` and its exact lowercase SHA-256.
- Metrics columns: `identity`, `channel`, `metric`, `numerator`, `denominator`, `denominator_key`.
- Cohort columns: `identity`, `role`, `include_by_default`, `genus`, `cohort`, `assembly_state`,
  `assembly_reason`. Use the current [aggregate guide](../docs/FIGURE_FACTORY_NEXT.md) for policy values.
- A nonempty `comparison.default_genera`, reviewed role/assembly policy and any explicitly selected
  optional identities or genera. External benchmarks and outgroups are default-off.
- Optional plotting dependencies and a new output directory: an existing output directory is refused.

### Command

```bash
python mamey_run.py doctor
python mamey_run.py figure-factory --config project/figure_factory_next.json
```

Check hashes, locator containment, metric schema, duplicate rows, finite integer counts and valid
denominators before rendering. Keep missing measurements distinct from observed zero. An empty
eligible set is refused; an all-zero numerator set is not universally refused. The old requirement
to name an excluded identity that matches an input row is not the current v2 cohort-policy contract.

### Outputs

The receipt lists the actual graphics for both publication profiles. Retain the matching
`figure_factory_next_data.tsv` and `.csv`, exclusions TSV, caption/methods JSON and Markdown,
owner-notes JSON, and `figure_factory_next_receipt.json` together. The current success status is
`PASS_PORTABLE_POLICY_RENDERER_CANDIDATE`; authority remains
`ENGINEERING_CANDIDATE_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED`.

### Recovery and interpretation

A refused configuration exits nonzero. Read the exception, correct the bound schema/input/policy,
and select a fresh output path before retrying. Do not assume a typed aggregate refusal receipt
exists. The same command routes phylogeny, bioassay and bioassay-plan `figure_kind` values to their own renderers;
those renderers have different inputs, and the phylogeny path catches `PhylogenyFigureHold` with exit 2.

Successful standalone rendering does not establish downstream PDF embedding QA, scientific
correctness, biological absence, compound identity, production, activity, acceptance or release.
Inspect the actual artwork and its intended document placement before claiming visual clearance.

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

**Limit:** A missing optional tool or dataset does not invalidate a package and is not a biological negative.

## Recipe 8 — resume and recovery

### Inputs

- An exact unpacked package directory with permission for mutable status writes. When the original must remain byte-preserved, use an identified working copy: `validate` normally updates `package_status.json`.
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

Use `workflow --strict` only when that implemented mandatory-step reduction is intended. W10 is mandatory but its behavioral checker returns `N/A`; the current reducer counts every mandatory state other than `PASS` as incomplete, so strict can exit1 even after every actionable upstream step passes. Inspect the named steps and retain the W10 implementation hold rather than inventing missing biological work. The non-strict view is useful for orientation because pending downstream work is normal immediately after extraction.

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

## Exact-locus inventory example

An individual row must be able to display the complete identity from a bound source record:

`<strain> / <full node-or-contig> / <region> / <BGC alias>`

The placeholders describe fields; they are not an example locus.

The normalized table may store those values in separate `strain`, `full_node`, `region`, and `bgc` columns. If any field is unavailable, the row is held; no recipe authorizes a fallback to the alias alone.
