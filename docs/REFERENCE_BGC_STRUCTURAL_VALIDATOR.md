# Exact-bound reference-BGC structural validator

`tools/reference_bgc_structural_validator.py` is an operator-only deterministic extractor. It does not perform biological validation and does not emit one row per gene. It measures the structural contents of curated, locus-resolved reference BGCs and preserves the established CSV columns consumed by `tools/seed_reference_library.py`.

Whole-genome records without a curated, locus-resolved reference BGC may be used as genome-profile comparators. They are not BGC validation controls.

## Inputs

The tool requires three explicit paths:

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

A sibling `*.failures.tsv` is always written. If any reference is held, the failure TSV records its exact locus, source ZIP, typed hold code, and detail; the main structural CSV is not replaced. The process exits with status 2.

`engine_markers_fired` remains for downstream compatibility but is explicitly scoped by `marker_scope=CCTT_PER_BGC_ONLY`. It is not a claim that every engine detector was surveyed.

## v9.7.390 naming migration

The generic Sapote-Mamey component and its generated artifacts use `reference_bgc_*` names. A `WAC` token is retained only when it is part of an actual strain designation or cited source identity. It is not a Sapote-Mamey subsystem, validation standard, contributor attribution, or product affiliation.

`tools/seed_reference_library.py` accepts the pre-v9.7.390 structural-CSV filename for one deprecation window when the generic default is absent. That fallback is input-only, emits a warning, and does not change the primary command or output names. The earlier validator script name is not retained as an executable wrapper because the tool was operator-only and not cut-wired; retaining a branded command would perpetuate the misleading public interface.

## Evidence and claim ceiling

Expected reference facts must come from a versioned local manifest with citations and curator authority. Model-generated prose is not reference truth. Observed similarity and markers support reference-panel navigation and structural concordance only; they do not establish product identity, production, activity, novelty, or biological validation.
