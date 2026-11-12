# rggmci: Reference-Guided Genome Mining Candidate Inference (RG-GMCI)

RG-GMCI surfaces antiSMASH regions in a fragmented genome assembly that may belong to one biosynthetic
pathway. The candidate regions lie on separate contigs; that alone does not establish that an assembly
break separated one pathway. It reads biosynthetic logic through the
ClusterBlast and KnownClusterBlast results that antiSMASH already wrote.

It is a homology-guided candidate method, not a contig joiner. An assembly can break for several reasons, and
rggmci does not say which one caused a particular break. A candidate is a hypothesis to check at gene level.

## Install

```bash
pip install "git+https://github.com/alexanderjsmith1/rggmci"
```

Python 3.12 or newer. Biopython is installed with it; it reads joined and origin-spanning gene locations.

## Run it

```bash
rggmci my_genome.antismash.zip --out result.json --pairs pairs.tsv --reference-completion off
rggmci antismash_zips/ --out-dir rggmci_results/ --reference-completion off
```

The first line scores one genome. The second scores every ZIP in a folder. These examples turn reference-guided
completion off; without the flag it runs whenever its database and aligner are found (see below).

`--out`, `--pairs` and `--out-dir` must be new files or a new or empty folder. Every input path and output path is
checked before any work starts, and a clash stops the run before anything is written. Archive contents are
read later, during the run, so a damaged ZIP fails then, with exit 1.

With `--out-dir`, each genome gets eight files:
- `<genome>.json`, the result;
- `<genome>_pairs.tsv`, the scored region pairs (see the limit below);
- `<genome>_related_loci.tsv`, `<genome>_candidate_groups.tsv` and `<genome>_summary.tsv`;
- three completion tables: `_reference_completion.tsv`, `_split_genes.tsv` and `_partner_contigs.tsv`.

The folder also gets `SUMMARY.tsv` and `CANDIDATE_GROUPS.tsv` across all genomes. A table with no rows has its
header only; a pair table with no scored pairs has only its first 15 columns. [docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md) explains every column.

A genome can score thousands of pairs. The pair table and the JSON's `ranked_pairs` keep the top 1,000 by rank, plus
every HIGH pair below them. `pairs_total` in the JSON and `scored_pairs` in `SUMMARY.tsv` count every scored pair;
`pairs_exported` counts the rows kept. Truncation is `scored_pairs - pairs_exported`; those omitted
pairs were scored, not absent or negative. The JSON's `rggmci_summary.ranked_pairs_not_exported` records the
omitted count, and the console states scored, retained, omitted and truncation explicitly. For example, one
previously checked public worked archive scored 1,360 pairs and retained 1,000: 360 were not exported. This
is a historical count example, not a new run on that archive. The retained count can exceed 1,000 because
later HIGH pairs are always kept. HIGH and MODERATE summary totals count all scored pairs, not just the export.

Exit codes:

| Exit code | Meaning |
|---|---|
| `0` | Every genome was scored. |
| `1` | At least one genome failed; the console names the input and error type. With `--out-dir`, its row in `SUMMARY.tsv` gives the error in the `error` column, and it has no JSON. In single-file `--out` / `--pairs` mode no `SUMMARY.tsv` is written. |
| `2` | The command was refused (a missing input, a clash between inputs or outputs, an occupied folder), or a file could not be written. |

Zero pairs means none scored in this run. It does not mean the genome has no split pathway: read the JSON's
`reference_map_status` and `reference_completion.completion_tier`, and with `--out-dir` each completion
table's `completion_tier`.

## The input it needs

A saved antiSMASH result ZIP with its region GenBank files and the cluster-level `knownclusterblast/` (KCB) or
`clusterblast/` (CB) results, or both. Each channel can support a pair on its own. SubClusterBlast alone is not
pairing evidence. A ZIP of region files without CB or KCB results can be read, but it gives no
reference-supported pairs.

### Starting from an assembly

rggmci does not call genes or detect clusters. antiSMASH does both, so run it on the assembly first:
- **Web server** ([antismash.secondarymetabolites.org](https://antismash.secondarymetabolites.org)): upload the
  FASTA and turn on **ClusterBlast**, which is off by default (or click "All on"). KnownClusterBlast is on by
  default. Download the result ZIP.
- **Command line:** `antismash --genefinding-tool prodigal --cb-general --cb-knownclusters --output-dir out assembly.fasta`,
  then give rggmci the result ZIP antiSMASH writes in `out/`.

The proteins `rggmci fasta` writes are antiSMASH's own gene calls, so no separate gene calling or Pfam scan
is needed.

## What it reports

- One row per kept region pair (the top 1,000 by rank, plus every HIGH pair), with the two regions' contigs,
  products and edge status.
- `rggmci_confidence`: `HIGH_RG_GMCI_RESCUE`, `MODERATE_RG_GMCI_CANDIDATE` or
  `LOW_SHARED_REFERENCE_SIGNAL`.
  - HIGH needs a pair score over the threshold. The score counts shared references, references where
    the two regions' hits overlap or sit side by side, and whether the regions touch a contig end or
    lie on different contigs.
  - HIGH also needs at least two such overlapping or side-by-side references, and a specific shared
    product class or a known compatible hybrid.
  - Only regions at a contig edge are paired, and never two regions on one contig. Two regions on one contig are
    listed apart as related loci (`related_locus_pairs` in the JSON), never as rescues. rggmci reads antiSMASH's own `/contig_edge` flag on each region feature. When the flag is missing, or the region's
    features disagree, it uses its own edge status instead. An explicit region-feature `False` excludes the
    region even when that fallback status is `Edge`. Flags on protocluster or candidate-cluster features do
    not substitute for the region feature. Missing source members and an unreadable source ZIP also use
    the fallback (`Edge` or `Full-contig`, defined in
    [docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md)). This is a rule of the method. A region inside a contig can still lack
    pieces that the assembly or antiSMASH did not show; rggmci does not look for them.
  - Product classes are compared by antiSMASH family, so an arylpolyene or PKS-like fragment matches a type I
    PKS as PKS, and a lanthipeptide matches as RiPP.
  - Further gates demote a pair that fails them: too few strong references, noise-only classes, a
    region linked to more than four HIGH partners, or paralog-like overlap. `acceptance_gate` says which gate
    acted; [docs/OUTPUT_GUIDE.md](docs/OUTPUT_GUIDE.md) lists every verdict.
  - Paralog-like overlap means the two regions hit the same genes of a reference. Up to 2 shared genes are
    tolerated when they are at most 15% of all genes hit and each region hits 2 genes of its own.
  - A pair held back only by the product-class gate, where one fragment carries only sugar genes, can return to
    HIGH when its partner is a backbone class (PKS, NRPS, RiPP, terpene) whose own region file names a
    glycosyltransferase. The two must be on different contigs, pass the gene-level split check, and tile 2 to 6
    MIBiG clusters together.
- The references that support each pair.
- `both_at_contig_ends`: whether both regions of a pair run to a contig end. It describes where the
  fragments sit and hides nothing.
- Candidate groups: HIGH pairs on different contigs that share regions, gathered into one group. That is
  how a pathway spread over three or more fragments shows up.
- Gene context, when the ZIP's gene annotations allow it: each fragment's functional roles and core fraction, and
  whether a modular assembly line continues across the pair. These describe the pair and never change a score.

To cite one region of a pair, copy `identity_a` or `identity_b`: strain / full contig name / region / BGC alias.
The strain label is the ZIP name or `--label`; rggmci does not check it against any taxonomy. The alias
(`BGC014`) is a reading order and can change between runs, so never use it alone.

[docs/WORKED_EXAMPLES.md](docs/WORKED_EXAMPLES.md) walks through four pairs from public genomes: a complementary
candidate split, overlapping-reference signal compatible with duplicate or related loci, a hub, and a pair
with too little support. These software descriptions do not establish two biological copies or one pathway.

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
  primary-metabolism genes among its four neighbors on each side (lysine or arginine synthesis, ribosomes, tRNA
  charging and similar) is set aside as housekeeping.

Every pair and table row says which tier ran: `FULL`, `NO_ALIGNER`, `NO_MIBIG_PROTEINS`, `NO_WHOLE_GENOME_GENBANK`
or `OFF` (`--reference-completion off`). Without completion the pairs are scored exactly as before. A tier other
than `FULL` means the search did not run; it does not mean no partner exists.

Completion is homology evidence. A partner is a candidate missing piece, a split gene is two pieces of one reference
protein at facing contig ends, no contigs are joined, and no score or confidence changes.

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
- A Hit Table saved without its header row is read when its columns can be matched unambiguously. Otherwise it is
  refused; download it again with the header.
- `blastp-layer` exits 0 even when some queries are missing from your results. Check `NOT_IN_RESULTS` and the
  unmapped list before treating the layer as complete.
- The layer reports, per pair, which source organisms carry homologs of both fragments' proteins. If the
  genome is already in NCBI, pass `--exclude-organism "<its species>"`, or its own proteins come back as hits.
- The layer sits beside the RG-GMCI confidence and never changes it. Similarity is not identity: shared
  homologs in one organism are a reason to look at that organism's genome, not proof of one pathway.

## What it does not do

- It does not join contigs, fill gaps, or show that two fragments are physically adjacent.
- It does not name a compound. ClusterBlast similarity is similarity, not identity.
- Region products come from antiSMASH's own annotations. A shared product label is a reason to look,
  not proof of one pathway.

## Cite

If you use rggmci, cite it (see `CITATION.cff`) and cite antiSMASH, whose output it reads:
antiSMASH 8.0, doi:10.1093/nar/gkaf334. Reference clusters come from MIBiG 4.0, doi:10.1093/nar/gkae1115.

## Where it comes from

rggmci is built from the Sapote-Mamey pipeline, which runs the same scorer. `src/rggmci/PROVENANCE.json` records
the source version, build and the SHA-256 of each engine source file copied into the package.
[CONTRIBUTING.md](CONTRIBUTING.md) says where to send a fix.

## License

MIT. See `LICENSE`.
