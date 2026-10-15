# Local 16S database: build it fully or for chosen genera, and which tools use it

Several bundle tools compare 16S rRNA gene sequences with type-strain 16S records. They read two local resources, which the bundle does not ship:

1. **The 16S RefSeq BLAST database.** This is NCBI's "16S ribosomal RNA (Bacteria and Archaea type strains)" database, named `16S_ribosomal_RNA`. Every tool that searches 16S reads it.
2. **The 16S SQLite store (optional).** `tools/phylo_16s_build_db.py` builds it from the BLAST database plus your own 16S sequences and their provenance. The panel and ranking tools read it.

Build the BLAST database first. The store is needed only for the panel and ranking tools.

## How the tools find the BLAST database

Every tool below resolves the database through one function, `tools/_phylo16s.py: refseq_16s_blastdb()`. One setting therefore reaches all of them. The order is:

1. the tool's own argument (`--db`, `--refseq-db`), when given;
2. `$SAPOTE_16S_DB`, then `$NCBI_16S_DB`;
3. the `ncbi_16s_blastdb` row of the workspace asset registry, `OFFICIAL_DATA/ASSET_REGISTRY.tsv`. Its `path` column is the prefix, or a folder holding `16S_ribosomal_RNA.*`;
4. `<workspace>/Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA`, then `<workspace>/blast_dbs/16S_ribosomal_RNA`; the first that has database volumes is used.

Keep one copy and point everything at it. Two copies of different dates would give different answers from different tools. BLAST+ cannot read a database path that contains spaces, so keep it in a path without spaces.

The BLAST programs are found through `$BLAST_BIN` (a folder), then `PATH`.

## Full build (all type strains)

The download is about 70 MB compressed; NCBI rebuilds it regularly.

```bash
mkdir -p /data/16s && cd /data/16s
update_blastdb.pl --decompress 16S_ribosomal_RNA
```

`update_blastdb.pl` ships with BLAST+. Without it, fetch and check the archive by hand:

```bash
curl -O https://ftp.ncbi.nlm.nih.gov/blast/db/16S_ribosomal_RNA.tar.gz
curl -O https://ftp.ncbi.nlm.nih.gov/blast/db/16S_ribosomal_RNA.tar.gz.md5
md5sum -c 16S_ribosomal_RNA.tar.gz.md5     # macOS: compare `md5 -q 16S_ribosomal_RNA.tar.gz` with the .md5 file
tar -xzf 16S_ribosomal_RNA.tar.gz
```

Record what you built. The header names the database, its sequence count and its date, and it belongs in the Methods:

```bash
blastdbcmd -db /data/16s/16S_ribosomal_RNA -info
export SAPOTE_16S_DB=/data/16s/16S_ribosomal_RNA
```

## Partial build (chosen genera, without the full download)

NCBI holds the bacterial type-strain 16S records in BioProject PRJNA33175 and the archaeal ones in PRJNA33317. A query on one genus returns only that genus's records. NCBI EDirect (`esearch`, `efetch`) runs the query:

```bash
esearch -db nucleotide -query '33175[BioProject] AND Nocardia[Organism]' \
  | efetch -format fasta > Nocardia_16S.fasta
makeblastdb -in Nocardia_16S.fasta -dbtype nucl -parse_seqids \
  -title "16S RefSeq type strains: Nocardia" -out /data/16s/Nocardia_16S
blastdbcmd -db /data/16s/Nocardia_16S -info
export SAPOTE_16S_DB=/data/16s/Nocardia_16S
```

For several genera, join them in one query: `33175[BioProject] AND (Nocardia[Organism] OR Rhodococcus[Organism])`. The same query works through the plain E-utilities web interface; keep to NCBI's request rate.

**What a partial database cannot do.** It answers "the nearest type strain *among the genera you chose*" only. A query whose true nearest type strain belongs to another genus finds a worse match, or none, and a genus-routing step cannot see the missing genera. Name the genera in every output and caption made from a partial database. Use the full database for routing, nearest-type checks and novelty statements.

**A subset from a full copy you already have.** List the accessions you want in a file, then run `blastdbcmd -db <full> -entry_batch accessions.txt > subset.fasta` and `makeblastdb` as above. For a placement run, `tools/harvest_16s.py --genus <Genus> --strains <ids> --out-dir <dir>` writes that genus's reference FASTA from the full database beside your query FASTA. It needs your strains and their 16S FASTA (`--authoritative`).

## The 16S SQLite store

Preview with `--dry-run`, then build into a new file:

```bash
python tools/phylo_16s_build_db.py --db /data/16s/rrna16s.sqlite \
  --refseq-blastdb /data/16s/16S_ribosomal_RNA --refseq-type-material \
  --authoritative-fasta my_isolates_16S.fasta --provenance my_isolates_provenance.tsv --dry-run
python tools/phylo_16s_build_db.py --db /data/16s/rrna16s.sqlite \
  --refseq-blastdb /data/16s/16S_ribosomal_RNA --refseq-type-material \
  --authoritative-fasta my_isolates_16S.fasta --provenance my_isolates_provenance.tsv
python tools/phylo_16s_validate_db.py --db /data/16s/rrna16s.sqlite --out-dir /data/16s/validate_reports
export SAPOTE_16S_SQLITE=/data/16s/rrna16s.sqlite
```

`--refseq-type-material` declares that the BLAST source holds type material only; this is true of `16S_ribosomal_RNA`. The input, provenance and later fetch/rank steps are described in [PHYLO_16S_DATA_CONTRACT.md](PHYLO_16S_DATA_CONTRACT.md). A partial BLAST database gives a partial store, with the same limits as above.

## Which tools use what

| Tool | Reads | Used for |
|---|---|---|
| `tools/sixteen_s_similarity_check.py` | BLAST database | Do deposited "closest type strain, % similarity" values reproduce? Also finds the nearest type strain overall. Writes `<out>.receipt.json` with the database prefix and its `-info` header. |
| `tools/comparator_select.py` | BLAST database | Nearest *named* type strain for picking comparator genomes |
| `tools/phylo_16s_from_genome.py` | BLAST database | Candidate 16S spans from an assembled genome |
| `tools/phylo_autopilot.py route`, `run-16s` | BLAST database | Genus routing, with GENUS_CONFLICT flags, and placement reference sets |
| `tools/harvest_16s.py` | BLAST database | Per-genus reference FASTA for EPA-ng placement |
| `tools/phylo_refset.py` | BLAST database | Right-sized, de-duplicated reference sets |
| `tools/outgroup_registry.py` | BLAST database | The cached 16S of each registered outgroup |
| `tools/phylo_16s_build_db.py` | BLAST database → store | Builds the SQLite store |
| `tools/phylo_16s_panel.py`, `phylo_16s_rank.py`, `phylo_16s_fetch.py`, `phylo_16s_esearch.py`, `phylo_16s_audit_merges.py`, `phylo_16s_validate_db.py` | SQLite store | Panels, ranking, fetches, merge screens, defect checks |

The same resources feed the isolate neighbourhood panel ([NEIGHBOUR_PANEL_16S_TYGS.md](NEIGHBOUR_PANEL_16S_TYGS.md)), the placement workflow ([PHYLO_PLACEMENT_WORKFLOW.md](PHYLO_PLACEMENT_WORKFLOW.md)) and outgroup selection ([OUTGROUP_AND_REFSET_WORKFLOW.md](OUTGROUP_AND_REFSET_WORKFLOW.md)).

## How identity is measured

`sixteen_s_similarity_check.py` and `comparator_select.py` measure identity the same way:

- **Every record is searched.** `-max_target_seqs` is set to the database's sequence count. BLAST keeps the first N subjects in its own order, not the N most identical, so a small cap misses the nearest type strain in large genera such as *Streptomyces* and *Nocardia*.
- **Ambiguous bases are left out.** BLAST's `pident` counts every IUPAC code (N, R, Y and so on) as a mismatch. A partial Sanger read with 27 ambiguous calls in 702 bp loses about 3.8 points that way. The tools report identity over the alignment columns where both sequences carry A, C, G, T or a gap (`_phylo16s.unambiguous_identity`). Gaps still count as differences.
- The similarity check writes both readings: `nearest_identity` (BLAST `pident`) and `nearest_identity_unambiguous`, with `query_ambiguous_bp`. Quote the unambiguous value against a species threshold.

## What to put in Methods

- the database title, sequence count and date, from `blastdbcmd -info`;
- full or partial, with the genera when partial;
- the BLAST+ version;
- the tool and its thresholds; for the similarity check, hits covering at least 90% of the query, with a flag at the chosen point difference;
- that identity was computed over unambiguous positions, across every record in the database.

A 16S similarity is a relatedness measurement. A value below a species threshold marks a candidate for genome comparison; it is not a species call.
