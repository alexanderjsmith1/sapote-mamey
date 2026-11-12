# Locus maps, gene tables and protein PCoA

These tools compare one antiSMASH region, or one protein family, with other genomes. Run them from the bundle root. The quick start needs only region GenBank files. An antiSMASH result ZIP works as input: `extract` reads the `*.region*.gbk` files inside it. To get a ZIP, see [your first run](reader/01_FIRST_RUN.md). Some tools below (gap rescue, reading pages) also need a validated package. A position or a match is sequence similarity. It does not show product identity, function or production.

## Terms

- **Kit:** the folder `protein_pcoa_ordinate.py extract` creates. `REGION_CDS.faa` holds each CDS that has a translation in the region files it admits (an exact repeat of a region file is admitted once); a CDS with no translation is left out. The set files hold only proteins matched to a named family: `extract` writes the KS, AT, A and C domain sets and the LANC and YCAO sets, `pfam` adds the Pfam family sets, and `card` adds the resistance sets. A translated CDS that matches none of them is in `REGION_CDS.faa` but in no set.
- **Set:** one protein family inside a kit, for example `KS` (ketosynthase), `AT`, `A`, `C`, or a resistance family `RES01`. Each set is ordinated on its own.
- **PCoA:** principal coordinates analysis. It turns protein-to-protein identity distances into points on a plane. Close points are similar proteins.
- **Cohort table:** a TSV with `strain` and `cohort` columns. It says which of your strains belong to which group. `protein_pcoa_compare.py` calls the second column `collection`.
- **DIAMOND:** a fast protein search program (`diamond` on `PATH`). **tblastn** is a BLAST+ program that searches protein queries against genome DNA.
- **Region GenBank file:** one antiSMASH region as a `.gbk` file, named like `<contig>.region001.gbk`. **Locus:** one such region.
- **Ledger:** a TSV with one row per gene (CDS) and a `strain` column, holding annotations. **Gap rescue:** the optional `gap-rescue` command, which looks for missing genes of a cluster near its edges.
- **Receipt:** a JSON file that lists a step's inputs and outputs with SHA-256 hashes, so you can check later that nothing changed.

## Quick start: extract, ordinate, render

Needs DIAMOND, a fast protein search program. Install it with
`conda install -c bioconda diamond`, or pass the path to an existing `diamond` with `--diamond`. Each step refuses to overwrite its own outputs.

**1. Extract.** Reads region GenBank files (`*.gbk` in a folder, searched recursively, or a `.zip` of them) and writes the kit. `--input` is `SOURCE=PATH`, where SOURCE is `isolate`, `reference` or `MIBiG`. The strain name comes from the input: for a ZIP it is the ZIP file name without `.zip`; for a loose `.gbk` file it is the part of the file name before `__`, or before the first `.` when there is no `__`. Your cohort table must use these exact names.

**Where the inputs come from.** Isolate inputs are your own antiSMASH result ZIPs. Reference inputs are antiSMASH region files from public genomes, for example from the [public antiSMASH datasets](PUBLIC_DATASETS.md). MIBiG inputs are MIBiG GenBank files ([MIBiG download](EXTERNAL_DATA.md#mibig-reference-index-and-neighborhoods)). The selected protein set needs at least four retained points for `ordinate`; the number of isolate ZIPs alone does not establish that count. A smaller retained set stops with `REFUSED: fewer than four retained points`. Accepted file names, duplicates and the assembly table are in [protein input rules](447_COMPANION_RETRIEVAL_CONTROLS.md#3-protein-input-for-protein_pcoa_ordinatepy-extract).

```bash
python3 tools/protein_pcoa_ordinate.py extract --kit kits/demo \
  --input isolate=regions/isolates --input reference=regions/references \
  --cohort-table cohorts.tsv
```

You should see the kit folder with `REGION_CDS.faa`, `REGION_CDS_META.tsv`, and one `<SET>.faa` and `<SET>_META.tsv` per set (a set with no proteins gets an empty file; the counts print to the terminal). `cohorts.tsv` is tab-separated with the header `strain<TAB>cohort`.

**2. Ordinate.** Pick one set. Run `--preflight` first to see the size estimate without computing anything.

```bash
python3 tools/protein_pcoa_ordinate.py ordinate --kit kits/demo --set KS \
  --preflight --resource-receipt-dir kits/demo_preflight
python3 tools/protein_pcoa_ordinate.py ordinate --kit kits/demo --set KS
```

Success writes `kits/demo/out_KS/PCOA_KS.tsv` and `RUN_KS.json`. A refusal prints the reason (a limit that failed, fewer than four retained points, or an input problem). Nothing is shrunk or subsampled. A refused run leaves `out_KS/RESOURCE_ATTEMPT/terminal.json` in the kit, and rerunning with the same `--kit` then prints `REFUSED: existing ordinate output is retained; choose a fresh --attempt-root`. To retry, fix the cause and add a new output folder: `python3 tools/protein_pcoa_ordinate.py ordinate --kit kits/demo --set KS --attempt-root kits/demo_try2`. Later steps then read `kits/demo_try2`. To also write `out_KS/NEAREST_KS.tsv` (each cohort protein's closest reference or MIBiG protein), run `python3 tools/protein_pcoa_ordinate.py nearest --kit kits/demo --set KS`.

**3. Render.** `--panel NAME=COHORT` draws the cohort named COHORT (a value in the `cohort` column of the cohort table) among the reference points, and NAME is used in the output file names.

```bash
python3 tools/protein_pcoa_render.py --kit kits/demo --set KS --out figs/ks \
  --cohort-table cohorts.tsv --panel isolates=isolate_group
```

Success writes `PCOA_KS_isolates.pdf`, `.svg` and `.png`, plus `LABELS_KS_isolates.tsv` and `panel_KS_isolates.json`. The output folder must be new or empty. Inspect the picture yourself, then follow [figure house rules](FIGURE_HOUSE_RULES.md) and [figure style](FIGURE_STYLE.md).

If `extract` fails it can leave partial files in the kit; keep them and start a new kit folder. If `ordinate` is refused, see step 2. A refused render leaves its output folder; use a new one.

## Which tool answers which question

| Tool | Question | Needs | Writes |
|---|---|---|---|
| `protein_pcoa_ordinate.py` | Where do these proteins sit among references? | region GenBank files | the kit, `out_<SET>/` |
| `protein_pcoa_render.py` | Draw that picture | a kit, a cohort table | PDF, SVG, PNG, label tables |
| `protein_pcoa_compare.py` | Do cohorts differ on the kit? | `--kit`, `--cohort`, `--out` | statistics, plots, `CAPTION.md` |
| `pcoa_bgc_explorer.py` | Click a cohort protein to see its whole BGC; rotate the three axes on request | `--kit --regions --out` | an offline HTML view |
| `locus_rarity_by_genus.py` | How common is one region in each genus? | `--kit --query-strain --query-region --out` | per-genus counts |
| `family_rarity_by_window.py` | How many genomes carry a region's core genes side by side? | `--antismash-zip --strain --proteomes --genome-table --query-family --out` | per-region counts, `PASS_GENOMES.tsv.gz` |
| `region_presence_survey.py` | Is one region present in each of these genomes? | `--genomes --out`, plus `--query-faa` or `--antismash-zip --contig --region` | per-genome table |
| `comparison_map_pages.py` | Draw many locus comparison maps on one scale | a spec TSV | maps, pages, `locus_pairs.tsv` |
| `locus_reading_pages.py` | One reading page per region, every gene and evidence layer | `--out --package STRAIN=DIR` and a ledger | Markdown pages |
| `gap_rescue_gene_table.py` | Per-gene table for a gap-rescue run | `--run --zip --reference` | gene table |

Run `python3 tools/<name>.py --help` for every flag.

## Locus tools

**Gap rescue.** `python mamey_run.py gap-rescue` is optional and runs after validation. It needs separately provisioned search inputs, and the main `run` never starts it. It is a screen, not an adjudication. Required: `--strain`, `--input-zip` and `--out`; `--out` must be outside the bundle. Example: `python mamey_run.py gap-rescue --strain EXAMPLE --input-zip antiSMASH.zip --out /path/outside/bundle/gap`. It finds MIBiG GenBank files and Pfam-A through `--mibig-dir` and `--pfam`, or the environment variables `SAPOTE_MIBIG_GBK_DIR` and `SAPOTE_PFAM_HMM` (these differ from the `MAMEY_*` variables in [external data](EXTERNAL_DATA.md)). Check `python mamey_run.py gap-rescue --help`. It writes one folder per region plus `SUMMARY.tsv` to `--out`. Then, for one region folder:

```bash
python tools/gap_rescue_gene_table.py --run OUT/<region folder> --zip antiSMASH.zip --reference reference.gbk
```

The table has one row per reference gene. A displayed split lists both pieces in one row. It gives saved local and reference protein lengths and their ratio (blank for splits). The ratio is not alignment coverage. Captions separate reference-gene counts from distinct local proteins.

**Reading pages.** `locus_reading_pages.py` needs one `--package STRAIN=DIR` per strain and a gene annotation ledger (`--ledger` or `--ledger-dir`). `--gecco`, `--mibig-json`, `--mibig-proteins`, `--proteomes`, `--pfam` and `--hmmsearch` read extra evidence, and `--proteomes`, `--pfam` and `--mibig-proteins` start new searches. Leave those out to read existing evidence only; unsearched layers are reported as unsearched. Each locus is shown as strain / full node-or-contig / region / BGC alias. Hand assessments (`--assessments`) are separate authored material.

**Rarity by genus.** `locus_rarity_by_genus.py` searches the region's proteins against every non-MIBiG region protein in the kit (DIAMOND, at least 50 % identity over at least 70 % of the query gene). Per genus it counts genomes with a region matching at least 50 % of the genes, at least 50 % of the core genes, and at least 30 % of the core genes. Core means antiSMASH `gene_kind` biosynthetic or biosynthetic-additional. Public reference genomes and your own isolates are counted in separate columns. Denominators come from the kit, or from `--genome-table` so that genomes with no region are counted.

The tool counts genomes by assembly by default, because a collection can hold one assembly several times (a versioned and an unversioned accession, a WGS id and its GCA, a CP/AP entry and the GCA entry). A strain's key is its `assembly_accession` from `--genome-table`, else its own id (GCF folded to GCA, version dropped). Strains of one genus with identical `total_bp` are merged only when at most one distinct explicit accession is among them (an `assembly_accession`, or a GCA/GCF accession used as the strain id). Two entries with different explicit accessions stay separate even at the same length, and `RECEIPT.json` lists them in `assembly_key_length_review_candidates`. Both rules are heuristics: equal length, or the same accession after dropping the version and folding GCF to GCA, does not prove two entries are one assembly. So `_by_assembly` counts are not verified unique assemblies. `ASSEMBLY_KEYS.tsv` shows every key and the rule that set it, and `RECEIPT.json` lists each length merge in `assembly_key_length_merges` for review. Every count is reported both `_by_assembly` and `_by_entry`; the main columns follow `--count-by` (`assembly` or `entry`).

**Rarity by window.** `family_rarity_by_window.py` searches each region's core genes (from the strain's antiSMASH zip) against a whole-proteome database whose headers read `ACC|contig|start|end|strand`. Same DIAMOND thresholds. A genome counts for a region when its genes sit in one window on one contig with gaps of at most 20 kb. A region is family-rare at 2 or fewer family genomes with at least 30 % of its core in one window, if it has at least 3 core genes. Headline counts are for `--query-family`, with whole-table counts beside them. `PASS_GENOMES.tsv.gz` keeps every genome that reached 30 %, so counts can be redone without searching again. It uses the same assembly rule and `--count-by` as above.

**Presence survey.** `region_presence_survey.py` tests one region in each genome under two rules, side by side. The protein rule is the one above (DIAMOND on proteomes). The nucleotide rule runs tblastn on each genome sequence and keeps the best hit per gene if it covers at least 50 % of the protein, with no identity floor. Per genome and rule it reports genes found, the identity range and the largest one-contig window (gaps of at most 20 kb) with coordinates. Give `--antismash-zip` with `--contig` and `--region` (`--flank` adds genes on each side), or give `--query-faa`. tblastn finds genes the protein rule misses: below 50 % identity, short genes, and ORFs the gene caller skipped. Report which rule a number comes from. A gene below a rule's floor is not thereby absent.

**Comparison maps.** `comparison_map_pages.py run SPEC.tsv --out DIR` draws `multi_reference_comparison.py` maps in batches, one spec row per map. Spec columns (tab-separated; `#` lines are comments; relative paths resolve against the spec's folder):

| Column | Meaning |
|---|---|
| `map_id` | required; output folder name |
| `zip` | required; antiSMASH zip of the query locus |
| `label` | required; the strain label the locus is drawn with |
| `bgc` or `rescue` | one required; the BGC alias, or a gap-rescue `<BGC>_vs_<ref>` folder |
| `genus`, `ref_gbk_dirs`, `ref_gbks`, `extra_zips` | optional; where public-genome references come from |
| `compare_loci`, `mibig` | optional; other isolate loci (`label|BGC|zip`) and MIBiG GenBank files, always drawn when they match |
| `top` | optional; how many unpinned references to draw |
| `gene_labels`, `page_group` | optional; a label TSV; maps sharing a value share pages |

All maps in a batch or `page_group` share one width and one kilobase scale; `--shared-scale none` lets each map fill its width. `locus_pairs.tsv` gives a global alignment (BLOSUM62, gap open 11, extend 1) of each matched protein pair. The receipt records every input and output with SHA-256. A matched gene is a best protein hit, not orthology, function or product.

**Compare cohorts.** `protein_pcoa_compare.py` takes the kit and a TSV with `strain` and `collection` columns. Its denominator is the cohort members represented in the kit's per-set tables. Genome-level tests are primary. Protein-level tests are secondary, and pairwise p-values are raw and exploratory.

**Explorer.** `pcoa_bgc_explorer.py` gives an offline rotatable three-axis view of the same coordinates. Rotating changes the display, not the scores. Points without identity values keep a separate symbol.

Tools and commands are listed in the [command catalog](COMMAND_CATALOG.generated.md) and [tools inventory](TOOLS_INVENTORY.generated.md).

# Reference: limits, receipts and refusals

You do not need this half for a first figure. Terms:

- **RSS:** the memory a process holds in RAM.
- **Cluster-first:** group near-identical reference and MIBiG proteins first and keep one representative each, so the ordination matrix stays small. Cohort proteins are never grouped.
- **Admission:** the check, before heavy work, that estimated memory and disk fit the limits.
- **Bound:** recorded in a receipt with a SHA-256 hash, so a later check can detect a change.
- **Native vs supplied:** native values were computed by the bundle's own ordination code. Supplied values (axis percentages, an embedding) came from a file you gave the renderer.

## Replay and receipts

`protein_pcoa_render.py` redraws a kit from saved coordinates and fits nothing. It needs the cohort table, the `out_<SET>/` PCoA and nearest tables and the original `RUN_<SET>.json`. Optional: a drop-origins list (region files whose points are not drawn) and a set-names table. A folder of delivered tables may need renaming into the `out_<SET>/` layout.

Axis percentages come from `pct_axes` in the RUN file. If missing, labels are plain and the panel receipt says `axis_metadata.state = NOT_PROVIDED`. `--require-axis-metadata` refuses to draw when they are missing.

The render receipt lists input and output hashes, the renderer source and the figure policy. If an input changes while drawing, the attempt is refused and the partial artwork is left without a success receipt. Do not present it as finished. Receipts can contain local paths; check them before sharing.

## Limits for `ordinate`

Defaults: 3,800,000,000 bytes of RSS (process and DIAMOND children), 2,000,000,000 bytes of free disk, 900 seconds, 4 DIAMOND threads. Change them with `--rss-limit-bytes`, `--min-free-disk-bytes`, `--timeout-seconds` and `--threads`. The estimates are conservative guesses. The tool never raises a limit or subsamples. If process monitoring is unavailable, it refuses.

`--preflight --resource-receipt-dir NEW_DIR` prints counts and estimates and computes nothing; `NEW_DIR` must not exist. A refused preflight writes `terminal.json` there.

Sets with reference or MIBiG proteins use cluster-first by default; `--no-cluster-first` checks the unclustered upper bound instead. Cohort-only sets are never clustered. After clustering, the count must fit within 80 % of the RSS limit before the all-against-all search. `--preflight --cluster-first` reports `PREFLIGHT_CLUSTER_ADMITTED_ORDINATION_PENDING`: clustering was not run and the final count is unknown.

Each attempt needs a fresh `out_<SET>`. Use `--attempt-root` to retry (see step 2). Failed scratch under `RESOURCE_ATTEMPT` is not a kit. Inputs must not pass through symlinks.

`--keep-allvsall` keeps `allvsall.tsv.gz`, the hit table behind the distances; the RUN file records its hashes. `distance_matrix(path, ids)` in `protein_pcoa_ordinate.py` rebuilds the float32 distance matrix from it: each pair takes the smallest `1 - percent_identity/100` over both hit directions, unreported pairs are 1, the diagonal is 0. Check memory before calling it.

## Axis percentages

A `pct_axes` vector is an annotation. It does not prove variance explained. Values are kept as given, including above 100 or below zero. The bundle's own PCoA reports `100 * eigenvalue / signed trace` of the double-centered squared-distance matrix. For non-Euclidean distances these ratios are not variance explained; do not clip or renormalize them. A caption calls the definition native only when the `ordinate` receipt chain is valid and the hashes match; otherwise it says "supplied".

## Renderer controls

- `--layout trimap` or `--layout tsne` needs one `--embedding-table SET=TSV` per set, with the kit's point IDs and `TRIMAP1/TRIMAP2` or `TSNE1/TSNE2` columns. Bad headers, duplicate or missing IDs and non-finite values are refused. No fit is run.
- An adjacent `.json` file may give `coordinates_sha256` and a `trimap` or `tsne` object with `version`, an integer `seed` and optional `parameters`. Only complete metadata with a matching hash enters the caption; otherwise the caption says unknown.
- `--page pcoa,trimap` puts saved layouts side by side on one R page with one legend. It needs R, uses an 8 pt text floor and 70/85 % identity tiers by default. `--label-names` takes a TSV with the header `strain<TAB>short<TAB>display`.
- `--quantile` (default 0.95) sets the fraction of background nearest-neighbor distances used to pick labels. Label TSVs add `threshold_distance` and `label_quantile`; `threshold_p95` is filled only at 0.95.
- `protein_pcoa_compare.py` writes `AXIS_ANNOTATIONS.json` and `CAPTION.md`. `--min-text-pt` (default 8, lower values refused) applies at each PDF's native width: 6.4 in for share-below, 7.2 in for other panels. A layout that does not fit is refused, not shrunk. It also writes `<figure>_text_check.json` and `SOURCES.tsv`.

## Page artwork and checks

Pages keep PDF and SVG masters and the PNG drawn by R, plus a `_plot_only.png` at 300 DPI. Captions and methods are separate files. `figure_render_qc.py --print-width-in W` checks effective DPI as pixels divided by W; without a width it reports `NOT_CHECKED`.

A finished packet has a completion receipt with every output hash. QA rechecks them and refuses an edited file. QA reports (`RENDER_QC.md`, `RENDER_QC.tsv`) are create-only: use a new folder inside the packet or beside it, never the packet root. A bad receipt or `--render-receipt-sha256` exits 2 and writes no reports. See [completed render-packet QA](COMPLETED_RENDER_PACKET_QA.md).

## t-SNE companion panel

`protein_pcoa_ordinate.py tsne --kit KIT --set S` fits t-SNE on the same identity distances. It reads the retained `allvsall.tsv.gz` and checks it against `RUN_<SET>.json`; a kit without one needs `--allvsall PATH` (the sidecar then records `SUPPLIED_NOT_BOUND_BY_RUN`). Defaults: perplexity 40, seed 20261019. It writes `out_<SET>/TSNE_<SET>.tsv` (`id`, `TSNE1`, `TSNE2`) and `TSNE_<SET>.json`, read by `protein_pcoa_render.py --page pcoa,tsne --embedding-table S=.../TSNE_<SET>.tsv`. It needs scikit-learn and scipy, refuses existing outputs, and substitutes no other method.

The sidecar holds trustworthiness (`k = min(10, (n - 1) // 2)`) and a Spearman rho over up to 200,000 seeded pairs (`spearman_pairs` gives the count used). Use PCoA for distances between groups. In t-SNE, cluster sizes, gaps and positions are not distances.

## Single-file offline viewers

[Standalone protein space and reference match explorer](PROTEIN_SPACE_STANDALONE.md) documents `tools/protein_space_standalone.py`. It packs an existing display and catalog, with Plotly and fonts, into standalone HTML files. It runs no new search, ordination, redraw or test.
