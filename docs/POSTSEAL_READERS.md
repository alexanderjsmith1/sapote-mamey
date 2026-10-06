# Immutable package reader outputs

For sealed packages, `compile-report`, `compound-families`, `assembly-line` and
`lead-pages` write to
`<package.parent>/post_seal/<command>/` by default. An explicit `--out` may choose
another external location. `compile-report --out` selects a Markdown file; the
other three select an output directory. Resolved paths into the original package,
including symlink aliases, are refused. Existing writer trees containing symlinks
are refused. No original manifests, checksums or seal receipts are amended.

The compile-report command and low-level assembly-line and compound-family APIs
retain their earlier output
layout while assembling an unsealed run. Once checksums or a seal marker exist,
they apply the same external reader route as the commands.

## Compiled reports

```bash
python mamey_run.py compile-report /path/to/package --no-figures
python mamey_run.py compile-report /path/to/package --pdf
```

For sealed input, the command validates its input and records all original file hashes in an
external `.source_receipt.json`. A unique `.reader_view_*/package/` snapshot holds
copied source files, generated figures, converted artwork and any explicitly
requested BLASTp waiver attestation. Discovery still reads the original project's
bound evidence; waiver provenance is recorded in the external reader manifest.
Keep that snapshot alongside the report: its absolute image links refer there.
Recompiling uses a new snapshot and preserves the original package. For mutable input without checksum or seal markers, the command writes the
construction-time report inside the package and the workflow reads that report.
For sealed input, the workflow compile step reads the default external report before the auto-emitted in-package
skeleton, and requires its current source/output receipt; stale or unbound external
reports stay pending. Explicit custom deliverable folders retain their existing
reader route. Copying has a
storage cost approximately equal to the source package for each attempt.

A recorded `locus_maps=off` run-phase receipt, or an explicit off option in the
source manifest, disables compile-time figure generation. `--no-figures` also
uses existing figures only. Missing or inadequate publication artwork refuses a
requested PDF; it is never silently removed. Unfilled narrative slots refuse a
requested PDF unless the existing explicit draft override is provided.

## PDF routes

The primary PDF route uses ReportLab with embedded fonts. Pandoc and XeLaTeX are
needed only for the fallback; the doctor reports each complete route. SVG fallback
conversion needs CairoSVG, rsvg-convert or Inkscape. Publication PDF checks also
require pdffonts, pdftotext and pdfimages. No dependency is installed automatically.

Tables wider than eight columns become a record ledger: the original field name
and full value are shown per row, with record identity repeated. Exceptional long
values continue in labelled rows; the former 300-character clipping is removed.
Every field remains present. Relative images resolve against the original
Markdown directory before fallback preflight moves it. Missing images and excess
unmatched table cells refuse rendering rather than disappear.

## Bound BiG-SCAPE staging

```bash
python mamey_run.py bigscape --package /path/to/package \
  --source-zip /path/to/original-antismash.zip --dry-run
```

A package with no embedded region GBKs reads its declared original antiSMASH
archive. The archive must match `manifest.json`'s `input_zip_sha256`. A moved or
renamed source can be supplied with `--source-zip`; the digest remains mandatory.
Automatic lookup is limited to the declared locator within the package and its
two parents. Multiple existing locators are refused, even when bytes agree.

Directory packages and Complete_Package ZIPs are supported. Archive member names,
assembly root, destination collisions and all selected region bytes are admitted
before staging. Multiple region-file roots or duplicate members refuse the input.
`source_staging_receipt.json` records the archive, manifest and each staged member's
hash. Zero staged inputs fail with source guidance, rather than suggest a detached
retry. Outputs, work directories and widget paths remain outside every input
package. A dry run stages and records inputs but executes no clustering engine.
