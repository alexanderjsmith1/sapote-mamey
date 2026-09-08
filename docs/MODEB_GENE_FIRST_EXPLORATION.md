# Mode B gene-first exploration

`modeb-gene-first` is an optional, offline composition tool for one already-sealed exact locus. It does not author a Mode B card and does not make biological calls.

The required identity is always:

`strain / full node-or-contig / region / BGC alias`

The command refuses shortened `NODE_n` tokens, identity conflicts, placeholder gene rows, malformed evidence indexes, and existing output artifacts before it writes a result.

## Usage

```bash
python mamey_run.py modeb-gene-first \
  --package /portable/project/runs/STRAIN/package \
  --strain STRAIN \
  --node NODE_7_length_120000_cov_42.5 \
  --region region002 \
  --bgc BGC007 \
  --out /portable/project/explorations
```

An optional `--evidence-index evidence.tsv` can bind external evidence without scanning a user-specific workspace. The TSV columns are:

```text
channel  strain  full_node  region  bgc_alias  gene  evidence_state  source_locator  source_sha256  note
```

Tabs are required. Every row must carry the same complete exact identity. `BOUND` rows require a portable relative or `evidence://` locator and a 64-character SHA-256. Allowed evidence states are `BOUND`, `UNBOUND`, `MISSING`, and `NOT_RUN`. Historical cards use the separate `historical_card` channel and must be `LEAD_ONLY`; they never contribute evidence support or ranking.

The ten evidence families remain separate: nr, ClusteredNR, local Swiss-Prot, MIBiG/KnownClusterBlast, ClusterBlast, BiG-SCAPE, RG-GMCI, cohort comparison, domain/HMM, and literature context. No channel substitutes for another.

The `--out` root must already exist. The command creates one child directory and four files whose names all carry the complete filesystem-safe identity in permanent order:

`STRAIN__NODE_7_length_120000_cov_42.5__region002__BGC007`

## Outputs

- `<complete-identity>__MODEB_GENE_FIRST_EXPLORATION.md` — concise, claim-capped synthesis and exactly one next analysis.
- `<complete-identity>__important_genes.tsv` — deterministic review order with the complete identity on every row.
- `<complete-identity>__evidence_channels.tsv` — channel-separated availability; missing is a workflow gap, not biological absence.
- `<complete-identity>__exploration_receipt.json` — content-addressed input and output receipt.

The gene order is an inspection order based on an explicit role category, then bound gene-channel count, coordinates, and locus tag. It is not a biological-importance score. Outputs remain engineering exploration artifacts pending separate scientific review.


## Optional frozen database bridge

`--database-selection selection.json` adds sequence-projected observations to the
existing exploration receipt, important-gene TSV and synthesis. It does not create
a second packet or admit evidence scientifically. The package roster remains the
denominator, including boundary genes absent from the selected database census.

The selection uses schema `mamey.gene-first-database-selection/1`, a required
`package_manifest_sha256`, and exactly four entries under `databases`: `census`,
`nr`, `clusterednr`, and `local_swissprot`. Each entry contains an explicit `root`,
relative `manifest` locator and required `manifest_sha256`. Relative roots resolve
from the selection JSON directory. Paths are configuration, never discovery by glob
or filename recency. The manifest pins the database bytes through the existing
read-only reader. No source database is copied or modified.

The package must seal its all-gene CSV and `<strain>_proteins.faa` in manifest
`files` entries. An external `--gene-table` cannot replace those sealed bytes for
this bridge. Missing package protein evidence fails closed. A missing individual
protein or disagreement with census sequence/geometry remains unbound, conserving
the gene. Region starts convert from the package zero-based convention to the
census one-based convention; CDS coordinates compare directly as one-based inclusive.
The census must supply matching full region geometry. Gene order and query hashes
must agree across census and channel databases before any channel observation binds.

`BOUND` includes sequence-projected verified no-hit outcomes; it never means that
all genes have hits. Inspect the per-channel state counts and per-gene columns.
`UNAVAILABLE_IN_SELECTED_DATABASE` makes no assertion about searches elsewhere.
`NO_VERIFIED_SEARCH` is the selected source state, not proof a search never ran.
The same three channels in an external evidence index conflict with a database
selection and are refused rather than silently taking precedence.

The reader's API `history` view keeps complete source-retained search histories,
including mixed hit/no-hit outcomes. Every search has its own lowest retained
source-rank representative, explicit retained-hit count, provenance and HSPs.
Representatives are not ranked across searches and are not chosen as biological
comparators. Other retained hits remain accessible through the existing reader's
`hits` and `hsps` views. The bridge does not imply that all database matches were
retained by the original search. More than 1000 search records per protein,
1000 selected locus genes, the existing reader result-size budget, or a held
source roster stops composition rather than truncating evidence silently.

Raw `query_union_coverage_pct` remains a source-reported query-coverage field,
not reference coverage or alignment percent identity. The bridge neither clamps
values nor scientifically validates the metric. Per-HSP identity and query interval
fields remain inspectable in the receipt; source metric holds remain in force.

This optional interface is an engineering candidate. Source provenance recorded
in a frozen database is retained, but external XML/job artifacts are not reopened.
No search, extraction, literature retrieval or phylogenetic work is performed.
