# B2 — Registry-Backed Detector Wiring Spec
**Goal:** make source_scans.py CONSUME the 179-marker / 98-cassette registry so markers actually drive detection, replacing the current state where the registry is catalog-only and regex _PATTERNS do the scanning. Real backend migration — implement in ChatGPT runtime with regression tests; Claude verifies.

## Current state (B1, what's running now)
- source_scans.py holds hardcoded regex dicts: DOMAIN_CLASS_PATTERNS, CHITINASE_PATTERNS, REGULATOR_PATTERNS, RESISTANCE_PATTERNS, CCTT_PATTERNS, FLBR_PATTERNS, CASSETTE_PATTERNS, UMED_PATTERNS, TFBS_MOTIFS, QS_CDS_PATTERNS.
- The 179-registry (release2_source_library, MarkerDefinition/EvidenceTier schema) is NOT imported by the scanner.
- The bundle's own mamey/ registry (MMK-/SMK- Marker dataclasses) is also descriptive, not consumed.

## Target state (B2)
Markers in ONE canonical registry drive detection; each marker declares HOW it's detected.

## Steps
1. **One canonical schema.** Reconcile the two registry schemas (v8.11 MarkerDefinition/EvidenceTier vs bundle Marker/Target). Pick the bundle's frozen-dataclass style as the package target; map v8.11 fields into it. Assign stable IDs (MMK-/SMK- prefixes) to the 179 markers.
2. **Add a detector-backend field per marker:** `detector ∈ {regex, antiSMASH_fullhmmer, DIAMOND, BLASTP, manual}` + the pattern/profile/accession payload. The current regex _PATTERNS become `detector=regex` registry entries (1:1 port, NO behavior change — this is the regression anchor).
3. **source_scans.py consumes the registry:** replace the hardcoded dicts with a loop over registry markers, dispatching by `detector`. Phase 1: only `regex` markers active (must reproduce current output EXACTLY). Phase 2: enable hmmer/DIAMOND/BLASTP markers (these EXPAND detection — the actual goal).
4. **Wire hits into scoring/claim-ceilings/provenance** only after detection parity is proven.

## REGRESSION DISCIPLINE (non-negotiable)
- Before enabling any new-backend marker, the registry-driven scan MUST reproduce the current regex output BIT-FOR-BIT on the validated strains (AJS-XXX + the ground-truthed corpus). Diff every scan column. Zero diffs = parity proven.
- Only then enable hmmer/DIAMOND/BLASTP markers, ONE family at a time, each diffed against expectation + spot-checked vs ground truth.
- Any marker that changes a previously-validated call must be flagged and human-reviewed, not silently accepted.
- New-backend hits get claim ceilings; never auto-promote to product claims.

## Acceptance
1. pytest green.
2. Phase-1 (regex-only registry-driven) output == current output, zero diffs, on AJS-XXX + corpus.
3. Phase-2 new-backend markers expand detection in expected ways; AJS-XXX ground truth (5 papers) still holds; marinoterpin mrt parts and DKP-A unchanged or improved, never lost.
4. Claude verifies parity + expansion against ground truth.

## Why phased
The runner produces hour-long, ground-truth-validated runs. A full registry swap risks silently changing validated results. Phase 1 (parity) de-risks; Phase 2 (expansion) delivers the value. Do not merge Phase 2 without Phase 1 parity proven.
