# Sapote–Mamey v9.4.1 Compatibility Patch

Date: 2026-06-10

This patch migrates three high-value v8.9.6 behaviors into the v9.4 runner as additive output fields only. It does not change the regex scan backend or existing columns.

## Additive field families

### EFLS fields
Appended to inventory and `B1_BGC_Master`:
`efls_status`, `flank_census_tier1`, `flank_census_tier2_todo`, `cross_contig_candidate_set`, `efls_claim_ceiling`.

Interior BGCs receive `NOT_APPLICABLE_INTERIOR` / `N/A_interior`. Edge and full-contig BGCs receive source-derived review status and linkage candidates, with the binding ceiling: edge/linkage candidate only; not a merged-cluster claim without long-read closure.

### DKP/CDPS fields
Appended to inventory and `B1_BGC_Master`:
`dkp_rank`, `dkp_cdps_evidence`, `dkp_oxidase_homology`, `dkp_provenance`, `dkp_claim_ceiling`.

DKP-A/B/C/D are assigned from source-derived CDPS, CDO/oxidase, tailoring, and resolved albonoursin/purincyclamide family context. Product identity remains capped: candidate DKP scaffold only; specific dipeptide requires isolation.

### Claim-calibration fields
Appended to inventory and `B1_BGC_Master`:
`diagnostic_signal_score`, `evidence_weight_tier`, `claim_confidence`, `claim_ceiling`, `safe_claim`.

Lead priority remains separate from claim confidence. These fields never alter AB/AF lead priority scores.

## Tests
`tests/test_v941_compatibility_fields.py` verifies DKP-A handling, EFLS claim ceilings, and separation of claim-calibration fields.
