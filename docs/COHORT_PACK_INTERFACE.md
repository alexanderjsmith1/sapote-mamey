# Cohort pack interface (external, operator-supplied, Git-ignored)

The public/canonical source tree is **generic**: it ships no cohort roster, no cohort exclusions,
and no cohort-specific adapters bound. A private cohort (e.g. an AS-series study) is supplied as an
**external pack** that the operator binds by configuration; nothing in the pack is tracked in Git.

## Binding
Set either environment variable (the engine probes them in this order, then walks parents for an
`OFFICIAL_DATA/` dir):
- `MAMEY_OFFICIAL_DATA` — path to the pack's `OFFICIAL_DATA/` (contains `exclusions.json`, registries).
- `MAMEY_DATA_ROOT` — path whose `OFFICIAL_DATA/` subdir holds the same.

## Pack contents (all optional; absence degrades cleanly, never crashes)
- `OFFICIAL_DATA/exclusions.json` — `{hard_excluded, raw_assembly_void, strain_of_record, qc_hold_audit_only, governed}`.
  Absent → the shipped empty default (exclude nothing).
- `OFFICIAL_DATA/*REGISTRY*.csv/.tsv` — strain⇄accession / genome registries used by cohort adapters.
- A cohort roster (`strain_genus.csv`-shaped) if cohort figures/widgets are used; absent → those
  adapters emit empty/степ-down output rather than failing.

## Fail-safe contract (shipped invariants, proven by `tests/public/`)
- With no pack bound: exclusions are empty, unknown strains resolve to PRIVATE, and `run`/`validate`/
  `explain` still work on a generic type/reference fixture.
- Binding a pack changes cohort behavior **without modifying canonical code**.
- Provenance: record the pack's own version/source; the engine never assumes a personal path.
