# Prevalence over saved cohort annotations

Use this workflow to ask how often a domain or keyword group appears across a saved cohort. It reads existing evidence and writes new summaries. It does not rebuild the evidence, check package sealing or show that the cohort is complete. Rarity order is a review queue. It is not chemical novelty, functional absence or host specificity.

The commands, with a short note on reading the widget, are on the [Domain and scan prevalence](../wiki/Domain-and-Scan-Prevalence.md) page. This page holds the details behind them.

## What you need

For domain prevalence, you need two SQLite databases for the cohort:

- `antismash_gene_census` (the census), passed as `--census`.
- `antismash_gbk_domains` (the domain table), passed as `--gbk-domains`.

No tool in this bundle builds these two databases. They come from a cohort annotation step done outside the bundle. The census needs the tables `attempt` and `locus` (with `strain`, `locus_key`, `exact_identity`). The domain table needs `gene` (with `locus_key`, `locus_tag`, `protein_sha256`), `domain_summary` and `feature`. If you do not have databases with these tables, the tool cannot run.

Optional: saved NR, ClusteredNR and Swiss-Prot databases (`--nr`, `--cnr`, `--sp`), and a host table (`--host-tsv`).

For keyword-scan prevalence, you need one keyword-scan SQLite database (`--scan-db`) and a name for the dataset (`--dataset-name`).

Open every input read-only. Write to a new, empty output folder (`--out`).

## Run it

```bash
python tools/domain_prevalence.py \
  --census ANTISMASH_GENE_CENSUS.sqlite --gbk-domains ANTISMASH_GBK_DOMAINS.sqlite \
  --out <new output folder>/ --widget

python tools/scan_prevalence.py \
  --scan-db MAMEY_KEYWORDS.sqlite --dataset-name <name> \
  --out <new output folder>/ --widget
```

Add `--exclude`, `--host-tsv` and `--host-override` as you need them (see [Host metadata and filtering](#host-metadata-and-filtering)). Run `python tools/domain_prevalence.py --help` or `python tools/scan_prevalence.py --help` for every flag.

Success: the tool prints one summary line, such as `domain_prevalence: <n> families, <n> strains, <n> held -> <folder>`. With `--widget` it also prints `widget + figures written`. If the widget step fails, the tables are already written, the tool prints `FAIL: widget step failed`, and it exits `3`. Any other non-zero exit is a failed run.

## Read the result

Open `domain_prevalence_ranking.json` first. `scope.strains` is the denominator, and `strains_sorted` lists its strains. Each entry in `rows` has `strains`, `loci` and `distinct_genes`. `strain_prevalence` is the row's `strains` divided by `scope.strains`, rounded to four decimals. A trimmed excerpt:

```json
{
  "scope": {"strains": 40, "loci": 1234, "genes": 56789},
  "strains_sorted": ["..."],
  "rows": [
    {"source_tool": "clusterhmmer", "feature_type": "...", "domain_label": "...",
     "strains": 2, "loci": 2, "distinct_genes": 2, "strain_prevalence": 0.05}
  ]
}
```

Rows are sorted rarest first: fewest strains, then fewest loci, then most feature occurrences. Read [Inputs, joins and denominator](#inputs-joins-and-denominator) before you compare two datasets.

## Inputs, joins and denominator

- Domain prevalence takes the distinct `strain` values from the census `attempt` table, minus `--exclude`, as its denominator. Scan prevalence takes the distinct `strain` values from the scan database's `source` table. Neither checks whether each strain's run succeeded or finished. Freeze the strain list before you compare datasets. Two scan databases can have different denominators for the same requested cohort.
- Domain rows are keyed by `(source_tool, feature_type, domain_label)`. Only features in the binding state `SOURCE_SEQUENCE_AND_GEOMETRY_BOUND` count. The rest go to the held list. Genes come from each feature's explicit gene-tag JSON, not from protein length.
- Malformed tag JSON becomes an empty list. That feature counts as an occurrence but adds no gene, locus or strain. A gene with no protein hash is left out of the sequence-hash count.
- Scan rows use the lists or dictionary keys in `groups_json`. Empty or malformed JSON is skipped with no held record. A scan's "feature occurrences" counts distinct tagged genes per group, which is not the domain tool's measure. Keep the source tool and feature type with every comparison. The SQLite host and evidence tables leave out `feature_type`, but the ranking JSON keeps it. Use the JSON key to avoid collisions.
- A locus label in `loci_list` is the locus's `exact_identity`. When that value is missing, NULL or blank, the entry reads `IDENTITY_HOLD: exact_identity missing; source locus_key <key> (locator, not a locus identity)`. The key is a source-scoped locator, not a full identity. Before you adopt a locus, confirm its `strain / full node-or-contig / region / BGC alias` from the source record.
- Optional evidence maps join on `(locus_key, locus_tag)`. The tool does not re-check protein hashes against those bindings. An omitted or empty map gives all-zero counters, so zero "missing" does not mean the search was complete or had no hits. Scan prevalence always writes zero placeholders for these channels.

## Host metadata and filtering

The host class of each strain comes from one of three places, in this order of precedence: `--host-override`, then the host table, then `unknown`.

- **From the host table** (`--host-tsv`): the tool reads the strain from `--host-strain-col` (default `strain`). By default it classifies the text in `--host-source-col` (default `source`) into `bee`, `wasp`, `bee_or_wasp`, `ant`, `moss`, `fungus_assoc`, `other` or `unknown`. The word lists are built into the tool, so a host outside these classes falls into `other`. This is a heuristic on the words of the text, not taxonomy validation: it uses exact words plus prefix and suffix tests, so a word ending in `bee` or `bees` reads as `bee`, a word starting with `moss` reads as `moss`, and a word starting with `fung` or `mushroom` reads as `fungus_assoc`. Review every inferred class against the deposited source text, and keep that text with the class. If a strain has repeated rows, the last recognized value wins.
- **From a class column** (domain tool only): pass `--host-source-col ""` to clear the source choice, and name the column with `--host-class-col`. Its values are used as given and are not checked against a list. The scan tool has no class-column option.
- **By override:** `--host-override <ID>=<class>`. The ID must be in the denominator and not excluded. Otherwise the domain tool prints `WARN --host-override <ID>: not in scope (unknown or excluded); ignored` to stderr, and the scan tool ignores it silently. Check the log if an override seems to do nothing. Never use an override to bring excluded evidence back.

## Output and recovery

| Tool | Writes |
|---|---|
| `domain_prevalence.py` | `domain_prevalence__v0.1.0.sqlite`, `domain_prevalence_ranking.json`, `AUDIT_RECEIPT.json`; with `--widget`, an HTML widget and top-20 SVGs |
| `scan_prevalence.py` | `domain_prevalence_ranking.json` and `AUDIT_RECEIPT.json` (with an empty channel list); with `--widget`, the widget and SVGs. No SQLite database. |

Both tools reuse an existing output folder and overwrite files in it. The domain tool deletes an old `domain_prevalence__v0.1.0.sqlite` first. Use a new folder for every build and for every keyword dataset.

The domain receipt (`AUDIT_RECEIPT.json`) holds no hashes. The SHA-256 of the main databases sits in `domain_prevalence_ranking.json` under `source`, and in the SQLite metadata. The hashes do not cover SQLite write-ahead log (WAL) bytes, the optional evidence databases, the host table, the code or the outputs. Use frozen upstream databases, and keep your own list of inputs, settings and outputs beside the build.

The widget's strain selector filters for presence, but its bars still show cohort strain counts. Host views change the bar denominator while the evidence and rare-locus lists stay cohort-wide. A channel with all-zero counters shows as "no saved states", which is not a completed search. An SVG export is a picture, not a new result. Open the widget and look at it before you use it.
