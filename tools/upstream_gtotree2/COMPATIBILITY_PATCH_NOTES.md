# GToTree v2 compatibility patch notes

This technical reference describes the retained [compatibility patch](gtotree2-input-sanity-and-env-compat.patch).

## Target snapshot

The diff headers identify the source tree as `GToTree-toying-with-whole-rewrite`, with source-file
timestamps dated 2026-08-26; modified paths use the local directory name `GToTree-2.0.0-src`.
These directory names and timestamps do not identify a verified upstream release or commit.
The exact upstream commit/archive binding is unavailable in this retained record.

Retained patch SHA-256: `28a6913a4eb4d588960d53e1c87a575c9a0925059d95eff6562b7aebb9eaf558`.

## Patch mechanics

The diff modifies five GToTree Python files:

- `gtotree/utils/misc/data_locations.py` adds a resolver that prefers current data-location environment names and falls back to the legacy names for NCBI assembly and GTDB data. It reports when a fallback is used.
- `gtotree/utils/gtdb/get_gtdb_data.py`, `gtotree/utils/ncbi/get_ncbi_assembly_data.py` and `gtotree/utils/ncbi/handle_ncbi_tax_info.py` use that resolver instead of reading those environment variables directly.
- `gtotree/utils/ncbi/get_ncbi_assembly_data.py` changes the missing-location fatal exit from status 0 to status 1.
- The upstream input preflight module adds an input-format check before downstream work. Malformed FASTA input fails; the size diagnostic is warning-only and does not impose a hard minimum input size.

## Validation scope

The historical local record reports **1294 passed, 1 skipped** with the patch applied.
That result has not been independently reverified against an actual external checkout in this cleanup.
It does not certify applicability to another GToTree revision, a present installation, or an analysis result.
No upstream checkout was fetched, modified or executed for this documentation change.
