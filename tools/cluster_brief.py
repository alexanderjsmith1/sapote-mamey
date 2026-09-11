#!/usr/bin/env python3
r"""cluster_brief.py — one-command driver for the comparative chain → a consolidated brief.

The v9.7.303–305 comparative chain is five tools run by hand, each consuming the prior's GBK:

    scope_cluster → (fetch_reference_cluster | extract_cluster) → cluster_gene_compare
                  → cluster_relate → cluster_completeness

Orchestrating them for one lead — scoping an over-merge, gathering references, comparing,
relating, scoring completeness, then reading four output sets to answer "is this query a
diverged homolog, a fragment, or something new?" — is manual every time. This runs the chain
for one query BGC and consolidates the real outputs into a single authoring-ready brief that
feeds Mode B §4 (independent homology) and §7 (completeness / truncation).

HONEST SCOPE: an ORCHESTRATOR. It invents nothing — it calls the real tools as subprocesses and
parses their real output files/lines. Every headline number is attributed to the tool that
produced it. If a step fails (e.g. biopython missing, a tool errors), the brief records the
failure and continues; it never fabricates a result to fill a gap.

CLAIM DISCIPLINE: capacity/architecture-level; shared-gene similarity is NOT identity;
completeness is gene-presence fraction vs a reference set, NOT "% of the product". A KCB/MIBiG
reference is a comparison anchor, not a product assignment.

Reference ingress (any combination):
    --reference LABEL:path.gbk     already-have reference GBK (repeatable)
    --ncbi ACCESSION:label         NCBI nucleotide efetch via fetch_reference_cluster (repeatable)
    --db DB --acc ACCESSION:label  anchored BiG-SCAPE DB via fetch_reference_cluster (repeatable)

    cluster_brief.py --query r001:region001.gbk \
        --ncbi MF055656.1:nikkomycin --reference sib:region007.gbk \
        [--category nucleoside] --query-boundary interior --outdir brief/

stdlib + the bundle's own tools. No new science; deterministic given inputs.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, re, csv, json, argparse, subprocess, glob
from pathlib import Path


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


_HERE = os.path.dirname(os.path.abspath(__file__))
_PY = sys.executable


def _tool(name):
    return os.path.join(_HERE, name)


def _run(argv, outdir):
    """Run a bundle tool; return (ok, stdout, stderr). Never raises."""
    try:
        p = subprocess.run([_PY] + argv, capture_output=True, text=True, timeout=900)
        return p.returncode == 0, p.stdout, p.stderr
    except Exception as e:  # pragma: no cover - defensive
        return False, "", f"{type(e).__name__}: {e}"


def _split_labelpath(s):
    """'LABEL:/a/b.gbk' -> ('LABEL', '/a/b.gbk'); tolerant of ':' in the path."""
    if ":" not in s:
        return None, s
    lab, path = s.split(":", 1)
    return lab, path


def _fetched_label(spec):
    """--ncbi/--acc spec is 'ACCESSION:label'; the fetched GBK is <label>.gbk (label AFTER colon)."""
    return spec.split(":", 1)[1] if ":" in spec else spec


# ── step parsers (read real outputs; attribute to the tool) ──────────────────
def _parse_compare(stdout):
    m = re.search(r"(\d+) clusters?, (\d+) confident gene pairs?, (\d+) ortholog groups? \((\d+) core", stdout)
    if not m:
        return None
    return dict(n_clusters=int(m[1]), n_pairs=int(m[2]), n_groups=int(m[3]), n_core=int(m[4]))


def _parse_relate_closest(stdout):
    m = re.search(r"Closest pair: (\S+) and (\S+) \((\d+) shared genes? at ([\d.]+)% mean identity; "
                  r"similarity ([\d.]+)\)", stdout)
    if not m:
        return None
    return dict(a=m[1], b=m[2], shared=int(m[3]), mean_id=float(m[4]), similarity=float(m[5]))


def _closest_ref_from_matrix(matrix_csv, query_label):
    """Nearest reference to the query from distance_matrix.csv (min non-self distance)."""
    if not os.path.exists(matrix_csv):
        return None
    rows = list(csv.reader(open(matrix_csv)))
    if not rows:
        return None
    header = rows[0][1:]
    qrow = None
    for r in rows[1:]:
        if r and r[0] == query_label:
            qrow = r[1:]
            break
    if qrow is None:
        return None
    best, best_d = None, None
    for lab, val in zip(header, qrow):
        if lab == query_label:
            continue
        try:
            d = float(val)
        except ValueError:
            continue
        if best_d is None or d < best_d:
            best, best_d = lab, d
    if best is None:
        return None
    return dict(label=best, distance=round(best_d, 4), similarity=round(1 - best_d, 4))


def _parse_completeness(outdir, query_label, stdout):
    j = glob.glob(f"{outdir}/{query_label}_completeness.json") or glob.glob(f"{outdir}/*_completeness.json")
    data = None
    if j:
        try:
            data = _read_json(j[0])
        except Exception:
            data = None
    # the tool's own truncation-vs-biology interpretation lives in stdout; quote it, don't re-derive
    interior_note = ""
    for line in stdout.splitlines():
        if "INTERIOR" in line or "truncation cannot explain" in line or "biological" in line:
            interior_note = line.split("]", 1)[-1].strip()
            break
    return data, interior_note


# ── driver ───────────────────────────────────────────────────────────────────
def run_brief(query, references, ncbi=None, db=None, accs=None, mibig=None, category=None,
              query_boundary="interior", min_id=None, outdir="brief"):
    """Run the comparative chain for one query. Returns a structured result dict."""
    os.makedirs(outdir, exist_ok=True)
    qlabel, qpath = _split_labelpath(query)
    steps = []            # (name, ok, note)
    refs = list(references or [])  # list of 'LABEL:path'
    fdir = os.path.join(outdir, "refs")

    # 0a. fetch MIBiG references from the public repo (no anchored DB needed)
    fetched = []
    if mibig:
        argv = [_tool("fetch_mibig_reference.py"), "--outdir", fdir]
        for spec in mibig:
            argv += ["--acc", spec]
        ok, out, err = _run(argv, outdir)
        steps.append(("fetch_mibig_reference", ok,
                      (err or out).strip().splitlines()[-1] if (err or out).strip() else ""))
        if ok:
            for spec in mibig:
                lab = _fetched_label(spec)
                hit = glob.glob(f"{fdir}/{lab}.gbk")
                if hit:
                    refs.append(f"{lab}:{hit[0]}")
                    fetched.append(lab)

    # 0b. fetch NCBI / DB references into the reference set
    fetch_specs = [("--ncbi", s) for s in (ncbi or [])] + [("--acc", s) for s in (accs or [])]
    if fetch_specs:
        argv = [_tool("fetch_reference_cluster.py"), "--outdir", fdir]
        if db:
            argv += ["--db", db]
        for flag, spec in fetch_specs:
            argv += [flag, spec]
        ok, out, err = _run(argv, outdir)
        steps.append(("fetch_reference_cluster", ok, (out or err).strip().splitlines()[-1] if (out or err).strip() else ""))
        if ok:
            for flag, spec in fetch_specs:
                # --ncbi/--acc format is ACCESSION:label; the output GBK is <label>.gbk
                lab = _fetched_label(spec)
                hit = glob.glob(f"{fdir}/{lab}.gbk")
                if hit:
                    refs.append(f"{lab}:{hit[0]}")
                    fetched.append(lab)

    # 1. scope an over-merged query to the target category
    if category:
        sdir = os.path.join(outdir, "scoped")
        ok, out, err = _run([_tool("scope_cluster.py"), "--gbk", qpath, "--category", category,
                             "--label", qlabel, "--outdir", sdir], outdir)
        scoped = glob.glob(f"{sdir}/*scoped.gbk")
        note = (out or err).strip().splitlines()[-1] if (out or err).strip() else ""
        steps.append(("scope_cluster", ok and bool(scoped), note))
        if ok and scoped:
            qpath = scoped[0]

    if not refs:
        return dict(query=qlabel, outdir=outdir, steps=steps,
                    error="no references (supply --reference / --ncbi / --acc)")

    gbk_args = []
    for spec in [f"{qlabel}:{qpath}"] + refs:
        gbk_args += ["--gbk", spec]
    minid = ["--min-id", str(min_id)] if min_id else []

    # 2. gene-by-gene comparison
    ok, out, err = _run([_tool("cluster_gene_compare.py")] + gbk_args
                        + ["--outdir", os.path.join(outdir, "compare")] + minid, outdir)
    compare = _parse_compare(out) if ok else None
    steps.append(("cluster_gene_compare", ok, out.strip().splitlines()[-1] if ok and out.strip() else (err.strip()[:120])))

    # 3. relationship tree / distances
    rdir = os.path.join(outdir, "relate")
    ok, out, err = _run([_tool("cluster_relate.py")] + gbk_args + ["--outdir", rdir] + minid, outdir)
    closest_line = _parse_relate_closest(out) if ok else None
    # AUDIT_374: was unconditional -- if THIS run's cluster_relate.py step failed (ok=False),
    # a stale distance_matrix.csv left in `rdir` from a PRIOR run was still read and rendered as a
    # confident "Nearest reference" line under "## Relationship", while the actual failure only
    # showed up buried in the "## Steps" list at the bottom. Directly contradicts this module's own
    # documented contract ("it never fabricates a result to fill a gap") -- gate on `ok` like every
    # other step's file/stdout read in this function already is.
    closest_ref = _closest_ref_from_matrix(os.path.join(rdir, "distance_matrix.csv"), qlabel) if ok else None
    steps.append(("cluster_relate", ok, out.strip().splitlines()[-1] if ok and out.strip() else (err.strip()[:120])))

    # 4. completeness vs the reference set
    cdir = os.path.join(outdir, "completeness")
    comp_args = [_tool("cluster_completeness.py"), "--query", f"{qlabel}:{qpath}",
                 "--query-boundary", query_boundary, "--outdir", cdir] + minid
    for spec in refs:
        comp_args += ["--reference", spec]
    ok, out, err = _run(comp_args, outdir)
    comp_data, interior_note = _parse_completeness(cdir, qlabel, out) if ok else (None, "")
    steps.append(("cluster_completeness", ok, out.strip().splitlines()[0] if ok and out.strip() else (err.strip()[:120])))

    return dict(query=qlabel, outdir=outdir, n_refs=len(refs), fetched=fetched,
                category=category, query_boundary=query_boundary,
                compare=compare, closest_pair=closest_line, closest_ref=closest_ref,
                completeness=comp_data, interior_note=interior_note, steps=steps)


# ── render ───────────────────────────────────────────────────────────────────
def render_md(res):
    q = res["query"]
    L = [f"# Comparative brief — {q}", ""]
    if res.get("error"):
        L.append(f"> **cannot run:** {res['error']}")
        L += ["", "## Steps", ""]
        for name, ok, note in res.get("steps", []):
            L.append(f"- {'✅' if ok else '🛑'} `{name}` {('— ' + note) if note else ''}")
        return "\n".join(L)

    L.append(f"*Query `{q}` vs {res['n_refs']} reference(s). Orchestrated real comparative-chain "
             "tools; numbers attributed below. Capacity/architecture-level — shared-gene similarity "
             "is not identity; completeness is gene-presence vs the reference set, not % of product.*")
    L.append("")

    comp = res.get("completeness")
    if comp:
        L.append("## Completeness (cluster_completeness)")
        ncg = comp.get("n_cluster_genes", 0) or 0
        if ncg == 0:
            L.append("- **undefined** — the references share no recurrent gene set (they are not "
                     "mutually homologous). Supply references homologous to each other and the query.")
        else:
            L.append(f"- **{comp.get('completeness_pct','?')}%** — {comp.get('n_present','?')}/"
                     f"{ncg} recurrent reference genes present, {comp.get('n_missing','?')} missing.")
            if res.get("interior_note"):
                L.append(f"- Truncation vs absence: {res['interior_note']}")
        L.append("")

    cr = res.get("closest_ref")
    cp = res.get("closest_pair")
    if cr or cp:
        L.append("## Relationship (cluster_relate)")
        if cr:
            L.append(f"- Nearest reference to `{q}`: **{cr['label']}** (distance {cr['distance']}, "
                     f"similarity {cr['similarity']}).")
        if cp:
            L.append(f"- Closest pair overall: {cp['a']}–{cp['b']} — {cp['shared']} shared genes at "
                     f"{cp['mean_id']}% mean identity (similarity {cp['similarity']}).")
        L.append("")

    cmp = res.get("compare")
    if cmp:
        L.append("## Shared architecture (cluster_gene_compare)")
        L.append(f"- {cmp['n_pairs']} confident ortholog pairs across {cmp['n_clusters']} clusters; "
                 f"{cmp['n_groups']} ortholog groups, {cmp['n_core']} core to all.")
        L.append("")

    # honest one-line read, gated on a DEFINED completeness (recurrent reference set exists)
    if comp and (comp.get("n_cluster_genes", 0) or 0) > 0 and isinstance(comp.get("completeness_pct"), (int, float)):
        pct = comp["completeness_pct"]
        if pct >= 80:
            read = "near-complete relative to the reference set (capacity plausibly intact)."
        elif pct >= 40:
            read = "partial relative to the reference set — reconcile interior-missing genes before any completeness claim."
        else:
            read = ("low overlap with the reference set — likely a diverged homolog or a different "
                    "cluster, not a truncated copy; do not treat the reference as the product.")
        L.append(f"**Read:** `{q}` is {read}")
        L.append("")

    L.append("## Steps")
    for name, ok, note in res.get("steps", []):
        L.append(f"- {'✅' if ok else '🛑'} `{name}`{(' — ' + note) if note else ''}")
    L.append("")
    L.append(f"*Sub-artifacts under `{res['outdir']}/` (compare/, relate/, completeness/, refs/, scoped/).*")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Run the comparative chain for one query BGC → consolidated brief.")
    ap.add_argument("--query", required=True, metavar="LABEL:query.gbk")
    ap.add_argument("--reference", action="append", default=[], metavar="LABEL:ref.gbk",
                    help="already-have reference GBK (repeatable)")
    ap.add_argument("--ncbi", action="append", default=[], metavar="ACC:label",
                    help="NCBI nucleotide accession, fetched via fetch_reference_cluster (repeatable)")
    ap.add_argument("--mibig", action="append", default=[], metavar="BGCxxxxxxx:label",
                    help="MIBiG accession, fetched from the public repo via fetch_mibig_reference "
                         "(no anchored DB; repeatable). KCB_top rank suffixes tolerated.")
    ap.add_argument("--db", default=None, help="anchored BiG-SCAPE DB (with --acc)")
    ap.add_argument("--acc", action="append", default=[], metavar="ACC:label",
                    help="cluster in the DB, fetched via fetch_reference_cluster (repeatable)")
    ap.add_argument("--category", default=None, help="scope an over-merged query to this category first")
    ap.add_argument("--query-boundary", default="interior", choices=["interior", "edge", "full-contig"])
    ap.add_argument("--min-id", default=None, help="confident-ortholog identity %% passed to the tools")
    ap.add_argument("--outdir", default="brief")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="write brief to path instead of stdout")
    a = ap.parse_args()

    res = run_brief(a.query, a.reference, ncbi=a.ncbi, db=a.db, accs=a.acc, mibig=a.mibig,
                    category=a.category, query_boundary=a.query_boundary,
                    min_id=a.min_id, outdir=a.outdir)
    out = json.dumps(res, indent=2) if a.json else render_md(res)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        emit(f"wrote {a.out}")
    else:
        emit(out)
    # non-zero if the query never got compared (no usable references / all steps failed)
    compared = any(ok for (name, ok, note) in res.get("steps", []) if name == "cluster_gene_compare")
    if res.get("error") or not compared:
        sys.exit(1)


if __name__ == "__main__":
    main()
