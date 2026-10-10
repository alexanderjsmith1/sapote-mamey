# SOP-02 — ChatGPT-Safe Capped-Session Run

Before any `doctor` example below, read the [write-probe boundary](../INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


> **v9.7.374 correction:** this SOP originally described a "smoke mode" first-run path. `--mode
> smoke` was **removed at v9.7.161** (`python mamey_run.py run --mode` now accepts only `{standard,gold}`, and
> `standard` is a deprecated alias of `gold` since v9.7.92) and the forced smoke-first gate for
> capped sessions was itself removed at **v9.7.160** ("capped sessions run gold DIRECTLY (the old
> forced smoke-first FATAL is gone)" — `cli.py:3037`). Gold is the only analysis mode; the
> wall-clock/output-budget behavior this SOP is actually protecting used to live behind `smoke` and
> now lives behind `--capped-session` (alias `--chatgpt-safe`) on a direct gold run. See
> `docs/BUNDLE_CAPABILITIES.md`'s "capped ChatGPT/Claude sessions" line for the current authoritative
> command.

## Purpose

This SOP defines the safest first run path for ChatGPT/Claude capped sessions.

## Principle

In a capped ChatGPT/Claude session, `--capped-session` should be the default modifier for unknown
or large antiSMASH ZIPs — it runs the same gold-mode extraction directly but suppresses the
wall-clock-expensive figure/brief work so the session doesn't time out. There is no separate
"smoke" mode to run first; gold is the only analysis mode.

## Required first commands

```bash
python mamey_run.py doctor
python mamey_run.py inspect <input.zip>
python mamey_run.py run --input-zip <input.zip> --mode gold --capped-session --json-evidence off --brief none
python mamey_run.py validate <package_dir> --workbook-strict
```

## Why `--capped-session` first

`--capped-session` reduces risk from:

- automatic figure/brief generation, while authored BGC judgment remains a later task,
- excessive JSON evidence,
- oversized output,
- ChatGPT/Claude tool timeout,
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

If the ChatGPT/Claude wrapper times out after Mamey reports manifest/checksum writing:

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
