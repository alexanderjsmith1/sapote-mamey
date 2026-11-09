# Finding a deliverable and checking what exists

To find a deliverable:

1. Use [the product map](PRODUCT_MAP.md) to choose a workflow.
2. Use [the deliverable menu](DELIVERABLE_MENU.md) to find a named outcome.
3. Use the command guide that owns the outcome to find its output paths.

The menu is a catalog. Its output labels describe what a builder can make. They do not say those files exist in your package. For one run, open the actual files and the phase receipts (the per-step records a run leaves; see [recovery and limits](reader/04_RECOVERY_AND_LIMITS.md)). [Per-mode outputs](PER_MODE_ARTIFACT_SET.md) and [reading your results](READING_YOUR_RESULTS.md) explain what to expect.

## Check what a deliverable needs

```bash
python mamey_run.py deliverables list
python mamey_run.py deliverables explain C01
python mamey_run.py deliverables availability C01 --input-zip EXAMPLE_antismash.zip
```

`list` prints every registered item. `explain ITEM` describes one. `availability [ITEM]` checks whether the inputs for an item are present. All three take `--json`. `availability` also takes `--package`, `--runs-dir`, `--input-zip` and `--locus`.

With no input, `availability C01` prints `C01: INPUT_OR_LOCAL_DEPENDENCY_REQUIRED — antismash_zip`. With an existing zip file given, it prints `C01: READY`.

`READY` means the catalog checks found no missing input for that item. Other states name a missing input or dependency, a judgment step, an authorization for external contact, or a human review. The command exits 0 even when an item is not ready. Read the state on each row. It does not build anything, check the bytes of your files, or grant permission for external work.

The check is shallow:

- A sealed package counts as present if `<package>/manifest.json` exists.
- With `--runs-dir`, it counts `*/package/manifest.json` directly below that folder. It does not search deeper.
- `--input-zip` must start as a ZIP, list an antiSMASH region record (`*.regionNNN.gbk` or `regions.js`), and read that one member back. The rest of the archive is not checked; `inspect` does that.
- `--locus` must have three ` / ` separators and a BGC alias. The four parts are not looked up in any evidence.

## What a command writes into a package

`ingest-receipts` writes Mode B judgment cards into the package's `judgment/` folder and updates the judgment register. Other authoring commands can also write into the package and refresh `post_seal_checksums.txt`. Read the owning command's guide for what it writes. The menu does not promise that your core evidence stays untouched.

## Generated file atlas

[FILE_ATLAS.md](FILE_ATLAS.md) and `FILE_ATLAS.csv` are maps of the source code, not of your results. They list most Python files under `mamey/` and `tools/` with line counts and rough links between them. The atlas skips `__init__.py` files and any path through `data`, `_vendor`, `__pycache__` or a folder whose name starts with a dot. Treat them as a starting point for reading code.

- Links are guessed from module names and text matches. Dynamic imports and duplicate names can distort them.
- An "orphan" label means a file deserves a look. It does not mean the file is dead.
- Counts describe one snapshot. They do not show that code runs or passes tests.

## Reader bundles and request names

[HTML template readers](HTML_TEMPLATE_READERS.md) lists the menu, related-view, portfolio, explorer, next-evidence and reaction-board tools, with their inputs and recovery steps.

For portable interactive pages, request the `render-widgets` builder. Name the source and a separate output folder. [Widget deliverables](WIDGET_DELIVERABLES.md) lists the files it writes and what happens on interruption or overwrite. A gene-table slide deck is a different artifact with its own builder.

Before you ask for any artifact, fix the input and its hash, the format, the profile, the destination and who accepts the result. Keep missing, failed and skipped states as they are. A finished build is not scientific or publication acceptance.
