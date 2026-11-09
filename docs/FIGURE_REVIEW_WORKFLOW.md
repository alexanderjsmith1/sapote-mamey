# Figure Factory owner-review queue

The review queue turns a `FIGURE_MANIFEST.json` into small review pages and a decision table.
It does not draw figures, copy images, choose conclusions or mark a figure ready for publication.

Use it when a figure set is too large to review in one HTML file. The images, plotted data and
captions stay where the figure tools wrote them. The queue adds:

- paginated HTML review pages;
- a TSV decision table;
- a short Markdown index; and
- a receipt (`FIGURE_REVIEW_RECEIPT.json`).

There are two review tools. Use this one to record `KEEP`, `REDESIGN`, `DROP`, `PARK` or
`UNREVIEWED` for each figure in a manifest. To compile owner comments into an action plan, use
the [owner action-plan compiler](FIGURE_OWNER_REVIEW_WORKFLOW.md). It uses different columns
(`figure_set_id`, `owner_comment`, `requested_changes`, `target_use`) and `HOLD` instead of `PARK`.
Nothing converts one table into the other.

## What you need
- A figure root: a folder that holds `FIGURE_MANIFEST.json` and every file it names. The Figure
  Factory atlas builders write this manifest. See [Figure Factory index](figure_factory/README.md).
- In the manifest, a top-level `figures` list. Each entry gives a figure ID, a title, an image, a
  caption and methods file, and an optional data file. Every file path is relative and stays inside
  the figure root. Every file carries its SHA-256.
- A new output folder inside the figure root. Its parent folder must already exist.

Which keys the reader accepts, in order:

| Item | Keys (first one found wins) |
|---|---|
| Figure ID | `figure_set_id`, `figure_id` |
| Title | `title` (required, not empty) |
| Image | `svg`, `png`, `image` (SVG, PNG, JPG or JPEG) |
| Image hash | `svg_sha256`, `png_sha256`, `image_sha256` |
| Caption file | `caption_methods` |
| Caption hash | `text_sha256`, `caption_sha256` |
| Data file | `data_csv`, `data` |
| Data hash | `data_sha256` (required when a data file is named) |

Give one image and its matching hash. Only that image is checked and shown. The reader does not
check a schema version.

Avoid figure IDs that start with `=`, `+`, `-` or `@`, and avoid `#`, `?` and `%` in file names.
The tool protects a leading formula character in the TSV and matches it again on import, but plain
IDs are easier in a spreadsheet, and `#`, `?` and `%` break the HTML links. Do not rename IDs by hand.

## Build a queue

```bash
python tools/build_figure_review_queue.py \
  --manifest FIGURE_ATLAS/FIGURE_MANIFEST.json \
  --figure-root FIGURE_ATLAS \
  --outdir FIGURE_ATLAS/owner_review \
  --page-size 25
```

`--page-size` is 1 to 100. Success exits 0. Open `owner_review/OPEN_FIGURE_REVIEW.html`. Each
figure shows its full caption and methods text below the image. A refusal listed under **When it
refuses** exits 2 and prints a typed code on stderr. Any other failure, such as an unexpected
error, prints a Python traceback and exits 1. In both cases check whether the output folder exists
before you retry. 

Keep the whole figure root together when you move the queue. The pages link to the images by
relative path. Copying only `owner_review` breaks those links.

## Record decisions and rebuild
The page has no save button. The HTML, the receipt counts and the hashes are a snapshot from build
time. They do not change when you edit the TSV.

1. Build the queue.
2. Edit `FIGURE_REVIEW_QUEUE.tsv`. Set `decision` to `KEEP`, `REDESIGN`, `DROP`, `PARK` or
   `UNREVIEWED`. The `decision_note` column is free text. Add a reason for every `REDESIGN`, `DROP`
   and `PARK`. The tool does not require one.
3. Rebuild into a new output folder with `--decisions <your edited TSV>`. The TSV must also sit
   inside the figure root. Save each edited TSV as a new revision.
4. Open the new HTML. Check the row counts.

The decision file needs the columns `figure_id`, `decision` and `decision_note`. A UTF-8 BOM is
fine. On import the tool:
- skips rows with a blank ID and trims every field;
- turns decision codes to uppercase;
- treats an empty cell as `UNREVIEWED`, but treats a cell that holds only spaces as an invalid code;
- matches `figure_id` as written or in its guarded form, and strips the guard apostrophe from
  `decision_note`; and
- refuses duplicate IDs and IDs that are not in the manifest.

## When it refuses
The command stops before it creates the output folder when:
- a path is absolute, leaves the figure root or is missing;
- a file hash is missing, malformed or does not match;
- a figure ID or title is missing, or an ID is repeated;
- the manifest, a caption file or the decision file cannot be read as UTF-8 (`FIGURE_REVIEW_MANIFEST_INVALID`,
  `FIGURE_REVIEW_CAPTION_UNREADABLE`, `FIGURE_REVIEW_DECISIONS_UNREADABLE`);
- a decision is unsupported, repeated or names an unknown figure;
- the page size is outside 1 to 100; or
- the output folder already exists.

If the system cannot create the folder safely, the tool stops with
`FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE`. Choose a new output folder. A run that is cut short can
leave a hidden `.<destination>.stage-*` folder. It is not a finished queue.

## What the receipt and the checks prove
`FIGURE_REVIEW_RECEIPT.json` records the manifest and decision-file hashes, the counts and the
output names. It does not hash the HTML, the index or the TSV. Keep the inputs unchanged while the
build runs, and record the output hashes yourself for a handoff. If you edit a caption or image
after you build the queue, rebuild it.

The checks prove the review pages match the manifest. They do not show the science is right, or
that the owner accepted a figure. The queue also does not fix a weak caption. Send a figure with an
incomplete caption back to its renderer, render into a new root, and review it again.

Source: `mamey/figure_review_queue.py`, `tools/build_figure_review_queue.py`.
