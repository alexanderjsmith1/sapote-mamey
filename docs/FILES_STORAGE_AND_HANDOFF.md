# Files, storage and handoff

A run produces a collection of evidence, not one self-contained spreadsheet. Keep the collection understandable without creating a new top-level folder system: use your existing project location and record the paths in a checkpoint.

## Know which object you have

| Object | Purpose | Keep or regenerate? |
|---|---|---|
| Original code ZIP or source revision | Identifies the program used | Keep the exact source/revision and candidate patch chain |
| Original antiSMASH result ZIP | Upstream evidence for reparsing and new analyses | Keep unchanged, with hash and provenance |
| Genome FASTA / reference inputs | May support separately requested workflows | Keep when used; the extraction package is not guaranteed to contain them |
| Expanded `package/` directory | Working view of the delivered evidence | Preserve as a coherent unit |
| `Complete_Package.zip` | Portable archive created by the run | Verify its actual contents and hash; it may precede later additions |
| `manifest.json` | Package index, metadata and status | Keep within the package; not a replacement for indexed files |
| CSV evidence and workbook | Tables used for review | Preserve originals; annotate a separate review copy |
| PDFs, PNGs and figure sidecars | Presentations of selected evidence | Some can be regenerated, but need source, configuration and renderer version |
| Logs, phase/validation receipts | Explain what ran and what failed | Keep with the attempt, including failures |
| Authored cards, notes and transcripts | Interpretation and decision history | Preserve with scope and coverage; they may live outside the extraction ZIP |
| Python environment and caches | Machine-specific runtime support | Recreate from a dependency record; do not treat as portable research evidence |

Do not delete a file simply because it is absent from this table. Specialized workflows add artifacts with their own contracts. Some files are intentionally mutable after sealing. Check the manifest and the producing workflow before deciding what is redundant.

## Open a saved run without rerunning it

1. Find the complete saved ZIP and its checkpoint. Retain the original archive, then extract it to a chosen review folder.
2. Open `OPEN_ME_FIRST.html` if present; use the file browser if the browser blocks local links. Then read `manifest.json`, the issue log, workbook and triage table as described in [Reading your results](READING_YOUR_RESULTS.md).
3. Record the program version and input hash. Use the compatible source environment for `validate` and `explain`, and retain their new receipts in the review record. These commands can write validation-related artifacts; they are not guaranteed to leave every package byte unchanged.
4. Locate later authored work separately. A ZIP made before that work cannot contain it. Confirm membership, not just a reassuring filename.

## Move a result to another laptop

Choose a destination inside that laptop's existing project layout. Copy the complete archive plus any later authored work, checkpoint and required external-input references. Compare SHA-256 before and after transfer. On macOS/Linux, `shasum -a 256 '/path/to/archive.zip'` prints a content fingerprint. Matching hashes show matching bytes; they do not certify the biological analysis.

Extract into a fresh directory. Recreate a compatible Python environment if execution is needed; reading a PDF or CSV does not require installing every companion tool. Run the compatible validator and inspect issues. Absolute source-machine paths in historical receipts will not automatically point to files on the receiving laptop. Record the new locations in the handoff without rewriting original provenance.

For patch transfer, a review ZIP contains candidate patches and docs, not necessarily the analysis datasets. Apply only missing patches in order on a separate source copy; preserve the original checkout. Do not mix code installation with data extraction.

## Why storage grows

A run can retain an expanded package and a compressed copy; detailed figures add many files. In Round 3, nine corrected standard-brief/locus-map runs produced **5,539 package files, 1,212,092,351 bytes** before counting their separate ZIPs and logs. The entire Round 3 scratch area, including broader attempts and runtime support, occupied approximately **4.76 GB across 18,463 files** at handoff. Those are observed settings-specific costs, not universal per-strain predictions.

Start with explicit `--brief none --locus-maps off` when those presentations are not needed. This limits optional rendering; it does not promise a tiny package or stop required evidence output. Announce the intended file groups before a run and count them afterward.

## Archive without losing the record

Before moving files to a chosen external disk or iCloud destination, list the proposed files, total size and what will remain locally. Copy first, verify hashes and readability, and update the location index. Removal of the originals is a separate decision. An external drive can be disconnected and cloud files may be downloaded only on demand; check availability before starting a dependent analysis. No automatic archival or deletion is installed by this guide.

## A useful checkpoint

Record the objective; input/source hashes and versions; exact output locations; completed and failed stages; selected settings; unresolved evidence; next action; transcript coverage; and file counts/bytes. Keep a transcript distinct from a summary. If an assistant cannot export a complete transcript, state which turns or exports are missing. See [the shared save-state policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).
