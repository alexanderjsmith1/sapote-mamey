# Gene-level analysis guide

This guide shows how to read a biosynthetic gene cluster (BGC) gene by gene. Use it after you have a sealed package for a strain. You end up with a per-gene table for one region, a rescue check, and a short evidence note you can hand to a Mode B card. Terms such as BGC, KCB, RG-GMCI and Mode B are in the [glossary](GLOSSARY.md). For install and the first run, see [first run](reader/01_FIRST_RUN.md).

Every result here is capacity. A gene shows that a pathway step could exist. It does not show that the strain makes a compound. A similar sequence is not the same compound.

## The rule

Read the genes. Do not classify a region from its antiSMASH product label alone.

antiSMASH reports regions. A region can merge neighboring clusters, which inflates any region-level domain sum. It can also split one cluster across contigs, which deflates it. Gene-level reading helps you spot both, but it does not settle the region boundaries, the assembly's coverage or whether two contigs are linked. Keep those as open questions with their evidence. A reference cluster that looks incomplete may be finished on another contig, so check RG-GMCI before you call a locus partial.

Name every locus with four parts, copied from one source row: `strain / full node-or-contig / region / BGC alias`. Do not shorten it.

## 1. List the BGCs

```bash
python mamey_run.py list-bgcs runs/EXAMPLE/package --top 10
```

You see a table of BGCs in triage order. Add `--json` for a machine-readable list, or `--include-dropped` to see BGCs removed as primary metabolism. Pick one BGC. Write down its strain, contig, region and alias.

The command needs a sealed package. If it fails, validate the package first (see [read results](reader/03_READ_RESULTS.md)).

## 2. Read the per-gene tables

A package holds the gene tables for each BGC. Open them in a spreadsheet or with a script.

- `EXAMPLE_cds_table.csv`: one row per gene in a BGC. Columns include `locus_tag`, `start`, `end`, `strand`, `length_aa`, `product` and `sec_met_domains`.
- `EXAMPLE_domains.csv`: one row per domain on a BGC gene, with `domain`, `pfam_acc`, `bitscore`, `evalue` and `substrate`.
- `EXAMPLE_gene_context.jsonl`: the same genes, one line per BGC.

Filter on your BGC's `contig` and `region`. Check three things.

1. Does the gene set cover a committed core, assembly or maturation, tailoring, and export or resistance? List what is missing.
2. Is the region on a contig edge? An edge region can be cut mid-cluster.
3. Do two genes share a `locus_tag` across contigs? Match on the full identity, not the tag alone.

An empty table is not evidence that a gene is absent. The tables hold only the genes antiSMASH placed in a region.

## 3. Look at one locus in detail

```bash
python mamey_run.py modeb-gene-first --package runs/EXAMPLE/package \
  --strain EXAMPLE --node NODE_7_length_120000_cov_42.5 \
  --region region002 --bgc BGC007 --out explorations
```

The `--out` folder must already exist. A success prints a JSON receipt and exits 0. A refusal prints a line starting `MODEB_GENE_FIRST_SOURCE_HOLD` or `MODEB_GENE_FIRST_OUTPUT_REFUSED` and exits 1. Open the `.md` file it writes first. [Mode B gene-first exploration](MODEB_GENE_FIRST_EXPLORATION.md) lists the outputs and the evidence-index option.

For the domain order of one region, run:

```bash
python mamey_run.py hmm-adjudicate path/to/EXAMPLE.region002.gbk
```

Add `--locus <locus_tag>` to see the module layout of one gene. The command reads a region GBK from the antiSMASH ZIP, so unzip the ZIP into a working folder first.

It also needs the scanner HMM database. That database is an add-on and is not in the code ZIP (see [find a missing input](COMPANION_FILES.md)). The command looks for it in `Wheelhouse/hmm/` or the add-on folder. Set the environment variable `SM_HMM_DB` to a database file, or pass `--hmm <file>`, to point at it. If the command prints `no HMM database available` and no domain readout, it did not run, even though it exits 0.

## 4. Check for a rescue

A KCB-dark or fragmented region may still pair with another region that supplies the missing genes. RG-GMCI proposes such pairs from reference similarity and gene context. The contigs stay separate sequences.

1. Find the pairs for your strain in `EXAMPLE_4A_RGGMCI_ranked_pairs.csv` in the package. Look for your locus as either side of a pair.
2. Run the second check on the package:

   ```bash
   python mamey_run.py two-proof-rescue runs/EXAMPLE/package --input-zip inputs/EXAMPLE.zip
   ```

   The default policy needs the antiSMASH ZIP the package was built from. Run `two-proof-rescue --help` for the other policies.
3. For genes missing from the reference, a gap-rescue run searches the whole assembly. It is heavy, runs one genome at a time, and needs DIAMOND and MIBiG reference files. Read [gap-rescue evidence in a card](MODEB_GAP_RESCUE_READER.md) before you start.

A pair is a hypothesis about linkage. Compare the competing partners and the genes that support each one. Do not call two contigs one cluster from a ranked pair alone. Detail on the atlas view is in [the RG-GMCI rescue atlas](RGGMCI_RESCUE_ATLAS.md).

## 5. Read the assembly line for NRPS and PKS regions

For modular synthase regions, count modules per gene.

```bash
python mamey_run.py assembly-line runs/EXAMPLE/package --out post_seal/EXAMPLE
python mamey_run.py domain-level runs/EXAMPLE/package --top-n 10 --out post_seal/EXAMPLE_domain_level
```

Both commands read the sealed package. Send `--out` to a new folder outside the package. With `--out` outside the package, `domain-level` leaves the package's bytes unchanged. Without `--out`, or with an `--out` inside the package, it writes `domain_level/` there and refreshes `post_seal_checksums.txt`. An occupied output folder is refused (`REFUSED`, exit 2). `assembly-line` writes a predicted assembly line for each BGC. `domain-level` writes the domain-level enrichment for the top leads.

Two standalone helpers work on region GBKs from the antiSMASH ZIP. Run them from the bundle root.

```bash
python tools/gene_assembly_line.py --dir regions/ --out gene_catalog.tsv
python tools/nrps_substrate.py path/to/EXAMPLE.region002.gbk
python tools/pks_product_class.py path/to/EXAMPLE.region002.gbk
```

- `gene_assembly_line.py` counts modules per gene from the `nrpspksdomains` features. It prints `wrote gene_catalog.tsv: N assembly-line genes` on success. It reads only genes whose IDs follow the `ctg<digits>_<digits>` pattern. An empty catalog can mean the IDs do not match, not that the region has no modular genes.
- `nrps_substrate.py` lists predicted adenylation substrates in gene order. It flags nonproteinogenic building blocks that match siderophore, glycopeptide or lipopeptide patterns. A pattern match is a lead to confirm with other genes, not a class call.
- `pks_product_class.py` reads the reductive domains per module and gives a rough class (aromatic, polyene, reduced macrolide). It is a domain-order heuristic.

The catalog takes the strain from the first underscore-delimited part of each file name and the contig from a `NODE_..._length_...` part. It writes no BGC alias. Map each row back to a full four-part identity yourself before you cite it.

## 6. Add homology context

Compare the core proteins to MIBiG reference proteins. This is the gene-level counterpart to KCB, which compares whole clusters. Keep the two separate.

```bash
python tools/bigscape_blastp_novelty.py build --help
python tools/bigscape_blastp_novelty.py query --help
python tools/bigscape_blastp_novelty.py modeb --help
```

`build` makes a MIBiG protein database from a folder of reference GBKs (`--mibig-dir`) and records the release you name with `--mibig-release`. `query` searches your proteins (`--targets`, a protein FASTA) against it. `modeb` turns the result TSV into a Markdown block. `query` needs BLAST+ (`blastp`) on your path. The tool name is historical. It does not run BiG-SCAPE, and its output is not a BiG-SCAPE family result. For BiG-SCAPE, see the [cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md). Run each `--help` and use the flags it lists.

The `pident` column is percent amino-acid identity. Read it with query coverage, subject coverage, E-value and bitscore. A low-identity hit over low coverage says little. A high-identity hit to a reference is similarity, not proof of the same product. A query with no result row is unavailable, not a tested negative.

## 7. Write the evidence into a card

The per-gene findings go into the Mode B card for the BGC. Follow the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). Use the section layout of the profile you chose (see the [current50 contract](MODEB_CURRENT50_V2_CONTRACT.md)), not section numbers from memory.

`tools/gene_modeb_enrichment.py` can print a block from a region GBK for a card. Pass `--complete-identity "strain / full node-or-contig / region / BGC alias"` so the block carries the full identity. Its 15 kb contig label is a local heuristic taken from a `length_<digits>` part of the file name. It is not a measure of cluster completeness.

To carry the section 6 search result into the block, use the bound route. Pass the `query` result TSV with `--mibig-protein-tsv` and its SHA-256 with `--mibig-protein-tsv-sha256`. Also pass a protein roster TSV with `--mibig-protein-roster` and `--mibig-protein-roster-sha256`. The roster lists every gene you searched, with its length and translation SHA-256, under the same complete identity. Get each digest with `shasum -a 256 <file>`. The command refuses a TSV that is not bound to the roster, a query missing from the roster, a hash mismatch, or a missing database receipt. The older `--blastp-pct` summary is unbound. It is not enough for a finished card.

For RiPP precursor motifs, use [saved RiPP evidence](ANTISMASH_INPUTS_CONSUMED.md#read-saved-ripp-motif-evidence). The motif table and `gene_data.json` are different views. Reconcile both against the full locus identity before you reuse either.

## What to write down

For each BGC you read, record:

- the full four-part identity;
- the genes you checked and the files they came from;
- the RG-GMCI result and whether a second check was run;
- the homology channels you ran, kept separate;
- what is missing or contradictory.

Say "capacity consistent with" for pathway steps. Do not write that the strain produces a compound.
