# Cohort pack interface

You need this page only if you analyze a private set of strains and want Mamey to apply your own exclusion list. A single-strain run does not need it.

A **cohort pack** is a folder named `OFFICIAL_DATA/` that you keep outside the program. It holds your list of excluded strains and your strain registries. Mamey ships with no pack. By default it excludes nothing, and unknown strains count as private. The program does not control your own Git repositories. Keep a private pack outside any tracked repository, and check that repository's status and sharing settings yourself.

The program ZIP includes a synthetic `tests/fixtures/cohort_pack/exclusions.json` for tests. It is not your pack.

## Binding

Set one environment variable before you run any command:

```bash
export MAMEY_OFFICIAL_DATA="$HOME/my_cohort_pack/OFFICIAL_DATA"
```

The loader reads the first of these that applies, and only that one:

1. A source context, if your run is bound to one. A source context carries its own exclusion list, and the variables below are then ignored. Note it when you use one.
2. `MAMEY_OFFICIAL_DATA`: the path to the `OFFICIAL_DATA/` folder, which holds `exclusions.json` and the registries.
3. `MAMEY_DATA_ROOT`: a path whose `OFFICIAL_DATA/` subfolder holds the same files. Used when `MAMEY_OFFICIAL_DATA` is not set.
4. If neither variable is set, the loader walks up the program's parent folders looking for an `OFFICIAL_DATA/` folder.

If a variable names a folder with a missing or invalid file, the loader does not look anywhere else for another pack.

To see which pack is bound, run this from the bundle root:

```bash
python -c "from mamey import exclusions as e; print(e.exclusion_binding())"
```

This reads the pack once, strictly, and prints what that one read bound:
- `source_type`: `MAMEY_OFFICIAL_DATA`, `MAMEY_DATA_ROOT`, `PARENT_WALK`, `SOURCE_CONTEXT` or `MODULE_DEFAULT`;
- `path`: the file it read, or `None` for the shipped default;
- `sha256`: the hash of the bytes it parsed, or `None` for the default;
- `hard_excluded`: the excluded strains, sorted.

A failed binding raises an error instead of printing an empty list. Copy the line into your run record. A new Python process does not see a source context bound inside another process, so this command reports what a fresh process would read.

## Example `exclusions.json`

```json
{
  "hard_excluded": ["DEMO-A", "DEMO-B"],
  "raw_assembly_void": [],
  "strain_of_record": {},
  "qc_hold_audit_only": [],
  "governed": {"strains": 9, "regions": 99}
}
```

`hard_excluded` must be a list of non-blank strain IDs with no leading or trailing spaces. Strict loading refuses the file otherwise. The other keys may be empty.

## Pack contents and missing-source behavior
- `OFFICIAL_DATA/exclusions.json` — `{hard_excluded, raw_assembly_void, strain_of_record, qc_hold_audit_only, governed}`.
  - With no pack bound or found, the shipped default excludes nothing.
  - Non-strict loading can warn and fall back to that empty default when a bound file is missing or unreadable.
  - Strict loading refuses a missing or malformed bound file.
  - The governed accessor `governed_excluded()` loads strictly and returns the strains from that same read; it does not read the file a second time. So the governed-output exclusion gate, package validation and master-workbook ingest stop on a failed binding. They raise an error or report the gate as `ERROR`; they do not use the empty default.
  - Raw-scope accessors keep the warning fallback.
  - Check the resolved source and any warnings before you use a governed denominator. "No exclusions loaded" does not prove that every strain was approved.
- `OFFICIAL_DATA/*REGISTRY*.csv/.tsv` — strain⇄accession and genome registries used by cohort adapters.
- A cohort roster shaped like `strain_genus.csv`, if you use cohort figures or widgets. When it is absent,
  the behavior depends on the selected adapter. Record whether the result was unavailable, held or empty. An empty result is not a completed cohort analysis.

## Scope and validation boundary

The pack is a governance input. It is not a privacy profile or a record that evidence was admitted.

The dataset check in `doctor` only looks at the file layout. It does not validate the full pack schema or the denominators.

The generic external-data resolver and the exclusion loader fall back in different ways. Record the exclusion source that was actually used. A green dataset check does not tell you which one it was. Keep the exact version and bytes of the pack the operator chose.

These behaviors hold for every generic install:
- With no pack bound, exclusions are empty and unknown strains resolve to PRIVATE. `run`, `validate` and
  `explain` still work on a generic type or reference fixture.
- Binding a pack changes cohort behavior **without changing canonical code**.
- Record the pack's own version and source with your results. The engine never assumes a personal path.
