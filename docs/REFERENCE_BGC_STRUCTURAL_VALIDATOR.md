# Exact-bound reference-BGC structural validator

`tools/reference_bgc_structural_validator.py` is an operator-only deterministic extractor. It does not perform biological validation and does not emit one row per gene. It measures the structural contents of curated, locus-resolved reference BGCs and preserves the established CSV columns consumed by `tools/seed_reference_library.py`.

Whole-genome records without a curated, locus-resolved reference BGC may be used as genome-profile comparators. They are not BGC validation controls.

## Inputs

The tool requires three explicit paths. The manifest path below is a local
example to prepare: this ZIP includes the `.template.tsv`, not a populated
`reference_bgc_validation_manifest.tsv`. Curate and pin the exact reference
rows before invoking the extractor; choose a fresh output outside preserved
source evidence.

```bash
python tools/reference_bgc_structural_validator.py \
  --manifest resources/reference_seed_inputs/reference_bgc_validation_manifest.tsv \
  --input-dir /path/to/local/reference-zips \
  --output resources/reference_seed_inputs/reference_bgc_structural.csv
```

The manifest is tab-separated. Start from `resources/reference_seed_inputs/reference_bgc_validation_manifest.template.tsv`. Each row must provide:

- `source_zip`: relative locator inside `--input-dir`;
- `source_zip_sha256`: immutable lowercase SHA-256;
- `compound` and `accession`: reference metadata;
- `strain`, `full_contig`, `region`, and `bgc_alias`: the complete exact identity, displayed as `strain / full contig / region / BGC alias`;
- `evidence_citation`: a locally curated source locator or citation;
- optional expected size, core-gene, and marker fields.

The tool refuses empty identities, duplicate exact loci, malformed region/BGC aliases, absolute or parent-traversing ZIP locators, hash mismatches, missing ZIPs, and any target that does not match exactly one parsed BGC. It never falls back to the first parsed cluster or to a bare alias.

## Outputs and failure behavior

Successful measurements are written atomically as comma-separated CSV so the historical seed-library consumer remains compatible. New columns bind the complete identity, source ZIP hash, inclusive coordinates, exact base-pair length, engine/bundle versions, citation, marker scope, and full untruncated KCB anchor.

A sibling `*.failures.tsv` is written after manifest admission and reference processing (see early-failure exceptions below). If any reference is held, the failure TSV records its exact locus, source ZIP, typed hold code, and detail; the main structural CSV is not replaced. The process exits with status 2.

`engine_markers_fired` remains for downstream compatibility but is explicitly scoped by `marker_scope=CCTT_PER_BGC_ONLY`. It is not a claim that every engine detector was surveyed.

## Older structural CSV filename

`tools/seed_reference_library.py` still reads an older structural CSV under its pre-rename filename when the current default is absent, with a deprecation warning. The rename history is in [history](history/REFERENCE_BGC_NAMING_MIGRATION_v97390.md).

## Evidence and claim ceiling

Expected reference facts must come from a versioned local manifest with citations and curator authority. Model-generated prose is not reference truth. Observed similarity and markers support reference-panel navigation and structural concordance only; they are not evidence of product identity, production, activity, novelty, or biological validation.

## Failure receipt and write-safety qualifications

The failures TSV is written after valid manifest loading and per-reference processing, including as a header-only file on success. It is **not always written**: configuration collisions and manifest read/schema failures return 2 before that step, and engine-load/hash-read failures may raise before the failure writer. An old sidecar can remain. Check current exit status and invocation identity; sidecar presence alone is not a current receipt.

Expected sizes, core-gene text and marker sets are supplied metadata; size/core values are copied into the output, not tested as acceptance gates. Marker intersection is reported without requiring all expected markers. Hash-bound exact selection validates source bytes and locus admission, not curator truth, expected biological facts or a panel-wide detector survey. Input SHA-256 text is normalized to lowercase before validation, so uppercase hex is accepted and recorded lowercase.

Atomic replacement protects each table separately; existing destinations can be replaced, and structural CSV plus failure TSV are not one commit. The guard protects the manifest, separates the outputs and compares both outputs against every declared source ZIP by resolved path and, for existing files, `samefile`. It does not check that source ZIPs reached through symlinks stay under `input-dir`. Review resolved inputs and choose fresh, disjoint output destinations. A held panel leaves an older main CSV unchanged; consumers must not reuse it as current PASS.

CSV rows bind source ZIP hash, full identity and reported engine/bundle versions, but not the manifest hash, owner-code hash or output file hashes. Retain an external receipt binding those before downstream seed-library admission. Zero exit is exact-bound extraction, not biological validation or scientific acceptance.
