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

The output directory must not exist. The command validates all inputs before creating
the final directory, stages three files in a sibling temporary directory, and commits by
one rename:

- `OWNER_REVIEW_PLAN.json` — machine-readable plan and input hashes;
- `OWNER_REVIEW_PLAN.tsv` — one row for every manifest figure;
- `OWNER_REVIEW_SUMMARY.md` — compact human review surface.

The plan does not select figures for publication. It preserves the owner's wording,
records unresolved figures as `UNREVIEWED`, and provides stable input for a separately
reviewed rerender or caption-revision step.
