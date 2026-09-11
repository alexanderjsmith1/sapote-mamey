# BiG-SCAPE GCF network + clinker figures

Two supporting figures the pipeline previously did not render (8 tools read the BiG-SCAPE DB; none
`savefig` a network). Both are SUPPORTING artifacts — never acceptance evidence for a card. GCF
membership and clinker gene links are **similarity, not identity**; no compound claim follows.

## Commands
```bash
# GCF network for one strain, from a BiG-SCAPE 2 SQLite DB (run + cutoff are REQUIRED)
python -m mamey figures gcf-network --db <bigscape.db> --strain <ID> --run <N> --cutoff 0.5 \
    --evidence <all_evidence.json> --out net.png

# clinker comparison across >=2 region GBKs (a lead + its RG-GMCI partners, or a GCF family)
python -m mamey figures clinker <gbk1> <gbk2> ... --out fig.html
```
`--evidence` is optional (maps canonical loci to BGC ids and highlights Exceptional/High leads).

## Node identity (why this can't mis-map)
Contig·region identity uses the **tested ingest mapping** `bigscape_ingest_to_mamey.canon_locator`
/`parse_locator` — the same cov-independent key (`NODE_<n>_length_<L>.region<NN>`) the BiG-SCAPE
ingest path uses. Figure identity therefore equals ingest identity, so a node cannot be attributed
to the wrong BGC. `tests/test_bigscape_mapping.py` pins this (DB gbk-path form and evidence
short-node form reduce to the same key) and guards against a hand-rolled NODE_ regex regressing in.

## Colours / categories
From `bigscape_figure_labels` (the single source of truth): MIBiG references are red, cohort type
strains grey, never a bare "Reference". Families are coloured by what a BiG-SCAPE DB actually knows —
**MIBiG-anchored** (has a known-cluster reference), **cohort-shared**, or **fragmented
supercomponent** (a large low-similarity component = assembly artifact, not one GCF). Host-habitat
colouring is intentionally not attempted here — habitat is not in the BiG-SCAPE DB.

## Interpretation (claim-safe)
- **GCF-dark singleton = novelty-leaning** (no characterized MIBiG/cohort analogue). Leads clustering
  dark is the expected, statable novelty signal.
- A broadly **MIBiG-anchored** family is usually conserved/primary metabolism (terpene, ectoine) — not
  a specialised-drug signal.
- clinker identities are similarity (report the range, e.g. 0.30–0.65). A lead + RG-GMCI partners
  visualizes a split assembly line; a single thin gene link is a cutoff caution.

## Dependencies (optional; degrade gracefully)
`gcf-network` needs `networkx` + `matplotlib`; `clinker` needs the `clinker` CLI on PATH. Absent →
a clear `SKIPPED_NO_DEPS` / `SKIPPED_NO_CLINKER` status, never a crash.

## Home
`mamey/bigscape_figures.py` (figure layer, alongside `bgc_figures`/`cohort_figures`); wired at
`mamey/cli.py` + `mamey/bgc_figures.py` (engine-surface — the `figures` subcommand table).

## See also — KCB comparative locus map (v9.7.338)
`figures kcb-locusmap` (`mamey/kcb_locusmap.py`) is the offline, per-BGC comparative sibling of the
`clinker` figure: it draws the query locus over its top-N MIBiG KnownClusterBlast references with
homology ribbons shaded by BLAST %identity, matplotlib-only (no `clinker` CLI, no network), reading
the `knownclusterblast/*.txt` already inside the raw ZIP. Same posture — a SUPPORTING artifact,
similarity not identity, never acceptance evidence for a card. Full spec in docs/BGC_FIGURES.md.
