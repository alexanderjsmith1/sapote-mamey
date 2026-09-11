"""BiG-SCAPE GCF network + clinker comparative figures (supporting figures only).

Sapote-Mamey encodes per-strain F/G/D figures and per-BGC diagram/atlas/ani, plus BiG-SCAPE-derived
*scalars* (GCF-dark -> novelty, RG-GMCI -> Mode B §10/§29). It does NOT render the GCF network graph
from a BiG-SCAPE 2 DB, nor clinker cross-cluster alignment. This module adds both.

Discipline (matches the rest of the figure layer):
  * GCF membership and clinker gene links are SIMILARITY, not identity. No compound claim follows.
  * Contig<->region identity uses the TESTED ingest mapping `bigscape_ingest_to_mamey.canon_locator`
    /`parse_locator` (cov-independent: NODE_<n>_length_<L>.region<NN>). Figure node identity is then
    identical to ingest identity, so a node can't be attributed to the wrong BGC (the .291/.292
    mis-map class a naive NODE_ regex would reintroduce — this time in a published figure).
  * Node categories/colours come from `bigscape_figure_labels` (the single source of truth that keeps
    MIBiG references red and cohort type strains grey, never a bare "Reference").

Deps: gcf_network needs networkx + matplotlib; clinker_figure needs the `clinker` CLI on PATH.
Both degrade with a clear status dict if a dependency is absent.
"""
from __future__ import annotations
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import warnings as _warnings
import json, os, sqlite3, subprocess, shutil, sys
from pathlib import Path
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

# v9.7.409 (DEEP_AUDIT2_resource_dos #5): clinker is an all-vs-all external CLI with no internal
# bound; a large/degenerate GBK set can make it run effectively forever, and the subprocess had no
# timeout, so a hung child would hang the whole Sapote-Mamey run. Bound every external-tool
# subprocess with a wall-clock timeout (env-overridable via MAMEY_SUBPROCESS_TIMEOUT_SEC; default
# 30 min). On timeout we return a typed status, never SIGKILL the parent or hang.
_DEFAULT_SUBPROCESS_TIMEOUT_SEC = 1800


def _subprocess_timeout_sec() -> float:
    """External-tool wall-clock timeout in seconds (env-overridable, read at call time)."""
    try:
        val = float(os.environ.get("MAMEY_SUBPROCESS_TIMEOUT_SEC", str(_DEFAULT_SUBPROCESS_TIMEOUT_SEC)))
        return val if val > 0 else _DEFAULT_SUBPROCESS_TIMEOUT_SEC
    except (TypeError, ValueError):
        return _DEFAULT_SUBPROCESS_TIMEOUT_SEC


def _load_json(path):
    """Safe JSON read — context-managed via read_text, explicit encoding, never a bare open()."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"could not read JSON {path}: {e}") from e


def _tool(module):
    """Import a tools/ helper module (canonical ingest + figure labels live there)."""
    tools = Path(__file__).resolve().parents[1] / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    return __import__(module)


def _strain_token_match(basename, strain):
    """True iff `strain` is a full '_'-delimited token in a bigscape_prep gbk basename.

    bigscape_prep names region files "<strain>_<contig>.regionNN.gbk". A bare substring
    test bleeds — "AS-XXX" would match "AS-XXX_...". Anchoring on '_' boundaries prevents
    that while still matching a token embedded in a longer prefix (e.g. "SID8374" inside
    "Streptomyces_sp._SID8374_...").
    """
    # v9.7.371 fix: the SQL prefilter (LIKE %strain%) that calls this is case-insensitive by
    # default (SQLite ASCII LIKE), but this token check was case-sensitive -- a caller/on-disk
    # casing mismatch (e.g. strain="AS-XXX" vs filenames "AS-XXX_...") silently dropped every
    # record the SQL layer found, reading as NO_RECORDS instead of a case mismatch.
    b, s = basename.lower(), strain.lower()
    return b.startswith(f"{s}_") or f"_{s}_" in b


def gcf_network(db, strain, run, cutoff, evidence=None, out="gcf_network.png", leads=None):
    """Render a strain's BiG-SCAPE GCF network at a cutoff, from a BiG-SCAPE 2 DB.

    run and cutoff are REQUIRED (no silent default — a cutoff changes the whole picture).
    Returns a dict roll-up so the figure ships with a claim-safe interpretation, not a bare graph.
    """
    if run is None or cutoff is None:
        return {"status": "MISSING_ARGS", "detail": "run and cutoff are required"}
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except Exception as e:  # pragma: no cover
        return {"status": "SKIPPED_NO_DEPS", "detail": f"needs networkx+matplotlib ({e})"}
    L = _tool("bigscape_figure_labels")
    I = _tool("bigscape_ingest_to_mamey")

    node2bgc = {}
    LEADS = set(leads or [])
    # AUDIT_374 fix: auto-populate LEADS from every Exceptional/High-tier BGC in the
    # evidence file when the caller passed no explicit --leads. The guard must gate the WHOLE
    # loop (caller-supplied vs auto-derive), not each item — `if not LEADS` re-checked per
    # iteration stopped auto-adding after the FIRST exceptional/high BGC (LEADS becoming
    # non-empty made every later iteration's check False), silently dropping every other real
    # lead from the figure's highlighted set. Decide once, before the loop.
    _auto_leads = not LEADS
    if evidence and Path(evidence).exists():
        for b, e in _load_json(evidence).items():
            key = I.canon_locator(f"{e.get('node','')}.{e.get('region','region001')}")
            if key:
                node2bgc[key] = b
            if _auto_leads and str(e.get("tier", "")).lower() in ("exceptional", "high"):
                LEADS.add(b)

    con = sqlite3.connect(str(db))
    recs = {}
    for rid, path in con.execute(
        "select br.id,g.path from bgc_record br join gbk g on br.gbk_id=g.id "
        "where g.path like ? and br.record_type='region'", (f"%{strain}%",)):
        # COMP-P01/P02: the SQL LIKE is a substring PREFILTER — on its own it bleeds
        # (e.g. strain "AS-XXX" also matches "AS-XXX"'s records). Require `strain` to be a
        # full '_'-delimited token in the basename before accepting the record.
        if not _strain_token_match(Path(path).name, strain):
            continue
        _s, key, _m = I.parse_locator(path)   # canonical, cov-independent
        if key:
            recs[rid] = key
    if not recs:
        con.close()  # COMP-P04: close on the early-return path (was leaked)
        return {"status": "NO_RECORDS", "detail": f"no 'region' records for {strain} in run {run}"}

    cc = {}
    for ccid, rid in con.execute(
        "select id,record_id from connected_component where cutoff=? and run_id=?", (cutoff, run)):
        cc.setdefault(ccid, set()).add(rid)
    rset = set(recs)
    shared = [(c, m) for c, m in cc.items() if (m & rset) and len(m) > 1]

    def partner_is_mibig(rid):
        r = con.execute("select g.path from bgc_record br join gbk g on br.gbk_id=g.id "
                        "where br.id=?", (rid,)).fetchone()
        if not r:
            return False
        _s, _loc, is_mibig = I.parse_locator(r[0])      # canonical MIBiG detection (never bare "reference")
        return is_mibig

    # Only MIBiG-vs-cohort is robustly knowable from a BiG-SCAPE DB (host habitat is not in it), so
    # colour families by that + the fragmentation flag. L.MIBIG keeps the anchor colour collision-safe.
    MIBIG_C = L.STYLE[L.MIBIG]["color"]
    G = nx.Graph(); col = {}; size = {}; lab = {}; cats_present = set()
    G.add_node(strain); col[strain] = "#111111"; size[strain] = 1400; lab[strain] = strain
    in_shared = set(); families = []
    for i, (ccid, mem) in enumerate(sorted(shared, key=lambda x: -len(x[1]))):
        n_mibig = sum(1 for rid in mem if rid not in rset and partner_is_mibig(rid))
        n = len(mem)
        if n > 120:  # a large low-similarity component of many records is an assembly artifact, not one GCF
            fcat, fcol, fname = "fragmented", "#7B241C", "fragmented supercomponent\n(assembly artifact)"
        elif n_mibig:
            fcat, fcol, fname = "mibig-anchored", MIBIG_C, "MIBiG-anchored family"
            cats_present.add(fcat)
        else:
            fcat, fcol, fname = "cohort-shared", "#27AE60", "cohort-shared family"
            cats_present.add(fcat)
        fid = f"F{i}"; G.add_node(fid); col[fid] = fcol; size[fid] = 260 + min(n, 60) * 10; lab[fid] = fname
        families.append({"members_in_strain": sorted({recs[r] for r in mem if r in rset}),
                         "dominant_category": fcat, "size": n})
        for rid in mem:
            if rid not in rset:
                continue
            b = node2bgc.get(recs[rid], recs[rid]); in_shared.add(b)
            G.add_node(b); col[b] = "#F39C12" if b in LEADS else "#95A5A6"
            size[b] = 150 if b in LEADS else 60; lab[b] = b if b in LEADS else ""
            G.add_edge(b, fid)
        G.add_edge(strain, fid)

    allb = set(node2bgc.values()) if node2bgc else set(recs.values())
    dark = sorted(allb - in_shared)
    G.add_node("DARK"); col["DARK"] = "#34495E"; size["DARK"] = 1600
    lab["DARK"] = f"{len(dark)} GCF-dark singletons\n(no cohort/MIBiG family @{cutoff})"
    G.add_edge(strain, "DARK")
    for b in (LEADS & set(dark)):
        G.add_node(b); col[b] = "#F39C12"; size[b] = 200; lab[b] = b; G.add_edge(b, "DARK")

    pos = nx.spring_layout(G, k=0.9, seed=7, iterations=200)
    fig, ax = plt.subplots(figsize=(15, 11))
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=1.0, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=[col[n] for n in G.nodes()],
                           node_size=[size[n] for n in G.nodes()],
                           edgecolors="white", linewidths=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: lab.get(n, "") for n in G.nodes()}, font_size=7.2, ax=ax)
    ax.set_title(f"{strain} — strain-centric GCF subgraph of the cohort BiG-SCAPE run "
                 f"(run {run}, cutoff {cutoff})\n"
                 f"GCF-dark = novelty-leaning; shared families are similarity, not identity",
                 fontsize=13, fontweight="bold")
    extra = [Patch(color="#111111", label=f"{strain} (strain hub)"),
             Patch(color="#34495E", label="GCF-dark singletons (novel-leaning)"),
             Patch(color="#F39C12", label="named leads"),
             Patch(color=MIBIG_C, label=L.assert_not_bare_reference("MIBiG-anchored family")),
             Patch(color="#27AE60", label="cohort-shared family"),
             Patch(color="#7B241C", label="fragmented supercomponent (assembly artifact)"),
             Patch(color="#95A5A6", label="BGC (family member)")]
    ax.legend(handles=extra, loc="lower left", fontsize=8.2, framealpha=0.9)
    ax.axis("off"); plt.tight_layout()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    # v9.7.409: tidy `<stem>_data.csv` node table beside the network PNG (R/ggplot2-reproducible; never blocks the figure).
    def _node_kind(n):
        if n == strain:
            return "strain_hub"
        if n == "DARK":
            return "gcf_dark_hub"
        if isinstance(n, str) and n.startswith("F") and n[1:].isdigit():
            return "shared_family"
        return "bgc_member"
    try:
        import csv as _csv
        _csv_path = str(Path(out).with_suffix("")) + "_data.csv"
        with open(_csv_path, "w", newline="", encoding="utf-8") as _fh:
            _w = _SafeWriter(_fh)
            _w.writerow(["node", "kind", "is_named_lead", "node_size", "degree", "label"])
            for _n in G.nodes():
                _w.writerow([_n, _node_kind(_n), int(_n in LEADS), size.get(_n, ""), G.degree(_n), lab.get(_n, "")])
    except OSError as _swallowed_exc:  # pragma: no cover
        _warnings.warn(f"bigscape_figures.py: non-blocking step skipped ({type(_swallowed_exc).__name__}: {_swallowed_exc})", RuntimeWarning, stacklevel=2)  # v9.7.409: was a silent swallow
    plt.savefig(out, dpi=_safe_dpi(plt.gcf(), 170), bbox_inches="tight"); plt.close()
    con.close()  # COMP-P04: close the sqlite connection on the normal return path (was leaked)
    # v9.7.409: persist a scope receipt beside the raster so the figure's provenance is
    # confirmable on disk. The raster cannot be read back, and a per-strain filename (e.g.
    # gcf_network_RB68.png) on a figure built from a whole-cohort BiG-SCAPE DB is ambiguous:
    # this JSON records that the figure is a STRAIN-CENTRIC SUBGRAPH (this strain's region
    # records + the GCF families they join), NOT the full cohort network, and carries the
    # node/edge counts that distinguish the two (the full cohort network has far more edges).
    scope = {
        "figure": Path(out).name,
        "scope": ("strain-centric subgraph of the cohort BiG-SCAPE run: this strain's region "
                  "records plus the GCF families they join; non-strain family members are "
                  "summarized as family nodes, not drawn individually"),
        "strain": strain, "run": run, "cutoff": cutoff, "db": str(db),
        "strain_region_records": len(recs),
        "families_drawn": len(families),
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
        "dark_singletons": len(dark),
    }
    scope_json = str(Path(out).with_suffix("")) + "_scope.json"
    Path(scope_json).write_text(json.dumps(scope, indent=2, sort_keys=True), encoding="utf-8")
    return {"status": "WRITTEN", "out": str(out), "run": run, "cutoff": cutoff,
            "dark_singletons": len(dark), "shared_families": len(families),
            "leads_all_dark": bool(LEADS) and LEADS.issubset(set(dark)), "families": families,
            "scope_json": scope_json, "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges()}


def clinker_figure(gbks, out="clinker.html"):
    """Run clinker across >=2 region GBKs -> interactive HTML + alignments.txt.
    Pick the set with intent (a lead + its RG-GMCI partners, or a GCF family)."""
    if shutil.which("clinker") is None:
        return {"status": "SKIPPED_NO_CLINKER", "detail": "clinker CLI not on PATH (pip install clinker)"}
    if len(gbks) < 2:
        return {"status": "NEED_2_GBKS", "detail": "clinker needs >=2 region GBKs"}
    aln = str(out).replace(".html", "_alignments.txt")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    _timeout = _subprocess_timeout_sec()
    try:
        r = subprocess.run(["clinker", *[str(g) for g in gbks], "-p", str(out), "-o", aln],
                           capture_output=True, text=True, timeout=_timeout)
    except subprocess.TimeoutExpired:
        # v9.7.409 (DEEP_AUDIT2_resource_dos #5): clinker exceeded the wall-clock bound (all-vs-all
        # over too many/too-large GBKs). Return a typed status so the run continues without this one
        # supporting figure, instead of hanging.
        return {"status": "CLINKER_TIMEOUT",
                "detail": f"clinker exceeded MAMEY_SUBPROCESS_TIMEOUT_SEC={_timeout:.0f}s over "
                          f"{len(gbks)} GBKs; skipped this figure"}
    if r.returncode != 0 or not Path(out).exists():
        return {"status": "CLINKER_FAILED", "detail": (r.stderr or r.stdout)[-300:]}
    return {"status": "WRITTEN", "out": str(out), "alignments": aln,
            "note": "gene links are similarity, not identity"}
