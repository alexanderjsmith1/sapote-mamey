<!-- SUPERSEDED GLOSSARY SOURCE — NOT CANONICAL -->
> **SUPERSEDED INVENTORY SNAPSHOT.** Retained as evidence of one historical add-on set, not as current dependency, installation, import, or functional authority. A wheel's presence did not prove that the engine imported or used it. Do not extend this file. Current term definitions live in the canonical [`docs/GLOSSARY.md`](../GLOSSARY.md); current dependency and optional-tool truth lives in `pyproject.toml`, `mamey/data/companion_tools.json`, the installer, and `mamey doctor` for the active environment.

# Superseded Sapote–Mamey Add-on Wheel Inventory Snapshot
**Bundle:** v9.7.319 · Add-ons staged 2026-07-03**
**Wheels inventoried:** 41 (30 core + 11 figures/analysis)
**Source:** canonical `METADATA` extracted from each `.whl` archive + installer stage labels from `install_sapote_addons.sh`

Entries are grouped by functional role, then alphabetical within each group. The **Stage** column uses the labels assigned in `install_sapote_addons.sh`'s verification block (S1–S7); packages with no stage label are infrastructure or figure-layer dependencies.

---

## Group 1 · Gene Calling

### pyrodigal — v3.7.1
**Stage:** S1 (gene prediction)
**Full name:** Pyrodigal
**License:** MIT
**Source:** https://github.com/althonos/pyrodigal
**Paper:** doi:10.21105/joss.04296

Cython bindings wrapping Prodigal, the standard ORF finder for prokaryotic genomes and metagenomes. In Sapote–Mamey this is the **proteome prediction stage**: given a raw genome sequence, Prodigal calls coding sequences, assigns start and stop coordinates, and computes a training model from the genome itself rather than requiring a reference. Pyrodigal exposes this without subprocess overhead, so the engine can call it inline and receive `SeqRecord`-compatible output. Used whenever the pipeline needs to generate a fresh protein set from a genome FASTA rather than reading one from the antiSMASH GBK.

### pyrodigal-gv — v0.3.2
**Stage:** S1 (gene prediction, virus/giant-virus extension)
**License:** GPL-3.0-only
**Source:** https://github.com/althonos/pyrodigal-gv

A thin wrapper around pyrodigal that extends gene calling to giant viruses and viruses with non-standard genetic codes (alternative codon tables, programmed frameshifts). In practice this means the engine can correctly call ORFs in BGC-bearing phage and giant-virus sequences without the standard bacterial model mistranslating stop codons or missing starts. Declared in the science stack check but rarely invoked on actinomycete runs — its presence covers edge cases where a BGC's host turns out to be viral or where a phage-integrated cluster is encountered.

---

## Group 2 · Whole-Genome Identity and ANI

### pyfastani — v0.6.1
**Stage:** S2 (whole-genome ANI)
**License:** MIT
**Source:** Martin Larralde, EMBL

Cython bindings for FastANI, the standard fast average nucleotide identity method. ANI measures the overall nucleotide identity between two genomes — values above ~95–96% conventionally define the same species, below ~80% indicate genus-level separation. In Sapote–Mamey this drives the comparison module (`mamey compare`) when assessing whether two strains are likely to be the same species and whether their BGC repertoires can be compared at all. FastANI uses a MinHash-like sketching step that makes genome-vs-genome distance computation fast enough to run over cohorts without alignment.

### pyskani — v0.2.0
**Stage:** S2 (fragmentation-robust ANI)
**License:** MIT
**Source:** https://github.com/althonos/pyskani

PyO3 bindings for skani, a newer ANI method that uses sparse chaining rather than k-mer hashing, making it substantially more robust on fragmented assemblies. This is the key distinction from pyfastani: FastANI degrades on fragmented genomes because it needs contiguous stretches to sketch; skani works well on POOR- and VERY_POOR-tier assemblies with many short contigs. For the Sapote–Mamey cohort, where assembly quality ranges widely (GOOD to VERY_POOR), pyskani is the preferred identity calculator because it returns reliable ANI estimates even when the assembly is discontinuous.

---

## Group 3 · Sequence Parsing and I/O

### biopython — v1.87
**Stage:** S3 / S5 / S7 (parsing, alignment, output)
**License:** Biopython License (permissive, BSD-like)
**Source:** https://biopython.org

The foundational bioinformatics library for Python. Sapote–Mamey uses it throughout: reading GenBank flat files (`.gbk`, `.gb`) from antiSMASH output, parsing FASTA sequences, handling `SeqRecord` and `SeqFeature` objects that carry BGC annotations, and writing output sequences. Every antiSMASH region GBK that the engine reads passes through Biopython's `SeqIO` parser. Also used in the BLASTp parsing path (`Bio.Blast`) and in alignment post-processing. Version 1.87 is vendored here to ensure a consistent parser regardless of what the host system has installed.

### gb-io — v0.4.0
**Stage:** S3 (fast GenBank I/O)
**License:** MIT
**Source:** https://github.com/althonos/gb-io.py

Python interface to gb-io, a GenBank parser and serializer written in Rust. Where Biopython's GenBank parser is general-purpose and tolerant of format variation, gb-io is narrowly focused on speed: it is 10–50× faster on large GenBank files. In Sapote–Mamey this is used for high-throughput passes over whole-genome GBKs — the initial parse during `mamey run` and the source scan passes that process every CDS feature across potentially hundreds of contigs. When the assembly has many contigs (common in POOR/VERY_POOR tiers), the speed difference is material.

### pyfaidx — v0.9.0.4
**Stage:** infrastructure (random-access FASTA)
**License:** BSD-3-Clause
**Source:** https://github.com/mdshw5/pyfaidx

Efficient random-access reads from FASTA files without loading the whole file into memory. It relies on the `.fai` FASTA index format (generated by `samtools faidx` or by pyfaidx itself). Used when the engine needs to fetch specific contig sequences by name — for example, extracting the nucleotide sequence under a BGC region for boundary analysis or for export to a comparator run — rather than reading the entire genome FASTA each time.

### pyfastx — v2.3.1
**Stage:** infrastructure (fast FASTA/FASTQ access)
**License:** MIT
**Source:** https://github.com/lmdu/pyfastx

Fast random access to sequences in plain and gzipped FASTA/FASTQ files. Complements pyfaidx with additional support for compressed input and FASTQ. In Sapote–Mamey the main use case is scanning potentially gzipped genome FASTAs supplied as companion files without requiring prior decompression.

### ijson — v3.5.0
**Stage:** S7 (streaming JSON / evidence arrays)
**License:** MIT / BSD
**Source:** https://github.com/ICRAR/ijson

Iterative (streaming) JSON parser with standard Python iterator interfaces. This is critical for the `--json-evidence bounded` mode: antiSMASH output JSON files and the Mamey evidence arrays can be very large (tens of MB for a large genome), and loading them fully into memory before parsing causes session timeouts or OOM errors in capped environments. ijson allows the engine to walk the JSON token stream without materializing the whole document. The `--json-evidence off` default in capped sessions exists specifically because without streaming the JSON stage can dominate session wall time.

### bcbio-gff — v0.7.1
**License:** Biopython License
**Source:** https://github.com/chapmanb/bcbb/tree/master/gff

Read and write GFF/GFF3 annotation files with Biopython integration. GFF3 is the standard feature annotation format alongside GenBank; this library handles the conversion between the two representations. Used in annotation import/export paths, particularly when working with genome annotations from sources other than antiSMASH that deliver GFF3 rather than GenBank format.

### gffutils — v0.14
**License:** MIT
**Source:** https://github.com/daler/gffutils

Works with GFF and GTF files via a SQLite-backed database framework. Where bcbio-gff handles in-memory GFF parsing, gffutils builds an indexed local database that supports efficient range queries (e.g., "give me all features between position X and Y on contig Z"). Useful when the engine needs to cross-reference antiSMASH BGC coordinates against a separately-supplied full genome annotation.

### simplejson — v4.1.1
**License:** MIT / AFL-2.1
**Source:** https://github.com/simplejson/simplejson

A fast, extensible JSON encoder/decoder that is API-compatible with the standard library `json` module but with better performance and additional features (e.g., `Decimal` support, ordered output). Used in contexts where the standard library JSON module's performance or precision handling is insufficient — particularly relevant for the evidence store, where floating-point fields like bitscore and identity need to round-trip without precision loss.

---

## Group 4 · Alignment and Sequence Comparison

### pyswrd — v0.3.1
**Stage:** S4 / S5 (fast database search, alignment backend)
**License:** GPL-3.0
**Source:** Martin Larralde, EMBL

Cython bindings for SWORD (Smith-Waterman On Reduced Database), a heuristic method for fast protein database search. SWORD pre-filters the database using a reduced alphabet to identify candidate sequences, then runs exact Smith-Waterman alignment only on the short list. This is the **primary alignment backend** for `mamey compare` — the installer note explicitly calls it "the PROVEN path (reproduced NCBI BLASTp to the decimal)." The comparison module uses pyswrd by default and only upgrades to DIAMOND if a `diamond` binary is on PATH. pyswrd requires pyopal and scoring_matrices as dependencies.

### pyopal — v0.7.3
**Stage:** S4 / S5 (SIMD-accelerated pairwise alignment)
**License:** MIT
**Source:** Martin Larralde, EMBL

Cython bindings for Opal, a SIMD-accelerated pairwise sequence aligner implementing Smith-Waterman. Where pyswrd handles the heuristic database pre-filter, pyopal handles the exact alignment stage on the candidate sequences that pass the filter. It uses SIMD instructions (SSE2/AVX2 on x86) to run many alignment cells in parallel, achieving speeds competitive with highly optimized C implementations. Not called directly from user-facing pipeline commands — it is a dependency of pyswrd.

### scoring-matrices — v0.3.4
**Stage:** S4 / S5 (substitution matrices)
**License:** MIT
**Source:** Martin Larralde, EMBL

Dependency-free, Cython-compatible substitution scoring matrices (BLOSUM62, PAM250, etc.) for use with biological sequence alignment. Provides the score lookup tables that pyopal and pyswrd use to compute alignment scores. Separated into its own package so different alignment backends can share a single authoritative source of matrix data without redundancy.

### pyfamsa — v0.7.0
**Stage:** S5 (ultra-scale multiple sequence alignment)
**License:** GPL-3.0
**Source:** https://github.com/althonos/pyfamsa

Cython bindings for FAMSA, an algorithm for ultra-scale multiple sequence alignment. FAMSA is designed for very large sets of sequences (thousands to hundreds of thousands) where standard MSA tools like MUSCLE or MAFFT become prohibitively slow. In Sapote–Mamey this is used when aligning large protein families — for example, building the alignment underlying a domain logo or a phylogenetic tree of KS domains across the cohort. Its speed advantage is most pronounced in the cohort-wide comparative analyses.

### pytrimal — v0.8.5
**Stage:** S5 (alignment trimming)
**License:** GPL-3.0
**Source:** Martin Larralde, EMBL

Cython bindings for trimAl, the standard tool for automated alignment trimming. After a multiple sequence alignment is produced (by pyfamsa or another tool), trimAl removes poorly aligned or highly gapped columns, reducing noise before phylogenetic analysis or logo generation. Sapote–Mamey uses this in the domain-alignment pipeline where a raw MSA is trimmed before being passed to downstream visualization or tree-building steps.

### pytantan — v0.1.4
**Stage:** S5 (repeat masking)
**License:** GPL-3.0
**Source:** Martin Larralde, EMBL

Cython bindings for Tantan, a fast method for identifying and soft-masking low-complexity and repetitive regions in DNA and protein sequences. In sequence database searches, low-complexity regions (e.g., runs of the same amino acid, coiled-coil regions) generate spurious high-scoring hits that are not biologically meaningful. Tantan masks these before alignment so that pyswrd/pyopal similarity scores reflect genuine homology rather than compositional bias.

---

## Group 5 · HMM Profiling

### pyhmmer — v0.12.1
**Stage:** S3 / HMM domain scan (offline HMMER3 profile search)
**License:** MIT
**Source:** https://github.com/althonos/pyhmmer
**Paper:** doi:10.1093/bioinformatics/btad214

Cython bindings for HMMER3, the standard hidden Markov model software suite for protein domain detection. This is the engine behind the offline HMM scan in Sapote–Mamey. Instead of calling the `hmmsearch` binary as a subprocess, pyhmmer runs HMMER3 profile search entirely within Python with no subprocess overhead. The scan uses the `scanner_pfam_150.hmm` reference file (148 curated Pfam families; see HMM Data section below) shipped in the figures addon. The installer verification explicitly tests `pyhmmer` under the label "HMM domain scan / adjudication" — it is one of the six required core imports.

---

## Group 6 · Taxonomy

### taxopy — v0.14.0
**License:** MIT
**Source:** https://github.com/apcamargo/taxopy

A Python package for obtaining complete taxonomic lineages and lowest common ancestor (LCA) from NCBI taxonomic identifiers (taxids). Used in Sapote–Mamey when the engine needs to resolve a BLAST hit's organism lineage — for example, determining whether a top BLASTp hit comes from the same genus or family as the query strain, which informs the KCB (KnownClusterBlast) interpretation and the conservation background calculation. Also relevant when assigning isolation-source habitat labels from taxonomy.

### DendroPy — v5.0.8
**License:** BSD
**Source:** https://github.com/jeetsukumaran/DendroPy

A full-featured Python library for phylogenetics: reading, writing, simulating, and manipulating phylogenetic trees and character matrices. Supports Newick, Nexus, PHYLIP, and FASTA formats. In Sapote–Mamey this is used in the cohort-level comparative analyses where BGC domain trees are built to assess evolutionary relationships between clusters — for example, evaluating whether a KS domain group is monophyletic within the cohort or scattered across genera, which bears on the HGT vs. vertical inheritance interpretation.

---

## Group 7 · Figures and Visualization

### matplotlib — v3.11.0
**Stage:** figure rendering
**License:** PSF-compatible
**Source:** https://matplotlib.org

The foundational Python plotting library. Nearly every figure in the Sapote–Mamey output — the strain brief panels (`_8a…_8m_fig_*.png`), the DAPR boards, the triage scatter plots, the boundary pie charts, the BGC size histograms — is rendered through matplotlib. The figures addon brings a recent version (3.11.0) to ensure consistent rendering behavior; the system matplotlib (if present) may be older.

### numpy — v2.5.0
**Stage:** figures/math
**License:** BSD
**Source:** https://numpy.org

The fundamental array computing library for Python. Used everywhere numerical computation is needed: score arrays, identity vectors, coverage matrices, the conservation background calculation. Also a dependency of matplotlib, scipy, and pandas, so its version constrains the entire numerical stack. Version 2.5.0 is the current release as of the addon build date.

### scipy — v1.18.0
**Stage:** figures/math (statistical analysis)
**License:** BSD
**Source:** https://scipy.org

Scientific computing algorithms built on numpy: statistical tests, interpolation, clustering, signal processing. In Sapote–Mamey scipy is used in the cohort comparison and figure modules — for example, computing kernel density estimates for the AB/AF score distributions in the atlas plots, running hierarchical clustering on the BGC distance matrix for the pangenome figure, and computing statistical summaries for the workbook.

### pandas — v3.0.3
**Stage:** figure data
**License:** BSD-3-Clause
**Source:** https://pandas.pydata.org

Tabular data analysis library. The workbook outputs (`.xlsx` sheets) and the figure-ready CSVs produced by `export_figure_ready.py` are built and manipulated primarily through pandas DataFrames. The cohort-wide BLASTp driver, the lead board, and the CCSM cross-strain comparison module all use pandas for aggregation and pivot operations before passing results to matplotlib for rendering.

### pycirclize — v1.10.1
**Stage:** genome atlas
**License:** MIT
**Source:** https://github.com/moshi4/pyCirclize

Circular visualization in Python, analogous to Circos but Python-native. Used by the BGC atlas (`generate_bgc_atlas.py`) to produce the circular genome map that shows all BGC regions laid out around a chromosome ring, colored by BGC class, with connection arcs indicating KnownClusterBlast links. This is the browsable HTML atlas deliverable produced after a successful run.

### logomaker — v0.8.7
**License:** MIT
**Source:** https://github.com/jbkinney/logomaker

Package for making sequence logos from a frequency or information matrix. A sequence logo displays a multiple sequence alignment as a stack of letters at each position, where letter height encodes conservation. In Sapote–Mamey this is used in domain-level visualization — for example, producing a logo of the KS active site residues across the cohort's PKS clusters to illustrate conservation vs. divergence at functionally critical positions.

### dna-features-viewer — v3.1.5
**License:** MIT
**Source:** https://github.com/Edinburgh-Genome-Foundry/DnaFeaturesViewer

Plot annotated DNA/protein features from GenBank or GFF records using matplotlib. Used to produce the per-BGC locus maps (`locus_maps/`) that show gene arrow diagrams: each gene in a BGC region rendered as a color-coded arrow with its annotation label, laid out at genomic scale. This is the visual format the bundle uses in the BGC Guide and the bench deliverables to give a schematic view of cluster architecture. As of v9.7.338 it also backs the offline `mamey figures kcb-locusmap` comparative locus map (query BGC vs its KnownClusterBlast/MIBiG comparator, rendered with zero network); gene links there are similarity, not identity.

*Note (v9.7.338): the v9.7.338 subcommands are reporting/deliverable layers over already-inventoried wheels — they add no new add-on wheel. `figures kcb-locusmap` uses dna-features-viewer + matplotlib (above); the docx/pdf renders (`good-guesses --docx/--pdf`, `modeb-export`) reuse the bundle's existing document-render path. Nothing new to stage in `install_sapote_addons.sh`.*

---

## Group 8 · Infrastructure and Build Tools

*These packages support the Python environment itself rather than any specific bioinformatics computation. They are required by the above dependencies and ship in the addon to ensure a consistent, self-contained installation.*

### archspec — v0.2.6
**License:** Apache-2.0 / MIT
**Source:** https://github.com/archspec/archspec

Runtime CPU architecture detection library. A dependency of pyrodigal: Prodigal selects SIMD-optimized code paths at runtime based on the host CPU's feature flags (SSE4.2, AVX2, etc.), and archspec provides the detection logic.

### argcomplete — v3.7.0
**License:** Apache Software License
**Source:** https://github.com/kislyuk/argcomplete

Bash tab-completion for Python argparse-based command-line tools. Enables shell completion for `mamey` subcommands when properly activated. Optional at runtime — the CLI works without it, but it improves the interactive experience.

### argh — v0.31.3
**License:** MIT
**Source:** https://github.com/neithere/argh

Plain Python functions as CLI commands without boilerplate. Used in some of the `tools/` scripts to build lightweight argument parsers from function signatures without explicit `argparse` setup.

### iniconfig — v2.3.0
**License:** MIT
**Source:** https://github.com/pytest-dev/iniconfig

Brain-dead simple INI config file parsing. A dependency of pytest — reads `pyproject.toml` and `pytest.ini` configuration sections.

### packaging — v26.2
**License:** Apache / BSD
**Source:** https://github.com/pypa/packaging

Core utilities for Python package version parsing, specifier evaluation, and marker handling. A dependency of pip and pytest; used by the installer to resolve version constraints when installing from the wheel pool.

### pip — v26.1.2
**License:** MIT
**Source:** https://pip.pypa.io

The standard Python package installer. Vendored here to ensure the offline install uses a consistent, recent pip version that correctly handles the manylinux wheel tags and `--no-index --find-links` semantics needed for the air-gapped installation.

### pluggy — v1.6.0
**License:** MIT
**Source:** pytest ecosystem

Plugin and hook calling mechanism. A dependency of pytest that manages the plugin registration system.

### psutil — v7.2.2
**License:** BSD-3-Clause
**Source:** https://github.com/giampaolo/psutil

Cross-platform process and system monitoring (CPU, memory, disk, network, processes). Used by pyhmmer to monitor memory usage during large HMM scans and by the engine's stall guard to detect whether a subprocess has hung.

### Pygments — v2.20.0
**License:** BSD
**Source:** https://pygments.org

Syntax highlighting library. A dependency of pytest for colorized terminal output.

### pytest — v9.1.1
**License:** MIT
**Source:** https://docs.pytest.org

The test runner for the Sapote–Mamey test suite (2,842 tests at v9.7.241). Vendored in the addon so the surrogate gate and full pytest suite can run in an air-gapped environment without requiring a network install. All bundle validation runs use this version.

### setuptools — v82.0.1
**License:** MIT
**Source:** https://setuptools.pypa.io

The Python build backend. Required for installing packages distributed as source distributions (`.tar.gz`) or for packages that use `setup.py`. Most wheels here are pre-built, but setuptools is needed for `pip install -e .` (editable install of the bundle itself) and as a dependency of several packages.

### six — v1.17.0
**License:** MIT
**Source:** https://github.com/benjaminp/six

Python 2 / Python 3 compatibility shim. Vestigial dependency of some older packages in the stack (bcbio-gff, some biopython modules). Has no functional role in a Python 3.12-only environment but must be present to satisfy import-time checks in those packages.

### wheel — v0.47.0
**License:** MIT
**Source:** https://wheel.readthedocs.io

The command-line tool for working with `.whl` (wheel) files: building, unpacking, inspecting. Vendored to support any wheel manipulation the installer needs to do.

---

## HMM Reference Data (not a wheel, but shipped in the figures addon)

### scanner_pfam_150.hmm
**Location:** `sapote_addons_figures/hmm/scanner_pfam_150.hmm`
**Size:** 13.3 MB · 148 HMM profiles
**SHA256:** `2db9ed0e58d1cd679b6b3c15e01c411e0bd49ae410a116d50bd23afa904aa57c`

The three-tier Pfam reference model used by the offline HMM scanner (pyhmmer). This is not a wheel but ships alongside the figures addon because it is data rather than code. The 148 profiles were selected empirically: the full Pfam-A (30,134 families) was scanned against SID10815's BGC proteome, the top ~130 families by hit frequency were retained, and all scanner-gate discriminating domains were force-added regardless of frequency (e.g., `DHQ_synthase` for aminocyclitol BGCs, which are rare but diagnostically critical). The result captures ~66% of domain signal across a typical actinomycete BGC proteome while remaining fast enough for per-run inline scanning.

The 148 families include all major BGC-relevant domain classes: PKS (ketoacyl-synthase, KR, DH, AT, ACP, docking), NRPS (condensation, adenylation, peptidyl carrier), terpene (Terpene_synth/C), RiPP (LANC_like, Lant_dehydr_N/C, YcaO, SPASM, RRE), aminoglycoside (aminotransferases, NDP-sugar synthases), and regulatory/resistance (TetR, MarR, ABC transporters).

This file lives in tier 3 of the three-tier model: the CODE bundle ships the first 25 core HMMs; the gemini-stack wheels supply the pyhmmer engine; this file supplies the full reference data. All three tiers must be present for the full offline HMM scan to run.

---

## Quick-reference index

| Package | Version | Group | Role in pipeline |
|---|---|---|---|
| archspec | 0.2.6 | Infrastructure | CPU feature detection (pyrodigal dep) |
| argcomplete | 3.7.0 | Infrastructure | CLI tab-completion |
| argh | 0.31.3 | Infrastructure | CLI builder for tools/ scripts |
| bcbio-gff | 0.7.1 | Parsing | GFF/GFF3 read/write with Biopython |
| biopython | 1.87 | Parsing | Core GBK/FASTA/BLAST parsing (S3/S5/S7) |
| DendroPy | 5.0.8 | Taxonomy | Phylogenetic tree I/O and manipulation |
| dna-features-viewer | 3.1.5 | Figures | Per-BGC locus map gene-arrow diagrams |
| gb-io | 0.4.0 | Parsing | Fast Rust-backed GenBank parser |
| gffutils | 0.14 | Parsing | GFF/GTF database with range queries |
| ijson | 3.5.0 | Parsing | Streaming JSON for large evidence arrays (S7) |
| iniconfig | 2.3.0 | Infrastructure | pytest config parsing |
| logomaker | 0.8.7 | Figures | Domain/sequence logos from MSA |
| matplotlib | 3.11.0 | Figures | Core figure rendering |
| numpy | 2.5.0 | Figures/Math | Array computing, score matrices |
| packaging | 26.2 | Infrastructure | Version/specifier parsing |
| pandas | 3.0.3 | Figures/Data | Tabular data, workbook construction |
| pip | 26.1.2 | Infrastructure | Package installer |
| pluggy | 1.6.0 | Infrastructure | pytest plugin hooks |
| psutil | 7.2.2 | Infrastructure | Process/memory monitoring |
| pycirclize | 1.10.1 | Figures | Circular genome atlas |
| pyfaidx | 0.9.0.4 | Parsing | Random-access FASTA |
| pyfamsa | 0.7.0 | Alignment | Ultra-scale MSA (S5) |
| pyfastani | 0.6.1 | ANI | Whole-genome ANI via FastANI (S2) |
| pyfastx | 2.3.1 | Parsing | Fast gzipped FASTA/FASTQ access |
| pyhmmer | 0.12.1 | HMM | Offline HMMER3 domain scan |
| Pygments | 2.20.0 | Infrastructure | Syntax highlighting (pytest dep) |
| pyopal | 0.7.3 | Alignment | SIMD Smith-Waterman (pyswrd dep) |
| pyrodigal | 3.7.1 | Gene calling | ORF finding, proteome prediction (S1) |
| pyrodigal-gv | 0.3.2 | Gene calling | Giant virus / alt-code extension (S1) |
| pyskani | 0.2.0 | ANI | Fragmentation-robust ANI via skani (S2) |
| pyswrd | 0.3.1 | Alignment | Fast Smith-Waterman database search (S4/S5) |
| pytantan | 0.1.4 | Alignment | Low-complexity / repeat masking (S5) |
| pytest | 9.1.1 | Infrastructure | Test runner |
| pytrimal | 0.8.5 | Alignment | MSA trimming (S5) |
| scipy | 1.18.0 | Figures/Math | Statistics, clustering, KDE |
| scoring-matrices | 0.3.4 | Alignment | Substitution matrices (pyswrd/pyopal dep) |
| setuptools | 82.0.1 | Infrastructure | Build backend |
| simplejson | 4.1.1 | Parsing | Precise JSON encode/decode |
| six | 1.17.0 | Infrastructure | Py2/3 compat shim (vestigial) |
| taxopy | 0.14.0 | Taxonomy | NCBI taxid lineage and LCA |
| wheel | 0.47.0 | Infrastructure | Wheel file tooling |
| scanner_pfam_150.hmm | — | HMM data | 148-family Pfam reference for offline scan |

---

## Appendix A: Complete Wheel Size Table (Compressed .whl Archive)

Sizes are for the compressed `.whl` archive files as staged in the addon directories. Installed sizes are typically 3–8× larger. All versions are as of addon build 2026-07-03.

| Wheel | Version | Addon group | Compressed size |
|---|---|---|---|
| archspec | 0.2.6 | core | 80 KB |
| argcomplete | 3.7.0 | core | 42 KB |
| argh | 0.31.3 | core | 44 KB |
| bcbio-gff | 0.7.1 | core | 16 KB |
| biopython | 1.87 | core | 3.10 MB |
| dendropy | 5.0.8 | core | 454 KB |
| gb-io | 0.4.0 | core | 539 KB |
| gffutils | 0.14 | core | 1.56 MB |
| ijson | 3.5.0 | core | 146 KB |
| iniconfig | 2.3.0 | core | 7 KB |
| packaging | 26.2 | core | 98 KB |
| pip | 26.1.2 | core | 1.73 MB |
| pluggy | 1.6.0 | core | 20 KB |
| psutil | 7.2.2 | core | 152 KB |
| pyfaidx | 0.9.0.4 | core | 29 KB |
| pyfamsa | 0.7.0 | core | 1.80 MB |
| pyfastani | 0.6.1 | core | 370 KB |
| pyfastx | 2.3.1 | core | 856 KB |
| pygments | 2.20.0 | core | 1.17 MB |
| pyhmmer | 0.12.1 | core | 3.80 MB |
| pyopal | 0.7.3 | core | 838 KB |
| pyrodigal | 3.7.1 | core | 2.81 MB |
| pyrodigal-gv | 0.3.2 | core | 830 KB |
| pyskani | 0.2.0 | core | 3.30 MB |
| pyswrd | 0.3.1 | core | 390 KB |
| pytantan | 0.1.4 | core | 277 KB |
| pytest | 9.1.1 | core | 377 KB |
| pytrimal | 0.8.5 | core | 790 KB |
| scoring-matrices | 0.3.4 | core | 122 KB |
| setuptools | 82.0.1 | core | 983 KB |
| simplejson | 4.1.1 | core | 186 KB |
| six | 1.17.0 | core | 11 KB |
| taxopy | 0.14.0 | core | 25 KB |
| wheel | 0.47.0 | core | 31 KB |
| dna-features-viewer | 3.1.5 | figures | 31 KB |
| logomaker | 0.8.7 | figures | 12.58 MB |
| matplotlib | 3.11.0 | figures | 9.57 MB |
| numpy | 2.5.0 | figures | 15.89 MB |
| pandas | 3.0.3 | figures | 10.39 MB |
| pycirclize | 1.10.1 | figures | 82 KB |
| scipy | 1.18.0 | figures | 33.65 MB |
| **Total core** | | | **~30 MB** |
| **Total figures** | | | **~87 MB** |
| **Grand total** | | | **~117 MB** |

*Size note: logomaker (12.58 MB) is unexpectedly large for a pure-Python package because it bundles font glyph data and rendering assets for nucleotide/amino-acid logo generation. scipy (33.65 MB) is the largest wheel and contains compiled LAPACK/BLAS wrappers for numerical linear algebra.*

---

## Appendix B: Wheel Dependency Graph (Within-Stack)

Within the Sapote-Mamey addon stack, several wheels are dependencies of others. Understanding this graph prevents install-order failures.

**pyswrd → pyopal + scoring-matrices** — pyswrd is the SWORD database-search wrapper. It requires pyopal for the SIMD pairwise alignment step and scoring-matrices for the substitution matrix data. Installing pyswrd without pyopal/scoring-matrices fails at import.

**pyrodigal → archspec** — pyrodigal uses archspec to detect SIMD instruction set availability (SSE4.2, AVX2) at runtime so it can select the fastest compiled Prodigal variant.

**biopython → numpy** — biopython uses numpy for sequence array operations. numpy must install first.

**matplotlib → numpy** — matplotlib requires numpy. In the figures addon, numpy installs as part of the same pass.

**pandas → numpy** — pandas requires numpy.

**scipy → numpy** — scipy requires numpy. The install order in `install_sapote_addons.sh` handles this automatically by pooling all wheels and letting pip resolve dependencies.

**pyfamsa (standalone)** — pyfamsa has no within-stack dependencies. It wraps the FAMSA C++ binary directly.

**pyhmmer (standalone)** — pyhmmer wraps HMMER3 C code compiled as a Cython extension. No within-stack dependencies.

**pyskani (standalone)** — pyskani wraps skani Rust code compiled as a PyO3 extension. No within-stack dependencies.

---

## Appendix C: Graceful Degradation Behavior

The addon stack is designed to degrade gracefully when components are absent. This table documents what works and what does not at each degradation level.

| Missing component | What degrades | What still works |
|---|---|---|
| pyhmmer absent | Offline HMM domain scan unavailable | All regex-based CCTT/UMED/resistance scanning; all figures; BLASTp pipeline |
| scanner_pfam_150.hmm absent | Full 148-family scan unavailable; falls back to 35-family Wheelhouse HMM | Core CCTT gates covered by 35-family set |
| Both HMM files absent | All HMM scanning unavailable | Regex-based scans still run; KCB scoring unaffected |
| pyrodigal absent | Gene calling from raw FASTA unavailable | Extraction from antiSMASH GBK works (main path) |
| pyfastani absent | FastANI-based whole-genome ANI unavailable | pyskani provides fragmentation-robust ANI |
| pyskani absent | Skani ANI unavailable | pyfastani still available; skani preferred for POOR assemblies |
| pyfamsa absent | MSA step for domain logos unavailable | Domain scan, BLASTp, and all figures still work |
| Figures addon absent (numpy/matplotlib) | All figure generation fails | All numerical extraction, BLASTp, HMM scan still work; figures produce `NO_FIGURES_RENDERED.md` |
| NP Atlas files absent | B6_Compound_Reference sheet not populated | All other workbook sheets unaffected |
| ijson absent | Bounded JSON streaming falls back to full-load json.loads | Still works; risk of memory pressure on large genomes |

The `mamey doctor` output reports all of these degradation states explicitly. The science stack line `5/5 available` confirms all five science-stack imports (pyrodigal, pyfastani, pyswrd, pyhmmer, pyskani) are importable.

---

*Last updated: 2026-07-09 · v2 additions (Appendices A, B, C) · Bundle v9.7.319*
