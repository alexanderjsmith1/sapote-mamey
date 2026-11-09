# Bioactivity metadata

Bioactivity metadata is optional context about one strain, such as "this extract was
tested against a target". `run` records it in the package. It does not score
anything, and it does not link an assay to a cluster or a compound. Its
`compound_linkage` field is always `NOT_ESTABLISHED`. Leaving the metadata out is
fine. The run then records `NOT_SUPPLIED`.

## Supply it

Pass the JSON text itself (not a file path) to `run`, with the other flags from the
[first run](reader/01_FIRST_RUN.md):

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --bioactivity-json '{"schema_version": "bioactivity_metadata_v1", "metadata_state": "SUPPLIED_UNKNOWN", "observation_state": "UNKNOWN", "usage_scope": "PRODUCTION", "assays": [], "compound_linkage": "NOT_ESTABLISHED"}'
```

If the object is valid, `run` goes on and records it. If a field is wrong, `run`
writes nothing, prints `ERROR:` with a code such as `BIOACTIVITY_LEGACY_SHAPE_HOLD`,
and exits `1`. If the text is not valid JSON, it exits `2` with the same code. Do not
combine `--bioactivity-json` with the old `--bioactivity` flag.

## Fields

All six keys below are required. Only `receipt_locator` and `warnings` may be added.

| Key | Allowed values |
|---|---|
| `schema_version` | `bioactivity_metadata_v1` |
| `metadata_state` | `NOT_SUPPLIED`, `SUPPLIED_UNKNOWN`, `MEASURED_NEGATIVE`, `MEASURED_POSITIVE`, `LEGACY_UNTYPED_CONTEXT` |
| `observation_state` | `NOT_OBSERVED`, `UNKNOWN`, `NEGATIVE`, `POSITIVE` |
| `usage_scope` | `PRODUCTION`. `EXAMPLE_ONLY` is refused in a real run. |
| `assays` | A list. It must be empty when `metadata_state` is `NOT_SUPPLIED`. |
| `compound_linkage` | `NOT_ESTABLISHED` only |

The states must agree:

- `NOT_SUPPLIED` goes with `NOT_OBSERVED`.
- `MEASURED_NEGATIVE` goes with `NEGATIVE`.
- `MEASURED_POSITIVE` goes with `POSITIVE`.

`BIOACTIVITY_LEGACY_SHAPE_HOLD` is a refusal code, not a metadata state. An object whose
`metadata_state` is that code is refused like any other unknown state.

`receipt_locator` is optional. It is a short relative name or URL-style string, such
as `receipts/EXAMPLE_assay_1`. The grammar is: an optional `scheme://` prefix, then a
letter or digit, then only letters, digits, `.`, `_`, `/` and `-`. It cannot start with
`/`, `~` or a drive letter, cannot carry spaces at either end or control characters, and
no `/`-separated segment may be exactly `..`. A segment that merely contains two dots,
such as `version..old`, is accepted. The check looks at the spelling only. A valid
locator does not show that the receipt exists, can be read, or is bound to the data.

## Older input shapes

Three older shapes are still accepted and converted:

| You give | The run records |
|---|---|
| A text string with `--bioactivity` | `LEGACY_UNTYPED_CONTEXT`. An empty string becomes `NOT_SUPPLIED` with a warning. |
| An object with exactly `status`, `targets` and `compound_linkage` | `LEGACY_UNTYPED_CONTEXT` if `targets` has text, else `NOT_SUPPLIED`. Warning `LEGACY_SHAPE_NORMALIZED`. |
| An object with exactly `status` and `targets` | The same. |

Any other object is refused with `BIOACTIVITY_LEGACY_SHAPE_HOLD`. The software does
not guess what you meant.

## What the check does not do

It checks the shape of the object. It does not read the entries in `assays`, check
evidence hashes, or open the receipt. An object with bad assay entries can pass, so
read them yourself.

Record the strain, sample, material, target, time point, dose, source and evidence
hash in the assay record you keep. An absent field is not a measurement, a negative
result or a link to a cluster. If you name one cluster, write it as
`strain / full node-or-contig / region / BGC alias`. This check does not join an
assay to a cluster.
