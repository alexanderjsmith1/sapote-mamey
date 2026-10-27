# SOP-02 — ChatGPT-Safe Capped-Session Run

Before any `doctor` example below, read the [write-probe boundary](../INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation. If `runs/_doctor_probe` is occupied, leave it
untouched and report the hold; the diagnostic refuses an occupied probe location.

Run the commands below from the bundle root, the folder that holds `mamey_run.py`.


## Purpose

Use this SOP when you run gold inside an assistant session or tool that has a time limit.

## Principle

Under a tool time limit, add `--capped-session` for unknown or large antiSMASH ZIPs. It runs the
same gold extraction with JSON evidence off, no brief, no automatic locus maps and a required
workbook. It does not set a time limit and does not turn off reference completion by itself.

## Required first commands

```bash
python mamey_run.py doctor
python mamey_run.py inspect <input.zip>
python mamey_run.py run --strain <bound-ID> --input-zip <input.zip> \
  --taxonomy "<bound taxonomy or explicit unknown>" --source "<bound source or explicit unknown>" \
  --outdir <fresh-run-root> --mode gold --capped-session --reference-completion off
python mamey_run.py validate <package_dir> --workbook-strict
```

## Why `--capped-session` first

`--capped-session` reduces risk from:

- automatic figure/brief generation, while authored BGC judgment remains a later task,
- excessive JSON evidence,
- oversized output,
- tool timeouts,
- too many regions or BGCs,
- missing optional deliverables (suppressed on purpose, not silently dropped — re-populate with
  the workflows in [figure start here](../FIGURES_START_HERE.md) post-seal). Rendering can refresh package integrity or populate package data; use an authorized working copy when preserving sealed bytes.

## Required outputs

A capped-session run should produce:

- package directory,
- manifest,
- checksums,
- workbook (required by the capped-session run settings),
- package status,
- validation result,
- issue list if present.

## Timeout-after-output rule

If the session or tool times out after Mamey reports writing the manifest and checksums:

1. Check whether the Mamey process is still running.
2. Validate the package.
3. Check checksums.
4. Check terminal/package status.
5. Do not call the run successful until validation passes.

## Bug-hunt checks

1. `--capped-session` should force conservative settings on the (only) gold-mode run.
2. `--json-evidence off` should prevent runaway evidence files.
3. A capped-session run should never require follow-up prompts unless explicitly needed.
4. Timeout-after-output should be documented and validated.
5. Missing optional deliverables should be NOT_RUN, not silent omission.
