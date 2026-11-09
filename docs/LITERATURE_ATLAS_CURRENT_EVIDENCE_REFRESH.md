# Literature atlas current-evidence refresh

`tools/refresh_literature_atlas.py` updates a legacy per-strain literature atlas with current four-part locus identities and governed report-corpus availability. It preserves the earlier scientific prose as a dated historical layer.

This is a maintainer tool. It is not a step in a normal run. Use it only if you hold a set of older per-strain atlas reports (the legacy input) and an evidence store (a SQLite file) built for the same strains; the four-part identity is the strain, full contig, region and BGC alias. The legacy reports and the SQLite store come from the maintainers of the report set; this page does not describe how to build them. Choose a separate, fresh output folder. The tool refuses an output folder inside the legacy input, but it does not catch an output folder that contains the input or a symlinked subfolder. It refuses to replace any output file that already exists. It rewrites each ranked heading it recognizes (`## Rank <n>: <strain> <BGCnnn> - <label>`) by looking up strain plus local alias in the store's `current_locus` table and copying the four-part identity. It trusts the store; it does not recheck package manifests, card bytes or citations. A `## Rank` heading in any other form is held as `UNRECOGNIZED_RANK_HEADING`, and a report with no ranked heading at all is held as `NO_RANKED_HEADINGS`; either way that strain's report is `WITHHELD`, not generated. A generated report's introduction states how many recognized ranked loci it binds.

The supplied SQLite evidence store must contain `metadata`, `current_locus`, `owner_record`, `locus_binding`, and `document`. Its `metadata.authority_ceiling` value is copied into every refreshed report. Database presence never establishes scientific acceptance, product identity, production, activity, or owner acceptance.

Markdown generation uses only the Python standard library:

```bash
python tools/refresh_literature_atlas.py \
  --legacy-strain-reports /path/to/legacy/strain_reports \
  --evidence-store /path/to/governed_reports.sqlite \
  --output-root /path/to/new/output \
  --package-label "the checksum-bound current package manifests" \
  --artifact-tag CURRENT_R001
```

Add `--emit-docx` when every source Markdown report has a paired DOCX and `python-docx` is installed. The legacy DOCX maps remain embedded; the contents table and ranked headings receive current exact-locus identifiers.

The output root includes `REFRESH_INDEX.tsv`, `LOCUS_REFRESH_LEDGER.tsv`, `UNBOUND_REPORT_HOLDS.tsv`, and `REFRESH_SUMMARY.json`. The per-strain index records immutable source Markdown and available DOCX SHA-256 values, and, separately, `markdown_sha256` and `docx_sha256` for each report this run generated. `UNBOUND_REPORT_HOLDS.tsv` gives the hold reasons in `unresolved_reasons`. A `WITHHELD` row is an identity hold, not a negative biological result. A good run writes these four files and exits 0.

## Before you rely on the output

- Use one fresh output folder for each refresh. The tool refuses before writing anything if any of its output files already exists, so earlier outputs are kept as they were.
- `REFRESH_INDEX.tsv` and its hashes say which files belong to the current refresh. Read them, not the folder listing. Check each generated file against its `markdown_sha256` or `docx_sha256` before you use it.
- If Markdown is written and the DOCX step then fails, the Markdown stays. No rollback happens.
- `GENERATED_REVIEW_ONLY` and the copied `authority_ceiling` are labels. They are not acceptance.
- Point the tool at the source files in place. Do not copy a whole report set or store just to inspect it.
