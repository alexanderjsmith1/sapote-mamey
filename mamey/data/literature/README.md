# Portable literature data — consumers and missingness

This CODE cut retains literature tooling and metadata. Per-genus prose, family digests and the full abstract corpus were intentionally omitted from the public cut. Their absence means unavailable local context, not absence of literature or negative biological evidence. Provisioning, source permissions and scientific citation verification remain separate work; this documentation does not authorize retrieval or redistribution.

## Two different reader paths

`mamey/literature_lookup.py::corpus_path` resolves the registered external literature directory via `MAMEY_LITERATURE_CORPUS` / `MAMEY_DATA_ROOT`, then appends `literature_corpus.jsonl`, with a legacy in-tree fallback. These settings locate the JSONL corpus; they do **not** automatically redirect the Markdown genus/family readers.

`mamey/modeb_subsections.py::genus_literature(pkg, lit_dir=None)` checks a supplied digest directory and then this in-tree directory. `family_literature(pkg, bgc_id, lit_dir=None)` uses a supplied family directory or this directory's `_families/`. The genus reader returns at most eight selected bullets; the family reader at most five per matched family. Their source text currently reports in-tree paths even when an external `lit_dir` was consumed. Preserve the actual supplied path/hash in the evidence receipt rather than trusting that displayed attribution.

Missing/unreadable digest files can produce empty subsections. That is a renderer fallback, not selected-profile literature completeness. Use the [Mode B profile guide](../../../docs/MODEB_PROFILE_MATRIX.md) and [literature workflow](../../../docs/LITERATURE_SEARCH_PROTOCOL.md) to record typed missing/held channels and the required source bindings. An alias-based helper lookup does not independently establish full locus identity.

The JSONL reader skips malformed JSON lines, accepts the last record for a repeated PMID and caches one load. Missing input returns an empty dictionary; successful loading does not verify citations, source authenticity or completeness. Record the resolved path, SHA-256 and parsed/input counts. If a corpus or environment changes in a running process, do not assume cached content is refreshed; explicitly use a fresh process or clear the documented load_corpus cache.

## Local rebuild tools

See [corpus rebuild scope](_corpus/README.md) for the actual offline input format, overwrites, output set and recovery. `pubmed_ingest.py` consumes supplied search-results PDFs; it does not fetch PubMed. `curate_kb.py` creates heuristic digests from supplied JSONL; it does not verify the scientific claims it summarizes. Prefer fresh external destinations and reference original evidence in place by path and SHA-256. Never replace source evidence simply to update a digest.
