# Make BiG-SCAPE family tables and figures

Stage antiSMASH regions, cluster them and export their families. You need the
selected ZIPs, matching Mamey inventories, a working BiG-SCAPE environment and
an existing `Pfam-A.hmm` with all four `.h3*` indexes. Use the model where it is
installed; see [settings](BIGSCAPE_GCF_WORKFLOW.md).

Run from an editable working folder. Use fresh staging, output and figure
folders, and keep the input hashes and database run ID.

## Stage the selected profile

Choose the profile recorded in the ZIP; this example uses `relaxed`:

```bash
python tools/bigscape_prep.py --inputs inputs/EXAMPLE-cohort \
  --strictness relaxed --out reviews/EXAMPLE-bigscape/gbk_input
```

Read `STRICTNESS_MANIFEST.tsv` and count the staged GBKs. Other profiles are
skipped; zero staged regions is a failure. Keep the source-member/hash/identity
roster and estimate substantial copy space before staging.

## Cluster the regions

With `bigscape` available on PATH, set its environment folder and your installed
Pfam path. Replace the model path below with its actual location:

```bash
export BIGSCAPE_ENV_BIN="$(dirname "$(command -v bigscape)")"
export PFAM_HMM=../reference-data/Pfam-A.hmm
set -o pipefail
nice -n 15 bash tools/bigscape_launch.sh \
  reviews/EXAMPLE-bigscape/gbk_input reviews/EXAMPLE-bigscape/out \
  --label EXAMPLE --cores 1 --include-singletons \
  2>&1 | tee reviews/EXAMPLE-bigscape/launch.log
```

`--label` names the database, `--cores 1` limits CPU use, and
`--include-singletons` keeps isolated regions visible. Default cutoffs are 0.3,
0.5 and 0.7. BiG-SCAPE 2.0.3 uses in-process Pfam scanning; the launcher's
external `hmmsearch`/`diamond` warnings alone need not stop that workflow.

Check `BIGSCAPE_EXIT`, `run.log`, loaded counts and the database run's end time.
For retries, follow the [settings guide](BIGSCAPE_GCF_WORKFLOW.md). The optional
MIBiG branch replaces an installed reference link and requires at least 2,000
GBKs; plan its inputs and resources before using it.

## Export families

Use the completed run ID; the example selects 1:

```bash
python tools/bigscape_family_verdicts.py reviews/EXAMPLE-bigscape/out/EXAMPLE.db \
  reviews/EXAMPLE-bigscape/FAMILY_VERDICTS.tsv --run-id 1
```

The default query matcher recognizes prefixes such as `AS-40_`. For other names,
set `--query-regex` to capture the query's staged prefix in group 1. Reconcile
query counts with the input roster before interpreting an empty table.

The default cutoff is 0.3. Family IDs belong to this database/run/cutoff;
`cross_strain` distinguishes multiple strains from multiple regions of one
strain. Without loaded references, the table describes cohort-only sharing.

The placement file's `singleton_records` counts regions lacking a family row.
Count actual single-member families from membership rows; visible singletons
can already have family rows.

## Draw selected families

Use a database with one unambiguous completed run; this legacy batch has no
run-ID filter:

```bash
python tools/bigscape_family_figures.py --db reviews/EXAMPLE-bigscape/out/EXAMPLE.db \
  --gbk-dir reviews/EXAMPLE-bigscape/gbk_input \
  --identity-glob 'runs/EXAMPLE/package/*_2_inventory.csv' \
  --out reviews/EXAMPLE-bigscape/figures \
  --private-tsv reviews/EXAMPLE-bigscape/FAMILY_VERDICTS.tsv --focus EXAMPLE
```

Use the staged query prefix for `--focus`, and the same query matcher when
needed. The default display limit is 40 tips; keep full membership tables. Inspect the indexes, identity holds and every figure. Query labels need
**strain / full contig / region / BGC alias**. Keep the closed database, source
records, selected settings and output hashes. For multiple runs, use the
[explicit-run report](BIGSCAPE_COHORT_NETWORK_GUIDE.md).

<a id="2-full-bgcs-with-gcf-evidence"></a>
<a id="3-singleton-or-small-family-evidence"></a>
<a id="4-per-strain-family-view"></a>
<a id="5-gap-rescue-candidates"></a>
<a id="6-optional-narrower-preparation"></a>
