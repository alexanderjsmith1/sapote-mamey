# Files, storage and handoff

A run produces a folder of evidence, not one spreadsheet. Keep that folder together. Keep the
original input beside it. Write down where both are.

## What each file is for

| File or folder | What it is | Keep it? |
|---|---|---|
| The code ZIP or git revision you ran | Identifies the program version | Yes. Note the version and hash. |
| The original antiSMASH result ZIP | The upstream evidence. Some later workflows need it. A sealed package alone supports many reading tasks. | Yes, unchanged. Record its SHA-256. |
| Genome FASTA and other reference inputs | Needed for companion workflows (BLAST, trees, ANI) | Yes, if you used them. The package does not contain them. |
| `runs/<ID>/package/` | The delivered evidence, expanded | Yes, as one unit. Do not pick files out of it. |
| `*Complete_Package.zip` | Snapshot of the package, made when the run seals it. The name is `<strain>_SapoteMamey_v<bundle>_engine<engine>_<profile>_Complete_Package.zip`, where `<profile>` is the antiSMASH strictness (`strict`, `relaxed`, `loose` or `unknown`). | Yes. Anything authored after sealing is not inside it. |
| `manifest.json` | Index of the package: versions, counts, status | Yes, inside the package. |
| CSV tables and the workbook | The evidence tables you review | Yes. Annotate a copy, not the original. |
| PDFs, PNGs and figure sidecars | Renderings of selected evidence | Keep them with their renderer and input receipts. Rebuilding a figure may also need archives, configs, databases or figure dependencies that you supply separately. |
| Logs and phase or validation receipts | What ran, what failed, how long it took | Yes, including failed attempts. |
| Authored cards, notes, transcripts | Your interpretation | Yes. These usually live outside the package. |
| The Python environment and caches | Machine-specific | No. Recreate them from the dependency record. |

A file missing from this table is not therefore disposable. Check `manifest.json` and the
workflow that wrote the file before you delete anything.

## Open a saved run without rerunning it

1. Find the ZIP and its checkpoint (see [What a checkpoint records](#what-a-checkpoint-records)).
   Keep the ZIP. Extract a copy into a review folder.
2. Open `OPEN_ME_FIRST.html` if it is there. If the browser blocks local links, use the file browser.
   Then read `manifest.json`, the issue log, the workbook and the triage table. See
   [Reading your results](READING_YOUR_RESULTS.md).
3. Note the program version and the input hash from the manifest.
4. Work in the review copy with a program version that matches the package.
   - `validate` rewrites `package_status.json` in that copy and prints its current findings.
     Save its output, errors and exit status beside the package.
   - `validate` does not replace the earlier `gate_validation.json`.
   - `explain` reads the saved manifests and prints a summary. It adds no receipts and does not
     rerun validation.
   - Keep the old and the current records, each with its date.
5. Anything authored after the ZIP was sealed is not in it. Look for it separately. Confirm it by
   opening the file, not by trusting a filename.

## Move a result to another computer

Copy the ZIP, the checkpoint, any authored work, and the original antiSMASH input. Compare the
SHA-256 on both computers:

```bash
shasum -a 256 '/path/to/archive.zip'
```

Matching hashes mean the bytes are identical. They say nothing about whether the analysis is right.

On the new computer, extract into a fresh folder. Absolute paths in old receipts point at the old
computer and will not resolve. Record the new locations in your checkpoint. Do not edit the old
receipts. Reading a PDF or CSV needs no Python. Running `validate` or any other command needs a
compatible environment; see [INSTALL.md](INSTALL.md).

A patch ZIP contains code and docs, not analysis data. Apply it to a separate copy of the source.
Keep the original checkout.

## Why the output is large

One run keeps both the expanded package and its ZIP, so the package exists twice on disk. The
standard brief and the locus maps add one set of figure files per BGC. On a strain with dozens of
BGCs that is hundreds of files and over a hundred megabytes per run. Nine such runs can pass a
gigabyte before their ZIPs and logs are counted.

If you do not need the brief or the locus maps, turn them off:

```bash
python mamey_run.py run ... --brief none --locus-maps off
```

These two flags remove optional rendering only. The evidence tables and the workbook are still written.

`--capped-session` does more than that, so do not treat it as a rendering switch. Its profile
(in `mamey/cli.py`) sets:
- `--brief none`;
- `--json-evidence off`, which skips the main KCB/RiQ JSON walker. Other record and metadata
  readers can still inspect JSON. Missing channel evidence is never a biological negative;
- `--require-workbook`;
- `--locus-maps off`, but only when maps were left on `auto`. An explicit `--locus-maps on` is kept;
- store-only ZIP compression, unless `MAMEY_ZIP_COMPRESSION` is already set;
- heartbeat lines every 20 seconds during quiet stages, unless `--heartbeat-seconds` is given.

When you need the JSON evidence, leave out `--capped-session` and use `--json-evidence bounded` with
enough runtime. The capped flag overrides that choice (`AGENTS.md`).

## Archive to an external disk or iCloud

1. List what will move, its total size, and what stays local.
2. Copy. Verify the hashes and open one file from the copy.
3. Update your location index.
4. Only then decide, separately, whether to delete the local original.

External disks get unplugged. Cloud files may be placeholders until they are downloaded. Check
that the files are actually present before you start an analysis that depends on them.

External archiving is a separate transfer task. Program workflows can create ZIPs, replace
output files and clean up their temporary files. Check where the chosen command writes before you
run it.

To file a finished package with its SHA-256 and a README record, submit it to a Strain Master. See
[where Mamey outputs land](DATA_HOME.md#where-mamey-outputs-land).

## What a checkpoint records

A checkpoint records:
- the objective;
- input and code hashes and versions;
- exact output paths;
- which stages completed and which failed;
- the settings used;
- unresolved evidence;
- the next action;
- if an assistant kept a transcript, which turns it covers.

A transcript is not a summary; keep both. See
[the shared save-state policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).

## Use the portable handoff builder deliberately

The `handoff` command (module `mamey/handoff.py`) builds one portable ZIP. The ZIP holds:
- the package, under `package/`;
- selected raw region GenBank files, under `region_gbks/`;
- `HANDOFF_README.txt`.

It does not include authored files kept outside the package. It does not include a software
environment.

```bash
python mamey_run.py handoff --package /absolute/review/package \
  --input-zip /absolute/inputs/strain_antismash.zip \
  --out /absolute/handoffs/new_handoff.zip
```

Create the output folder first and choose a new filename. The builder writes to a sibling file,
`<output>.tmp`, then moves it over the destination. An existing file at the destination is
replaced. An existing `<output>.tmp` is deleted first. Do not run two builds to the same name. Do
not point the output at your only earlier handoff.

To hand over several packages together with their catalog, use the private project handoff in
[the project catalog guide](PROJECT_CATALOG.md#export-a-private-archive). Unlike `handoff`, it
refuses an existing output path.

The builder checks that every package file is a real file inside the package folder, not a
symbolic link. It does not run the full
package validator. It does not compare the input ZIP hash with the manifest. Check both on your
review copy before you package. A wrong archive can otherwise supply the wrong region files.

Without `--input-zip`, or when that path does not exist, the command still exits with success. It
writes a package-only archive with an explanatory note. An input ZIP with no matching region
GenBank files also gives zero region files. Check the reported count and the archive contents
against your downstream task. Zero region files do not prove that per-CDS sequence evidence is
unnecessary, or that it is unavailable elsewhere.

`--top-n N` keeps only the region files for the top N ranked rows. It finds their filenames
through the package crosswalk. Use a positive integer. Know these limits:
- When none of the selected rows map to a file, it falls back to all region files.
- When only some selected rows map, the unmapped rows are left out.
- It ranks by `Corrected_rank` and falls back to raw `Rank` when `Corrected_rank` is blank. An
  excluded locus can therefore still be selected.
- Region filenames are reduced to their base names. Check for name collisions.

Review the selected full identities and the included filenames. Do not treat the limit as an
admission gate.

Building a handoff does not grant permission for live BLASTp submission. Sequence staging and any
decision to contact an outside service stay separate.

## Fingerprints have a narrower scope than archive integrity

`python mamey_run.py fingerprint /absolute/review/package --json` prints a fingerprint over eight
listed table and state file suffixes. It converts CRLF line endings to LF. For each suffix it hashes
only the first match in sorted order. It records an absent component as `MISSING`.

Matching fingerprints do not prove that every package byte matches. They do not prove that required
files exist. They do not prove that scientific conclusions agree. For package integrity, use
whole-package checksums and a current validation result. For transfer integrity, compare the
archive SHA-256 separately.
