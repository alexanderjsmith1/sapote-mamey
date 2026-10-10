## Current PDF reader and export scope (.447)

The packet list below is an authoring/delivery requirement, not a claim that the exporter creates every item. The current `mamey/modeb_export.py:449–545` wrapper filters the structure linter to CLAIM_SAFETY findings; it does not require a mature profile verdict, sealed-package validation, complete locus binding or a narrative-versus-table classification. Direct PDF/DOCX helpers are separate paths; `--force` bypasses the wrapper's claim-content lint after review and does not certify evidence.

The wrapper writes selected DOCX/PDF files sequentially alongside source Markdown unless an output directory is supplied. It returns statuses rather than writing this contract's manifest, integrated evidence CSV, wide-table companion or thumbnails. A later failure can leave earlier files written. `--format both` requires both outputs WRITTEN for CLI success; single DOCX can skip for a missing optional dependency without the same CLI failure rule. Preserve existing sealed evidence and use an external, separately authorized output candidate for rendering. Inspect actual pages and complete the required packet before sharing; WRITTEN is not visual QA or scientific sign-off. See [export guide](MODEB_EXPORT_HOOK.md) for current invocation and dependencies.

The original .144 authoring requirement follows unchanged.

---

# Mode B PDF Output Contract — v9.7.144

When a mature Mode B result is exported for sharing, emit a reader-ready packet:

- printable narrative PDF;
- source Markdown;
- integrated evidence CSV/table when available;
- wide-table PDF or CSV for oversized gene tables when needed;
- manifest/receipt with generation status;
- optional render-check thumbnails.

A PDF export is not allowed to be just a table dump unless the user asks for table-only output.
