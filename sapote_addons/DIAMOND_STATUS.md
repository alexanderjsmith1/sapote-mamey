# Optional DIAMOND backend for `compare`

DIAMOND is an optional acceleration backend. It is not required for the `compare` command when an executable pyswrd installation or Biopython is available, and it is not installed by `bundle_support/install_sapote_addons.sh`.

## What the command detects

Backend selection is automatic and follows this order:

1. DIAMOND, when `diamond4py.Diamond` imports or a `diamond` executable is found on `PATH`. This selection does not itself call the binding’s alignment entry point or validate the executable’s version.
2. pyswrd, only when import succeeds and a one-pair smoke alignment executes successfully.
3. Biopython local alignment.
4. No backend. In this case `compare` returns a nonzero status and does not write its normal comparison files.

If pyswrd is importable but cannot execute on the current CPU, the command warns and falls through to Biopython. If pyswrd is selected but raises any exception during the full alignment, the command falls back to Biopython. If DIAMOND is selected, the fallback covers the failure the DIAMOND path reports as a `RuntimeError` (the helper returned no usable result); another exception type stops the command. After a fallback, rows that have a returned result say `biopython`. A fallback that returns no rows leaves no per-row backend at all.

DIAMOND availability does not add a new comparison stage. It changes only the protein-alignment backend used for the same directional A-to-B best-hit table.

## Enable and check DIAMOND

Install DIAMOND for the current operating system using a trusted upstream or environment-manager package, then make the executable available on `PATH`. A local `diamond4py` installation is also detected, but it requires a working compiled extension.

Verify the executable before relying on it:

```bash
diamond version
```

Then run a small comparison and inspect the recorded backend rather than assuming selection:

```bash
python mamey_run.py compare \
  --strain-a inputs/query-antismash.zip \
  --strain-b inputs/reference-antismash.zip \
  --out comparison_results
```

DIAMOND uses `--alignment-threads` (default 1). Add `--alignment-threads 4` to use more cores; see [compare resource control](../docs/COMPARE_RESOURCE_CONTROL.md).

Check both:

- the top-level `backend` and `alignment_threads` fields in `comparison_results/gemini_summary.json`;
- the `backend` column in `comparison_results/S5_gene_level_similarity.csv`.

For a returned result, the per-row backend names the alignment path that produced it. A query with no returned record has backend `unknown` and the note "no per-query result returned; not an observed no-hit; effective backend unrecorded". That row is unobserved, not a searched no-hit. The summary's `backend_selected` is a record of the selection only; it does not show a search completed. If the summary and row backends disagree, preserve the discrepancy as a runtime hold; a DIAMOND or pyswrd execution failure causes a Biopython fallback after the initial selection. The summary's `backend_selected` field holds the backend chosen at the start, and `backend_provenance` explains the choice.

## Failure and interpretation boundaries

DIAMOND selection is a discovery result, not execution validation. The CLI probe checks only whether `diamond` is on PATH; the binding probe checks import. `diamond version` does not certify the selected alignment completed on the intended input. 

The absence of DIAMOND alone is not an error. The command should continue with an executable fallback and will warn when pyswrd is unavailable or unusable.

A zero-hit result needs evidence review. A DIAMOND run that finishes with no matches gives zero hits. A DIAMOND run that fails with the handled error does not: it falls back to Biopython, so rows with a returned result carry `backend` = `biopython` while `backend_selected` still says `diamond`. Confirm input translations and terminal warnings before treating zero hits as a comparison result.

DIAMOND output remains sequence-similarity evidence. Percent identity and coverage do not establish compound identity, biosynthetic production, gene function, or biological absence. No historical single-dataset agreement should be treated as general validation of the current platform, binary, inputs, or result.

## Receipts and recovery

`compare` creates its output directory before input/backend refusal and replaces CSV then summary individually. It does not invalidate prior results or attach input hashes or the executable version to the normal summary. Preserve the terminal diagnostics and reviewed input/backend identity, and check the two files belong to the latest invocation before reuse. An ANI omission and a zero-hit table can coexist with exit 0. See [offline comparison](README_OFFLINE_ANALYSIS.md) for output, recovery and identity limits.

The summary's `diamond_status` field lists the backend or backends actually seen in the result rows. If no row was measured, it says the backend is unrecorded. Check it together with `backend`. Neither field validates your platform or inputs, so keep your own run record.
