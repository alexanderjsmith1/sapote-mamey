# SOP-02 — ChatGPT-Safe Capped-Session Run

> **v9.7.374 correction:** this SOP originally described a "smoke mode" first-run path. `--mode
> smoke` was **removed at v9.7.161** (`mamey run --mode` now accepts only `{standard,gold}`, and
> `standard` is a deprecated alias of `gold` since v9.7.92) and the forced smoke-first gate for
> capped sessions was itself removed at **v9.7.160** ("capped sessions run gold DIRECTLY (the old
> forced smoke-first FATAL is gone)" — `cli.py:3037`). Gold is the only analysis mode; the
> wall-clock/output-budget behavior this SOP is actually protecting used to live behind `smoke` and
> now lives behind `--capped-session` (alias `--chatgpt-safe`) on a direct gold run. See
> `SESSION_START_MANIFEST.md`'s "capped ChatGPT/Claude sessions" line for the current authoritative
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
python -m mamey doctor
python -m mamey inspect <input.zip>
python -m mamey run --input-zip <input.zip> --mode gold --capped-session --json-evidence off --brief none
python -m mamey validate <package_dir> --workbook-strict
```

## Why `--capped-session` first

`--capped-session` reduces risk from:

- long-running BGC judgment,
- excessive JSON evidence,
- oversized output,
- ChatGPT/Claude tool timeout,
- too many regions or BGCs,
- missing optional deliverables (suppressed on purpose, not silently dropped — re-populate with
  `mamey render-all-figures --package <pkg> --all --workbook <wb.xlsx>` post-seal).

## Required outputs

A capped-session run should produce:

- package directory,
- manifest,
- checksums,
- workbook when expected,
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
