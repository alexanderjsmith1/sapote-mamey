# Make reports from a saved package

Use an existing package to make a report or prepare another analysis while
keeping the original ZIP. You need the extracted package and an installed bundle.
Some commands write into the package; choose the command before choosing a working folder.

## Compiled reports

From the program folder, replace `EXAMPLE` with your run label:

```bash
python mamey_run.py compile-report runs/EXAMPLE/package --no-figures
```

`--no-figures` uses the figures already available instead of generating more.
For a sealed package, the report goes under `runs/EXAMPLE/post_seal/compile-report/`.
The command saves a source receipt and a `.reader_view_*/package/` snapshot there.
Keep the snapshot with the report because its images link to that folder.
Each attempt copies roughly one package's worth of files.

Recompiling can replace the report and its sidecars. Choose a new Markdown
filename with `--out` when you need to keep an earlier report. Other external
reader commands—`compound-families`, `assembly-line` and `lead-pages`—take an output
directory instead of a Markdown filename. They refuse paths inside the original
sealed package, including paths reached through symlinks.

For an unsealed run, these commands can write inside the package while it is
being assembled. Check for checksum or seal markers before relying on the external route.

## PDF routes

To request a PDF after writing the report text:

```bash
python mamey_run.py compile-report runs/EXAMPLE/package --pdf
```

Missing artwork or unfinished narrative sections can stop PDF creation. A run
with locus maps disabled also disables compile-time figure generation. Read the
error before changing a setting just to force a PDF through.

ReportLab is the main PDF route. The fallback needs Pandoc and XeLaTeX; SVG
conversion needs CairoSVG, rsvg-convert or Inkscape. PDF checks use `pdffonts`,
`pdftotext` and `pdfimages`. See [Install](INSTALL.md) for the selected dependencies.

Wide tables become record ledgers with full field names and values. Inspect the
actual pages for clipped text, missing images and broken tables before sharing them.

## Bound BiG-SCAPE staging

This prepares region inputs without starting clustering. Supply the original
antiSMASH ZIP matching the package's input hash:

```bash
python mamey_run.py bigscape --package runs/EXAMPLE/package   --source-zip ~/Downloads/EXAMPLE.zip --dry-run
```

Replace both example paths. `--source-zip` locates the original archive if it has
moved; `--dry-run` stops after staging. Read `source_staging_receipt.json` for the
selected members and hashes. Missing input, conflicting archive roots or zero
staged regions stop this step. The command accepts an extracted package or its ZIP.

<a id="commands-that-still-author-package-data-in-447"></a>

## Commands that write into the package

Use a working copy for `render-figures`, `render-all-figures`, `mode-b`,
`domain-level` and BLASTp authoring/import commands. They refresh package checksums
even when some output files go to an external folder. `locus-maps` requires an
output inside the supplied package; use the working copy for it.

`domain-level` may create a missing metric table. `ingest-receipts` writes cards
and the judgment register but does not use that checksum-refresh wrapper.
`ingest-blastp` also updates the supplied master workbook, so select a working
master. See [BLASTp imports](ONLINE_BLASTP_PROTOCOL.md) for the different import routes.

External `guide --outdir`, template emission with external `--out`, and verification
with an external report destination use their own write rules. `explain`,
`list-bgcs` and `blastp-status` read saved records.

## Validation can update a mutable status receipt

`validate` refreshes `package_status.json`. Use a writable review copy and keep
the printed results beside it. `compile-report` validates sealed input without
that write. The Python API has a read-only option, but the normal `validate` CLI
has no equivalent switch. [Read results](reader/03_READ_RESULTS.md) explains the checks.

## Strain brief profiles and partial rendering

Brief profiles choose PDF contents, not a guaranteed file count. A run can print
`COMPLETE` while skipping optional figures, and a failed attempt can leave partial
files. Read the render warnings. Keep the full authored text
because the brief's page limits can shorten it.

For the exact field and selection rules, see the
[brief reference](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-5-brief-profiles-display-labels-and-boundary-payloads).
