# BGC figure set (tools/bgc_figures.py)

Per-BGC figures for deliverables, each with a reproducible data CSV. Locus map (region GBK),
GCF-novelty lollipop (anchored BiG-SCAPE DB), and per-gene BLASTp identity (blastp-online panel).
Genes are labeled by function and colored by role, with no decorative reference lines.

## KCB comparative locus map (`figures kcb-locusmap`, `mamey/kcb_locusmap.py`)
An offline (matplotlib-only; no DIAMOND, no clinker CLI, no network) KnownClusterBlast query-vs-MIBiG
gene-cluster alignment. Query gene arrows sit on top (to genomic scale, role-colored from the region GBK
when a raw ZIP is supplied, else by KCB participation). The top-N MIBiG reference clusters stack
beneath, with each subject gene aligned under the query gene it pairs with. Homology ribbons link paired
genes, shaded by BLAST %identity. The figure carries a claim-safe caption and legend. Reads the antiSMASH
`knownclusterblast/*.txt` (or `clusterblast/*.txt`) already inside the raw ZIP — no new inputs. Emits
`<stem>_kcb_locusmap.png` + `.svg` + `<stem>_kcb_locusmap_data.csv`. Similarity, not identity; a
SUPPORTING figure, never acceptance evidence for a card.

## Optional Python dependencies

From the bundle root and the intended virtual environment, install `python -m pip install -e '.[figures]'` (or the broader `.[all]`). This selects DNA Features Viewer (`dna-features-viewer`, imported as `dna_features_viewer`), pyCirclize (`pycirclize`) and Biopython alongside the plotting stack. Native `figures diagram` and `figures atlas` require Biopython's `Bio.SeqIO`; the legacy tool's GBK parser has a separate built-in fallback. ANI additionally needs `pyskani` from the separate `addons` extra; `figures` and `all` do not provision that scanner/comparison stack, external binaries or reference datasets.

The two plotting libraries have no declared version interval pending API compatibility validation. Dependency selection does not establish a successful install, valid scientific input or successful rendering. For offline wheels and the best-effort add-on installer, see [Install](INSTALL.md#3-add-the-features-you-need). Optional imports stay local to the render functions; a lean core install does not acquire these libraries.

## Current routes and limits

There are distinct producers; do not transfer one route's receipt or data guarantee to another.

| Producer | Current behavior | Review limit |
|---|---|---|
| `tools/bgc_figures.py` | Up to three PNGs with per-figure CSVs; supplied GBK required, DB/BLASTp optional | Legacy PNG-only route (150-dpi request), no full identity/hash receipt or run/cutoff selector |
| `mamey/bgc_figures.py` / `figures diagram` | GBK arrow view through shared PNG/SVG save helper | Arrow labels use truncated first domain tokens, not a lossless exact-locus roster; no per-gene CSV from this function |
| `figures atlas` | Top 20 sectors by default from recursively found region GBKs | Sector lengths are region-record sequence lengths; multiple regions overwrite same filename-derived contig key. This is not a validated whole-genome/contig atlas |
| `figures ani` | First discovered FASTA per directory; per-sequence identities averaged and directional matrix symmetrized | Missing directions do not count as zero: retain the measured direction, average two measured directions, or show `no hit`/`NO_HIT` when neither is measured. Diagonal 100 is assigned; this is not automatic taxonomy/species admission. |
| `figures kcb-locusmap` | PNG/SVG plus pair-alignment CSV from supplied ZIP/text | Supporting comparative view, not the v8 complete gene-roster/receipt contract |

The legacy DB lollipop reads all distance rows for a selected record with no run/cutoff binding and takes the first matching record. Supply a separately verified single-run evidence export/database view or retain a run-scope hold; do not merge distances from different run identities. Missing BLASTp identity is plotted as zero while the CSV writes `NO_HIT`; that bar is missing comparison state, not measured zero percent identity. The consumer's nr axis label does not verify the imported search channel/query/run. Preserve those bindings independently. Optional plots may be absent despite overall completion.

The native ANI route returns `out_png=None` with an error if fewer than two eligible strain directories remain, and its CLI branch reports that no figure was written and returns 1. It can cap the strain list, chooses the first recursively discovered `.fna/.fasta` without validating a genome manifest, and omits alignment-fraction admission. Verify the exact selected input roster/hashes and directional comparison evidence separately; never use its fixed species-boundary title as a taxonomy verdict. Its artwork receipt hashes rendered outputs and prose provenance, not the source FASTAs.

Supply the full contig and region for KCB ZIP selection and verify that they identify one source member. The parser rejects some ambiguous selections, but a region-only selector can take the first matching region across contigs. Prefer an independently checked, uniquely selected `--kcb-txt` input when ZIP membership is ambiguous. The parser prefers knownclusterblast files globally and uses clusterblast only if none exist, so a missing KCB region is not silently supplemented from another channel. Pair CSV rows omit nonmatching query genes and do not carry full source identity/coordinates as separate columns. Zero query/reference counts can still render. Record source ZIP/member/text hashes, selection, full four-part locus identity and complete query roster separately. Use a fresh output/stem: current producers reuse fixed filenames, and shared receipts are candidate engineering artifacts. See [locus-map review](LOCUS_MAP_REVIEW_CONTRACT.md) and [v8](LOCUS_MAP_V8.md).

Source: `tools/bgc_figures.py`, `mamey/bgc_figures.py`, `mamey/kcb_locusmap.py`, `mamey/figure_save.py`.
