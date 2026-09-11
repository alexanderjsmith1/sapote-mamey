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
never replaced. Images are linked with relative locators and are never copied.

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
output directory.

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

