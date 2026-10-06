# Isolate neighbourhood panel: 16S genome hits, NCBI genome table and TYGS

This page describes how to build one isolate's genome panel for core-genome trees, MLSA and ANI/AAI from three sources: the
isolate's 16S BLAST hits on complete genomes, NCBI's genome table, and the isolate's TYGS result. The panel holds the genomes the
isolate is actually near, not every genome in its genus. Tree building itself is described in
[PHYLOGENOMIC_TREES_METHOD.md](PHYLOGENOMIC_TREES_METHOD.md) and needs the project lead's go.

The tools are `tools/neighbour_panel_candidates.py` (builds the panel) and `tools/check_tygs_coverage.py` (checks it). Both read local
files only and make no network call.

## 1. The isolate's 16S

- **Source:** use the 16S gene from the isolate's own assembly. A published 16S accession is often a partial Sanger read.
- **Record** where the sequence came from: contig and coordinates, or accession.
- **Fragmented assemblies** often split the rRNA operon across contigs. Use the longest single piece, and do not join pieces from different contigs, because a join can build a chimera.
- **Short pieces:** a piece shorter than the minimum alignment length (section 5) gives no 16S genome hits. The panel then rests on TYGS.

## 2. 16S BLAST (NCBI web BLAST)

- **Search:** blastn (megablast) against `core_nt`, with the hit list set to 1,000.
- **Output:** save the result as tabular text, 12 columns (`qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue
  bitscore`).
- **Unpublished sequences** are sent only with the project lead's explicit permission for that batch.
- **Pacing:**
  - one search at a time;
  - at least 15 s between requests;
  - poll each search ID no more than once a minute;
  - send no email address;
  - never retry a failure automatically;
  - prefer evenings and weekends for more than about 20 searches.
- **Download every finished result.** A search ID stays retrievable for about 24 hours, so re-fetch a bad download with the same ID instead of
  searching again.
- **Check the download.** A finished search can return only its status block (`QBlastInfoBegin … Status=READY`) and no hits. Check that the file
  holds hit lines before counting the search as done.

## 3. NCBI genome table (`datasets` only)

```bash
datasets summary genome taxon Actinomycetota --assembly-level complete,chromosome --as-json-lines > assemblies.jsonl
datasets summary genome taxon Actinomycetota --from-type --as-json-lines > type_assemblies.jsonl
# sequence -> assembly map; query by accession list (one GCF per pair), in parallel chunks
datasets summary genome accession --inputfile chunk_aa --report sequence --as-json-lines > seq_chunk_aa.jsonl
```

- **Speed:** the sequence report runs at about one assembly per second, so run it over an accession list split into a few chunks.
- **Hits to genomes:** a BLAST subject sequence becomes a genome through this map.
- **Accession choice:** RefSeq (GCF) is preferred over the paired GenBank (GCA) accession.

## 4. TYGS

The tool reads the TYGS digital DDH tables (`comp_type`, `query_genome`, `subject_genome`, `digital_ddh_d4`, …) in **both** formats TYGS
results come in:

| Format | `subject_genome` example |
|---|---|
| HTML-tagged | `<I>Streptomyces</I> <I>sulphureus</I> <a …>DSM 40104</a>` |
| plain text | `Streptomyces sampsonii NBRC 13083` |

The isolate's top `--tygs-top` rows are taken by d4. Each is resolved to a type-material assembly:

1. **By species name:** the organism equals the species, or the species plus a subspecies or strain. `subsp.`, `pv.` and `var.` stay part of the
   species. A strain-designation match is preferred, then GCF.
2. **Otherwise by strain designation:** a type-material assembly whose recorded designations include the TYGS strain designation, with or without a trailing type "T". The recorded designations are the strain name plus the BioSample `strain` and `culture_collection` entries.
   - **Why this step exists:** NCBI files some type strains under a newer or synonym name. Examples: *S. gilvigriseus* MUSC 26T is *Mangrovactinospora gilvigrisea* MUSC 26, and *Nocardia soli* NBRC 100376 is *N. salmonicida* NBRC 100376.
   - **Logging:** each such match gets a `TYGS_resolved_by_designation` line naming the NCBI name.
   - **Short designations:** under 5 characters, they never match.
3. **A blank or unreadable name never resolves.** It is logged as `UNPARSED: …`.

**Every top row is either in the panel or logged in `PANEL_ISSUES.tsv`. A row is never dropped without a trace.** The cases:
- **Not added to the panel:** the type genome is excluded, or is a second deposit of a strain already present.
- **Ties at the cap:** rows tied with the last kept d4 but past the cap.
- **No type genome:** no type-material assembly under either the species name or the strain designation.

**Two designations, one genome:** when TYGS lists one type strain under two designations that resolve to the same assembly, both names are recorded in the panel row's `tygs_type_strain`, joined by "; ".

## 5. Build the panel

```bash
python tools/neighbour_panel_candidates.py --isolate ISOLATE_001 --blast blast/ISOLATE_001.tsv \
  --assemblies assemblies.jsonl --sequences seq_chunk_*.jsonl --type-assemblies type_assemblies.jsonl \
  --tygs tygs_digital_ddh_batch_a.tsv tygs_digital_ddh_batch_b.tsv --top-16s 100 --tygs-top 10 \
  --exclude OWN_GENOMES.txt --out-dir PANEL/ISOLATE_001
```

- **`PANEL_TREE.tsv`:** one row per assembly. `why` lists every source that added it (`16S_genome_hit`, `TYGS_type_strain`). The other columns give the best 16S identity with its subject sequence, the organism, the strain, the NCBI type-material text, the TYGS type strain(s) with d4, and the assembly level.
- **`PANEL_ISSUES.tsv`:** one line per item that was not added:
  - subject sequences with no complete or chromosome assembly;
  - TYGS rows not added, and why;
  - TYGS rows resolved by strain designation;
  - second deposits of one strain (`duplicate_strain`).
- **16S ranking:**
  - genome hits rank by best identity, then bitscore, over alignments of at least `--min-align` bp;
  - **the default is 600 bp**;
  - the top `--top-16s` are kept.
- **Excluded genomes:** the isolate's own genomes (`--exclude`) are removed **before** ranking, so they never take a slot.
- **One strain counts once.** Two assemblies sharing a BioSample, or with the same organism and strain designation, count as one strain. The second is logged as `duplicate_strain` and does not take a `--top-16s` slot.

Add the outgroup as described in [GTOTREE_PANEL_SELECTION.md](GTOTREE_PANEL_SELECTION.md), and record its reason in `why`.

## 6. Check the panels

```bash
python tools/check_tygs_coverage.py --tygs tygs_digital_ddh_*.tsv --panels-dir PANEL --strains ISOLATE_001:10 ISOLATE_002:5 --out TYGS_TOP_COVERAGE.tsv
```

The check reads the TYGS tables independently of the panel builder. It takes each strain's top N plus ties, and exits 1 if any row is
neither in `PANEL_TREE.tsv` (`tygs_type_strain`) nor logged in `PANEL_ISSUES.tsv`. Run it on every set of panels before trees are built.

## Claim limits

Panel membership is comparator selection. A 16S identity and a dDDH value measure relatedness. Neither is a species or genus call by
itself, and a 16S genome hit is not proof of nearest-neighbour status.
