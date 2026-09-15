# Files, storage and handoff

A run produces a folder of evidence, not one spreadsheet. Keep that folder together, keep the
original input beside it, and write down where both are.

## What each file is for

| File or folder | What it is | Keep it? |
|---|---|---|
| The code ZIP or git revision you ran | Identifies the program version | Yes. Note the version and hash. |
| The original antiSMASH result ZIP | The upstream evidence. Every later step reads from it. | Yes, unchanged. Record its SHA-256. |
| Genome FASTA and other reference inputs | Needed for companion workflows (BLAST, trees, ANI) | Yes, if you used them. The package does not contain them. |
| `runs/<ID>/package/` | The delivered evidence, expanded | Yes, as one unit. Do not pick files out of it. |
| `Complete_Package.zip` | The same package, zipped by the run | Yes. It is made at seal time, so anything authored later is not inside it. |
| `manifest.json` | Index of the package: versions, counts, status | Yes, inside the package. |
| CSV tables and the workbook | The evidence tables you review | Yes. Annotate a copy, not the original. |
| PDFs, PNGs and figure sidecars | Renderings of selected evidence | Regenerable from the package with the same renderer version. Keep them anyway; re-rendering is slow. |
| Logs and phase or validation receipts | What ran, what failed, how long it took | Yes, including failed attempts. |
| Authored cards, notes, transcripts | Your interpretation | Yes. These usually live outside the package. |
| The Python environment and caches | Machine-specific | No. Recreate from the dependency record. |

A file missing from this table is not therefore disposable. Check `manifest.json` and the
workflow that wrote it before deleting anything.

## Open a saved run without rerunning it

1. Find the ZIP and its checkpoint. Keep the ZIP; extract a copy into a review folder.
2. Open `OPEN_ME_FIRST.html` if it is there. If the browser blocks local links, use the file browser.
   Then read `manifest.json`, the issue log, the workbook and the triage table. See
   [Reading your results](READING_YOUR_RESULTS.md).
3. Note the program version and the input hash from the manifest.
4. Run `validate` and `explain` with the same program version. Both may add receipt files to the
   package. Keep those receipts.
5. Anything authored after the ZIP was sealed is not in it. Look for it separately and confirm
   by opening the file, not by trusting a filename.

## Move a result to another computer

Copy the ZIP, the checkpoint, any authored work, and the original antiSMASH input. Compare the
SHA-256 on both machines:

```bash
shasum -a 256 '/path/to/archive.zip'
```

Matching hashes mean the bytes are identical. They say nothing about whether the analysis is right.

On the new machine, extract into a fresh folder. Absolute paths in old receipts point at the old
machine and will not resolve; record the new locations in your checkpoint without editing the
old receipts. Reading a PDF or CSV needs no Python. Running `validate` or anything else needs a
compatible environment; see [INSTALL.md](INSTALL.md).

A patch ZIP contains code and docs, not analysis data. Apply it to a separate copy of the source
and keep the original checkout.

## Why the output is large

One run keeps both the expanded package and its ZIP, so the package exists twice on disk. The
standard brief and the locus maps add one figure file set per BGC. On a strain with dozens of
BGCs that is hundreds of files and over a hundred megabytes per run. Nine such runs can pass a
gigabyte before their ZIPs and logs are counted.

If you do not need the brief or the locus maps, turn them off:

```bash
python mamey_run.py run ... --brief none --locus-maps off
```

`--capped-session` already sets both. This removes optional rendering only. The evidence tables
and the workbook are always written.

## Archive to an external disk or iCloud

1. List what will move, its total size, and what stays local.
2. Copy. Verify the hashes and open one file from the copy.
3. Update your location index.
4. Only then decide, separately, whether to delete the local original.

External disks get unplugged and cloud files may be placeholders until downloaded. Check that the
files are actually present before starting an analysis that depends on them. Nothing in this
program archives or deletes anything on its own.

## What a checkpoint records

Objective; input and code hashes and versions; exact output paths; which stages completed and
which failed; the settings used; unresolved evidence; the next action; and, if an assistant
kept a transcript, which turns it covers. A transcript is not a summary; keep both. See
[the shared save-state policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).
