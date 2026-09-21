# Methods reporting checklist

Use this checklist only for modules actually used. Inclusion in the bundle does not assert that a study was performed.

## Universal requirements

- [ ] Report exact bundle, engine, build or commit and relevant database/tool versions.
- [ ] Use portable logical input identifiers and archive SHA-256 values.
- [ ] Report version-sensitive thresholds, registries, references, and non-default limits.
- [ ] Define the observation unit, numerator, denominator, exclusions, and missingness.
- [ ] Preserve failure, degraded, capped, held, and not-applicable states; do not turn them into zero or absence.
- [ ] Display every individual BGC as `strain / full node-or-contig / region / BGC alias`.
- [ ] State the claim ceiling and give authored conclusions a human disposition.

## Module-specific requirements

### Input, inventory, and exact identity

- [ ] Report antiSMASH version/strictness, schema state, archive safety overrides, coordinate recovery, assembly fields, and heuristic corrected-count status.

### KnownClusterBlast, MIBiG, and RiQ

- [ ] Report database version, evidence source/precedence, query-subject binding, admitted rows, coverage/similarity, and explicit search failure state.

### RG-GMCI, FLBR, and EFLS

- [ ] Name each channel used; report thresholds, tiling/geometry, terminus and hub guards, scan caps, deterministic state, and physical-linkage validation status.

### CCTT and other source-derived scans

- [ ] Report marker registry/pattern version, sequence/annotation availability, class/veto/context guards, count unit, and fallback or not-applicable state.

### Triage scoring

- [ ] Report score-policy version, raw axis scores, tier thresholds, bonuses, standing rules, downgrades, exclusions, and corrected-rank policy.

### Mode B and LLM assistance

- [ ] Report exact-locus evidence inventory, channel binding/freshness, profile/contract, model and prompt/controller, deterministic-versus-authored boundary, and reviewer disposition.

### Cohort analysis

- [ ] Report cohort manifest/hash, compatible profiles and scoring versions, duplicate policy, biological unit, denominators, exclusions, metadata source, and held/reference roles.

### Phylogeny and ANI/AAI

- [ ] Report sequence roster/hashes, reference-selection rule, outgroup, marker set, tool builds, model, seed, threads, aligned fraction, and failed/held samples.

### Figures

- [ ] Report governed inputs, renderer/version, dimensions/DPI, source-data and methods/caption sidecars, hashes, mechanical checks, and human visual QA.

### Sealing, privacy, and validation

- [ ] Report manifest/schema, reciprocal checksums, validation and seal mode, privacy/export profile, known-answer controls, exact command, environment, and unresolved gates.

## Final manuscript gate

- [ ] Add study-specific wet-lab, culture, sequencing, assembly, database-date, statistical, metabolomic, and validation details.
- [ ] Confirm the Methods and technical appendix use the same release-sensitive values.
- [ ] Confirm figures have source data and visual QA at target size.
- [ ] Do not generalize historical or module-specific validation beyond the evaluated task.
- [ ] Disclose LLM assistance and keep deterministic evidence independently accessible.

