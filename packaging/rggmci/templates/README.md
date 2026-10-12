# rggmci: Reference-Guided Genome Mining Candidate Inference (RG-GMCI)

> This is a package-build template, not an already assembled standalone release. `build_rggmci_package.py` combines lifted/copied source, templates and a generated provenance file (`:140–194`). The standalone project version comes from its own `pyproject.toml` (`1.0.0rc3`, Python ≥3.12); it is distinct from the Sapote-Mamey bundle version. Inspect the generated artifact's provenance and source bindings before use. Do not install the template directory as if all generated modules were present. Installation examples below require an explicitly selected artifact/environment; template contents alone do not establish a completed installation or search.

## Output and result-scope checks

The primary antiSMASH CLI admits the entire input/output roster before analysis or directory creation. Use new JSON/TSV files and a new or empty ordinary `--out-dir`; an occupied directory (including unrelated or hidden files) or a symlink directory is refused. Duplicate physical inputs, case/Unicode-insensitive ZIP-stem collisions, input/output aliases, overlapping output paths and multi-input `--out`/`--pairs` are refused with exit 2. Rename colliding input files explicitly while retaining their provenance, or run them separately into fresh directories. Preflight refusals preserve existing bytes.

For every successfully analyzed input in `--out-dir`, the CLI writes JSON, ranked-pair and related-locus TSVs, per-input summary/group TSVs, and the three completion tables. Requested pair TSVs and per-input related-locus TSVs are header-only when no rows exist: their empty schema contains identity/score fields (plus related-locus fields where applicable), while populated tables retain the engine's full columns. Zero rows describe the current result, not biological absence or proof that missing reference evidence was searched. Read the JSON and completion tier.

JSON/TSV files are created exclusively, including completion tables from the shared byte formatter. Concurrent filesystem changes or a write failure can still leave partial fresh outputs; this is not a transactional batch. An output failure returns 2. Per-input analysis exceptions remain recorded in `SUMMARY.tsv`, with final exit 1 if any input errored; earlier successful outputs remain and a failed input has no success JSON. These admission rules cover the primary antiSMASH CLI; the optional subcommands have their own write contracts.

The BLASTp layer returns 0 even when result queries are unmapped and excluded (`:105–117`). Review NOT_IN_RESULTS, unmapped queries and the exact query/result roster rather than interpreting a zero exit as complete coverage. Keep original files, generated manifest and input hashes. No cross-locus evidence transfer follows from a matching alias alone.

RG-GMCI surfaces antiSMASH regions in a fragmented genome assembly that may belong to one biosynthetic
pathway: fragments that the assembly left on separate contigs. It reads biosynthetic logic through the
ClusterBlast and KnownClusterBlast results that antiSMASH already wrote.

It is a homology-guided candidate method, not a contig joiner. Assembly fragmentation can have several causes; this reader does not determine which caused a particular break. A candidate is a hypothesis to check at gene level.

It has no required dependencies. Biopython is used when installed; otherwise a built-in
GenBank reader is used.

## Run it

```bash
pip install rggmci-*.whl
rggmci my_genome.antismash.zip --out result.json --pairs pairs.tsv --reference-completion off
rggmci antismash_zips/ --out-dir rggmci_results/ --reference-completion off
```

A successful batch writes one JSON, one pairs table and one related-locus table per genome, three
completion tables per genome, plus `SUMMARY.tsv` and `CANDIDATE_GROUPS.tsv`. Empty pair/related-locus
tables contain headers only. The examples above read saved antiSMASH evidence with completion explicitly
off; optional completion still defaults to auto when this flag is omitted.
[docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md) explains every column.

The input is an antiSMASH result ZIP that includes its `knownclusterblast/` and `clusterblast/` output.
A ZIP with only region GenBank files still runs, but no pairs can be scored without the reference hits.

### Starting from an assembly

rggmci does not call genes or detect clusters. antiSMASH does both, so run it on the assembly first:
- **Web server** ([antismash.secondarymetabolites.org](https://antismash.secondarymetabolites.org)): upload the
  FASTA and turn on **ClusterBlast**, which is off by default (or click "All on"). KnownClusterBlast is on by
  default. Download the result ZIP.
- **Command line:** `antismash --genefinding-tool prodigal --cb-general --cb-knownclusters --output-dir out assembly.fasta`,
  then give rggmci the result ZIP antiSMASH writes in `out/`.

The proteins `rggmci fasta` writes are antiSMASH's own gene calls, so no separate gene calling or Pfam scan
is needed.

## A second layer from your own BLASTp

`rggmci fasta` writes the proteins of the regions in HIGH cross-contig pairs as FASTA files sized for NCBI
web BLASTp, plus a manifest and a short how-to. You run the searches yourself. `rggmci blastp-layer` reads the
results back.

```bash
rggmci fasta my_genome.antismash.zip --out-dir queries/          # then BLASTp each queries/*.fasta on NCBI
rggmci blastp-layer --manifest queries/blastp_manifest.json \
       --hits Hit_Table.csv --xml2 results.xml --out-dir layer/
```

- Per region it takes up to 6 biosynthetic genes from the whole region, core genes first and nearest the
  contig end first. `--edge-genes N` adds the N genes nearest the break, of any kind. `--include-moderate` adds
  MODERATE pairs.
- Download both the Hit Table (CSV) and the Single-file XML2. The XML2 carries organism names and lists the
  queries that found nothing. A Hit Table alone cannot tell "no hits" from "not run".
- The layer reports, per pair, which source organisms carry homologs of both fragments' proteins. If the
  genome is already in NCBI, pass `--exclude-organism "<its species>"`, or its own proteins come back as hits.
- The layer sits beside the RG-GMCI confidence and never changes it. Similarity is not identity: shared
  homologs in one organism are a reason to look at that organism's genome, not proof of one pathway.

## Reference-guided completion

ClusterBlast lists the reference clusters each region resembles. Completion asks the reference itself where its genes
are. For each region at a contig edge, it takes the best KnownClusterBlast MIBiG reference and searches every protein
of that cluster against every protein in the genome, not only those inside antiSMASH regions. A missing piece of a
pathway can sit on a short contig that antiSMASH never flagged, and one gene can be cut in two by the assembly.

Per region it reports:
- each reference gene: present in the region, found clearly elsewhere, found ambiguously, or not found;
- reference genes split across two contig ends, with a call: `CLEAR`, `WEAK`, `RIVAL_STRONGER`,
  `MODULAR_UNRESOLVED` or `RECURRENT_COMMON_GENE`;
- partner contigs, each with the tests it passed: position near a contig end, read depth, a reciprocal search against
  all MIBiG proteins, and support from more than one gene.

A region with no KnownClusterBlast hit gets a discovered reference: the MIBiG cluster that most of its proteins match.

Completion needs two things and runs only when both are found:
- a MIBiG protein database, built once with `rggmci build-mibig-db` and given with `--mibig-db` or `$RGGMCI_MIBIG_DB`;
- an aligner: DIAMOND (`diamond` on PATH, `--diamond` or `$RGGMCI_DIAMOND`), or BLAST+ (`blastp` and `makeblastdb`
  on PATH). DIAMOND is faster. BLAST+ uses the same thresholds and gives comparable, not identical, tables.

It also needs the whole-genome GenBank file that antiSMASH writes into its result ZIP. A ZIP of region files alone
cannot be searched outside its regions.

```bash
rggmci build-mibig-db mibig_gbk/ mibig_proteins/                          # once
rggmci my_genome.antismash.zip --out-dir results/ --mibig-db mibig_proteins/
```

- `build-mibig-db` reads a folder of MIBiG GenBank files, one cluster per file, named by accession
  (`BGC0000001.gbk`). Files annotated by antiSMASH also carry each gene's role and domains, which it records.
- `--compounds index.json` adds compound names, in the form
  `{"entries": [{"accession": "BGC0000001", "compounds": ["abyssomicin C"]}]}`. Related entries then count as one
  compound family in the reciprocal search; without it, each entry is its own family.
- It writes the protein FASTA, a protein table, a cluster table and a manifest with checksums, plus a DIAMOND index
  when DIAMOND is found. It downloads nothing, and it refuses a folder that already holds files.
- With `pyhmmer` installed and a pressed `Pfam-A.hmm` (`--pfam` or `$RGGMCI_PFAM_HMM`), a lone find with two or more
  primary-metabolism genes among its four neighbours on each side (lysine or arginine synthesis, ribosomes, tRNA
  charging and similar) is set aside as housekeeping.

Every pair and table row says which tier ran: `FULL`, `NO_ALIGNER`, `NO_MIBIG_PROTEINS`, `NO_WHOLE_GENOME_GENBANK`
or `OFF` (`--reference-completion off`). Without completion the pairs are scored exactly as before. A tier other
than `FULL` means the search did not run; it does not mean no partner exists.

Completion is homology evidence. A partner is a candidate missing piece, a split gene is two pieces of one reference
protein at facing contig ends, no contigs are joined, and no score or confidence changes.
[docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md) describes every column.

## What it reports

- One row per scored region pair, with the two regions' contigs, products and edge status.
- `rggmci_confidence`: `HIGH_RG_GMCI_RESCUE`, `MODERATE_RG_GMCI_CANDIDATE` or
  `LOW_SHARED_REFERENCE_SIGNAL`.
  - HIGH needs a pair score over the threshold. The score counts shared references, references where
    the two regions' hits overlap or sit side by side, and whether the regions touch a contig end or
    lie on different contigs.
  - HIGH also needs at least two such overlapping or side-by-side references, and a specific shared
    product class or a known compatible hybrid.
  - Only regions antiSMASH flags as touching a contig edge are paired, and never two regions on one contig. A region
    antiSMASH places inside a contig is whole there, and two regions on one contig have no assembly break between
    them; such pairs are listed apart as related loci (`related_locus_pairs` in the JSON), never as rescues.
  - Product classes are compared by antiSMASH family, so an arylpolyene or PKS-like fragment matches a type I
    PKS as PKS, and a lanthipeptide matches as RiPP.
  - Further gates demote a pair that fails them: too few strong references, noise-only classes, a
    region linked to more than four HIGH partners, or paralog-like overlap. `acceptance_gate` says which gate
    acted; [docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md) lists every verdict.
  - Paralog-like overlap means the two regions hit the same genes of a reference. Up to 2 shared genes are
    tolerated when they are at most 15% of all genes hit and each region hits 2 genes of its own.
  - A pair held back only by the product-class gate, where one fragment carries only sugar genes, can return to
    HIGH when its partner is a backbone class (PKS,
    NRPS, RiPP, terpene) whose own region file names a glycosyltransferase. The two must be on different
    contigs, pass the gene-level split check, and tile 2 to 6 MIBiG clusters together.
- The references that support each pair.
- `both_at_contig_ends`: whether both regions of a pair run to a contig end. It describes where the
  fragments sit and hides nothing.
- Candidate groups: HIGH pairs on different contigs that share regions, gathered into one group. That is
  how a pathway spread over three or more fragments shows up.

Regions are named by contig and region number, exactly as antiSMASH named them, so every pair can be
found in the antiSMASH output. Cite a region by contig and region, never by its `BGC` alias alone: the alias is
rggmci's reading order and changes between antiSMASH runs.

[docs/WORKED_EXAMPLES.md](docs/WORKED_EXAMPLES.md) walks through four pairs from public genomes: a complementary
split, two copies of one cluster, a hub, and a pair with too little support.

## What it does not do

- It does not join contigs, fill gaps, or show that two fragments are physically adjacent.
- It does not name a compound. ClusterBlast similarity is similarity, not identity.
- Region products come from antiSMASH's own annotations. A shared product label is a reason to look,
  not proof of one pathway.

## Install

```bash
pip install "git+https://github.com/alexanderjsmith1/rggmci"          # or: pip install rggmci-*.whl
pip install "rggmci[bio] @ git+https://github.com/alexanderjsmith1/rggmci"  # with Biopython
```

Python 3.12 or newer. No other dependency is required.

## Cite

If you use rggmci, cite it (see `CITATION.cff`) and cite antiSMASH, whose output it reads:
antiSMASH 8.0, doi:10.1093/nar/gkaf334. Reference clusters come from MIBiG 4.0, doi:10.1093/nar/gkae1115.

## Where it comes from

`src/rggmci/PROVENANCE.json` records the source version this build came from, and the SHA-256 of every
source file used.

## Licence

MIT. See `LICENSE`.


## Shared invocation contract (`rggmci-shared-invocation-v3`)

The embedded pre-triage gate and standalone `run` use the same `run_archive` owner. Common preparation
binds complete region identities, source coordinates/products/order and pre-enrichment records. Internal snapshots require an immutable parser-created
process-local capability bound to archive bytes; caller JSON/hashes are not derivation authority. The
public standalone `run` rejects snapshot overrides. The
high-level default now supplies archive sequence context to the unchanged scoring gates. This is a
behavior-affecting standalone input migration: complexity-sensitive outcomes can differ from older
standalone runs. Explicit low-level `contigs=None` still means unavailable; explicit high-level None
disables automatic extraction. FASTA-first/longest-GBK-per-contig fallback is retained; clipped region
sequence is not a whole genome. Receipts contain lengths/hashes, never nucleotide/protein payloads.

Expected TypeError/ValueError/AttributeError coordinate failures retain legacy partial bounds and shared
diagnostics. Unexpected exceptions and typed resource refusals propagate. Relevant guarded GBK/FASTA
members refuse common intake before a subset is reported. General source-reader malformed/empty-member
warnings remain visible. The embedded wrapper cannot convert a canonical preparation refusal into an
empty successful RGGMCI result.

Both routes default to completion auto, sensitivity sensitive, threads4, residue scope st_paralog and
no registry anchor. MIBiG/Pfam database assets resolve explicit path, then the corresponding RGGMCI environment variable,
then an explicitly supplied registry anchor. Mamey no longer searches its installation ancestry
implicitly. A missing higher-priority database retains its explicit missing state. Existing aligner fallback remains:
DIAMOND tries explicit, then environment, then PATH; completion can fall back to BLAST+. Receipts bind
the actual selected content. Standalone
`--registry-from` matches Mamey `--rggmci-registry-from`; `--label` matches `--rggmci-label` for one input.
Mamey exposes matching `--rggmci-threads`, `--rggmci-diamond`, `--rggmci-diamond-db`,
`--rggmci-residue-scope`, `--rggmci-residue-work-dir` and `--rggmci-completion-work-dir` controls.
Shared threads reach both existing completion and residue interfaces; legacy low-level residue calls
retain their prior default. Completion OFF skips optional aligner probing; an explicit residue database
is a distinct requested layer. No automatic database download is introduced.

Per successful input the canonical set is eight artifacts: JSON and seven TSVs (ranked pairs, related
loci, candidate groups, summary, and three completion tables). Every row key is retained, including
later-row-only fields; nested evidence uses JSON cells with spreadsheet protection. Empty candidate
tables have headers only. Empty completion tables retain their explicit tier row. JSON includes full
region metadata and four-component endpoint identities: logical strain / full physical contig / region /
BGC alias. Ambiguous alias/source bindings refuse instead of being guessed. Scientific results and
effective resource fingerprints are shared; distribution/path/provenance presentation is confined to
`wrapper_context`. Compare complete analytical data, not a selected subset of scores.

Standalone primary writes remain exclusive and use whole-roster preflight; batch failures retain the
attempted-input denominator. Per-input canonical summary/group TSVs coexist with aggregate SUMMARY.tsv
and CANDIDATE_GROUPS.tsv. Mamey writes its canonical set before sealing with prefix
`<strain>_4A_RGGMCI_canonical`; legacy CSV/workbook views derive from the same result and remain distinct
presentation contracts. No legacy sealed package is rewritten. Shared source is an implementation
contract; runtime parity, optional active-resource profiles and published standalone synchronization
require their own bound validation. Candidate labels remain unadjudicated homology hypotheses, not
physical joins, compound identity or biological accuracy.

## Shared functional context (invocation schema v3)

The embedded and standalone high-level programs derive the same CDS/domain context directly from
archive features, using the shared native parser and gene-context builder. Ranked pairs and exported
split-candidate views retain `functional_rescue_class`, both core fractions and functional-role strings,
`modular_continuation`, and both assembly-line/release CDS counts. These are existing source-derived
annotations; they do not change RG-GMCI confidence thresholds or prove physical linkage or product identity.
The result also records functional/modular profiles and context counts bound to the input archive hash.

This migrates native-only annotations into the shared invocation. Package gene-context file write/readback
no longer determines scientific pair fields. Absent CDS context retains `UNKNOWN_NO_PROFILE` and existing
empty defaults; raised extraction/computation errors and resource refusals propagate consistently.
Existing general source-reader malformed/empty-member warnings remain visible.
The native wrapper consumes shared profiles for its downstream report/triage context. Low-level scorer
APIs and explicit unavailable sequence context (`contigs=None`) retain their previous semantics.
