# Figure Factory owner-review queue

The review queue turns an existing `FIGURE_MANIFEST.json` into small, paginated owner-review
pages. It does **not** render figures, copy images, select scientific conclusions, or mark a
figure as publication-ready.

## Why this exists

Large atlases become difficult to review when hundreds of images are placed in one HTML file or
copied into successive dossiers. The queue keeps each rendered image, plotted-data file, and
traveling caption/method file in its original Figure Factory output. It adds only:

- a paginated HTML review surface;
- a TSV decision queue;
- a compact Markdown index; and
- a deterministic machine receipt.

## Required source structure

`--figure-root` is the portable root containing both `FIGURE_MANIFEST.json` and every referenced
image, caption/method file, and optional data file. Manifest locators must be relative, remain
inside that root, and resolve to regular files. Every referenced image and caption/method file,
and every referenced optional data file, must carry its expected SHA-256 in the manifest. Missing,
malformed, and mismatched digests are refused before any review output is created.

The output directory must be a new descendant of the same figure root. Existing directories are
never replaced. Images are linked with relative locators and are never copied. Keep the complete figure-root layout when transferring the queue; copying only `owner_review` breaks the source links.

The reader takes identity from nonempty `figure_set_id` before `figure_id`, and the image from `svg` before `png` before `image`; supported suffixes are SVG, PNG, JPG and JPEG. Image digest selection independently prefers `svg_sha256`, then `png_sha256`, then `image_sha256`. Supply one unambiguous chosen image/digest pair, or reconcile all populated fields before invocation. Only the chosen image is checked/displayed. Optional data uses `data_csv` before `data`; caption digest uses `text_sha256` before `caption_sha256`. There is no required manifest schema-version check or verification of alternate images.

Use stable, non-formula-leading figure IDs and simple portable asset filenames. TSV output applies spreadsheet formula escaping, including to figure IDs and notes, while decision import does not reverse that escaping. An admitted ID beginning with `=`, `@` or another formula-leading sequence can therefore change in the generated TSV and fail to rejoin on the next import. HTML links escape markup but do not URL-encode reserved filename characters such as `#`, `?` and `%`; such a valid local locator can fail in the browser. Preserve original names/evidence and hold affected queue output for a source-owner correction rather than silently renaming identities.

## Build a queue

```bash
python tools/build_figure_review_queue.py \
  --manifest FIGURE_ATLAS/FIGURE_MANIFEST.json \
  --figure-root FIGURE_ATLAS \
  --outdir FIGURE_ATLAS/owner_review \
  --page-size 25
```

Open `owner_review/OPEN_FIGURE_REVIEW.html`. Record one of `KEEP`, `REDESIGN`, `DROP`, `PARK`,
or `UNREVIEWED` in `FIGURE_REVIEW_QUEUE.tsv`. The note column is free text. To rebuild a new
queue while retaining decisions, supply the prior queue with `--decisions` and choose a new
output directory. HTML pages contain a build-time snapshot of the decisions and notes; editing the TSV does not refresh the displayed cards or saved receipt counts. Retain the edited TSV as a new decision revision and rebuild into a fresh directory before relying on the HTML/counts as a current review surface. The page has no browser save control.

Decision import requires `figure_id`, `decision`, `decision_note` columns and supports a UTF-8 BOM. It ignores blank-ID rows, trims fields and uppercases decision codes, rejects duplicate nonblank IDs and refuses unknown IDs. Whitespace-only decision cells become an empty invalid code, whereas genuinely empty cells default to `UNREVIEWED`. Retain the manifest-bound IDs unchanged and inspect row counts after import.

## Caption and comparison requirements

The review pages display the complete traveling caption/method file below each figure. The
source renderer remains responsible for the Figure Factory caption contract: source and release,
unit of analysis, inclusion/exclusion roles, denominators and typed missingness, transformation,
visual grammar, statistics, comparison design, genus control, contradictions, and interpretation
boundary. External benchmarks remain optional and default-off; they do not enter study-cohort
denominators or percentages.

The queue does not repair a weak caption. A figure whose source caption is incomplete must be
redesigned at the renderer or figure-recipe owner, then rendered into a new source root and
reviewed again.

## Refusal behavior

The command refuses before creating the output directory when:

- a locator is absolute, escapes the figure root, or is missing;
- a referenced artifact hash is missing, malformed, or does not match;
- figure identity is missing or duplicated;
- a decision is unsupported, duplicated, or refers to an unknown figure;
- the page size is outside 1–100; or
- the destination already exists.

These checks establish review-surface integrity only. They do not establish biological
validation, owner acceptance, thesis acceptance, integration, release, or publication readiness.

## Decision-file scope and handoff

The optional `--decisions` file must also be inside `--figure-root`. The chosen output's parent directory must already exist inside that root. An empty decision cell becomes `UNREVIEWED`; `decision_note` may be blank even for `REDESIGN`, `DROP`, or `PARK`, so mechanical queue validation does not establish that an actionable owner explanation was supplied. Preserve the note and add the required rationale before passing a decision downstream.

[The owner action-plan compiler](FIGURE_OWNER_REVIEW_WORKFLOW.md) has a different manifest/TSV contract: `figure_set_id`, `owner_comment`, `requested_changes`, `target_use`, and `HOLD` instead of `PARK`. There is no automatic schema conversion here. Keep each review revision in a new output directory, with the matching manifest and source hashes; editing a caption/image after queue creation invalidates its recorded binding.

The builder uses Python and bundled helpers; it does not require a plotting or document-rendering engine. It writes a private sibling staging directory and publishes the whole queue with a platform no-replace primitive. Windows rename, Darwin `renameatx_np`, or Linux `renameat2` support is required; an unavailable primitive produces `FIGURE_REVIEW_OUTPUT_COMMIT_UNAVAILABLE`, rather than permitting a replacing rename. A caught build exception removes its staging directory; interruption can leave a hidden `.<destination>.stage-*` sibling. Preserve any such partial evidence, inspect it and choose a fresh output rather than treating it as a resumable completed queue.

`FIGURE_REVIEW_RECEIPT.json` binds the manifest and optional decision-file hashes, records counts and lists output names; it does not hash generated HTML/index/TSV files. The TSV records selected source artifact digests. Caption text and decisions are read before their later hash operations, and there is no final frozen-input recheck. Keep manifest, decision TSV and referenced artifacts unchanged throughout a build; record the queue's output/receipt hashes separately for a handoff. The CLI prints the receipt and exits 0 on success; typed refusals print status/code on stderr and exit 2. Other I/O failures can propagate as exceptions, so inspect exit status and partial artifacts rather than expecting every failure to have the same structured report.

Source owners: `mamey/figure_review_queue.py:1–492` and `tools/build_figure_review_queue.py:1–46`.
