# Figure owner-review workflow

Figure rendering and scientific selection are separate steps. The renderer produces a
`FIGURE_MANIFEST.json`; the scientific owner records concise decisions in a TSV; this
compiler turns those decisions into a deterministic action plan without changing or
rerendering any figure.

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

The output directory must not exist, and its parent must already exist; the compiler does not create that parent. Select a new destination outside source evidence and the code bundle. It validates the required manifest/decision structure before output staging, creates a unique sibling temporary directory, and publishes three files by one ordinary rename:

- `OWNER_REVIEW_PLAN.json` — machine-readable plan and input hashes;
- `OWNER_REVIEW_PLAN.tsv` — one row for every manifest figure;
- `OWNER_REVIEW_SUMMARY.md` — compact human review surface.

The plan does not select figures for publication. It transports the owner's decisions with whitespace trimmed and decision codes uppercased; spreadsheet-safe TSV cells may receive a leading apostrophe, while the Markdown summary escapes table separators. Keep the original decision TSV and its hash as the authoritative wording. Use single-line comment/change fields and the exact UTF-8 tab header above; do not substitute a spreadsheet export with a BOM or reordered columns. Unknown/duplicate figure IDs are refused. Omitted IDs become `UNREVIEWED`, and output rows follow manifest order. Use the compiled plan as input for a separately reviewed rerender or caption-revision step.

Keep manifest and decisions unchanged throughout compilation: the source reads them before calculating their receipt hashes, with no final comparison against the consumed bytes. Ordinary caught staging/publication errors remove the temporary directory. A process interruption can leave a sibling stage, and a concurrent writer can create the final destination after preflight; ordinary rename can replace an empty competing directory on POSIX. Preserve any stage/previous plan and diagnostics, then choose a new destination for recovery after resolving the cause. The plan contains input hashes but no output-file hashes or self-hash; retain those separately. A changed decision file requires a newly bound plan, not a claim that the old receipt covers it.

## Keep the two review schemas separate

The [paginated review queue](FIGURE_REVIEW_WORKFLOW.md) uses `figure_id`, `decision`, and `decision_note`, including `PARK` and explicit `UNREVIEWED`. This compiler requires `figure_set_id`, `decision`, `owner_comment`, `requested_changes`, and `target_use`; supplied decisions accept only `KEEP`, `REDESIGN`, `DROP`, or `HOLD`. `UNREVIEWED` is generated only for manifest rows omitted from the decisions file. Do not feed the queue TSV into this compiler or automatically translate `PARK` into `HOLD`. A human must bind the figure IDs and retain the original review meaning in a documented conversion.

The compiler requires a nonempty figure list, unique safe figure IDs, nonblank titles and three locator strings (`svg`, `data_csv`, `caption_methods`). It records the manifest's schema label but does not require a specific schema/version. Locator checks replace backslashes, reject POSIX absolute paths and `..` components, and otherwise only inspect strings: they do not establish containment, reject every drive/URI-shaped value or prove portable existing assets. Resolve that scope with the owning renderer before adopting or following a locator. It hashes the manifest and decision file, but does **not** open or hash-check the SVG, data or caption named in that manifest. Its exit 0 / printed `PASS` means the action plan compiled, even when all figures are unreviewed or held. Use a matching artifact-integrity check and rendered inspection separately; retain the original manifest, decisions and plan together. Invalid decisions/output errors return 2.

Source owners: `tools/compile_figure_owner_review.py:77–110,113–170,233–242`; queue schema `mamey/figure_review_queue.py:30–41,124–145`.
