# Changelog

## {version}
Built from Sapote-Mamey 9.7.457 (engine 1.9.177). Scores, ranks and confidence labels are unchanged: on the bundled example every pair keeps its confidence, and only the junction label below changes.
- **Junction evidence label.** `junction_evidence_state` is `SEQUENCE_COMPLEXITY_CLEAR` only when every truncated contig end was read and is complex. An end that could not be read, or holds N or another non-ACGT base, gives `SEQUENCE_COMPLEXITY_UNRESOLVED`. A pair with no truncated end is `NOT_APPLICABLE`; it was `SEQUENCE_COMPLEXITY_CLEAR` before. On the bundled example, 5 pairs change from CLEAR to NOT_APPLICABLE.
- **Contig ends.** An end window holding N or another non-ACGT base is `AMBIGUOUS_TERMINUS`. `/contig_edge` is read from the region feature itself, not from the first match in the file.
- **One read of each archive.** An antiSMASH ZIP is read from one recorded copy (`archive_snapshot.py`, `source_context.py`). A ZIP that changes while it is prepared is refused (`RGGMCI_INPUT_CHANGED_DURING_PREPARATION`).
- **Gene context on pairs.** When the archive's CDS annotations allow it, pairs carry `a_functional_roles`, `b_functional_roles`, `a_core_fraction`, `b_core_fraction`, `modular_continuation` and `functional_rescue_class` (`_feature_records.py`, `_functional_profiles.py`, `_gene_context.py`). They describe the pair and never change a score. The bundled example has none.
- **Outputs.** `--out`, `--pairs` and `--out-dir` must be new files or a new or empty directory, and every input and output is checked before any work starts. A batch also writes a related-locus table and the three completion tables per genome. New options: `--registry-from`, `--label`, `--residue-work-dir`, `--completion-work-dir`.
- **Built-in GenBank reader.** Without Biopython, a record with no sequence and no numeric LOCUS length is an error, as it is with Biopython.
- **BLASTp layer exit code.** It returns 0 even when some queries are unmapped. Check `NOT_IN_RESULTS` and the unmapped list before treating a run as complete.
- Changed lifted modules: `_parsers.py`, `core.py`, `cli.py`, `ref_completion.py`, `reader.py`, `blastp.py`, `residue_tiling.py`, `ziputil.py`, `_gbk_shim.py`, `groups.py`, `_blastp_io.py`, `__init__.py`.
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
