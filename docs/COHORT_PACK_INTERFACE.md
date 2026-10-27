# Cohort pack interface (external, operator-supplied, Git-ignored)

The public runtime defaults are **generic**. No study roster, exclusion list or cohort-specific adapter is bound automatically.

The CODE archive includes a synthetic `tests/fixtures/cohort_pack/exclusions.json` for the test harness. That fixture is not the operator's study pack.

A private cohort, such as an AS-series study, comes as an **external pack**. The operator binds it by configuration. Nothing in the pack is tracked in Git.

## Binding
An active source context can supply governance directly, before any environment lookup. Record that context when it is in use.

Otherwise, the exclusion and governance loader uses an explicit environment binding when one is set, and only that binding:
- `MAMEY_OFFICIAL_DATA` — path to the pack's `OFFICIAL_DATA/` folder (holds `exclusions.json` and the registries). This wins when set.
- `MAMEY_DATA_ROOT` — path whose `OFFICIAL_DATA/` subfolder holds the same files. Used when `MAMEY_OFFICIAL_DATA` is not set.

If an explicitly bound file is missing or invalid, the loader does not look for another pack in a parent folder. Only when neither variable is set does it walk up the bundle's parent folders looking for `OFFICIAL_DATA/`.

## Pack contents and missing-source behavior
- `OFFICIAL_DATA/exclusions.json` — `{hard_excluded, raw_assembly_void, strain_of_record, qc_hold_audit_only, governed}`.
  - With no pack bound or found, the shipped default excludes nothing.
  - Non-strict loading can warn and fall back to that empty default when a bound file is missing or unreadable.
  - Strict loading refuses a missing or malformed bound file.
  - The governed accessor `governed_excluded()` always loads strictly. So the governed-output exclusion gate, package validation and master-workbook ingest stop on a failed binding. They raise an error or report the gate as `ERROR`; they do not use the empty default.
  - Raw-scope accessors keep the warning fallback.
  - Check the resolved source and any warnings before you use a governed denominator. "No exclusions loaded" does not prove that every strain was approved.
- `OFFICIAL_DATA/*REGISTRY*.csv/.tsv` — strain⇄accession and genome registries used by cohort adapters.
- A cohort roster shaped like `strain_genus.csv`, if you use cohort figures or widgets. When it is absent,
  the behavior depends on the selected adapter. Record whether the result was unavailable, held or empty. An empty result is not a completed cohort analysis.

## Scope and validation boundary

The pack is a governance input. It is not a privacy profile or a record that evidence was admitted.

The dataset check in `doctor` only looks at the file layout. It does not validate the full pack schema or the denominators.

The generic external-data resolver and the exclusion loader fall back in different ways. Record the exclusion source that was actually used. A green dataset check does not tell you which one it was. Keep the exact version and bytes of the pack the operator chose.

The rules below are meant to hold for every generic install. Check them against the selected package and a public-suite receipt before you claim they hold:
- With no pack bound, exclusions are empty and unknown strains resolve to PRIVATE. `run`, `validate` and
  `explain` still work on a generic type or reference fixture.
- Binding a pack changes cohort behavior **without changing canonical code**.
- Provenance: record the pack's own version and source. The engine never assumes a personal path.
