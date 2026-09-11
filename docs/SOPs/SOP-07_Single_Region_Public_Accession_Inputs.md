# SOP-07 — Single-Region Public Accession Inputs

## Purpose

This SOP defines how Sapote/Mamey should handle single-region antiSMASH ZIPs from public GenBank accessions.

## Example

`KY089035.1.zip` is a single-region antiSMASH output for a public accession. It is not a full genome and not a sealed Mamey package. It is a valid raw antiSMASH intake target if `inspect` passes.

## Recognition pattern

Typical contents:

- `index.html`
- `regions.js`
- `<accession>.json`
- `<accession>.gbk`
- `<accession>.region001.gbk`
- `clusterblast/`
- `knownclusterblast/`
- `subclusterblast/`

## Required behavior

Mamey should classify this as:

```text
raw antiSMASH single-region accession run
```

and explain:

- this is not a full genome,
- this is not a sealed Mamey package,
- it can still be parsed,
- assembly completeness warnings may be expected,
- use it as reference/control evidence unless the user says otherwise.

## Correct first command

```bash
python -m mamey inspect <accession_zip>
```

If inspect passes, run gold mode directly — gold has been the only analysis mode since v9.7.161
(`smoke` was removed; `standard` is a deprecated alias of `gold`):

```bash
python -m mamey run --input-zip <accession_zip> --mode gold --capped-session --json-evidence off --brief none
```

## Warning interpretation

A single-region accession may produce:

- one BGC,
- 0% interior BGCs,
- VERY_POOR assembly architecture,
- edge-like status.

These warnings should not be framed as a failed full-genome run.

## Bug-hunt checks

1. Single-region accession is recognized.
2. Status language does not panic the user.
3. Public accession is not treated as private AS/SID strain.
4. KnownClusterBlast evidence is reported if available.
5. BLASTP panel export should be optional, not recommended by default for known redundant controls.
