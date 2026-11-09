# Run the reference-panel test

This page is for a maintainer. It explains how to run the test that checks the bundle's
reference cluster library, and how to point the test at a folder of antiSMASH ZIPs for a
second, deeper check. You do not need it to run an analysis.

The task: run the reference-panel test and tell a pass from a skip.

## Run it

From the bundle root:

```bash
pytest -q -rs tests/test_reference_panel.py
```

The bundled library is `mamey/data/reference_bgc_library.json`. The whole file skips if the library is missing.

## What it checks

- **Library check.** Needs no extra input. It checks required fields, marker syntax, duplicate accessions and recorded signatures.
- **ZIP check.** Needs a folder of antiSMASH result ZIPs. For each library entry it finds the matching ZIP by accession in the file name, takes the largest region, recomputes the markers and compares them with the markers recorded in the library (`found_markers`). The recorded markers are earlier observations, not an independently verified answer. A match means the scanner still agrees with itself. It does not show the product or the biology.

To turn the ZIP check on, name the folder. Only top-level `.zip` files in it are used:

```bash
MAMEY_REF_ZIPS=/path/to/reference_zips pytest -q -rs tests/test_reference_panel.py
```

## Pass and skip

Without `MAMEY_REF_ZIPS`, every ZIP test skips with `MAMEY_REF_ZIPS not set`. Some library
tests skip too: an entry with no recorded `architecture_signature` skips its signature check.
With the variable set, entries with no matching ZIP skip with
`no source zip for <accession> in MAMEY_REF_ZIPS`. A skip is not a pass. Run with `-rs` to see
each skip and its reason, and report library skips and ZIP skips separately. A run on the shipped library
without `MAMEY_REF_ZIPS` ended `228 passed, 77 skipped`: 75 ZIP skips and 2 signature skips.
Expect different numbers if the library changes.

## List what the ZIPs produce

```bash
python tools/reference_panel_ledger.py <zip-directory> <new-output.csv>
```

Both paths are required. The tool scans the top-level ZIPs, prints `skip` for any archive that
fails, and writes one CSV row per parsed BGC region. A multi-region ZIP gives several rows, and a ZIP
with no parsed region gives none. Columns include `obs_region_type` and `cmp_t43_markers`. It
overwrites the CSV if rows exist, so give it a new path.
Exit 0 means rows were written. Exit 1 prints `NO_ROWS` and writes nothing. Exit 2 means a missing argument or folder.

Do not compare the row count with the ZIP count. Read the `zip roster:` line instead: it gives the
number of ZIPs, how many produced rows, how many had no parsed region (each listed under
`no regions:`), and how many were skipped. Compare the distinct `source_file` values with the ZIPs you
supplied.

The strain part of `identity` is the ZIP file name stem, not a bound strain record;
`identity_strain_basis` reads `zip_filename_stem_unbound`. Bind each row to its strain and full locus
record before you cite it.

## Adding a real fixture

Write down the accession and version, the strain, contig, region and cluster, the source
archive and its hash, which part of it you kept, how the expected answer was decided, and the
software versions. Label synthetic fixtures as synthetic. Public availability of a genome does not
by itself allow you to ship it; see the [reference seed inputs policy](../resources/reference_seed_inputs/README.md).

See also [tests and gated coverage](../tests/README.md) and the [fixture index](../tests/fixtures/README.md).
