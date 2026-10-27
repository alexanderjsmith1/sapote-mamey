# BiG-SCAPE GCF network + clinker figures

Run these commands from the bundle root.


Two supporting figures: a strain's GCF network and a clinker comparison. Neither is acceptance evidence for a card. GCF
membership and clinker gene links are **similarity, not identity**; no compound claim follows.

## Commands
```bash
# GCF network for one strain, from a BiG-SCAPE 2 SQLite DB (run + cutoff are REQUIRED)
python mamey_run.py figures gcf-network --db <bigscape.db> --strain <ID> --run <N> --cutoff 0.5 \
    --evidence <all_evidence.json> --out net.png

# clinker comparison across >=2 region GBKs (a lead + its RG-GMCI partners, or a GCF family)
python mamey_run.py figures clinker /path/to/lead.region001.gbk /path/to/comparator.region001.gbk --out /path/to/new_review/fig.html
```
`--evidence` is optional (maps canonical loci to BGC ids and highlights Exceptional/High leads).

## Identity, actual graph scope, and interpretation

The network is a **strain-centric membership subgraph**, not a pairwise-distance or full-cohort network. Non-strain members are summarized as family nodes; the node CSV and `_scope.json` report this scope and counts. Canonical locator normalization helps reconcile supported input spellings but discards coverage text and does not establish full assembly/version identity. Evidence mappings keyed by normalized node/region can overwrite duplicates and do not verify protein/region/source hashes. Independently bind the full strain / full node-or-contig / region / BGC alias crosswalk before accepting labels/highlights.

Check that the run and cutoff exist and finished before you read the graph. The tool does not: a wrong run ID draws every record as dark. With `--evidence`, the dark set is counted from the evidence aliases, not the database records, so the two can differ. A dark record is absent from this membership view; it is not chemical novelty.

Components above 120 records are labeled “large component (N records)”, and the legend says the cause is not tested. Size alone does not show why a component is large, so no assembly or biological explanation is drawn; put any such reading in the caption, with its evidence. MIBiG anchoring is similarity, not product identity or production. Clinker links show similarity between supplied regions; they do not prove split-pathway reconstruction or physical joining.

## Outputs and completion

The network writes the image (170 dpi, capped by the safe-DPI limit), a node table `<stem>_data.csv` and `<stem>_scope.json`. The node table is not enough to redraw the graph. If the CSV write fails you get a warning and still `WRITTEN`; if the scope JSON fails the image may already exist. Check all three files.

Clinker requires at least two GBKs and its CLI on PATH. It requests HTML plus an alignments path; `WRITTEN` checks process return and HTML existence, not the alignment file, full identity or output freshness. Use an `.html` output name: the alignment name is made by literal `.html` replacement, so a suffix-free name can collide with the HTML output. Existing outputs are reused and can confuse a later attempt. Keep a fresh directory, exact GBK/hash roster and new artifact hashes. Timeout uses `MAMEY_SUBPROCESS_TIMEOUT_SEC` (default 30 minutes); `CLINKER_TIMEOUT`/`CLINKER_FAILED` are incomplete attempts.

## Planned clinker work (not built)

These are plans for later, not commitments. None is implemented and none has a date. Today's clinker routes are `figures clinker` above and `tools/bigscape_clinker_html.py`, described in the [cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

1. **One clinker folder per locus**, named `<strain>__<node>__<region>__<alias>/clinker/`. It would hold three pages: the best pairwise comparator, the cohort or type family, and the MIBiG or characterized references. Each page would have its own binding TSV and caption/methods file. The folder name and every row would carry the full strain / node / region / alias identity, never a bare alias.
2. **A narrower family view.** Draw the query locus, a few nearest cohort loci and a few genus-matched type or reference loci. Drawing every family record gives unreadable ribbon tangles on large families.
3. **A fixed checklist for each folder.**
   - Which named genes or domains define the shared biosynthetic core?
   - Which shared proteins are only generic transport, regulatory or housekeeping genes?
   - Do the core genes share order and orientation?
   - Which tailoring or resistance-like genes set the query apart?
   - Is the comparison full, partial or single-gene?
   - Does assembly fragmentation truncate either locus?
   - What stays unresolved?
4. **A note for type-II PKS comparisons.** ABC-transporter and membrane-component domains do not identify a type-II PKS on their own. Diagnostic weight belongs on the minimal PKS machinery, cyclases and aromatases, ketoreductases, tailoring enzymes and conserved neighborhood structure. The note would need literature support before it ships.

A clinker comparison is a similarity view between supplied regions. It does not assign a metabolite identity.

## Dependencies (optional; degrade gracefully)
`gcf-network` needs `networkx` + `matplotlib`; `clinker` needs the `clinker` CLI on PATH. Missing optional dependencies return `SKIPPED_NO_DEPS` / `SKIPPED_NO_CLINKER`. The CLI returns 1 unless the figure result is `WRITTEN`; database/schema/read/render errors may still raise exceptions.

## Home
`mamey/bigscape_figures.py` (figure layer, alongside `bgc_figures`/`cohort_figures`); wired at
`mamey/cli.py` + `mamey/bgc_figures.py` (engine-surface — the `figures` subcommand table).

## See also: KCB comparative locus map
`figures kcb-locusmap` (`mamey/kcb_locusmap.py`) is the offline, per-BGC comparative sibling of the
`clinker` figure: it draws the query locus over its top-N MIBiG KnownClusterBlast references with
homology ribbons shaded by BLAST %identity, matplotlib-only (no `clinker` CLI, no network), reading
the `knownclusterblast/*.txt` already inside the raw ZIP. Same posture — a SUPPORTING artifact,
similarity not identity, never acceptance evidence for a card. Full spec in docs/BGC_FIGURES.md.

Source owners: `mamey/bigscape_figures.py`; `mamey/bgc_figures.py`; `mamey/cli.py`.
