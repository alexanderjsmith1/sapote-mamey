# Mode B PDF Output Contract — v9.7.144

When a mature Mode B result is exported for sharing, emit a reader-ready packet:

- printable narrative PDF;
- source Markdown;
- integrated evidence CSV/table when available;
- wide-table PDF or CSV for oversized gene tables when needed;
- manifest/receipt with generation status;
- optional render-check thumbnails.

A PDF export is not allowed to be just a table dump unless the user asks for table-only output.
