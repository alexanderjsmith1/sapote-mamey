# BiG-SCAPE GCF network + clinker figures

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


Two supporting figures the pipeline previously did not render (8 tools read the BiG-SCAPE DB; none
`savefig` a network). Both are SUPPORTING artifacts — never acceptance evidence for a card. GCF
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

The strain record query is not constrained to the selected run; only component membership uses `run` and `cutoff`. Records absent from those components are labeled dark. A nonexistent/mismatched run or missing cutoff rows can therefore produce a written graph full of dark records rather than a run-binding refusal. Check that the selected run exists, completed and admits the exact region/reference roster; reconcile included/held/unassigned records before interpreting darkness. A dark record means absence from the loaded membership view, not chemical novelty or no homolog in nature.

Components above 120 records are automatically labeled “fragmented supercomponent (assembly artifact).” That is a size heuristic; no fragmentation/assembly evidence is checked by this label. Keep the component-size observation separate from a biological/assembly explanation. MIBiG anchoring likewise does not establish primary metabolism, drug potential, product identity, or production. Clinker links show similarity between supplied regions; they do not prove split-pathway reconstruction or physical joining.

## Outputs and completion

The network writes the requested image (PNG in the CLI example, 170-dpi request subject to the safe-DPI cap), `<stem>_data.csv` and `<stem>_scope.json`. It does not emit a vector sibling or source/output hash receipt. The CSV is a node table, not an edge/coordinate manifest sufficient to regenerate the graph. Sidecar writing is non-blocking, so `WRITTEN` can coexist with a missing CSV. Bind the DB snapshot, evidence JSON, exact roster, run/cutoff, source version and output hashes separately; check native pixels at intended size and actual sidecar existence.

Clinker requires at least two GBKs and its CLI on PATH. It requests HTML plus an alignments path; `WRITTEN` checks process return and HTML existence, not the alignment file, full identity or output freshness. Use an `.html` output name: the alignment name is made by literal `.html` replacement, so a suffix-free name can collide with the HTML output. Existing outputs are reused and can confuse a later attempt. Keep a fresh directory, exact GBK/hash roster and new artifact hashes. Timeout uses `MAMEY_SUBPROCESS_TIMEOUT_SEC` (default 30 minutes); `CLINKER_TIMEOUT`/`CLINKER_FAILED` are incomplete attempts.

## Dependencies (optional; degrade gracefully)
`gcf-network` needs `networkx` + `matplotlib`; `clinker` needs the `clinker` CLI on PATH. Missing optional dependencies return `SKIPPED_NO_DEPS` / `SKIPPED_NO_CLINKER`. The CLI returns 1 unless the figure result is `WRITTEN`; database/schema/read/render errors may still raise exceptions.

## Home
`mamey/bigscape_figures.py` (figure layer, alongside `bgc_figures`/`cohort_figures`); wired at
`mamey/cli.py` + `mamey/bgc_figures.py` (engine-surface — the `figures` subcommand table).

## See also — KCB comparative locus map (v9.7.338)
`figures kcb-locusmap` (`mamey/kcb_locusmap.py`) is the offline, per-BGC comparative sibling of the
`clinker` figure: it draws the query locus over its top-N MIBiG KnownClusterBlast references with
homology ribbons shaded by BLAST %identity, matplotlib-only (no `clinker` CLI, no network), reading
the `knownclusterblast/*.txt` already inside the raw ZIP. Same posture — a SUPPORTING artifact,
similarity not identity, never acceptance evidence for a card. Full spec in docs/BGC_FIGURES.md.

Source owners: `mamey/bigscape_figures.py:98–180,205–277`; `mamey/bgc_figures.py:246–259`; `mamey/cli.py:7614–7623`.
