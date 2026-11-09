# Batch intake and small-cohort rules (reference)

Start with the [reader page](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md). If the two pages differ, the reader page wins. This page holds the detail. For terms, see the [glossary](../GLOSSARY.md). Mamey is the extraction engine. Sapote is the judgment layer that writes cards and guides from a Mamey package.

## 1. Run a batch with the harness

First list every input ZIP: strain ID, taxonomy, source and release. Decide which to run now and which to defer. Then run the harness:

```bash
python tools/intake_harness.py --inputs <dir> --outdir <out> --registry <reg.csv> --metrics <m.csv> --resume \
  [--source "..."] [--release PUBLIC|PRIVATE]
```

- New batches default to `PRIVATE` with source "not verified". For reviewed public inputs, pass `--release PUBLIC --source "<verified source>"`. `PRIVATE` is not redaction and does not permit export.
- `--inputs` takes ZIP files, folders or both. A folder is read one level deep: only the `*.zip` files directly inside it.
- Each strain is named from its ZIP filename with assembly boilerplate removed. Colliding names get an assembly tag or a number. Check the registry names before you rely on them.
- Each input runs through the engine and Diagnostic Rescue. The harness records wall time and memory. The package lands in `<out>/<name>/package/` and the completion receipt in `<out>/<name>/intake_completion_receipt.json`.
- `--resume` skips an input only when its completion receipt matches the input bytes, engine, options and output package. A change to release, source, mode, taxonomy map, timeout, engine, harness code or Python puts the input on hold. Use a fresh output folder and registry.
- Without `--resume`, a rerun into the same output folder or registry holds every input that already has a package, receipt or success row.
- `NEEDS_ANTISMASH` can be retried. An archive with region files in several parent folders is refused. A failed attempt with no package left can be retried. Each attempt stages into its own new folder, `<out>/_stage/<name>.attempt-<random>/`, so a retry never removes or overwrites an earlier attempt's staged files or anything else under `_stage/`. Keep those folders as evidence; remove them yourself after review when you need the space. A package left by an unfinished attempt needs review and a fresh output folder.

## 2. A slow strain

Mamey never reruns antiSMASH. It reads the antiSMASH output already in the ZIP. Elapsed time alone does not show a defect. Optional reference completion, scans, finalization and rendering can all take time.

If one strain stalls, do not retry it in a loop:

1. Save the log and the current package folder.
2. Confirm the process has stopped.
3. Rerun that one input alone with `--resume`, or follow `prompts/RUN_DIAGNOSIS_PROMPT.md`.

`--per-input-timeout SECONDS` is optional and off by default. An input that passes it is recorded as `RUN_FAILED` with an `INPUT_TIMEOUT` message, and the harness moves on. It stops only the engine process the harness started, not necessarily its children, and it does not promise a full log. It cannot be combined with `--capture-policy`. The harness does not use `--capped-session`. Each engine call gets `--json-evidence bounded --brief none`.

## 3. Read the harness result

| Harness exit | Meaning | Next step |
|---|---|---|
| 0 | No attempted row was `RUN_FAILED`. Rows may still be `NEEDS_ANTISMASH`. Resume skips are not counted. | Open the registry, metrics, completion receipts and each package before you call the set complete. |
| 1 | The summary ends with `BATCH_INCOMPLETE`: at least one attempted row failed. | Find the `RUN_FAILED` rows in the metrics CSV and the matching diagnostic lines in the harness output, then follow section 2. A failed input usually has no registry row. If writing the completion receipt fails, the registry can hold a success row while metrics say `RUN_FAILED`: check the package and its `intake_completion_receipt.json`, and do not judge success or failure from the registry alone. |

A registry row alone is not a resume receipt. Keep existing packages. After a hold, use a fresh output folder and registry.

The harness does not pass `--master` to `run`, so it updates no master workbook. To keep packages in a Strain Master, submit each `*_Complete_Package.zip` through the inbox. See [where Mamey outputs land](../DATA_HOME.md#where-mamey-outputs-land). For one cross-strain table, run:

```bash
python mamey_run.py cohort-assemble --runs-dir <out> --out <out>/COHORT_MASTER.csv
```

## 4. Small cohorts

The full per-strain set can be made at any cohort size, including one strain. A small sample limits comparative statistics. It is not a reason to skip a per-strain deliverable. Cross-strain tables come after the per-strain runs exist. What you can finish still depends on runtime, evidence and scope. Say what is unresolved.

Ecology follows the genome, not the collection label:

- Read ecology from the genome and BGC evidence. An unknown isolation source does not block it.
- Report a known source as provenance. Do not turn it into a functional claim.
- Habitat comparisons are exploratory. Source is not function.
- Cite only verified references.

## 5. Check a deliverable manifest

```bash
python tools/check_deliverable_suite.py --manifest <file> [--mode {smoke,standard,gold}] [--artifact-root <dir>]
```

The manifest is a 13-row table; use [the template](../DELIVERABLE_MANIFEST_TEMPLATE.md). The checker requires the reported statuses, reasons and some gold text and count fields. Default mode is `standard`; pass `--mode gold` for the gold text checks. It rejects `JUDGMENT_PENDING`.

It checks artifact paths only when you pass `--artifact-root <folder>`. It does not compare checksums, tie counts to the package, require unique rows or enforce batch size. A zero exit does not certify content or scientific validity. See the [deliverable contract](../DELIVERABLE_CONTRACT.md).
