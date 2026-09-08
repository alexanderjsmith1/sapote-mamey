# SOP-01 — Intake: Raw antiSMASH ZIP vs Mamey Package vs Reference Accession

## Purpose

This SOP defines how Sapote/Mamey should classify uploaded ZIP files and choose the correct first command.

## Raw antiSMASH ZIP

A raw antiSMASH ZIP commonly contains:

- `index.html`
- `regions.js`
- one or more `.gbk` files
- one or more `.region###.gbk` files
- optional `.json`
- `clusterblast/`
- `knownclusterblast/`
- `subclusterblast/`

First action:

```bash
python -m mamey inspect <input.zip>
```

## Full-genome antiSMASH ZIP

Expected signs:

- many region GBKs,
- many clusterblast files,
- one or more source contigs,
- raw BGC count usually greater than 1.

Run gold mode directly in ChatGPT (gold has been the only analysis mode since v9.7.161 — `smoke`
was removed and `standard` is a deprecated alias of `gold`; `--capped-session` keeps the run inside
a capped-session wall-clock budget, it does not select a different mode):

```bash
python -m mamey run --input-zip <input.zip> --mode gold --capped-session --json-evidence off --brief none
```

## Single-region antiSMASH accession ZIP

Expected signs:

- one `.region001.gbk`,
- one accession-style sequence name such as `KY089035.1`,
- one BGC,
- public accession rather than private strain name.

Run inspect first. If clean, gold mode (the only analysis mode) is valid, but warnings about poor
assembly or 0% interior BGCs must be interpreted as expected for the input shape.

## Sealed Mamey package

Expected signs:

- package manifest,
- checksums,
- workbooks,
- receipts,
- run metadata.

First action:

```bash
python -m mamey validate <package_dir>
```

Do not re-run the package as if it were raw antiSMASH input.

## Reference accession interpretation

Public accession inputs should be labeled as:

- public reference sequence,
- control BGC,
- comparison BGC,
- parser smoke fixture.

They should not be treated as private discovery strains.

## Bug-hunt checks

1. `inspect` should print archive type.
2. Single-region accession inputs should be called valid but limited.
3. Public reference accession should not trigger private AS/SID handling.
4. Sealed package should not be treated as raw antiSMASH.
5. Missing KCB should lower evidence availability, not necessarily fail intake.
