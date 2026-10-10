# Optional DIAMOND backend for `compare`

Before any `doctor` example below, read the [write-probe boundary](../docs/INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

DIAMOND is an optional acceleration backend. It is not required for the `compare` command when an executable pyswrd installation or Biopython is available, and it is not installed by `bundle_support/install_sapote_addons.sh`.

## What the command detects

Backend selection is automatic and follows this order:

1. DIAMOND, when either the compiled `diamond4py` binding loads or a `diamond` executable is found on `PATH`.
2. pyswrd, only when import succeeds and a one-pair smoke alignment executes successfully.
3. Biopython local alignment.
4. No backend. In this case `compare` returns a nonzero status and does not write its normal comparison files.

If pyswrd is importable but cannot execute on the current CPU, the command warns and falls through to Biopython. If pyswrd fails during the full alignment, the alignment function also falls back to Biopython.

DIAMOND availability does not add a new comparison stage. It changes only the protein-alignment backend used for the same directional A-to-B best-hit table.

## Enable and check DIAMOND

Install DIAMOND for the current operating system using a trusted upstream or environment-manager package, then make the executable available on `PATH`. A local `diamond4py` installation is also detected, but it requires a working compiled extension.

The similarly named historical Python package `diamond` is not the DIAMOND protein aligner. Verify the executable before relying on it:

```bash
diamond version
python mamey_run.py doctor
```

Then run a small comparison and inspect the recorded backend rather than assuming selection:

```bash
python mamey_run.py compare \
  --strain-a inputs/query-antismash.zip \
  --strain-b inputs/reference-antismash.zip \
  --out comparison_results
```

Check both:

- the top-level `backend` and `alignment_threads` fields in `comparison_results/gemini_summary.json`;
- the `backend` column in `comparison_results/S5_gene_level_similarity.csv`.

The per-row backend identifies the aligner that produced that hit. If the summary and row backends disagree, preserve the discrepancy as a runtime hold; a pyswrd execution failure can cause a Biopython fallback after initial backend selection.

## Failure and interpretation boundaries

DIAMOND selection is a discovery result, not execution validation. The CLI probe checks only whether `diamond` is on PATH; the binding probe checks import. `doctor` or `diamond version` does not certify the selected alignment completed on the intended input. Source: `mamey/diamond_align.py:53–79`, `mamey/compare.py:70–108`.

The absence of DIAMOND alone is not an error. The command should continue with an executable fallback and will warn when pyswrd is unavailable or unusable.

A zero-hit result needs evidence review. In the current implementation, a selected DIAMOND path that returns no hit records is reported through the same downstream zero-hit route as a successful alignment with no matches; the DIAMOND failure reason is not preserved in the normal summary. Confirm input translations, terminal warnings, and backend execution before treating zero hits as a comparison result.

DIAMOND output remains sequence-similarity evidence. Percent identity and coverage do not establish compound identity, biosynthetic production, gene function, or biological absence. No historical single-dataset agreement should be treated as general validation of the current platform, binary, inputs, or result.

## Receipts and recovery

`compare` creates its output directory before input/backend refusal and replaces CSV then summary individually. It does not invalidate prior results or attach input hashes, executable version or detailed DIAMOND failure reason to the normal summary. Preserve the terminal diagnostics and reviewed input/backend identity, and check the two files belong to the latest invocation before reuse. An ANI omission and a DIAMOND zero-hit route can coexist with exit 0. See [offline comparison](README_OFFLINE_ANALYSIS.md) for output/recovery and identity limits (`mamey/compare.py:407–525`).

The current JSON `diamond_status` string is static descriptive text, even when the selected `backend` is DIAMOND (`mamey/compare.py:504–516`). Use the backend fields and diagnostics rather than treating that string's historical “proven” wording as a current platform/input validation receipt. Backend execution, installation and dataset agreement need their own current run records.
