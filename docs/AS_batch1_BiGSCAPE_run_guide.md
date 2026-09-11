# BiG-SCAPE 2.0 run guide — AS_batch1 (11 strains, 624 BGCs)

> **HISTORICAL COHORT RECEIPT — NOT AN ACTIVE RUNBOOK.** The commands below preserve an earlier
> AS_batch1 analysis and may contain superseded resource, download, and interpretation practices.
> LLMs must use `docs/LLM_COMPANION_TOOL_PROTOCOL.md` and `docs/BIGSCAPE_GCF_WORKFLOW.md`; do not
> execute this file's automatic downloads, high-core examples, cleanup commands, or novelty wording.


This walks a BiG-SCAPE 2.0 gene-cluster-family (GCF) analysis on the 11-strain cohort.
BiG-SCAPE clusters antiSMASH BGCs by Pfam-domain content, adjacency, and sequence
identity into GCFs. It is the network/GCF complement to the Mamey pangenome layer:
Mamey gives you per-BGC architecture + KCB anchors; BiG-SCAPE gives you the cross-strain
family graph.

Version note: BiG-SCAPE 2.0 (Navarro-Muñoz/Reitz et al., Nat Commun 2026) uses a
subcommand CLI (`bigscape cluster`, replacing the BiG-SCAPE 1.x bigscape.py entrypoint). Everything below is
2.x syntax.

---

## What's already prepared

`AS_batch1_bigscape_input_624gbk.zip` — all 624 antiSMASH region GBKs from the 11 strains,
each filename prefixed with its strain ID (e.g. `AS-XXX_NODE_2_..._region002.gbk`).
Prefixing matters: these are SPAdes assemblies, so `NODE_*` record names can collide
across strains; the prefix keeps every record uniquely named and keeps strain provenance
visible in the BiG-SCAPE HTML and the SQLite `gbk.path` column.

Per-strain region counts: AS-XXX 46 · AS-XXX 62 · AS-XXX 68 · AS-XXX 71 · AS-XXX 65 ·
AS-XXX 48 · AS-XXX 60 · AS-XXX 48 · AS-XXX 48 · AS-XXX 57 · AS-XXX 51 = 624.

Unzip it to a working folder; that folder is your `-i` input.

```
mkdir -p AS_batch1_bigscape && cd AS_batch1_bigscape
unzip ../AS_batch1_bigscape_input_624gbk.zip -d input/
```

---

## 1 · Install BiG-SCAPE 2.0

Bioconda is the least-friction path (pulls HMMER and deps):

```
conda create -n bigscape -c bioconda -c conda-forge big-scape
conda activate bigscape
bigscape --version        # confirm a 2.x version
```

Alternative (from source): clone `medema-group/BiG-SCAPE`, create the env from the repo's
`environment.yml`, `pip install .`. HMMER (`hmmscan`) must be on PATH either way.

## 2 · Get the Pfam database

BiG-SCAPE needs a pressed `Pfam-A.hmm`. If antiSMASH is already installed you likely
already have one (look under the antiSMASH data dir); otherwise fetch and press it:

```
wget https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz
gunzip Pfam-A.hmm.gz
hmmpress Pfam-A.hmm       # creates .h3f/.h3i/.h3m/.h3p next to it
```

## 3 · Run the clustering

```
bigscape cluster \
  -i input/ \
  -o AS_batch1_bigscape_out/ \
  -p /path/to/Pfam-A.hmm \
  --mibig-version 3.1 \
  --cores 8
```

- `--mibig-version 3.1` pulls antiSMASH-processed MIBiG references and folds them in, so
  any GCF containing a MIBiG BGC is immediately dereplicated (this is the cross-check for
  the Mamey KCB anchors — a GCF that lands on a MIBiG reference is your "known" family;
  one that doesn't is a novelty candidate). Drop this flag for a strains-only graph.
- Classification defaults to antiSMASH **Category** (2.0 behavior). Add `--classify class`
  for the finer antiSMASH-class bins, or `--mix` to compare all BGCs in one bin regardless
  of class (useful for spotting cross-class hybrids). `--classify legacy` reproduces
  BiG-SCAPE 1's 8 groups if you want continuity with older runs.
- Cutoffs: the default distance cutoff is 0.30. Add e.g. `--gcf-cutoffs 0.3 0.5 0.7` to
  emit GCFs at several stringencies in one run (0.3 ≈ same compound, 0.7 ≈ loosely related
  family) — worth doing so you can see how the cohort's families split/merge with
  stringency.
- `--include-singletons` if you want the un-familied BGCs shown as nodes too (default hides
  them; for a discovery cohort you usually want them visible).

Runtime for ~624 BGCs + MIBiG on 8 cores is minutes-to-low-tens-of-minutes; the hmmscan
domain pass dominates the first run and is cached in the SQLite DB for re-runs.

## 4 · Explore the output

Open `AS_batch1_bigscape_out/index.html` in a browser; when prompted, select the `.db`
file in the output folder. You get the similarity network, per-class GCF bins, and
CORASON-like multi-locus alignments per family. The tab-delimited GCF membership files and
the SQLite DB are the machine-readable outputs for joining back to the Mamey workbook.

---

## Tying it back to the Mamey analysis (claim-safe)

- A **GCF is domain-content + adjacency similarity, not compound identity**. Frame any GCF
  membership as "capacity consistent with the same biosynthetic family," never "produces
  the same compound." Same discipline as KCB/BLASTp = similarity not identity.
- **Join key:** the strain-prefixed GBK filename → strain ID + `NODE·region` locator. That
  is the same `node·region` locator the Mamey triage boards and Mode B cards use, so a GCF
  table row maps 1:1 onto a Mamey BGC. Reconcile on that locator, not on BGC_ID (BGC_ID is
  per-run and not portable across the two tools).
- **Cross-check against the Mamey pangenome:** the cohort-precompute domain tables
  (`COHORT_domain_architecture_by_bgc.csv`, 110 rows) and any `build_pangenome.py` output
  are Mamey's family view; BiG-SCAPE's GCFs are an independent family view over the same
  BGCs. Concordant families are strong; families that disagree between the two tools are
  exactly where to look (fragmented assemblies — AS-XXX VERY_POOR, AS-XXX VERY_POOR — will
  split families across contigs in both tools, so expect and caveat that).
- **MIBiG-anchored GCFs** dereplicate against known chemistry; **MIBiG-free GCFs shared
  across strains** are the cohort's novelty candidates and the natural priority list for
  the Mode B campaign.

## Reproducing the input prep for other cohorts

The staging step (extract region GBKs from each antiSMASH zip, strain-prefix, collect into
one folder):

```
mkdir -p bigscape_input
for z in *.zip; do
  s=$(basename "$z" .zip)
  tmp=$(mktemp -d)
  unzip -j -q "$z" "*region*.gbk" -d "$tmp"
  for f in "$tmp"/*region*.gbk; do cp "$f" "bigscape_input/${s}_$(basename "$f")"; done
  rm -rf "$tmp"
done
```
