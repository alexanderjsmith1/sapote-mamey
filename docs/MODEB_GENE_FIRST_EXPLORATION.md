# Mode B gene-first exploration

`modeb-gene-first` gives you a quick look at the genes of one region before you write a card. It works offline on one sealed locus. It does not write a Mode B card and makes no biological calls. It is optional and is not part of the standard card recipe in the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). Terms such as RG-GMCI, KnownClusterBlast, MIBiG and BiG-SCAPE are in the [glossary](GLOSSARY.md).

The locus is always named by four parts: `strain / full node-or-contig / region / BGC alias`. The command refuses a shortened `NODE_n` token, conflicting identities, placeholder gene rows, a malformed evidence index and an existing output folder. It refuses before it writes anything.

## Usage

Take the four values from one row of `<strain>_2_inventory.csv` in the package: `Strain`, `Contig`, `antiSMASH_Region` and `BGC_ID`.

```bash
python mamey_run.py modeb-gene-first \
  --package runs/EXAMPLE/package \
  --strain EXAMPLE \
  --node NODE_7_length_120000_cov_42.5 \
  --region region002 \
  --bgc BGC007 \
  --out explorations
```

The package must already be sealed and validated. The `--out` folder must already exist. The command makes one child folder in it, named `STRAIN__NODE__region__BGC__SapoteMamey_v<bundle-version>`, with the four files below.

On success the command prints a JSON receipt and exits 0. On a refusal it prints one line with the reason and exits 1. The line starts with one of four prefixes:

- `MODEB_GENE_FIRST_IDENTITY_HOLD`: the strain, full node-or-contig, region or BGC alias is missing, shortened, malformed, or disagrees with the manifest or a source row;
- `MODEB_GENE_FIRST_SOURCE_HOLD`: an input file is missing, unreadable or malformed;
- `MODEB_GENE_FIRST_DATABASE_HOLD`: a `--database-selection` input is refused;
- `MODEB_GENE_FIRST_OUTPUT_REFUSED`: the output root or child folder cannot be used.

Save the whole line; the text after the prefix names the field or file. A refusal that happens before the write stage leaves no output. A failure after the child folder is made can leave a partial set, and the next try refuses that folder. Keep that folder and the refusal line as they are, since they show how far the run got. Retry with a new `--out` root.

## Optional evidence index

`--evidence-index evidence.tsv` binds outside evidence without scanning your workspace. It is a tab-separated file with this header:

```text
channel  strain  full_node  region  bgc_alias  gene  evidence_state  source_locator  source_sha256  note
```

- Every row must carry the same complete identity.
- `evidence_state` is `BOUND`, `UNBOUND`, `MISSING` or `NOT_RUN` for every channel except `historical_card`. `LEAD_ONLY` is the only state allowed for `historical_card`, and it is refused in any other channel.
- A `BOUND` row needs a portable relative path, an `evidence://` or a `package://` locator, and a 64-character SHA-256.
- Historical cards go in the `historical_card` channel and must be `LEAD_ONLY`. They never add support or rank.

The ten evidence channels stay separate: nr, ClusteredNR, local Swiss-Prot, MIBiG/KnownClusterBlast, ClusterBlast, BiG-SCAPE, RG-GMCI, cohort comparison, domain/HMM and literature context. No channel stands in for another.

## Outputs

Open the `.md` file first.

- `<identity>__SapoteMamey_v<version>__MODEB_GENE_FIRST_EXPLORATION.md`: a short, claim-capped synthesis and one next analysis.
- `..__important_genes.tsv`: the review order, with the full identity on every row.
- `..__evidence_channels.tsv`: availability by channel. A missing channel is a workflow gap, not biological absence.
- `..__exploration_receipt.json`: input and output hashes, and the bundle versions of the tool and the package. It does not list itself, so hash it yourself if you need to bind it.

The gene order is an inspection order: role category first, then the number of bound channels, then coordinates and locus tag. It is not a score of biological importance. These outputs are working notes pending scientific review.

## Optional frozen database bridge

`--database-selection selection.json` adds observations from frozen search databases to the receipt, the important-gene table and the synthesis. It builds on databases you already have. This page does not cover how they are made.

The JSON uses the schema string `mamey.gene-first-database-selection/1` and a `package_manifest_sha256`. It names exactly four entries under `databases`: `census`, `nr`, `clusterednr` and `local_swissprot`. Each entry gives a `root`, a relative `manifest` path and a `manifest_sha256`. Paths are configuration. The tool never finds databases by glob or file date, and it never copies or changes them.

The package must seal its all-gene CSV and `<strain>_proteins.faa` in the manifest. An outside `--gene-table` cannot replace them here. The package roster is the gene denominator, including boundary genes that the databases lack. A gene whose sequence or geometry disagrees with the census stays unbound and is kept.

Read the states with care:

- `BOUND` includes verified no-hit results. It does not mean every gene has a hit. Check the per-channel state counts.
- `UNAVAILABLE_IN_SELECTED_DATABASE` says nothing about searches elsewhere.
- `NO_VERIFIED_SEARCH` is the state of the selected source. It does not prove a search never ran.
- The same channels in an evidence index conflict with a database selection, and the command refuses them.
- `query_union_coverage_pct` is a source-reported query coverage. It is not reference coverage or percent identity.

More than 1000 search records for one protein, more than 1000 genes in the locus, or a held source roster stops the run. It never truncates quietly. No search, extraction, literature retrieval or tree building happens. This interface is not part of the standard workflow.

## Input-admission and write boundaries

The package must already be sealed; this command does not re-check its seal.

An external `--gene-table` is checked for alias, contig, unique tags and positive lengths only. It is
not compared with the sealed CDS roster. The receipt labels it `package://` even when it is not, so record its real path and SHA-256.

Evidence-index `BOUND` rows are checked for locator and hash syntax, known genes and identity. The
index file is hashed, but the sources it points to are not opened.

The child folder must not exist yet, and the `--out` folder must. A failure can leave a partial set that a retry refuses. Keep it for diagnosis and retry under a new `--out` root. The receipt does not list itself among its outputs.
