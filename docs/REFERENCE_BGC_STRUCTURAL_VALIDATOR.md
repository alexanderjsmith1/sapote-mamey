# Exact-bound reference-BGC structural validator

`tools/reference_bgc_structural_validator.py` is an operator-only deterministic extractor. It does not perform biological validation and does not emit one row per gene. It measures the structural contents of curated, locus-resolved reference BGCs and preserves the established CSV columns consumed by `tools/seed_reference_library.py`.

Whole-genome records without a curated, locus-resolved reference BGC may be used as genome-profile comparators. They are not BGC validation controls.

## Inputs

The tool requires three explicit paths. The manifest path below is a local
example to prepare: the bundle ships the `.template.tsv`, not a populated
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

The tool refuses empty identities, truncated rows (a row with fewer cells than the header) and rows with extra cells, duplicate exact loci, malformed region/BGC aliases, absolute or parent-traversing ZIP locators, hash mismatches, missing ZIPs, and any target that does not match exactly one parsed BGC. It never falls back to the first parsed cluster or to a bare alias.

The match against a parsed BGC uses the parsed contig (or node), region and BGC alias. The parsed antiSMASH record carries no strain field, so `strain` is the curator's declaration; the ZIP hash and the parsed locus checks do not bind it to source metadata. Every output row says so in `strain_binding_state`: `CURATOR_DECLARED_NOT_SOURCE_BOUND` when the parsed record has no strain, or `PARSED_STRAIN_MATCHES_DECLARATION` when a parsed strain exists and equals the declaration. A parsed strain that differs from the declaration does not match. `evidence_citation` is checked as present, nonblank text; the tool does not resolve or validate the locator.

## Outputs and failure behavior

Successful measurements are written atomically as comma-separated CSV so the historical seed-library consumer remains compatible. New columns bind the complete identity, source ZIP hash, inclusive coordinates, exact base-pair length, engine/bundle versions, citation, marker scope, and full untruncated KCB anchor. The last column, `strain_binding_state`, records how the strain was bound (see above).

A failures file is written after manifest admission and reference processing (see early-failure exceptions below). Its path is `--failure-output`, or `<output>.failures.tsv` beside the CSV when the flag is omitted. If any reference is held, the failure TSV records its exact locus, source ZIP, typed hold code, and detail; the main structural CSV is not replaced. The process exits with status 2.

`engine_markers_fired` remains for downstream compatibility but is explicitly scoped by `marker_scope=CCTT_PER_BGC_ONLY`. It is not a claim that every engine detector was surveyed.

## Evidence and claim ceiling

Expected reference facts must come from a versioned local manifest with citations and curator authority. Model-generated prose is not reference truth. Observed similarity and markers support reference-panel navigation and structural concordance only; they are not evidence of product identity, production, activity, novelty, or biological validation.

## Failure receipt and write safety

- The failures TSV is written after the manifest loads and each reference is processed. On success it is header-only.
- It is not always written. Configuration collisions and manifest read or schema errors exit 2 before that step. Engine-load or hash-read errors may raise first. An old sidecar can remain, so check the current exit status; the file alone is not a receipt.
- Each table is replaced atomically on its own. The CSV and the failures TSV are not one commit. A held panel leaves an older main CSV unchanged. Do not reuse it as a current pass.
- The guard protects the manifest, keeps the two outputs apart, and compares both against every declared source ZIP by resolved path and `samefile`. It does not check that ZIPs reached through symlinks stay under `--input-dir`. Review resolved inputs and choose fresh output paths.
- Expected sizes, core genes and marker sets are copied from the manifest, not tested as gates. Marker overlap is reported without requiring all expected markers.
- Hash-bound selection validates source bytes and locus admission. It does not validate curator truth. SHA-256 text is lowercased before checking, so uppercase hex is accepted.
- CSV rows bind the ZIP hash, full identity and engine and bundle versions. They do not bind the manifest hash, the tool's code hash or the output hashes. Keep an external record of those before the seed library uses the CSV.

Exit 0 means exact-bound extraction. It is not biological validation or scientific acceptance.
