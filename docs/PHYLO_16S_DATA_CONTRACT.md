# Portable 16S data workflow

These tools prepare candidate sequence data and screening evidence. They do not establish strain identity, taxonomic membership, gene boundaries, biological orientation, novelty, tree validity, or accepted strain merges.

## Additive databases and input selection

Select every ingest source explicitly. The builder requires `--db` for a new output and at least one source option. Transformations use an existing `--db` and a new `--out-db`. Existing output files and symlinks are refused. Output parent directories must already exist. No command updates an external asset registry.

```bash
python tools/phylo_16s_build_db.py --db output/initial.sqlite --authoritative-fasta inputs/queries.fasta
python tools/phylo_16s_build_db.py --db output/references.sqlite --refseq-blastdb inputs/reference_db
python tools/phylo_16s_fetch.py --db output/initial.sqlite --out-db output/fetched.sqlite --source pdf_candidate
python tools/phylo_16s_esearch.py --db output/initial.sqlite --out-db output/search.sqlite --sets moss
python tools/phylo_16s_rank.py --db output/fetched.sqlite --out-db output/ranked.sqlite
python tools/phylo_16s_audit_merges.py --db output/ranked.sqlite --out-db output/audited.sqlite
```

The first two commands illustrate separate source selections; include both source options in one build to combine them. The fetch command processes only pending records of the specified source. A query-only database may have no pending fetch records. Other builder inputs are `--nontype-dir`, `--reference-metadata-dir`, `--pdf-hits`, and `--provenance`. Source omission is intentional; a selected missing source is an error. Rebuilding sets requires `--sets-only --input-db INPUT --db NEW_OUTPUT`.

Inputs must be closed, checkpointed SQLite snapshots without WAL or journal sidecars. Transformations use an in-memory copy and publish a completed database with an `operation_event` receipt. Input hashes are checked before publication. Memory use includes the database copy and serialized output; large stores require adequate memory and separate performance validation.

All CLI dry runs validate inputs and display plans without publishing files or running network/BLAST/MAFFT operations. Database dry runs may read an in-memory copy. Dry-run counts that would require remote operations remain unmeasured.

## Sequence and accession identity

FASTA records require unique first-token identifiers, a sequence, and ungapped IUPAC DNA symbols. Sequence normalization is uppercase; SHA-256 binds sequence content. Distinct biological records with identical sequence content remain distinct when their source identities differ. Duplicate accession identities in one ingest source, conflicting accession versions, and conflicting sequences at a shared accession are held for explicit reconciliation.

Authoritative FASTA records without accession provenance receive internal `LOCAL:` keys. Their accession field remains missing. A provenance TSV must include `strain`; assigning an accession also requires its exact version and a matching `sequence_sha256`. Optional metadata columns are `organism_as_deposited`, `host`, `isolation_source`, `geo_loc_name`, `collection_date`, and `lat_lon`. These are operator-supplied observations.

Reference directories use `*_nontype_16S.fasta`; reference metadata uses `*/*_nontype_meta.tsv`, keyed by exact `accession.version`. Metadata columns consumed are `accession`, `isolation_source`, and `geo`. Saved-hit TSV inputs use `accession`, `subject`, `subject_len`, `strain`, and `pct_identity`. Missing or invalid percent identities never become zero-valued measurements.

The legacy database column `acc_base` also stores local internal keys; `acc_version` is always missing for these. Panel metadata includes a separate `record_key` and an empty `accession` for local query records. Local keys never appear as deposited accessions in labels.

## Remote retrieval and metadata

Fetch binds every returned record once to a requested accession and, where requested, its exact version. Unexpected, duplicate, mismatched, malformed, or truncated returned records hold that batch. Missing requested records remain `NOT_RETURNED` with cause unknown. Some successes may be published to a new database; any held request produces a nonzero CLI exit and `PARTIAL_WITH_HOLDS` in its receipt. Known whole-genome records are held before download for separately bound extraction. Unsupported returned records are not admitted as standalone 16S candidates.

GenBank parsing requires optional Biopython. It reads the source feature and wrapped qualifiers, verifies primary ACCESSION/VERSION and declared sequence length, and preserves lineage without assigning taxonomic ranks from name suffixes. Geographic comma order does not establish administrative levels. Missing qualifiers remain missing. A culture-collection identifier does not establish type status. BLAST ingest marks type scope only with the explicit `--refseq-type-material` operator declaration.

Raw GenBank cache files are named by content hash under the selected input database's adjacent `gb_cache/INPUT_DATABASE_SHA256` directory. `--cache-dir` or `SAPOTE_16S_GB_CACHE` selects a different cache base; the database hash still namespaces it. `--no-cache` creates no cache directories or files. Existing content-addressed cache files must match their names.

ESearch is complete only when returned unique IDs equal its reported count. Over-limit or incomplete searches are held. ESummary must map each requested UID to exactly one accession/version; conflicting versions already in the selected database are held. Search tags indicate query matches only.

Source format references: [NCBI sample GenBank record](https://www.ncbi.nlm.nih.gov/genbank/samplerecord/) and [NCBI sequence identifiers](https://www.ncbi.nlm.nih.gov/genbank/sequenceids/).

## Ranking and merge screening

Ranks and habitat tags are heuristic screens with their observation text. Keyword matches in titles can be indirect; tags require review before use as biological membership. An absent tag does not establish a negative phenotype, absent habitat, or nonmembership in a taxon. Missing lineage remains unknown. Missing sequence remains unavailable. Without `--pdf-hits`, the saved-hit rescue channel is `NOT_MEASURED`. Incomplete percent identities prevent rescue classification for the affected query.

The ranker rebuilds its generated tag namespaces in the new output while preserving search and genome tags. The `panel_candidates` view exposes `sequence_status`, `tag_scope`, and `candidate_tags`; previous Boolean membership columns are removed because absence was ambiguous. Consumers of the old view must migrate explicitly.

Builder strain groups based on designation or collection IDs remain proposed groups. Panel selection can use those groups to choose representative records; operators must review grouping authority. The merge audit retains the original k-mer note and writes a separate alignment screen. Only A/C/G/T columns count toward identity; zero comparable columns yield missing identity. A threshold pass is named `SIMILARITY_SCREEN_PASS`, never accepted nesting or a resolved strain merge.

## Genome extraction and panel output

```bash
python tools/phylo_16s_from_genome.py inputs/genome.fna --blastdb inputs/reference_db --out output/candidate_spans.fasta
python tools/phylo_16s_panel.py --db output/ranked.sqlite --strains QUERY_A --refs type:1x --name candidate_panel --outdir output
```

Extraction clusters HSP intervals using the existing gap-at-most-100-nt heuristic. Each cluster derives relative orientation from both query and subject coordinate directions. Conflicting directions within one cluster cause an orientation hold. There is no contig-wide vote or motif-driven flip. Coordinates delimit a BLAST-supported candidate span, not a verified gene. The operator must establish reference biological orientation. `--best` retains the longest candidate span with deterministic coordinate ties.

Duplicate genome paths or content identities are refused. Output tip keys contain the genome content hash and exact contig coordinates. A separate receipt retains input/reference hashes, parameters, local HSP evidence, and output hash. Panel metadata includes explicit `role` (query/reference/outgroup) and `taxon` copied from the bound record binomial, with `taxon_source`. This supports the tree-display contract without inferring taxonomy from labels. Missing taxon stays empty and prevents reference collapse. Panel FASTA, metadata, and receipt are exclusive new files; the receipt is written last as the completion marker. Identical sequence content across separately bound strains is retained.

BLAST staging requires a space-free temporary path. Spaced source files are copied and direct database volume files are linked, with copy fallback. A spaced `TMPDIR` is refused, and owned temporary resources are released after failures. Alias databases (`.nal`) remain held because dependency closure and path rewriting are not established; provide a direct volume prefix. Tool failures and malformed results are never interpreted as no hits.

## Console and receipt channels

CLI progress and dry-run plans use configured logging on stderr. Importing these helpers does not configure application logging. Database operation events and the named output receipts remain the completion/provenance records; stdout silence is not a success or failure verdict. Check the exit code and receipt status.

## Validation boundary

The focused regression suite uses generic fixtures and simulated service/tool results. Live NCBI retrieval, real BLAST/MAFFT scientific results, production database migration, large-store memory behavior, and full release/integration validation require their own evidence. No focused pass authorizes scientific acceptance or release.

The rich GenBank source-record parser requires optional Biopython. If it is unavailable, parsing returns an explicit dependency failure instead of using the minimal `_gbk_shim` and silently losing required accession or source-qualifier evidence. The ordinary extraction shim remains available for its existing uses.
