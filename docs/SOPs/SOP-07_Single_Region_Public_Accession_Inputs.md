# SOP-07 — Single-Region Public Accession Inputs

Run the commands below from the bundle root, the folder that holds `mamey_run.py`.


## Purpose

This SOP defines how Sapote/Mamey should handle single-region antiSMASH ZIPs from public GenBank accessions.

## Example

`KY089035.1.zip` is the single-region public-accession example, rather than a full-genome export or sealed Mamey package. `inspect` only previews file names. Check the source record and its identity before you run it.

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

`inspect` classifies this as:

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
python mamey_run.py inspect <accession_zip>
```

If `inspect` passes, run gold directly:

```bash
python mamey_run.py run --strain auto --input-zip <accession_zip> \
  --outdir <fresh-run-root> --mode gold --capped-session --reference-completion off
```

`--strain auto` resolves the organism identity from the archive when available. If keeping the accession as the output label is intentional, use `--strain <accession> --allow-accession-strain-id` instead and record that decision. Public accession origin does not grant disclosure/release permission or determine every local privacy tag.

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
