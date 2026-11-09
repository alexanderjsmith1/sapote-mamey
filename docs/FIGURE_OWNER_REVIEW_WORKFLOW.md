# Figure owner-review workflow

Figure rendering and scientific selection are separate steps. You record concise decisions in a TSV; this
compiler turns those decisions into a deterministic action plan without changing or
rerendering any figure.

## What you need

A `FIGURE_MANIFEST.json` from a figure-set run. `python mamey_run.py codex-figure-sets` writes one in each tranche folder (see `python mamey_run.py codex-figure-sets --help`). The [Figure Factory index](figure_factory/README.md) covers the figure-set tools. The manifest needs a top-level `figures` list. Each entry needs `figure_set_id`, `title`, `svg`, `data_csv` and `caption_methods`; the last three are relative file paths. If you want paginated review pages instead of a plain action plan, use the [review queue](FIGURE_REVIEW_WORKFLOW.md).

## Decision file

Use this exact header:

```text
figure_set_id	decision	owner_comment	requested_changes	target_use
```

Allowed decisions are `KEEP`, `REDESIGN`, `DROP`, and `HOLD`. Missing figure IDs remain
`UNREVIEWED`; they are never silently treated as accepted. `REDESIGN` requires both an
owner comment and explicit requested changes. `DROP` and `HOLD` require a comment.

Example:

```text
figure_set_id	decision	owner_comment	requested_changes	target_use
F03a	KEEP	Strong domain-level comparison		main paper
F04f	REDESIGN	Comparison should be genus-aware	Use within-genus groups and show group n	appendix
F08b	DROP	Single zero point is not informative		
```

## Compile the review

```bash
python tools/compile_figure_owner_review.py \
  --manifest path/to/FIGURE_MANIFEST.json \
  --decisions path/to/owner_decisions.tsv \
  --outdir path/to/new_owner_review_plan
```

Success prints `{"status": "PASS", ...}` and exits 0. An output directory that already exists exits 2 with `OUTPUT_EXISTS`. The output directory must not exist, and its parent must already exist; the compiler does not create that parent. Select a new destination outside source evidence and the code bundle. It validates the required manifest/decision structure before output staging, creates a unique sibling temporary directory, and publishes three files by one ordinary rename:

- `OWNER_REVIEW_PLAN.json` — machine-readable plan and input hashes;
- `OWNER_REVIEW_PLAN.tsv` — one row for every manifest figure;
- `OWNER_REVIEW_SUMMARY.md` — compact human review surface.

The plan does not select figures for publication. It carries your decisions over with whitespace trimmed and decision codes in uppercase. Keep the original decision TSV as the authoritative wording. Use single-line comment and change fields and the exact tab-separated header above, saved as UTF-8 without a BOM and with the columns in that order. Unknown or duplicate figure IDs are refused. Omitted IDs become `UNREVIEWED`, and output rows follow manifest order. Use the plan as input for a separate rerender or caption-revision step.

Keep the manifest and decisions unchanged while the compiler runs, and keep them with the plan: the plan records their hashes but not the hashes of its own files. A changed decision file needs a new plan. If a run is interrupted, a temporary sibling folder can remain. Keep it, fix the cause and choose a new output folder.

## Keep the two review schemas separate

The [paginated review queue](FIGURE_REVIEW_WORKFLOW.md) uses `figure_id`, `decision`, and `decision_note`, including `PARK` and explicit `UNREVIEWED`. This compiler requires `figure_set_id`, `decision`, `owner_comment`, `requested_changes`, and `target_use`, and accepts only `KEEP`, `REDESIGN`, `DROP` or `HOLD`. `UNREVIEWED` is generated only for manifest rows omitted from the decisions file. Do not feed the queue TSV into this compiler, and do not translate `PARK` into `HOLD` automatically. A person must match the figure IDs and keep the original review meaning in a documented conversion.

## What a pass means

The compiler needs a nonempty figure list, unique safe figure IDs, nonblank titles and three file paths per figure (`svg`, `data_csv`, `caption_methods`). Each path must be relative. A path that starts with `/` or `\`, a drive-qualified path such as `C:/x` or `C:x`, any path whose first part holds a `:`, and any path with a `..` part are refused with `MANIFEST_LOCATOR_UNSAFE`. It hashes the manifest and the decision file. It does not open the SVG, data or caption files the manifest names. Exit 0 and the printed `PASS` mean the action plan compiled, even when every figure is unreviewed or held. Check the figure files and look at the rendered images separately.
