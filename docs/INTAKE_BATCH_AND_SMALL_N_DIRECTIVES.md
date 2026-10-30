# Run a batch of antiSMASH ZIPs

Extract one or more genomes and record their package paths, runtime and completion
status. You need the installed program and antiSMASH result ZIPs. For one interactive
extraction with a brief and locus maps, use [Your first run](reader/01_FIRST_RUN.md).

Check the input filenames, strain names, taxonomy, source and release settings
before starting. Put only the selected ZIPs in `inputs/EXAMPLE-batch`.

```bash
python tools/intake_harness.py --inputs inputs/EXAMPLE-batch \
  --outdir runs/EXAMPLE-batch --registry runs/EXAMPLE-batch-registry.csv \
  --metrics runs/EXAMPLE-batch-metrics.csv
```

`--inputs` accepts files or folders; folders include only ZIPs directly inside them.
The other three options choose the output root and the two CSV records.
Defaults are gold mode, PRIVATE release and source `not verified`. For reviewed
public inputs, choose `--release PUBLIC` and provide the verified `--source`.
The release label does not redact files.

## Check what finished

Each genome goes under `runs/EXAMPLE-batch/<name>/package/`, with an
`intake_completion_receipt.json` beside it. Names come from ZIP filenames, with collisions resolved. Check the registry's assigned names.

The harness uses bounded JSON evidence and omits the brief; it does not pass
`--capped-session`. This output differs from the interactive first-run recipe.
Read the registry, metrics and completion receipts: exit zero can still include
`NEEDS_ANTISMASH`, which means no extraction was completed for that input.

## Resume the same batch

```bash
python tools/intake_harness.py --inputs inputs/EXAMPLE-batch \
  --outdir runs/EXAMPLE-batch --registry runs/EXAMPLE-batch-registry.csv \
  --metrics runs/EXAMPLE-batch-metrics.csv --resume
```

`--resume` skips a completed input only when its bytes, code, options and output
package match the saved receipt. A changed binding or an unbound existing package
is held; keep it and choose a fresh output root and registry after review.

A slow input needs its phase log checked; Mamey consumes antiSMASH results and
never reruns antiSMASH. Stop repeated retries and keep the available diagnostics.
For an explicit per-engine time limit, choose `--per-input-timeout SECONDS`.
The default has no limit; this option does not guarantee descendant cancellation
and cannot be combined with captured-policy intake.

## Compare or save the results

The harness does not update a master workbook. To assemble a cross-strain table:

```bash
python mamey_run.py cohort-assemble --runs-dir runs/EXAMPLE-batch \
  --out runs/EXAMPLE-batch/COHORT_MASTER.csv
```

Use [Strain Master](DATA_HOME.md) to submit finished results for storage.
Sample count alone does not disqualify a per-strain deliverable. The unchanged
[small-cohort, interpretation and checker policy](reference/INTAKE_AND_SMALL_COHORT_POLICY_REFERENCE.md)
defines the requested suite, ecology wording and limits of its text-only checker.
