# Offline corpus rebuild contracts

The public CODE cut retains tools and metadata here; the historical full abstract JSONL and curated prose are not included. A metadata manifest describes a past export and does not prove the corresponding corpus is currently present or verified. Supplied literature remains source evidence with its own permissions and provenance.

## Ingest supplied PDFs

Declared interface, from the bundle root in the intended environment:

```bash
python mamey/data/literature/_corpus/pubmed_ingest.py /absolute/path/to/search-results-pdfs /absolute/path/to/new-corpus-directory
```

Owner: `pubmed_ingest.py::ingest`. It requires pypdf, searches only immediate lowercase `*.pdf` children and parses the expected PubMed search-results text patterns. It is not a general full-paper importer or network downloader. Within that invocation it deduplicates PMID and may prefer a longer abstract; it rebuilds from the PDFs supplied now rather than merging an existing JSONL corpus. Confirm the intended input PDF roster and hashes first. Missing/empty input can produce an empty corpus and normal completion.

It creates the destination and directly rewrites `literature_corpus.jsonl`, deletes an existing `literature_corpus.sqlite`, builds a replacement FTS5 database (plain-table fallback), then writes `_manifest.json`. These are separate operations without a whole-set transaction or backup. Counts/query labels/source basenames in the manifest are not input/output hash bindings or DOI/full-text verification. Use a fresh output directory, preserve earlier evidence in place and check the entire expected set after a failure; do not use the old source corpus directory as the output.

## Curate supplied JSONL

```bash
python mamey/data/literature/_corpus/curate_kb.py /absolute/path/to/corpus.jsonl /absolute/path/to/new-literature-directory --only TARGET_A,TARGET_B
```

`--only` names configured target keys from `_TARGETS`, not arbitrary taxa/categories. Unknown keys can select nothing without a failure status. The tool loads each JSONL line with json.loads, creates `_families/` and overwrites each selected digest directly. This is a keyword/heuristic index; it does not prove relevance, product identity or primary-evidence verification. A malformed line or later write failure can interrupt a partial output set; inspect selected target files and source/output hashes independently.

Digests are consumed via the separate genus/family paths described in [the literature data guide](../README.md). Setting an external JSONL corpus directory does not redirect those readers. Compare actual resolved inputs and displayed source text; the current digest renderer can show an in-tree attribution for externally supplied digest files.

Ingestion, curation, downloads and scientific acceptance are separate steps. Record the current producer and source evidence for each, and preserve original inputs.
