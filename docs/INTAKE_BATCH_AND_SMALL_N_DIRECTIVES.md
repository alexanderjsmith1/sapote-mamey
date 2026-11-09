# Run a batch of antiSMASH ZIPs

Extract one or more genomes and record their package paths, runtime and completion
status. You need the installed program and antiSMASH result ZIPs. For a single strain, use
[Your first run](reader/01_FIRST_RUN.md). The batch run differs from it in two ways. It does not pass
`--capped-session`, and it keeps bounded antiSMASH JSON evidence on. Like the first run, it writes no brief.

Check the input filenames, strain names, taxonomy, source and release settings
before starting. Put only the selected ZIPs in `inputs/EXAMPLE-batch`.

```bash
python tools/intake_harness.py --inputs inputs/EXAMPLE-batch \
  --outdir runs/EXAMPLE-batch --registry runs/EXAMPLE-batch-registry.csv \
  --metrics runs/EXAMPLE-batch-metrics.csv
```

`--inputs` accepts files or folders; folders include only ZIPs directly inside them.
To set the taxonomy per strain, add `--taxonomy-map taxonomy.json`. The file is a flat
JSON object of strain name to taxonomy, for example
`{"EXAMPLE-1": "Streptomyces sp.", "EXAMPLE-2": "not verified"}`. A blank value or a
bare `sp.` stops the harness.
The other three options choose the output root and the two CSV records.
Defaults are gold mode, PRIVATE release and source `not verified`. For reviewed
public inputs, choose `--release PUBLIC` and provide the verified `--source`.
The release label does not redact files.

## Check what finished

Each genome goes under `runs/EXAMPLE-batch/<name>/package/`, with an
`intake_completion_receipt.json` beside it. Names come from ZIP filenames, with collisions resolved. Check the registry's assigned names.

When the harness finishes, its last lines are `[intake] attempted N: OK a, RUN_FAILED b,
NEEDS_ANTISMASH c`. It exits 1 if any input failed (`BATCH_INCOMPLETE`) and 0 otherwise.
Read the registry, metrics and completion receipts: exit zero can still include
`NEEDS_ANTISMASH`, which means no extraction was completed for that input.

`engine_peak_mb` in the metrics is in MB of 10^6 bytes. The start line
`mem-monitor=` and the report's Performance section name the method:
- `psutil`: the engine child's and its descendants' resident size, sampled while it
  runs. Sampling can miss a short peak.
- `ru_maxrss` (psutil not installed): the largest resident size of any finished child
  of the harness so far, converted per platform (bytes on macOS, KiB on Linux). It is
  not this input's own peak, and a later input can repeat an earlier, larger value.

Neither is an exact peak. Use them as a rough guide, not as a resource limit.
Batches run before this conversion was fixed stored macOS fallback values about
1,000 times too large; do not reuse those numbers.

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
