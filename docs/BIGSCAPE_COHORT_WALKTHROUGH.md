# BiG-SCAPE cohort walkthrough — from antiSMASH zips to family figures

**Read first:** `docs/LLM_COMPANION_TOOL_PROTOCOL.md`, then `docs/BIGSCAPE_GCF_WORKFLOW.md` for the input
contract, QA fields and claim rules. This page is the hands-on route: the exact commands, in order, with the check
that tells you each step worked. Companion page: `docs/troubleshooting/BIGSCAPE_TROUBLESHOOTING.md`.

What you get at the end: one SQLite database of gene-cluster families at three cutoffs, a per-family verdict table
(query-private, MIBiG-matched, shared with a reference layer), and one figure per family of interest. Each figure shows the family tree
beside gene-arrow tracks, labeled `strain / full node-or-contig / region / BGC alias`. All of it is similarity grouping. None of it
is compound identity, activity or novelty; those calls are deferred.

## Bind the run before interpreting results

Run examples from the selected bundle directory in its compatible Python environment.
Keep the installed BiG-SCAPE executable, Pfam/MIBiG source versions and hashes,
exact input manifest, resource budget and selected completed database run together.
Family IDs belong to that database/run/cutoff; they are not global locus identifiers.

The verdict helper exposes `--run-id`; without it, it chooses the latest family-table run, not every run (`tools/bigscape_family_verdicts.py`). Select the exact intended ID explicitly. It does not check the run table’s completion state, and its region denominator still counts all database region records. Do not interpret that total as the selected run’s admitted roster without independent reconciliation. The figure batch helper still queries by cutoff without a run filter (`tools/bigscape_family_figures.py`); use it only after proving the database’s scope is unambiguous. An explicit multi-run cohort export uses
[the cohort report route](BIGSCAPE_COHORT_NETWORK_GUIDE.md) with `--run-id`; it does
not replace all legacy gene-track figure products. Do not resolve ambiguity by
silently taking the newest run or editing the source database. See
[BiG-SCAPE troubleshooting](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md) for recovery.

## 0. What you need on disk

| item | how to check |
|---|---|
| BiG-SCAPE 2.0.x in a conda env, with `fasttree` in the same env | `ls <env>/bin/bigscape <env>/bin/fasttree` |
| Pfam-A.hmm, pressed | `ls Pfam-A.hmm Pfam-A.hmm.h3i` (all four `.h3?` files) |
| MIBiG antiSMASH GBKs, one folder of `BGC*.gbk` (optional but recommended) | `ls <mibig>/BGC*.gbk \| wc -l` (about 2,000) |
| loose-mode antiSMASH result zips, one per genome, plus any reference layers | `unzip -l <zip> \| grep -c region` |
| the strains' validated Mamey packages (for the figure labels) | `<package>/<strain>_2_inventory.csv` exists |

Set once per shell:

```bash
export BIGSCAPE_ENV_BIN=<env>/bin
export PFAM_HMM=<path>/Pfam-A.hmm
```

## 1. Stage the region GBKs (one strictness flavor)

```bash
python tools/bigscape_prep.py --inputs <dir of zips or zip…> --strictness loose --out <stage>/gbk_input
```

`bigscape_prep.py` prefixes every file with its strain (`<strain>_<contig>.regionNNN.gbk`). It stages only zips of the
requested strictness and skips every other zip with a `SKIP` line on stderr. `STRICTNESS_MANIFEST.tsv` in the output
records the flavor and staged or skipped state of every zip. Reference layers are staged
into the same folder under a layer prefix, which is how every later tool tells them apart:

| layer | file name form | example |
|---|---|---|
| query strains | `<strain>_<contig>.regionNNN.gbk` | `STR-12_NODE_4_length_….region002.gbk` |
| named reference layer | `<LAYER>_<stem>.regionNNN.gbk` | `SID_REF-01_ABCD01000002.1.region001.gbk`, `TYPE_Genus_species_DSM_1_CP000001.1.region003.gbk` |
| other reference genome | `<genome stem>__<original region file>` | `Genus_species__GCF_000000001.1__NZ_ABCD01000001.1.region001.gbk` |
| MIBiG | not staged here; loaded with `--mibig-dir` | `BGC0000853.gbk` |

Check: `ls <stage>/gbk_input/*.gbk | wc -l` equals the sum of the layers you meant to stage, and no two files share a
sha256 (`shasum -a 256 <stage>/gbk_input/*.gbk | cut -d' ' -f1 | sort | uniq -d` prints nothing). Count only `.gbk`
files: the manifest and any filter receipts sit in the same folder. Write the count per layer down; it is the
denominator for everything after.

## 2. Run

```bash
set -o pipefail
nice -n 15 bash tools/bigscape_launch.sh <stage>/gbk_input <stage>/out \
    --label <run label> --cores 1 --mibig-dir <mibig folder> --mibig-name local2088 --include-singletons \
    2>&1 | tee <stage>/launch.log
```

`--include-singletons` matches the GCF runbook (`docs/BIGSCAPE_GCF_WORKFLOW.md`) and `mamey_run.py bigscape`, which both keep singletons.

The launcher puts the env on PATH, verifies Pfam and `fasttree`, links the MIBiG folder into BiG-SCAPE's `-m` slot
and verifies the link, then runs `bigscape cluster` with `--gcf-cutoffs 0.3,0.5,0.7`. Cost on a laptop: about 3 hours
for 18,000 records at 4 cores; the run is one job, so nothing else heavy runs beside it.

Check, in `launch.log` at the end: `BIGSCAPE_EXIT=0`, `Loading <N> query GBKs` equals your staged count, and
`Loading <M> mibig GBKs` is about 2,000 when you asked for MIBiG. A `0` there means the reference set was not loaded
and the run must be repeated; do not interpret a MIBiG-free run as "no MIBiG match".

The launcher writes `run.log` in its selected output and accepts existing output
directories; choose a new run/output directory to preserve earlier logs and state.
With `--mibig-dir`, it creates or replaces a symlink inside the installed
`big_scape/MIBiG/` package directory (`ln -sfn`), so that operation also mutates the
selected companion installation. Its current guard requires at least 2,000 GBKs;
a deliberately smaller reference panel is refused by this launcher even if it is
scientifically appropriate. Neither that count nor a symlink proves source release
or type/reference quality. These mutations and the actual compute budget must
match the user's selected operation. The four-core historical timing above is not a
measurement for the one-core example. `pipefail` preserves launcher failure through
`tee`; still inspect the explicit BIGSCAPE_EXIT and logs.

The database is `<stage>/out/<label>.db`. Retain a closed, checkpointed database and any necessary source-state receipts in the selected results layout; never merge two
databases by family id (ids are local to a run).

## 3. Verdicts and denominators

```bash
python tools/bigscape_family_verdicts.py <label>.db <results>/FAMILY_VERDICTS_c0.3.tsv --cutoff 0.3 --run-id <exact-run-id>
```

One row per family that holds a query record: query strains, products, member counts per layer, MIBiG members, and
the verdict (`QUERY_PRIVATE_REFERENCE_DARK`, `QUERY_PRIVATE_MIBIG_MATCHED`, `QUERY_MIBIG_AND_REF`,
`QUERY_SHARED_REFERENCE`). It also carries `cross_strain` (yes / no: two regions of one strain are a family too). The companion
`…placement.tsv` gives, per cutoff, how many region records have a family row at all. BiG-SCAPE 2 writes family rows
only for records inside a connected component at that cutoff, so at 0.3 about half the records are singletons.
Quote "private" with that denominator, never against the total record count.

Check: the sum of the verdict counts printed equals the row count of the TSV; `records_with_family_row` rises from
0.3 to 0.7.

## 4. Figures

Family figure per private family, filed by strain, and everything for a few strains of interest:

```bash
python tools/bigscape_family_figures.py --db <label>.db --gbk-dir <stage>/gbk_input --gbk-dir <mibig folder> \
    --identity-glob '<packages>/*/package/*_2_inventory.csv' --out <results>/figures \
    --private-tsv <results>/FAMILY_VERDICTS_c0.3.tsv \
    --focus STR-12 --focus STR-40 --cutoff 0.3 --fallback-cutoff 0.7 --max-tips 40
```

Output layout:

```
figures/private_families/_all/GCF<id>_c0.3_<product>.{pdf,png,_rows.tsv,_gene_roles.tsv,_caption.txt}
figures/private_families/<strain>/            the same PDF and PNG, hard-linked, for every member strain
figures/private_families/INDEX.tsv
figures/strain_focus/<strain>/family_trees_c0.3/GCF<id>_…   families at 0.3 holding one of the strain's regions
figures/strain_focus/<strain>/family_trees_c0.7/GCF<id>_…   the 0.7 family of each region unplaced at 0.3
figures/strain_focus/<strain>/BGC_TO_FAMILY_FIGURE.tsv      one row per region: alias, family ids, figure or "singleton at every cutoff"
figures/strain_focus/<strain>/FAMILY_FIGURES_INDEX.tsv
```

Each figure shows BiG-SCAPE's own tree for the family on the left and one gene-arrow track per
member on the right. Rows are labeled `strain / full node-or-contig / region / BGC alias` from the package inventory (an identity hold
where no alias is bound). Reference rows are labeled by layer, organism and accession. Dotted homology links run between
neighboring rows. Families above `--max-tips` are drawn as a pruned view anchored on the focal strain; the title
says so. Cost: seconds for a small family, one to two minutes for a 40-row pruned view of a PKS/NRPS family.

Interactive alignment pages (clinker-style, one HTML per family, optional single-page PDF):

```bash
python tools/bigscape_clinker_html.py --db <label>.db --out <results>/figures \
    --focus STR-12 --cutoff 0.3 --fallback-cutoff 0.7 --chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Check, before sending any figure: open the PNG. Labels are complete (nothing cut at the left edge), the red rows are
your strains, the `_rows.tsv` `identity_hold` column is empty for every strain that has a package, and the caption
file states the link rule. A hold means a contig mismatch or no admitted package alias was found; missing inventory inputs, filename collisions, staging names and differing source runs all require investigation. It does not by itself prove which cause occurred. The current renderer indexes `Source_GBK` basenames with last-row-wins behavior, checks a supplied contig when present, and does not compare the saved region field or source hashes (`tools/render_gcf_synteny_tree.py`). Even a blank hold is not a full source/package identity audit. Bind the complete identity and exact source files independently; see the troubleshooting page.

## 5. What to write and what not to write

Write: "regions A and B were assigned to the same BiG-SCAPE family at cutoff 0.3 in run <label>; the family has no
reference-layer or MIBiG member in this run". Cite the figure and the verdict row. Carry the placement denominator
and the contig-edge flag with every count.

Do not write: novel, new, rare, unknown compound, bioactive, or any product name from a MIBiG neighbor. A private
family is a statement about this panel and this reference set. A MIBiG member in the family is architecture
similarity, not compound identity. Judgment is deferred to the person who signs the card.


## Optional input and display scope

`bigscape_prep.py --min-query-genes N --query-strain <exact-id>` filters only the explicitly named query inputs before staging. Repeat `--query-strain` for additional queries; other inputs are never filtered. The default minimum is zero (disabled). Excluded source records, CDS counts and hashes are written to `EXCLUDED_SMALL_QUERY_FRAGMENTS.tsv`, with the exact rule in `QUERY_FILTER.json`. This is an operator-selected input scope, not a statement of biological absence or assembly completeness. Raw archives stay unchanged. These records carry source locators; an unbound BGC alias is explicitly recorded rather than invented.

`bigscape_prep.py --drop-contigs STRAIN=removed_contigs.tsv` drops that strain's regions on contigs a decontamination removed (first TSV column = antiSMASH record id; `clade_decontam.py`'s `<clade>_contig_bins.tsv` is also accepted, and only its `keep = 0` rows are dropped); repeat per strain. Use it whenever the antiSMASH registry marks a zip `RAW_CONTAMINATED_ASSEMBLY`. Dropped regions are listed in `DROPPED_CONTIG_REGIONS.tsv`. A drop list naming a strain that did not stage exits 2, so a mistyped id cannot silently drop nothing.

An empty or duplicate drop list is refused. A list with zero matching regions also exits 2; after verifying that the assembly and contig IDs agree and zero regions are genuinely affected, pass `--allow-zero-drop STRAIN` for that exact strain. The zero count remains visible in stderr and the dropped-region table.

`bigscape_cross_strain.py --out` takes a TSV filename. `--labels` reads unique exact strain keys and deposited display names, retaining the `strains` join column. `--exclude-products terpene,ectoine` parks families by their dominant product label, ignoring case. Parked families go to `<out>.PARKED.tsv`, and the rule and counts go to `<out>.FILTER.json`. The default `--exclude-match all-tokens` parks a family only when every `.`-separated product in that label is named, so a hybrid such as `NRPS.terpene` stays. `any-token` parks a family when any product is named. `contains` is the old substring match, so `terpene` also parks `terpene-precursor`. No exclusion is enabled by default. `FILTER.json` lists up to five kept labels that still contain a named token; review them when selecting scope.

`bigscape_clinker_html.py --row-order genes|similarity --min-genes N --labels labels.tsv` controls display order, minimum track size and deposited names. Similarity is a deterministic greedy order by shared dominant Pfam domains, not a phylogeny. Hidden tracks remain in the database and exports; the page states the hidden count. `--query-regex` must compile and contain a capture group. Full names remain in the page payload; the gutter bounds their on-page width. These options do not change family assignment, locus identity, product identity or activity claims.

The optional clinker `--chrome` PDF route requires the `documents` extra (`pypdf`). It validates a complete single-page family PDF, then closes its isolated browser process; it refuses an existing PDF instead of reporting stale output as newly rendered.
