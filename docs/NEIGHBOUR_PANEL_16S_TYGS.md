# Isolate neighborhood panel: 16S genome hits, NCBI genome table and TYGS

This page describes how to build one isolate's genome panel for core-genome trees, MLSA and ANI/AAI from three sources: the
isolate's 16S BLAST hits on complete genomes, NCBI's genome table, and the isolate's TYGS result. The panel holds the genomes the
isolate is actually near, not every genome in its genus. To build the tree, follow the
[phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md). A tree build needs approval first.

The tools are `tools/neighbour_panel_candidates.py` (builds the panel) and `tools/check_tygs_coverage.py` (checks it). Both read local
files only and make no network call.

## 1. The isolate's 16S

- **Source:** use the 16S gene from the isolate's own assembly. A published 16S accession is often a partial Sanger read.
- **Record** where the sequence came from: contig and coordinates, or accession.
- **Fragmented assemblies** often split the rRNA operon across contigs. Use the longest single piece, and do not join pieces from different contigs, because a join can build a chimera.
- **Short pieces:** a piece shorter than the minimum alignment length (section 5) gives no 16S genome hits. The panel then rests on TYGS.

## 2. 16S BLAST (NCBI web BLAST)

This step searches NCBI's `core_nt` online. For local searches against type strains only, build the local 16S RefSeq database described in [LOCAL_16S_DATABASE.md](LOCAL_16S_DATABASE.md).


- **Search:** blastn (megablast) against `core_nt`, with the hit list set to 1,000.
- **Output:** save the result as tabular text, 12 columns (`qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue
  bitscore`).
- **Unpublished sequences** are sent only if you have decided the sequence may leave your machine.
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

`datasets` is NCBI's command-line program for genome metadata. It is not part of this tool set and is not installed by default. Install it before this step, by either route, then check it with `datasets --version`:

- Download the `datasets` binary for your system from NCBI's command-line tools page, make it executable and put it on your `PATH`.
- Or, with conda: `conda install -c conda-forge ncbi-datasets-cli`.

Step 3 needs network access to NCBI. The two tools on this page do not.

```bash
datasets summary genome taxon Actinomycetota --assembly-level complete,chromosome --as-json-lines > assemblies.jsonl
datasets summary genome taxon Actinomycetota --from-type --as-json-lines > type_assemblies.jsonl
```

The sequence map comes from a second query. Its input, `chunk_aa`, is a plain text file of assembly accessions, one per line. Take the accessions from `assemblies.jsonl`, keep one per assembly (RefSeq `GCF_` where present), and split the list into chunks:

```bash
python3 -c "import json,sys; [print(json.loads(l)['accession']) for l in open('assemblies.jsonl') if l.strip()]" > accessions.txt
split -l 2000 accessions.txt chunk_
for c in chunk_??; do
  datasets summary genome accession --inputfile "$c" --report sequence --as-json-lines > "seq_$c.jsonl"
done
```

`split` names the pieces `chunk_aa`, `chunk_ab` and so on. This produces `seq_chunk_aa.jsonl`, `seq_chunk_ab.jsonl` and so on, which section 5 reads as `seq_chunk_*.jsonl`.

- **Speed:** the sequence report runs at about one assembly per second, so chunks keep each call short and let you restart one piece.
- **Hits to genomes:** a BLAST subject sequence becomes a genome through this map. The builder reads the `assembly_accession`, `genbank_accession` and `refseq_accession` fields.
- **Accession choice:** RefSeq (GCF) is preferred over the paired GenBank (GCA) accession.

## 4. TYGS

TYGS (the Type Strain Genome Server) compares a genome with type-strain genomes. Download the result tables from your TYGS job page and save them as TSV files. The tool reads the digital DNA-DNA hybridization (dDDH) tables (`comp_type`, `query_genome`, `subject_genome`, `digital_ddh_d4`, …). `d4` is the dDDH value from formula 4 (identities over HSP length). The tool reads **both** formats TYGS results come in:

| Format | `subject_genome` example |
|---|---|
| HTML-tagged | `<I>Streptomyces</I> <I>sulphureus</I> <a …>DSM 40104</a>` |
| plain text | `Streptomyces sampsonii NBRC 13083` |

The isolate's top `--tygs-top` rows are taken by d4. Each is resolved to a type-material assembly:

1. **By species name:** the organism equals the species, or the species plus a subspecies or strain. `subsp.`, `pv.` and `var.` stay part of the
   species. A strain-designation match is preferred, then GCF.
2. **Otherwise by strain designation:** a type-material assembly whose recorded designations include the TYGS strain designation, with or without a trailing type "T". The recorded designations are the strain name plus the BioSample `strain` and `culture_collection` entries.
   - **Why this step exists:** NCBI files some type strains under a newer or synonym name. Example: a strain listed by TYGS under its old species name may be filed at NCBI under a newer genus and species name.
   - **Logging:** each such match gets a `TYGS_resolved_by_designation` line naming the NCBI name.
   - **Short designations:** under 5 characters, they never match.
3. **A blank or unreadable name never resolves.** It is logged as `UNPARSED: …`.

**Every top row is either in the panel or logged in `PANEL_ISSUES.tsv`. A row is never dropped without a trace.** The cases:
- **Not added to the panel:** the type genome is excluded, or is a second deposit of a strain already present.
- **Ties at the cap:** rows tied with the last kept d4 but past the cap.
- **No type genome:** no type-material assembly under either the species name or the strain designation.

**Two designations, one genome:** when TYGS lists one type strain under two designations that resolve to the same assembly, both names are recorded in the panel row's `tygs_type_strain`, joined by "; ".

## 5. Build the panel

Before this step you should have:

- the 16S BLAST table from section 2;
- `assemblies.jsonl`, `seq_chunk_*.jsonl` and `type_assemblies.jsonl` from section 3;
- one or more TYGS tables from section 4;
- optionally, a list of the isolate's own genome accessions for `--exclude`.

```bash
python tools/neighbour_panel_candidates.py --isolate ISOLATE_001 --blast blast/ISOLATE_001.tsv \
  --assemblies assemblies.jsonl --sequences seq_chunk_*.jsonl --type-assemblies type_assemblies.jsonl \
  --tygs tygs_digital_ddh_batch_a.tsv tygs_digital_ddh_batch_b.tsv --top-16s 100 --tygs-top 10 \
  --exclude OWN_GENOMES.txt --out-dir PANEL/ISOLATE_001
```

Use a fresh output directory and a fresh checker report path. The builder creates its directory if needed but replaces `PANEL_TREE.tsv` and `PANEL_ISSUES.tsv` when they already exist; the checker also replaces its `--out` file. Preserve the preceding panel, source roster and hashes before a changed build.

The builder prints counts of the 16S and TYGS rows it used. A usable build has a `PANEL_TREE.tsv` with at least one row. Read every `PANEL_ISSUES.tsv` line before you use it. Some lines are counts, not one line per item (see below), so the issues file is not a full per-hit ledger. To trace one hit, look it up in your BLAST table.

- **`PANEL_TREE.tsv`:** one row per assembly. `why` lists every source that added it (`16S_genome_hit`, `TYGS_type_strain`). The other columns give the best 16S identity with its subject sequence, the organism, the strain, the NCBI type-material text, the TYGS type strain(s) with d4, and the assembly level.
- **`PANEL_ISSUES.tsv`:** columns `source`, `item` and `detail`. The `source` values are:
  - `16S_below_min_align`: one count line for the subject sequences with no alignment of at least `--min-align` bp;
  - `16S_blast`: one count line for the subject sequences with no complete or chromosome assembly in the index;
  - `16S_excluded`: one line per assembly removed by `--exclude` before ranking;
  - `16S_cap`: one line per mapped assembly ranked past the `--top-16s` cap;
  - `duplicate_strain`: one line per second deposit of a strain already in the panel;
  - `TYGS`: one line per row in the top `--tygs-top` (plus rows tied with the last one) that was not added, with the reason. TYGS rows ranked below that, and rows with no numeric `digital_ddh_d4`, get no line;
  - `TYGS_resolved_by_designation`: one line per TYGS row matched by strain designation rather than name.
  Lines your BLAST tool could not parse (fewer than 12 columns, or a non-number in the identity, length or bitscore column) are skipped without a line.
- **16S ranking:**
  - for each subject sequence, retain its highest-bitscore HSP meeting `--min-align`; choose each assembly's representative by identity, then bitscore, and rank assemblies the same way;
  - 12-column input uses raw BLAST `pident`. Optional appended `qseq` and `sseq` columns allow identity over unambiguous alignment columns; the output records `best_16S_identity_basis`. Keep that basis with each reported identity; these two identity readings are not interchangeable;
  - **the default minimum alignment length is 600 bp** (`--min-align`);
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

Exit 0 can mean zero rows were checked (wrong query labels, no `U vs. T` rows, unreadable d4 or N = 0). Check that the report has the rows you expected.

## Claim limits

Panel membership is comparator selection. A 16S identity and a dDDH value measure relatedness. Neither is a species or genus call by
itself, and a 16S genome hit is not proof of nearest-neighbor status.
