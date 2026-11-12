# Make reports from a saved package

Use a finished package to make a report or prepare another analysis, and keep the
original ZIP. You need the extracted package from a finished `run`
([first run](reader/01_FIRST_RUN.md)) and the installed program.

A sealed package is one that passed the extraction and package-integrity checks
([glossary](GLOSSARY.md)). A finished `run` makes one.
`python mamey_run.py seal-package runs/EXAMPLE/package` repeats the quality checks and
writes `seal_status.json`. Commands that read a sealed package write their output
under `runs/EXAMPLE/post_seal/`, outside the package. Some commands still write
inside the package, as the section "Commands that write into the package" says.

In every command below, replace `EXAMPLE` with your run label. Run them from the
program folder.

## Compiled reports

Compiling copies about one package's worth of files into a reader snapshot.
Compiling again can replace the report and its extra files. To keep an earlier
report, give the new one a different Markdown name with `--out`.

```bash
python mamey_run.py compile-report runs/EXAMPLE/package --no-figures
```

`--no-figures` uses the figures that already exist and does not draw new ones. For a
sealed package, the report goes under `runs/EXAMPLE/post_seal/compile-report/`, with a
source receipt and a `.reader_view_*/package/` snapshot beside it.

<a id="compiled-report-image-links"></a>

Image links in the report are absolute paths into that snapshot. Moving the report
breaks them, and the paths show your local folder names. Share a rendered PDF, or
compile again at the destination.

`compound-families`, `assembly-line` and `lead-pages` take an output folder instead of
a Markdown name. They refuse a folder inside a sealed package, including one reached
through a symlink. On a package that is not sealed, they can write inside it.

## PDF routes

To make a PDF after the narrative sections are written:

```bash
python mamey_run.py compile-report runs/EXAMPLE/package --pdf
```

The command stops if a narrative section is still empty or artwork is missing. Read
the error. Do not add `--allow-unfilled-pdf` just to get a file. A run with locus
maps turned off also skips figure drawing at compile time.

The PDF is made with ReportLab. If that fails, Pandoc with XeLaTeX is the fallback.
Turning SVG figures into images needs CairoSVG, `rsvg-convert` or Inkscape. To check
the PDF you can use the Poppler tools `pdffonts`, `pdftotext` and `pdfimages`. See
[Install](INSTALL.md) for what to add.

Wide tables become one record per row, with full field names. Open the PDF and look
for clipped text, missing images and broken tables before you share it.

## Bound BiG-SCAPE staging

This prepares the region files for BiG-SCAPE and does not cluster them. Give the
original antiSMASH ZIP that matches the package:

```bash
python mamey_run.py bigscape --package runs/EXAMPLE/package \
  --source-zip ~/Downloads/EXAMPLE.zip --dry-run
```

`--source-zip` points to the original ZIP if it has moved. `--dry-run` prepares the
input, writes `source_staging_receipt.json` (the chosen members and their hashes) in the
output folder, prints the BiG-SCAPE command, and stops. The command stops with an error if the ZIP
is missing, the archive roots conflict, or no region is staged. It accepts an
extracted package or its ZIP. To run the clustering, see the
[BiG-SCAPE walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

<a id="commands-that-still-author-package-data-in-447"></a>

## Commands that write into the package

Work on a copy of the package for these commands: `render-figures`,
`render-all-figures`, `mode-b`, `guide`, `domain-level`, `ingest-receipts`, and the
BLASTp commands `ingest-blastp`, `ingest-blastp-trove`, `blastp-online`, `blastp-ebi`
and `blastp-round`. After each one returns, the wrapper refreshes
`post_seal_checksums.txt` if the package's core checksum file exists, even when the
command returned a nonzero exit code. It skips the refresh only when the command's `--out` or `--outdir`
points outside the package (`mamey/cli.py:9339-9366`, `mamey/packaging.py:355-368`).
A refresh failure prints a warning and does not change the exit code.

Copy into a folder that does not exist yet:

```bash
mkdir runs/EXAMPLE/package_work && cp -R runs/EXAMPLE/package/. runs/EXAMPLE/package_work/
```

If either command fails, stop. Preserve an existing or partial folder and choose a new name
after inspection. After a successful copy, check that `package_work/manifest.json` is the
package you mean. Only then render:

```bash
python mamey_run.py render-figures runs/EXAMPLE/package_work --figure-set locus-maps
```

`locus-maps` is a figure set, not a command of its own. It always writes inside the
package, to `locus_maps/` by default. `--outdir` must also resolve inside the package, so
the command refuses a folder elsewhere. That is why you use the copy.

`domain-level` can create a missing metric table. `ingest-receipts` writes cards and
the judgment register. `ingest-blastp` also
updates the master workbook you give it, so pass a working copy of the workbook. See
[BLASTp imports](ONLINE_BLASTP_PROTOCOL.md) for the import routes.

`guide --outdir`, template emission with an outside `--out`, and verification with an
outside report destination follow their own write rules. `explain`, `list-bgcs` and
`blastp-status` only read saved records.

<a id="validation-can-update-a-mutable-status-receipt"></a>

## Validation updates a status file

`validate` rewrites `package_status.json`, so run it on a copy you can change and
keep its printed result beside it. `compile-report` checks a sealed package without
that write. The Python API has a read-only option. The `validate` command does not.
For the command and its exit codes, see step 4 of the
[first run](reader/01_FIRST_RUN.md) and [Read results](reader/03_READ_RESULTS.md).

## Strain brief profiles

A brief profile chooses what goes in the PDF. It does not promise a number of files.
A run can print `COMPLETE` and still skip optional figures, and a failed attempt can
leave partial files. Read the warnings. Keep the full text you wrote, because the
page limits can shorten the brief. For the field rules, see the
[brief reference](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-5-brief-profiles-display-labels-and-boundary-payloads).
