# mamey/data/literature — portable genus/family literature knowledge

The Mode B card writer's §5 subsections (`genus_literature`, `family_literature` in
`mamey/modeb_subsections.py`) consume small per-genus (`<Genus>.md`) and per-family
(`_families/<family>.md`) markdown digests as **class-level authoring context** — a
similarity/capacity anchor, never a per-strain identity or product claim. Judgment deferred.

## Public release: the prose digests are not shipped

**This public release ships no literature prose.** The per-genus `<Genus>.md`, the
`_families/*.md` digests, and the full-abstract corpus (`_corpus/literature_corpus.jsonl`) are
**derived from a third-party PubMed/PMC abstract export and are intentionally omitted** — they are
source literature, not engine code, and are not ours to redistribute. The card writer degrades
cleanly: with these files absent the §5 literature subsections simply render empty; nothing else is
affected.

## Regenerating the corpus locally

The fetch/curate tooling and the corpus **metadata** (PMID/DOI index) do ship, so you can rebuild
the knowledge base from your own PubMed access:

- `mamey/data/literature/_corpus/pubmed_ingest.py` — ingest a PubMed/PMC abstract export into
  `literature_corpus.jsonl` (+ an FTS SQLite index).
- `mamey/data/literature/_corpus/curate_kb.py` — curate the per-genus / per-family `*.md` digests
  from that corpus.
- `mamey/data/literature/_corpus/_manifest.json` — the metadata manifest (unique PMIDs, per-file
  entry counts) describing the export the shipped index was built from.

Point the reader at an externally provisioned corpus via `MAMEY_LITERATURE_CORPUS` /
`MAMEY_DATA_ROOT` (see `mamey/literature_lookup.py::corpus_path`) rather than committing abstract
text back into the tree.

Naming: one file per genus, `<Genus>.md`; one file per warhead family, `_families/<family>.md`.
