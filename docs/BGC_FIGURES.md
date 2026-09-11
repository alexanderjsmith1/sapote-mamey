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
