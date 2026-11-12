# SOP-02 — Capped-Session Run

Before any `doctor` example below, read the [write-probe boundary](../INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation. If `runs/_doctor_probe` is occupied, leave it
untouched and report the hold; the diagnostic refuses an occupied probe location.

Run the commands below from the bundle root, the folder that holds `mamey_run.py`.


## Purpose

Use this SOP when you run gold inside an assistant session or tool that has a time limit.

## Principle

Under a tool time limit, add `--capped-session` for unknown or large antiSMASH ZIPs. It runs the
same gold extraction with `--brief none`, `--json-evidence off` and a required workbook. It sets
`--locus-maps off` unless you pass `--locus-maps on`. It does not set a time limit and does not turn
off reference completion by itself. `--chatgpt-safe` is an older name for the same flag.

`run --json-evidence` defaults to `bounded`; `--capped-session` forces `off`, even if another JSON mode was requested. `off` turns off the main JSON walker. A separate record pass still reads JSON for KnownClusterBlast similarity (KCB percent) and TIGRFAM hits when eligible, readable evidence is available. Check its recorded status for absent, held or unreadable input; `off` does not mean no JSON is opened. The evidence parse records requested and effective modes. For bounded main-walker evidence, drop `--capped-session` and use the default or pass `--json-evidence bounded`.

## Required first commands

```bash
python mamey_run.py doctor
python mamey_run.py inspect path/to/EXAMPLE.zip
python mamey_run.py run --strain EXAMPLE --input-zip path/to/EXAMPLE.zip \
  --taxonomy "unknown" --source "not verified" \
  --outdir reviews/fresh-run --mode gold --capped-session --reference-completion off
python mamey_run.py validate reviews/fresh-run/EXAMPLE/package --workbook-strict
```

Replace the illustrative ID, taxonomy, source and paths with source-bound values; retain an explicit unknown when not established. Use a fresh output root and quote paths containing spaces. `--reference-completion off` is an explicit choice in this example, not an effect of `--capped-session`.

## What `--capped-session` changes

It leaves out work that an assistant session often cannot finish in time: the written brief and the
automatic locus maps. Authored BGC judgment stays a later task. Render figures and maps from the
finished package with [figure start here](../FIGURES_START_HERE.md). Rendering can refresh package
integrity or populate package data, so use a working copy when the sealed bytes must stay unchanged.
A capped run also stores its package ZIP uncompressed unless `MAMEY_ZIP_COMPRESSION` is already set,
and defaults `--heartbeat-seconds` to 20 when not specified. An explicit value is retained; heartbeats are progress messages, not completion evidence.

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

1. Check whether the Mamey process is still running. If it is, wait for it to end.
2. `validate` rewrites `package_status.json`, so validate a stable copy of the package after the run ends.
3. Check checksums.
4. Check terminal/package status.
5. Do not call the run successful until validation passes.
