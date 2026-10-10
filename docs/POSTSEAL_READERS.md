# Immutable package reader outputs

For sealed packages, `compile-report`, `compound-families`, `assembly-line` and
`lead-pages` write to
`<package.parent>/post_seal/<command>/` by default. An explicit `--out` may choose
another external location. `compile-report --out` selects a Markdown file; the
other three select an output directory. Resolved paths into the original package,
including symlink aliases, are refused. Existing writer trees containing symlinks
are refused. These output helpers do not amend original manifests, checksums or seal receipts.
However, `compile-report` first calls the package validator with its default
status-writing behavior, so it can refresh `package_status.json` in the supplied
original package before the snapshot binding is recorded. The later
`source_unchanged` receipt does not cover that earlier step. To preserve every
original byte in .447, compile from a separately identified working copy; retain
the original and its hashes. This implementation repair remains held.

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
Recompiling uses a new snapshot, but can replace the external report and its
sidecars at the selected destination. Choose a new `--out` file to retain earlier
attempts. Original-package preservation still has the validation caveat above. For mutable input without checksum or seal markers, the command writes the
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

## Commands that still author package data in .447

The immutable external-reader behavior above applies to the four named commands, not to every post-seal command. In .447 the CLI refreshes `post_seal_checksums.txt` after `render-figures`, `render-all-figures`, `mode-b`, `domain-level` and BLASTp authoring/ingest commands when a package is supplied. An external `--outdir` does not bypass that wrapper for those commands. External `guide --outdir` has a separate explicit exemption.

To retain an original sealed package byte-for-byte, use a separately identified working package copy for these authoring commands. Preserve the original ZIP, hashes and manifests, record the copy's source binding and destination, and validate/review the working result separately. Do not infer that `post-seal` or `non-blocking` means read-only. A written checksum is not scientific acceptance.

`render-figures --figure-set standard` can put its image files externally, but still enters the CLI refresh wrapper. `domain-level` can populate `<package>/domain_level/` when its metric table is absent. `locus-maps` requires its requested output to be inside the supplied package. For that set, use the working copy's internal destination; an arbitrary external path is refused. Some renderer branches return zero even when outputs were skipped or held, so inspect their actual counts, status records and rendered pages.

`ingest-blastp-trove` writes channel overlays, admission/quarantine and ledger records under the supplied package. `ingest-blastp` updates the supplied master workbook; adding `--package` also writes a package overlay and binding records. Use explicitly selected working copies and preserve prior masters. `tools/ingest_blastp_rollups.py` is a different path: its default is a read-only dry run, while `--execute` inserts into the named existing reservoir. See [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) for format and channel boundaries.

`explain`, `list-bgcs`, `validate` and `blastp-status` are not in the CLI authoring refresh list. Template emission with an explicit external `--out`, and verification with an external report destination, are different from the native `mode-b` authoring route; check each selected handler rather than assuming all Mode B commands mutate or all are readers.

## Validation can update a mutable status receipt

The normal `validate` command calls the package validator with its default `write_status_receipt=True`, refreshing `package_status.json`. Its absence from the authoring checksum-refresh list does not make every package byte immutable. Read-only API consumers can explicitly request `write_status_receipt=False`; that API option is not exposed as a general `validate` CLI switch. Preserve the before state and captured validation JSON separately when documenting an original seal; see [result status meanings](READING_YOUR_RESULTS.md).

## Strain brief profiles and partial rendering

The deterministic strain brief is an authoring renderer, not a read-only package viewer. Its `minimal` profile can still attempt extra figure families and print packs; the profile controls selected PDF composition rather than a guaranteed complete output count. Standard can append already-authored judgment text, whose page limits can omit lines or paragraphs. Preserve the full text and inspect actual pages.

Optional family skips and image-embedding failures can coexist with renderer `COMPLETE`. A failure can leave overwritten or partial files despite an empty returned file list; a wrapper phase END is not rendered-output acceptance. Use a separately identified working package, retain the original seal and inspect actual warnings, output hashes and pages. See [current brief/display contracts](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-5-brief-profiles-display-labels-and-boundary-payloads) for board selection, priority-exclusion transport and shortened-label limits.
