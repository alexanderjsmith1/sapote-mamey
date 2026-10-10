# Files, storage and handoff

A run produces a folder of evidence, not one spreadsheet. Keep that folder together, keep the
original input beside it, and write down where both are.

## What each file is for

| File or folder | What it is | Keep it? |
|---|---|---|
| The code ZIP or git revision you ran | Identifies the program version | Yes. Note the version and hash. |
| The original antiSMASH result ZIP | The upstream evidence. Some later workflows need it; a sealed package alone supports many reader operations. | Yes, unchanged. Record its SHA-256. |
| Genome FASTA and other reference inputs | Needed for companion workflows (BLAST, trees, ANI) | Yes, if you used them. The package does not contain them. |
| `runs/<ID>/package/` | The delivered evidence, expanded | Yes, as one unit. Do not pick files out of it. |
| `*Complete_Package.zip` | Snapshot archived by the run, with strain/bundle/engine/antiSMASH-profile in its actual filename | Yes. It is made at seal time, so anything authored later is not inside it. |
| `manifest.json` | Index of the package: versions, counts, status | Yes, inside the package. |
| CSV tables and the workbook | The evidence tables you review | Yes. Annotate a copy, not the original. |
| PDFs, PNGs and figure sidecars | Renderings of selected evidence | Keep them with their renderer/input receipts. Regeneration may also need separately supplied archives, configs, databases or figure dependencies. |
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
4. Use a review copy with the source-compatible program version. `validate` normally rewrites
   `package_status.json` in that copy and prints its current findings; capture stdout/stderr and
   exit status beside the package. It does not automatically replace the earlier
   `gate_validation.json`. `explain` reads saved manifests and prints a summary without adding
   receipts or rerunning validation. Keep old and current records with their dates.
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

These two flags remove optional rendering only; the evidence tables and the workbook are still written.

`--capped-session` does more than that, so do not treat it as a rendering switch (`mamey/cli.py`, capped-session
profile):
- `--brief none`;
- `--json-evidence off`: the JSON-derived evidence channel is **not** written. That is an omitted channel, never a
  biological negative;
- `--require-workbook`;
- `--locus-maps off`, but only when maps were left on `auto`; an explicit `--locus-maps on` is kept;
- store-only ZIP compression (unless `MAMEY_ZIP_COMPRESSION` is already set);
- heartbeat lines every 20 s during quiet stages (unless `--heartbeat-seconds` is given).

When you need the JSON evidence, leave out `--capped-session` and use `--json-evidence bounded` with enough
runtime. The capped flag overrides that choice (`AGENTS.md`).

## Archive to an external disk or iCloud

1. List what will move, its total size, and what stays local.
2. Copy. Verify the hashes and open one file from the copy.
3. Update your location index.
4. Only then decide, separately, whether to delete the local original.

External disks get unplugged and cloud files may be placeholders until downloaded. Check that the
files are actually present before starting an analysis that depends on them. External archiving is a separate transfer task. Record and verify the new location
before deciding whether to remove an original. Program workflows can create ZIPs,
replace output files and clean up their temporary files; check the selected command’s
write targets before running it.

## What a checkpoint records

Objective; input and code hashes and versions; exact output paths; which stages completed and
which failed; the settings used; unresolved evidence; the next action; and, if an assistant
kept a transcript, which turns it covers. A transcript is not a summary; keep both. See
[the shared save-state policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).

## Use the portable handoff builder deliberately

Request **Sapote-Mamey portable handoff**, implemented by `mamey/handoff.py` and exposed as `handoff`. It archives the supplied package under `package/`, selected raw region GenBanks under `region_gbks/`, and `HANDOFF_README.txt`. It does not include arbitrary external authored files or a full software environment.

```bash
python mamey_run.py handoff --package /absolute/review/package \
  --input-zip /absolute/inputs/strain_antismash.zip \
  --out /absolute/handoffs/new_handoff.zip
```

Create the output parent first and choose a new filename. The builder replaces an existing destination after writing a fixed sibling `<output>.tmp`; avoid concurrent writers or a destination containing your only prior handoff. It checks package containment but does not run the full package validator or compare the supplied input ZIP hash to the manifest. Verify those bindings on your review copy before packaging. A wrong archive can otherwise supply the wrong region files.

Without `--input-zip`, or when its path does not exist, the command can return success with a package-only archive and an explanatory note. An existing archive with no matching region GenBanks can also produce zero region files. Inspect the reported count and archive contents against your requested downstream task. Zero files are not proof that per-CDS sequence evidence is unnecessary or unavailable elsewhere.

Optional `--top-n N` selects ranked rows and resolves region filenames through the package crosswalk. Use a positive integer. The implementation falls back to all region files when no selected mapping exists; it can also omit partially unmapped selected rows. It falls back from blank Corrected_rank to raw Rank, so the selection is not a guarantee that excluded loci have been removed. Review selected full identities and included filenames rather than treating the limit as an admission gate. Region filenames are flattened to basenames, requiring a collision check for archives that reuse names.

This is packaging, not permission for live BLASTp submission. Sequence staging and any external-contact decision remain separate.

## Fingerprints have a narrower scope than archive integrity

`python mamey_run.py fingerprint /absolute/review/package --json` prints a fingerprint over eight whitelisted table/state suffixes. It normalizes CRLF to LF, hashes only the first sorted match per suffix and records absent components as `MISSING`. Matching fingerprints do not prove every package byte matches, that required files exist, or that scientific conclusions agree. Use whole-package checksums and a current validation result for package integrity, and compare archive SHA-256 separately for transfer integrity.
