# Literature atlas current-evidence refresh

`tools/refresh_literature_atlas.py` updates a legacy per-strain literature atlas with current four-part locus identities and governed report-corpus availability. It preserves the earlier scientific prose as a dated historical layer.

The tool is additive and fail-closed. It emits a strain report only when every legacy rank binds one-to-one through `current_locus` using the report strain plus its legacy local alias. Owner-card data is admitted only when `owner_record.exact_identity` equals the fresh four-part identity. A bare or alias-only join is never treated as current evidence.

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
