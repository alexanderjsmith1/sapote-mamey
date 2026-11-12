# Save and move a result

Keep the result folder, its ZIP and the original antiSMASH ZIP together. This page
shows what to save and how to copy it to another computer without losing files.
You need the originals and enough disk space for the copy. To keep results in a
checked, logged store instead, see [Keep results in a Strain Master](DATA_HOME.md).

## What to keep

A finished run writes `runs/EXAMPLE/`. It holds:

- `package/`, the folder with the manifest, tables, workbook and issue log;
- `EXAMPLE_SapoteMamey_..._Complete_Package.zip`, a ZIP snapshot of that folder;
- the run's logs.

Keep all of it, plus the original antiSMASH ZIP. Record the program version and
each ZIP's hash (see below). Failed-run logs can explain why a retry used
different settings, so check a file's role before you delete it.

The `Complete_Package.zip` is a snapshot from the end of extraction. Written cards,
notes and other files you add later live outside it; save those separately.
Figure rebuilds may need their source tables and reference data. You can recreate
Python environments and caches from `pyproject.toml` and [Install](INSTALL.md).

## Open a saved run without rerunning it

Extract the package ZIP into a new review folder and keep the original ZIP. Open
`<review folder>/package/OPEN_ME_FIRST.html`, then follow
[Read one saved package](reader/03_READ_RESULTS.md). If the browser blocks local
links, open the listed files from your file browser.

Command-line checks need the matching program version. `explain` reads saved
summaries. For a fresh validation, see
[Run a fresh check](reader/03_READ_RESULTS.md#run-a-fresh-check-if-needed). Keep the old
records and the new terminal output separately.

## Move a result to another computer

Copy the ZIPs, notes and files you added. A hash is a fingerprint of a file's
bytes. Run the same command on both computers and check that the two values are
identical.

macOS or Linux:

```bash
shasum -a 256 ~/Downloads/EXAMPLE.zip
```

Windows Command Prompt:

```bat
certutil -hashfile "%USERPROFILE%\Downloads\EXAMPLE.zip" SHA256
```

Windows PowerShell:

```powershell
Get-FileHash "$HOME\Downloads\EXAMPLE.zip" -Algorithm SHA256
```

Replace the path with each archive you are copying. Matching hashes mean the
bytes arrived intact. Extract into a fresh folder at the destination. Old
absolute paths still name locations on the original machine; write the new
locations beside the old records. Compiled reports hold absolute image paths that
point into a reader snapshot; see the
[absolute-path note](POSTSEAL_READERS.md#compiled-report-image-links).

PDFs and CSVs open without Python. Commands need a compatible environment; see
[Install](INSTALL.md).

## Why the output is large

A run keeps both an expanded package and its ZIP. The brief adds a PDF and its
figures. Locus maps add one figure per region. To skip both, add
`--brief none --locus-maps off` to your `run` command.

`--capped-session` is a mode for tools with a time limit. It skips the brief and the
main antiSMASH JSON walker, and turns automatic gene maps off unless you set `--locus-maps`.
Available KnownClusterBlast text and eligible JSON can still be read by separate paths;
check their saved states for missing, held or unreadable input. It requires the workbook,
writes an uncompressed ZIP unless `MAMEY_ZIP_COMPRESSION` is set, and prints a progress line
every 20 seconds unless you set `--heartbeat-seconds`. It is not just a way to save space. The
[input guide](ANTISMASH_INPUTS_CONSUMED.md) explains the evidence modes. The
[first run](reader/01_FIRST_RUN.md) uses the capped command that `inspect` prints. The
[first-run flags](reader/01_FIRST_RUN.md#3-run-the-command-that-inspect-printed)
say how to turn it into a run without the cap.

## Archive to an external disk or iCloud

Copy the files you chose, check their hashes, and open one file from the copy.
Update your location notes before you decide whether to delete a local original.
A cloud placeholder or a disconnected disk cannot supply inputs to a running
analysis.

## What a checkpoint records

Save a short note with the objective, input and program versions and hashes,
output paths, settings, completed and failed steps, open questions and the next
action. Keep any assistant transcript with that note. The policy is in
[AGENTS.md](../AGENTS.md#next-paths-automatic-save-state-and-transcripts).

<a id="use-the-portable-handoff-builder-deliberately"></a>

## Build a portable ZIP

Use `handoff` when the receiver needs to run online BLASTp. That search needs the
protein sequences and their source identities. A package can contain a `*_proteins.faa`
file with available BGC-member translations, but its presence does not establish complete
coverage or replace the region GenBank records needed by this handoff route. The region
GenBank files from the antiSMASH ZIP can carry those translations. `handoff` packs the package and those
files into one ZIP, so you do not send the 20 to 120 MB antiSMASH ZIP. For any
other transfer, copy `*_Complete_Package.zip`.

`handoff` does not include your Python environment or files you added outside the
package. Create a new output folder first:

```bash
mkdir -p ../EXAMPLE-transfer
python mamey_run.py handoff \
    --package runs/EXAMPLE/package \
    --input-zip ~/Downloads/EXAMPLE.zip \
    --out ../EXAMPLE-transfer/EXAMPLE.zip
```

Before you run it, check that the package and the input ZIP belong together.
Compare `shasum -a 256` (or the Windows command above) of the input ZIP with
`input_zip_sha256` in `runs/EXAMPLE/package/manifest.json`. `handoff` does not
compare them. Use a new filename: an existing destination is replaced. Run one
build per destination.

A good run prints:

```text
handoff -> ../EXAMPLE-transfer/EXAMPLE.zip (2.9 MB)
  region GBKs: 70  (all regions)
```

Your size and count will differ. A `NOTE:` line means the input ZIP was missing
and no region files went in. The result is a package-only ZIP and online BLASTp
will not work from it. The ZIP root holds `HANDOFF_README.txt`, which lists what
is inside.

The output must sit outside the package folder and must not be an input file. A
bad package path prints `ERROR:` and exits 1.

A region-only ZIP can change the protein set. Compare query identifiers and
sequence hashes before you reuse a search plan or results. With `--top-n N`, the writer selects BGC IDs using `Corrected_rank`; it uses raw
`Rank` only when that column is absent. Blank corrected ranks do not enter selection.
If the selected IDs yield no mapped source GBKs, the writer falls back to all region
GBKs, including when no IDs were selected. With a partial crosswalk it includes only
mapped selected regions and can omit the others. Read `HANDOFF_README.txt` and compare
`selected_bgcs` with actual archive members. A selected-ID count is not an archive-region
count. Check the full region identities and filenames; filename collisions can also
change what the handoff contains.

To move several packages with their catalog, use
[private project export](PROJECT_CATALOG.md#export-and-test-the-archive). It refuses an
existing destination.

## Fingerprints and archive integrity

A package fingerprint covers selected normalized table and state files. Use the
whole-archive SHA-256 above to check a transfer, and `validate` to check package
structure.
