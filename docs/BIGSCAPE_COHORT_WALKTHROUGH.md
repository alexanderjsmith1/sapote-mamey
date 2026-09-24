# BiG-SCAPE cohort walkthrough — from antiSMASH zips to family figures

**Authority:** `docs/LLM_COMPANION_TOOL_PROTOCOL.md` first, then `docs/BIGSCAPE_GCF_WORKFLOW.md` for the input
contract, QA fields and claim rules. This page is the hands-on route: the exact commands, in order, with the check
that tells you each step worked. Companion page: `docs/troubleshooting/BIGSCAPE_TROUBLESHOOTING.md`.

What you get at the end: one SQLite database of gene-cluster families at three cutoffs, a per-family verdict table
(query-private, MIBiG-matched, shared with a reference layer), and one figure per family of interest: the family tree
beside gene-arrow tracks, labelled `strain / contig / region / BGC alias`. All of it is similarity grouping. None of it
is compound identity, activity or novelty; those calls are deferred.

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

`bigscape_prep.py` prefixes every file with its strain (`<strain>_<contig>.regionNNN.gbk`) and refuses a mixed
loose/relaxed set; `STRICTNESS_MANIFEST.tsv` in the output records the flavor of every zip. Reference layers are staged
into the same folder under a layer prefix, which is how every later tool tells them apart:

| layer | file name form | example |
|---|---|---|
| query strains | `<strain>_<contig>.regionNNN.gbk` | `STR-12_NODE_4_length_….region002.gbk` |
| named reference layer | `<LAYER>_<stem>.regionNNN.gbk` | `SID_SID69_WWHM01000591.1.region001.gbk`, `TYPE_Genus_species_DSM_1_CP000001.1.region003.gbk` |
| other reference genome | `<genome stem>__<original region file>` | `Genus_species__GCF_000000001.1__NZ_ABCD01000001.1.region001.gbk` |
| MIBiG | not staged here; loaded with `--mibig-dir` | `BGC0000853.gbk` |

Check: `ls <stage>/gbk_input | wc -l` equals the sum of the layers you meant to stage, and no two files share a
sha256 (`shasum -a 256 * | cut -d' ' -f1 | sort | uniq -d` prints nothing). Write the count per layer down; it is the
denominator for everything after.

## 2. Run

```bash
nice -n 15 bash tools/bigscape_launch.sh <stage>/gbk_input <stage>/out \
    --label <run label> --cores 4 --mibig-dir <mibig folder> --mibig-name local2088 2>&1 | tee <stage>/launch.log
```

The launcher puts the env on PATH, verifies Pfam and `fasttree`, links the MIBiG folder into BiG-SCAPE's `-m` slot
and verifies the link, then runs `bigscape cluster` with `--gcf-cutoffs 0.3,0.5,0.7`. Cost on a laptop: about 3 hours
for 18,000 records at 4 cores; the run is one job, so nothing else heavy runs beside it.

Check, in `launch.log` at the end: `BIGSCAPE_EXIT=0`, `Loading <N> query GBKs` equals your staged count, and
`Loading <M> mibig GBKs` is about 2,000 when you asked for MIBiG. A `0` there means the reference set was not loaded
and the run must be repeated; do not interpret a MIBiG-free run as "no MIBiG match".

The database is `<stage>/out/<label>.db`. Copy or hard-link it into the folder where results live; never merge two
databases by family id (ids are local to a run).

## 3. Verdicts and denominators

```bash
python tools/bigscape_family_verdicts.py <label>.db <results>/FAMILY_VERDICTS_c0.3.tsv --cutoff 0.3
```

One row per family that holds a query record: query strains, products, member counts per layer, MIBiG members, and
the verdict (`QUERY_PRIVATE_REFERENCE_DARK`, `QUERY_PRIVATE_MIBIG_MATCHED`, `QUERY_MIBIG_AND_REF`,
`QUERY_SHARED_REFERENCE`) plus `cross_strain` (yes / no: two regions of one strain are a family too). The companion
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

Each figure is the sealed family figure: BiG-SCAPE's own tree for the family on the left, one gene-arrow track per
member on the right, rows labelled `strain / contig / region / BGC alias` from the package inventory (an identity hold
where no alias is bound), reference rows labelled by layer, organism and accession, dotted homology links between
neighbouring rows. Families above `--max-tips` are drawn as a pruned view anchored on the focal strain; the title
says so. Cost: seconds for a small family, one to two minutes for a 40-row pruned view of a PKS/NRPS family.

Interactive alignment pages (clinker-style, one HTML per family, optional single-page PDF):

```bash
python tools/bigscape_clinker_html.py --db <label>.db --out <results>/figures \
    --focus STR-12 --cutoff 0.3 --fallback-cutoff 0.7 --chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Check, before sending any figure: open the PNG. Labels are complete (nothing cut at the left edge), the red rows are
your strains, the `_rows.tsv` `identity_hold` column is empty for every strain that has a package, and the caption
file states the link rule. A hold on a strain that has a package means the staged GBK and the package come from
different antiSMASH runs; see the troubleshooting page.

## 5. What to write and what not to write

Write: "regions A and B were assigned to the same BiG-SCAPE family at cutoff 0.3 in run <label>; the family has no
reference-layer or MIBiG member in this run" and cite the figure and the verdict row. Carry the placement denominator
and the contig-edge flag with every count.

Do not write: novel, new, rare, unknown compound, bioactive, or any product name from a MIBiG neighbour. A private
family is a statement about this panel and this reference set. A MIBiG member in the family is architecture
similarity, not compound identity. Judgment is deferred to the person who signs the card.


## Optional input and display scope

`bigscape_prep.py --min-query-genes N --query-strain <exact-id>` filters only the explicitly named query inputs before staging. Repeat `--query-strain` for additional queries; other inputs are never filtered. The default minimum is zero (disabled). Excluded source records, CDS counts and hashes are written to `EXCLUDED_SMALL_QUERY_FRAGMENTS.tsv`, with the exact rule in `QUERY_FILTER.json`. This is an operator-selected input scope, not a statement of biological absence or assembly completeness. Raw archives stay unchanged. These records carry source locators; an unbound BGC alias is explicitly recorded rather than invented.

`bigscape_cross_strain.py --out` takes a TSV filename. `--labels` reads unique exact strain keys and deposited display names, retaining the `strains` join column. `--exclude-products terpene,ectoine` performs an explicit case-insensitive contains match on the dominant product label, writing matching families to `<out>.PARKED.tsv` and the rule/counts to `<out>.FILTER.json`. No exclusion is enabled by default; mixed labels can match a token and must be reviewed when selecting scope.

`bigscape_clinker_html.py --row-order genes|similarity --min-genes N --labels labels.tsv` controls display order, minimum track size and deposited names. Similarity is a deterministic greedy order by shared dominant Pfam domains, not a phylogeny. Hidden tracks remain in the database and exports; the page states the hidden count. `--query-regex` must compile and contain a capture group. Full names remain in the page payload; the gutter bounds their on-page width. These options do not change family assignment, locus identity, product identity or activity claims.

The optional clinker `--chrome` PDF route requires the `documents` extra (`pypdf`). It validates a complete single-page family PDF, then closes its isolated browser process; it refuses an existing PDF instead of reporting stale output as newly rendered.
