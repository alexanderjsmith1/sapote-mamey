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
