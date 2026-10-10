# BGC size-by-type: annotated region content and scope

`tools/build_size_profile.py` summarizes saved banked BGC `length_kb` by one primary class per region. This is a companion view to counts, not an estimate of an unknown true number of clusters or independent proof that fragmentation has been removed. Region length and cluster count have different units; opposite correlations cannot mathematically bracket one biological quantity.

## Current computation

Input is `bgc_data.json` under `--banked-dir` (default `cohort`). Pure-saccharide omission policy applies before local classification, so `--include-saccharide` cannot necessarily restore rows already omitted. Family labels are derived for grouping; one primary class follows a preference list, with a fallback to the first available class. Hybrids do not contribute their full length to every component class. Each retained row's saved `length_kb` is summed; missing/falsey length contributes zero, not a verified zero-length BGC. Rows/overlaps/duplicates are not merged or deduplicated as genomic interval unions. No calculation establishes the “true length” of a split pathway.

Columns are the **top eight** classes by summed retained content. Strains are ordered by saved contig count; missing/falsey contig count sorts as zero, while plotted fragmentation uses `log10(max(contigs,1))`. The stacked figure/CSV show selected classes, while whole-cohort total correlations and workbook `total_kb` use all retained classes. Those different denominators must be named (`tools/build_size_profile.py:64–110,118–123,128–155`). Fewer than three observations or a zero-variance series returns correlation zero, not a measured null association (`:86–89`).

## Outputs and recovery

Outputs are three 160-dpi PNGs (`fig_bgc_size_by_type.png`, `fig_count_vs_size_fragmentation.png`, `fig_strain_class_size_heatmap.png`) and `fig_bgc_size_by_type_data.csv`. When a supplied workbook exists, `Size_By_Type` is replaced and that workbook is saved; a missing supplied workbook is silently not updated. Input reading uses the bank reader guard, but no source/code/config/output hash receipt is emitted. PNGs are direct writes; CSV and workbook use their respective atomic helpers, not an all-output transaction. Use a new external output and a separately authorized candidate workbook; inventory and hash actual inputs/outputs.

`--replot` restores rounded size columns from the CSV but initializes an **empty count table**. Its count panels are not reproduced from the original run. The source itself prints “count panels need full data.” Preserve the original full-data outputs and hashes; do not replace them with a replot and call the count/size comparison reproduced. Bank guard still applies even for replot (`:168–189`).

The current plot title still states “opposite biases bracket the truth” (`:148`). That is a residual scientific-wording hold: the documentation correction does not change or approve the generated label. Do not adopt it without separate owner review. Full individual-locus discussion requires strain / full node-or-contig / region / BGC alias; this summary does not supply that mapping.

## Historical cohort narrative, retained for provenance

The following original text contains redacted strain labels, point correlations, percentage estimates and claims about “real biology.” Its denominator, source inventory, receipt and cohort version are not bound here and were not reanalysed. It is retained verbatim as a historical statement, **not current guidance or verified result**. The “upper/lower frame,” causal interpretation and class-leader conclusions are held. Current user guidance is the source-scoped contract above.

````text
# BGC size-by-type — a fragmentation-robust alternative to BGC count

Instead of counting BGCs per class (which inflates with fragmentation because a split megasynthase is counted
several times), we sum the **total nucleotide content (kb) of each strain's BGCs by type**. A cluster split
across three contigs still contributes roughly its true length, so size is far less sensitive to the
count-inflation artefact.

## Result: count and size bias in opposite directions and bracket the truth

Whole-genome correlation with fragmentation (log10 contig count):

| metric | r vs fragmentation | bias |
|---|---|---|
| BGC **count** | **+0.39** | inflates — split clusters over-counted |
| total BGC **size (kb)** | **−0.55** | deflates — clusters truncated at contig edges lose nucleotides |

Neither is perfectly neutral: count over-counts in fragmented genomes, size under-counts (edge truncation).
Because the two biases run in opposite directions, **the true value is bracketed between them.** (Restricting
to "complete" clusters does not cleanly fix this — antiSMASH's `Full-contig` status means the region fills its
contig, which in fragmented genomes is itself a fragment, not a complete cluster: 61% of BGC content is
`Full-contig` in highly fragmented strains vs 1% in contiguous ones. So there is no free fragmentation-neutral
single metric here.)

## Why size is the better default anyway: the leaders become trustworthy

Switching count → size moves class leadership off fragmented artefacts and onto well-assembled genomes:

| class | leader by COUNT (contigs) | leader by SIZE (contigs) | change |
|---|---|---|---|
| NRPS | SID-XXX (1305) | **SID-XXX, 947 kb (453)** | artefact → a real Class-A lead strain |
| Terpene | SID-XXX (1108) | **SID-XXX, 315 kb (4 contigs)** | fragmented → near-complete genome |
| RiPP | SID-XXX (1646) | **SID-XXX, 262 kb (1 contig)** | fragmented → complete genome |
| Siderophore | SID-XXX (1902) | **SID-XXX, 122 kb (1 contig)** | fragmented → complete genome |
| T1PKS | SID-XXX (1108) | SID-XXX, 1186 kb (1108) | same — genuinely T1PKS-rich, not just split |
| T2PKS | SID-XXX (34) | SID-XXX, 208 kb (34) | same — already fragmentation-robust |

The size leaders for terpene, RiPP and siderophore are 1–4-contig assemblies — so their leadership is real
biology, not an assembly artefact. T1PKS staying on SID-XXX even by size shows that strain truly carries
exceptional T1PKS content (the 89-cluster count was not *only* fragmentation). T2PKS is unchanged because, as
shown earlier, its count was already fragmentation-independent.

## Recommendation
- **Report per-strain class profiles by SIZE (kb), not count** — `fig_bgc_size_by_type.png` is the
  fragmentation-aware version of the earlier per-strain class heatmap.
- Treat size as a **conservative (slightly downward-biased) lower frame** and count as the **upper frame**; for
  a specific cross-strain claim, the safest comparisons are among well-assembled genomes, or read the
  count/size pair together.
- The residual antiSMASH-annotation bias the original idea flagged is real (region boundaries + edge
  truncation), so size is "better, not perfect" — but it is the right default for biosynthetic *capacity*.

## Figures (reproducible from fig_bgc_size_by_type_data.csv)
- `fig_bgc_size_by_type.png` — per-strain total BGC size (kb) stacked by type (saccharide-omitted), strains
  ordered by contiguity.
- `fig_count_vs_size_fragmentation.png` — (left) per-class count(+) vs size(−) fragmentation correlation;
  (right) whole-genome count vs size against fragmentation.

All values candidate-level; KCB anchors are similarity, not identification.

````
