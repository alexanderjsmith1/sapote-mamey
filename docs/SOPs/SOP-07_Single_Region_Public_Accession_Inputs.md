# SOP-07 — Single-Region Public Accession Inputs

Run the commands below from the bundle root, the folder that holds `mamey_run.py`.


## Purpose

This SOP covers antiSMASH ZIPs made from one public GenBank sequence with one BGC region.

## Example

The bundle does not ship an example ZIP. `<accession>.zip` stands for a raw antiSMASH run on one public accession, not a full-genome export or a sealed Mamey package. Check the source record and its identity before you run it.

## Recognize the input

Run `inspect` first:

```bash
python mamey_run.py inspect path/to/EXAMPLE.zip
```

Replace the example with the actual accession ZIP path, quoting paths containing spaces. `inspect` classifies the input shape from file names. It reports `raw antiSMASH single-region accession run` and prints a single-region note only when the ZIP has exactly one region GenBank file plus `index.html` or `index.htm`, `regions.js`, at least one JSON file and a name containing `clusterblast` (including KnownClusterBlast or SubClusterBlast names). A one-region ZIP without all of those is reported as `raw antiSMASH region run`, with no note. The emitted note calls it a non-full-genome reference/control unless you say it is a discovery strain; that is canned guidance, not verification of assembly completeness, reference status or the role of a deposited sequence. One region file is an input-shape observation. Check the source assembly before you treat it as a reference or test input.

## Run it

`inspect` also prints a suggested run command. Review that command, including its strain label, and bind `--taxonomy` and `--source` to verified records; retain an explicit unknown where the deposition does not establish a value. The full recipe, with its one strain-ID rule, is in [single-region accession inputs](../troubleshooting/SINGLE_REGION_ACCESSION_INPUTS.md#recommended-first-run-command). Public accession origin does not grant disclosure or release permission, or set every local privacy tag.

## Warning interpretation

A single-region accession may produce:

- one BGC,
- 0% interior BGCs,
- VERY_POOR assembly architecture,
- edge-like status.

Treat these as signals about the supplied record and boundary scope. Check the actual source assembly and run status: an input-shape warning alone neither establishes assembly quality nor proves that extraction failed or succeeded.
