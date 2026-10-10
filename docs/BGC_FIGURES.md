# BGC figure set (tools/bgc_figures.py)

Per-BGC figures for deliverables, each with a reproducible data CSV. Locus map (region GBK),
GCF-novelty lollipop (anchored BiG-SCAPE DB), and per-gene BLASTp identity (blastp-online panel).
Function-labelled, role-coloured, no decorative reference lines. See README_PATCH (v9.7.319).

## KCB comparative locus map (`figures kcb-locusmap`, `mamey/kcb_locusmap.py`) — v9.7.338
An offline (matplotlib-only; no DIAMOND, no clinker CLI, no network) KnownClusterBlast query-vs-MIBiG
gene-cluster alignment. Query gene arrows on top (to genomic scale, role-coloured from the region GBK
when a raw ZIP is supplied, else by KCB participation); the top-N MIBiG reference clusters stacked
beneath, each subject gene aligned under the query gene it pairs with; homology ribbons linking paired
genes, shaded by BLAST %identity; claim-safe caption + legend. Reads the antiSMASH
`knownclusterblast/*.txt` (or `clusterblast/*.txt`) already inside the raw ZIP — no new inputs. Emits
`<stem>_kcb_locusmap.png` + `.svg` + `<stem>_kcb_locusmap_data.csv`. Similarity, not identity; a
SUPPORTING figure, never acceptance evidence for a card.

## Current routes and limits

There are distinct producers; do not transfer one route's receipt or data guarantee to another.

| Producer | Current behavior | Review limit |
|---|---|---|
| `tools/bgc_figures.py` | Up to three PNGs with per-figure CSVs; supplied GBK required, DB/BLASTp optional | Legacy PNG-only route (150-dpi request), no full identity/hash receipt or run/cutoff selector |
| `mamey/bgc_figures.py` / `figures diagram` | GBK arrow view through shared PNG/SVG save helper | Arrow labels use truncated first domain tokens, not a lossless exact-locus roster; no per-gene CSV from this function |
| `figures atlas` | Top 20 sectors by default from recursively found region GBKs | Sector lengths are region-record sequence lengths; multiple regions overwrite same filename-derived contig key. This is not a validated whole-genome/contig atlas |
| `figures ani` | First discovered FASTA per directory; per-sequence identities averaged and matrix symmetrized | Missing comparison hits become 0; diagonal 100 is assigned. This is not automatic taxonomy/species admission |
| `figures kcb-locusmap` | PNG/SVG plus pair-alignment CSV from supplied ZIP/text | Supporting comparative view, not the v8 complete gene-roster/receipt contract |

The legacy DB lollipop reads all distance rows for a selected record with no run/cutoff binding and takes the first matching record. Supply a separately verified single-run evidence export/database view or retain a run-scope hold; do not merge distances from different run identities. Missing BLASTp identity is plotted as zero while the CSV writes `NO_HIT`; that bar is missing comparison state, not measured zero percent identity. The consumer's nr axis label does not verify the imported search channel/query/run. Preserve those bindings independently. Optional plots may be absent despite overall completion.

The native ANI route returns `out_png=None` with an error if fewer than two eligible strain directories remain, yet its CLI branch returns 0. It can cap the strain list, chooses the first recursively discovered `.fna/.fasta` without validating a genome manifest, and omits alignment-fraction admission. Verify the exact selected input roster/hashes and directional comparison evidence separately; never use its fixed species-boundary title as a taxonomy verdict. Its artwork receipt hashes rendered outputs and prose provenance, not the source FASTAs.

KCB ZIP selection requires explicit full contig and region when multiple source members could match; prefer a checked exact member binding. The parser prefers knownclusterblast files globally and uses clusterblast only if none exist, so a missing KCB region is not silently supplemented from another channel. Pair CSV rows omit nonmatching query genes and do not carry full source identity/coordinates as separate columns. Zero query/reference counts can still render. Record source ZIP/member/text hashes, selection, full four-part locus identity and complete query roster separately. Use a fresh output/stem: current producers reuse fixed filenames, and shared receipts are candidate engineering artifacts. See [locus-map review](LOCUS_MAP_REVIEW_CONTRACT.md) and [v8](LOCUS_MAP_V8.md).

Source owners: `tools/bgc_figures.py:43–58,176–217,223–295`; `mamey/bgc_figures.py:39–50,59–140,143–244`; `mamey/kcb_locusmap.py:290–370,479–500,599–623`; `mamey/figure_save.py:63–142`.
