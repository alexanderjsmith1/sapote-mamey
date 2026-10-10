# Cohort pack interface (external, operator-supplied, Git-ignored)

The public/canonical source tree is **generic**: it ships no cohort roster, no cohort exclusions,
and no cohort-specific adapters bound. A private cohort (e.g. an AS-series study) is supplied as an
**external pack** that the operator binds by configuration; nothing in the pack is tracked in Git.

## Binding
For exclusion/governance loading, an explicit environment binding is exclusive. `MAMEY_OFFICIAL_DATA` wins; otherwise `MAMEY_DATA_ROOT` selects its OFFICIAL_DATA subdirectory. A missing or invalid explicitly bound file does not trigger a search for a different parent pack. Only when neither binding exists does the loader walk bundle parents for `OFFICIAL_DATA/`.
- `MAMEY_OFFICIAL_DATA` — path to the pack's `OFFICIAL_DATA/` (contains `exclusions.json`, registries).
- `MAMEY_DATA_ROOT` — path whose `OFFICIAL_DATA/` subdir holds the same.

## Pack contents and missing-source behavior
- `OFFICIAL_DATA/exclusions.json` — `{hard_excluded, raw_assembly_void, strain_of_record, qc_hold_audit_only, governed}`.
  With no pack bound or discovered, the shipped default excludes nothing. Non-strict loading can fall back to that empty default after a warning when a bound file is unreadable/missing. Strict loading refuses a missing or malformed bound source. Inspect the resolved source and warning state before using any governed denominator; “no exclusions loaded” does not prove all strains were approved.
- `OFFICIAL_DATA/*REGISTRY*.csv/.tsv` — strain⇄accession / genome registries used by cohort adapters.
- A cohort roster (`strain_genus.csv`-shaped) if cohort figures/widgets are used; absent → those
  behavior depends on the selected adapter. Record its actual unavailable/held/empty state instead of treating an empty result as a completed cohort analysis.

## Scope and validation boundary

The pack is a governance input, not a privacy profile or evidence-admission receipt. Dataset presence in `doctor` is a file-layout probe, not full pack schema or denominator validation. The generic external-data resolver and exclusion loader have different fallback policies; record the actual exclusion source rather than assuming a green dataset probe identifies it. Preserve exact version and bytes of the operator-selected pack.

The following are intended generic invariants. Verify them with the selected package and public-suite receipt before claiming conformance.
- With no pack bound: exclusions are empty, unknown strains resolve to PRIVATE, and `run`/`validate`/
  `explain` still work on a generic type/reference fixture.
- Binding a pack changes cohort behavior **without modifying canonical code**.
- Provenance: record the pack's own version/source; the engine never assumes a personal path.
