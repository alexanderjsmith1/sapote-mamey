# Changelog

## {version}
`src/rggmci/PROVENANCE.json` names the Sapote-Mamey build this release came from. On the bundled example every pair keeps its score and confidence, and only the junction label below changes. On other genomes, the changes to joined genes, origin-spanning regions and whole records can change which regions are read and their edge status, and so their pairs.
- **Biopython is now required.** It is installed with the package. The built-in GenBank reader refuses joined and origin-spanning gene locations instead of guessing them, so without Biopython most complete genomes and many drafts could not be read. `pip install "rggmci[bio]"` still works.
- **Joined genes.** A gene with joined segments (origin-spanning or spliced) is placed in a region by its segments, not by the span from its first to its last base. Its length is the sum of its segments.
- **Regions across the origin.** On a circular contig, a region that crosses the origin is read with its real span and is checked against the contig length. A region covering 95% or more of the contig is `Full-contig`.
- **ZIPs with whole records and no region files.** A whole record is admitted only when it has exactly one antiSMASH region feature with its own region number; it becomes one region with that number. Any other record is held, with a code in `intake_diagnostics` (for example `WHOLE_RECORD_MULTI_REGION_HELD`), instead of a region boundary being guessed.
- **Fixed: a missing module.** Before this fix, a genome with a joined gene inside a region failed with `ModuleNotFoundError: No module named 'rggmci.source_scans'`. The build now refuses any package with an unresolved import.
- **Junction evidence label.** `junction_evidence_state` is `SEQUENCE_COMPLEXITY_CLEAR` only when every truncated contig end was read and is complex. An end that could not be read, or holds N or another non-ACGT base, gives `SEQUENCE_COMPLEXITY_UNRESOLVED`. A pair with no truncated end is `NOT_APPLICABLE`; it was `SEQUENCE_COMPLEXITY_CLEAR` before. On the bundled example, the one scored pair and the four related loci change from CLEAR to NOT_APPLICABLE.
- **Contig ends.** An end window holding N or another non-ACGT base is `AMBIGUOUS_TERMINUS`. `/contig_edge` is read from the region feature itself, not from the first match in the file.
- **One read of each archive.** An antiSMASH ZIP is read from one recorded copy (`archive_snapshot.py`, `source_context.py`). A ZIP that changes while it is prepared is refused (`RGGMCI_INPUT_CHANGED_DURING_PREPARATION`).
- **Gene context on pairs.** When the archive's CDS annotations allow it, pairs carry `a_functional_roles`, `b_functional_roles`, `a_core_fraction`, `b_core_fraction`, `modular_continuation` and `functional_rescue_class` (`_feature_records.py`, `_functional_profiles.py`, `_gene_context.py`). They describe the pair and never change a score. On the bundled example the one scored pair carries them.
- **Outputs.** `--out`, `--pairs` and `--out-dir` must be new files or a new or empty directory, and every input and output is checked before any work starts. A batch also writes a related-locus table and the three completion tables per genome. New options: `--registry-from`, `--label`, `--residue-work-dir`, `--completion-work-dir`.
- **Built-in GenBank reader.** Without Biopython, a record with no sequence and no numeric LOCUS length is an error, as it is with Biopython.
- **BLASTp layer exit code.** It returns 0 even when some queries are unmapped. Check `NOT_IN_RESULTS` and the unmapped list before treating a run as complete.
- **Hit Tables without a header.** A Hit Table saved without its header row is read when its columns can be matched by type, including numeric subject IDs. A row that could be read more than one way is refused (`HIT_TABLE_LAYOUT_UNRESOLVED`) rather than read with shifted columns. A row with an unreadable identity or bit score is skipped, not read as zero.
- **Completion strand.** Reference-guided completion reads each gene's strand from its source record when deciding which contig end a split gene faces.
- **Summary counts.** `scored_pairs`, `high` and `moderate` in `SUMMARY.tsv` count every scored pair. They counted only the rows kept in the pair table, which holds the top 1,000 by rank plus every HIGH pair. A new `pairs_exported` column, after `scored_pairs`, gives the kept rows. The terminal line says so when the two differ.
- **Docs.** The README, output guide, worked examples and contributing guide are rewritten for people running the package. The output guide now covers gene context and contig-end fields.
- Changed modules: `_parsers.py`, `core.py`, `cli.py`, `ref_completion.py`, `reader.py`, `blastp.py`, `residue_tiling.py`, `ziputil.py`, `_gbk_shim.py`, `groups.py`, `_blastp_io.py`, `_records.py`, `csv_safety.py`, `__init__.py`. New modules: `archive_snapshot.py`, `source_context.py`, `_feature_records.py`, `_functional_profiles.py`, `_gene_context.py`.
## 1.0.0rc3

- `rggmci build-mibig-db --help` names the command `rggmci build-mibig-db`. It said `ref_completion`.
- A package test now runs `rggmci build-mibig-db` on a small made-up MIBiG GenBank file, without DIAMOND, so CI
  covers the command the README asks you to run first.

## 1.0.0rc2

- **Reference-guided completion.** For each region at a contig edge, the best KnownClusterBlast MIBiG reference
  (or, without one, a discovered one) is searched against every protein in the genome, not only those inside
  antiSMASH regions. It reports reference genes found elsewhere, genes split across two contig ends, and partner
  contigs with the tests each passed. It runs when a MIBiG protein database and DIAMOND or BLAST+ are found, and it
  never changes a score or a confidence.
- **`rggmci build-mibig-db`** builds that database from a folder of MIBiG GenBank files. It downloads nothing.
- New options: `--mibig-db`, `--reference-completion off`, `--sensitivity`, `--threads` and `--pfam`.
- Pairs gain `completion_tier`, `ref_completion_partner` and `split_gene_links`. With `--out-dir`, each genome also
  gets `_reference_completion.tsv`, `_split_genes.tsv` and `_partner_contigs.tsv`, and `SUMMARY.tsv` gains three
  completion columns.
- Without a database, or for a ZIP without its whole-genome GenBank file, the pairs are scored as before and the tier
  says why completion did not run.
- Pairs carry the read depth of both contigs, taken from SPAdes contig names, and `DEPTH_MISMATCH` when the lower is
  under 0.67 of the higher.
- **Residue tiling.** For pairs the paralog gate demoted, a DIAMOND search shows which stretch of each shared MIBiG
  protein each region covers. It runs with `--diamond-db`, or by default when the completion database has its DIAMOND
  index. It never changes a confidence.
- **Product names.** A product name now matches its antiSMASH category whether it is written with hyphens or
  underscores, so a region whose name used the other spelling gets its category, and its pairs can score
  differently from rc1. (This line was missing from the rc2 changelog; the rc2 release notes carried it.)

## 1.0.0rc1

- First standalone release of RG-GMCI (see `src/rggmci/PROVENANCE.json` for the exact source version and
  the SHA-256 of every source file used).
- `rggmci` scores region pairs for one genome or a folder of genomes.
- `rggmci fasta` and `rggmci blastp-layer` add an optional BLASTp layer that you run yourself on NCBI.
- The result JSON records which antiSMASH ZIP and which build produced it.
