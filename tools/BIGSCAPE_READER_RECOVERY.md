# Checking BiG-SCAPE reader outputs

These shipped tools read BiG-SCAPE database content and write review artifacts. Their exit status and output names have narrower meanings than a completed, accepted cohort analysis. Start with [the cohort SOP](../docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md) and [the cohort workflow](../docs/BIGSCAPE_GCF_WORKFLOW.md).

## Before opening a database

Bind an existing database path, its SHA-256, source roster, exact completed run and cutoff. Check its recorded completion and integrity evidence before rendering or calculating family denominators. A populated family table alone does not prove run completion. Preserve a partially failed database and logs as incomplete evidence until the cause and completed membership scope are established.

The shipped `bigscape_family_verdicts.py`, `bigscape_family_figures.py` and `bigscape_clinker_html.py` use ordinary `sqlite3.connect(path)`, not a read-only connection. A misspelled nonexistent path can create an empty database before a query fails. Verify the database exists first and work from an authorized disposable copy when immutable originals must be preserved.

Their family queries filter by cutoff but do not offer an exact completed-run ID selector. If the database contains multiple run memberships at the same cutoff, do not assume these readers isolate the intended run. Resolve a reviewed snapshot with the intended membership scope through the governed export workflow, or retain a scope hold. Do not silently join or collapse memberships across runs.

## Select the intended namespace

The default query regex is `^([A-Za-z]+-\d+)_`. Its first capture group supplies the query strain. A staged filename that does not match can be treated as a reference, changing query-private verdicts and counts. Bind the staging manifest and choose an explicit matching regex when the query naming scheme differs.

Reference prefixes take precedence over query classification in the verdict and clinker readers. Defaults are `SID_` and `TYPE_`. Supplying any `--layer-prefix` values replaces those defaults rather than extending them; include every intended reference prefix. The renderer similarly replaces its default reference prefixes when explicit `--reference-prefix` values are supplied.

`QUERY_PRIVATE_REFERENCE_DARK` and other QUERY_PRIVATE values describe family composition in the selected panel. They are not confidentiality labels, release permission or universal novelty. `QUERY_PRIVATE_MIBIG_MATCHED` includes a MIBiG member; private here means no other reference layer, not “query only.” Report the full verdict and its cutoff/reference scope.

## Exact GBK and inventory bindings

`render_gcf_synteny_tree.py` resolves database members by GBK basename, taking the first existing match among `--gbk-dir` folders. It does not compare that file's bytes with an input hash. Different assemblies or antiSMASH runs can have the same basename. Avoid overlapping candidate folders and verify every selected member against the run's staged-file hash manifest before interpreting its gene architecture.

The renderer's identity loader indexes `Source_GBK` by basename across all supplied inventory CSVs. A later row with the same basename overwrites the earlier binding. The row check compares contig names when present, but does not independently verify strain identity, stored region equality or GBK content hashes. A missing identity-hold label therefore does not prove a complete exact-locus match. Restrict inventories to the selected sources, check basename collisions and independently reconcile `strain / full node-or-contig / region / BGC alias` before accepting the figure. Keep conflicts on hold; do not choose an alias from the last-loaded row.

## Verdict output

`bigscape_family_verdicts.py` writes the requested TSV and `<out>.placement.tsv`. It can return 0 with no query-containing families. Read the row count and reconcile expected query regions rather than treating an empty header-only file as completed coverage.

The placement table counts all region records in the database and those with family rows at each observed cutoff. Its `singleton_records` column is computed as total minus placed; it does not independently demonstrate that every unplaced record was a biologically or computationally verified singleton. In an incomplete or mixed-scope database, preserve “unplaced” as the observed state until exclusions and completion are reconciled.

## Batch figure output

`bigscape_family_figures.py` catches individual renderer failures, writes FAILED rows and continues. Its main function returns 0 even when selected families fail. Inspect `private_families/INDEX.tsv`, each focus strain's `FAMILY_FIGURES_INDEX.tsv`, `BGC_TO_FAMILY_FIGURE.tsv` and the log. Reconcile requested, rendered, failed and unplaced counts. A blank figure path is unresolved output, not a successful figure.

The focus mapping's text “singleton at every cutoff” actually means no family was found at the requested main cutoff and optional fallback cutoff. It does not enumerate every cutoff stored in the database. Report the exact checked cutoffs and retain a completion/scope hold when appropriate.

`--max-tips` is a target for a pruned display, not a hard ceiling. The renderer retains all query and MIBiG tips; that retained set can exceed the requested maximum. Display pruning does not change full family membership denominators. Inspect page size and labels rather than assuming 40 selected tips always fit.

## Clinker HTML and PDF output

`bigscape_clinker_html.py` requires a nonempty render selection (`--family` or `--focus`) to produce family pages. No selection can return 0 with no pages. Selected families with fewer than two renderable members are recorded as skipped. Hidden tracks from `--min-genes` remain database members; a display filter is not an exclusion from the family.

Without `--chrome`, OK in `CLINKER_INDEX.tsv` means HTML output; it does not mean a PDF was made. With `--chrome`, PDF failures are recorded as PDF FAILED while the script can still return 0. Inspect every requested row, the PDF column and actual output.

PDF printing needs `pypdf` for validation (the documents extra) and an existing compatible Chrome/Chromium binary. The helper refuses an existing PDF path. Use a fresh output directory rather than retrying over old PDFs. It checks a complete single-page PDF containing the expected family title; this is a completion check, not visual inspection or scientific validation. The generated temporary print HTML is removed afterward, while HTML and incomplete diagnostic outputs may remain.

## Recovery receipt

Record the selected database/hash/run/cutoff, staging namespace and prefixes, intended family/strain selection, expected row counts, actual output statuses and files, failed/skipped reasons and next bounded correction. Preserve prior outputs before a retry. Do not replace a failed or skipped output with a prose success claim.
