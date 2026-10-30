# Save and move a result

Keep the complete result folder, its ZIP and the original antiSMASH ZIP together.
This page shows what to save and how to move it without losing files. You need
access to the originals and enough space for the destination copy.

## What each file is for

The program version and input ZIP identify how the run was made. Record their
hashes. Keep the package as a unit: its manifest, tables, workbook, figures and
logs link to one another. Keep any reference sequences used in later analyses too.

The `*_Complete_Package.zip` is a snapshot from the end of extraction. Later
cards, notes and other authored files may live outside it; save those separately.
Figure rebuilds may also need their source tables, configs and reference data.
Python environments and caches can be recreated from the dependency record.

Check a file's role before deleting it. Failed-run logs can explain why a retry
used different settings.

## Open a saved run without rerunning it

Extract the package ZIP into a review folder and keep the original ZIP. Open
`OPEN_ME_FIRST.html`, then follow [Read results](reader/03_READ_RESULTS.md).
If the browser blocks local links, open the listed files from your file browser.

Use the matching program version for command-line checks. `explain` reads saved
summaries. Follow [Read results](reader/03_READ_RESULTS.md#run-a-fresh-check-if-needed)
for fresh validation and its status-write result. Keep the old records and the
new terminal results separately.

## Move a result to another computer

Copy the ZIPs, notes and authored files. Compare the archive hash on both machines:

```bash
shasum -a 256 ~/Downloads/EXAMPLE.zip
```

Replace the path with the archive you are transferring. Matching hashes confirm
that its bytes arrived intact. Extract into a fresh folder at the destination.
Old absolute paths still name locations on the original machine; record the new
locations beside the old records.

PDFs and CSVs can be read without Python. Commands need a compatible environment;
see [Install](INSTALL.md).

## Why the output is large

A run keeps both an expanded package and its ZIP. Briefs and locus maps add figure
files for each region. If you deliberately want tables without those renderings,
add `--brief none --locus-maps off` to your chosen `run` command.

`--capped-session` also changes JSON reading, workbook requirements, compression
and progress output. It is not just a way to save figure space. The [input guide](ANTISMASH_INPUTS_CONSUMED.md)
explains the evidence modes; leave the defaults for the [first run](reader/01_FIRST_RUN.md).

## Archive to an external disk or iCloud

Copy the selected files, verify their hashes and open a file from the copy.
Update your location notes before deciding whether to delete any local original.
Cloud placeholders and disconnected disks cannot supply inputs to a running analysis.

## What a checkpoint records

Save a short note with the objective, input and program versions/hashes, output
paths, settings, completed and failed steps, unresolved questions and next action.
Keep any assistant transcript with that note. See the [save-state guide](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).

<a id="use-the-portable-handoff-builder-deliberately"></a>

## Build a portable ZIP

The `handoff` command combines a package and selected raw region GenBank files.
It does not include your Python environment or authored files outside the package.
Create a new output folder first:

```bash
mkdir -p ../EXAMPLE-transfer
python mamey_run.py handoff --package runs/EXAMPLE/package   --input-zip ~/Downloads/EXAMPLE.zip   --out ../EXAMPLE-transfer/EXAMPLE.zip
```

Replace the run label and input path. Check the package and input hash first:
the builder does not compare them for you. Use a new filename because both an
existing destination and its `.tmp` file can be replaced. Run one build per destination.

A region-only ZIP can change the protein set; compare query identifiers and sequence hashes before reusing a search plan or results.

Read the reported region count and inspect the ZIP. A missing input archive can
still return success with a package-only ZIP. For a limited region selection,
`--top-n` uses ranked rows and the filename crosswalk; inspect the selected full
identities and filenames because unmapped rows and filename collisions can
change the result.

For several packages with their catalog, use [private project export](PROJECT_CATALOG.md#export-a-private-archive),
which refuses an existing destination.

## Fingerprints have a narrower scope than archive integrity

A package fingerprint covers selected normalized table/state files. Use the
whole-archive SHA-256 above to check a transfer, and validation to check package structure.
