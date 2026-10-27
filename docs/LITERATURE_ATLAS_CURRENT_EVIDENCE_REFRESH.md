# Literature atlas current-evidence refresh

`tools/refresh_literature_atlas.py` updates a legacy per-strain literature atlas with current four-part locus identities and governed report-corpus availability. It preserves the earlier scientific prose as a dated historical layer.

Choose a separate, fresh output folder. The tool refuses an output folder inside the legacy input, but it does not catch an output folder that contains the input or a symlinked subfolder, and it can overwrite files. It rewrites each ranked heading it recognizes by looking up strain plus local alias in the store's `current_locus` table and copying the four-part identity. It trusts the store; it does not recheck package manifests, card bytes or citations. Headings it does not recognize are left unchanged.

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

The output root includes `REFRESH_INDEX.tsv`, `LOCUS_REFRESH_LEDGER.tsv`, `UNBOUND_REPORT_HOLDS.tsv`, and `REFRESH_SUMMARY.json`. The per-strain index records immutable source Markdown and available DOCX SHA-256 values. A `WITHHELD` row is an identity hold, not a negative biological result.

Use one explicitly owned refresh destination. Existing output roots are accepted; same-strain/tag
reports, ledgers and summary files are overwritten. A later WITHHELD report does not remove an older
report file left in that root, so the latest REFRESH_INDEX and hashes govern which artifacts belong
to the current refresh. Markdown can be written before a DOCX failure, and the output directory is
created before all database/report checks complete; no all-output transaction or rollback is promised.
`GENERATED_REVIEW_ONLY` and the copied authority_ceiling are review/provenance labels, not independently
established acceptance. Reuse source artifacts by path/hash; do not copy a full report corpus or store
merely to inspect the refresh contract.
