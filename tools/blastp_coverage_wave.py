#!/usr/bin/env python3
"""blastp_coverage_wave.py — measure BLASTp coverage gaps, stage a priority wave into isolated
runner queues with a full receipt manifest + provenance quarantine, and (optionally) plot cumulative
throughput. Engine-NEUTRAL: reads the existing blastp.sqlite (READ-ONLY) and cohort package FASTAs,
and drives the existing nr_rid_runner.py. It computes NO scores, priors, ranks, or gate thresholds —
coverage is a MEASUREMENT state, never a novelty verdict ("no hit" != novel until judged).

Validated live 2026-08-19 (the roster lane): generalization of the one-off stage_wave1.py that ran
Wave 1 = the 1,491 core-NEITHER genes across 6 isolated ledgers.

THREE composable subcommands
  measure  — classify every gene by nr vs ClusteredNR: BOTH / nr-only / clustered-only / NEITHER,
             with a per-strain CSV and a role breakdown. SwissProt/EBI are reported but do NOT count
             toward the NEITHER priority (house rule). NEITHER = hit_ncbi=0 AND hit_clustered=0.
  stage    — given a priority gene CSV (strain,bgc_id,gene[,role]) and a package-FASTA path template,
             stage panels into ISOLATED nr + ClusteredNR queues with a receipt manifest (per-gene
             query SHA-256 + source FASTA path/SHA). Genes whose id does NOT join EXACTLY to the
             strain's package FASTA are QUARANTINED, never fuzzy-aliased. Larger clustered super-panels
             (multi-BGC via the runner's defline-based result filing) clear the thin channel fast.
  plot     — cumulative proteins-fetched from a set of ledgers (">" headers in fetched panels).

PORTABILITY: all paths derive from $SAPOTE_ROOT (default: this file's repo, 4 parents up). DB access is
strictly read-only (sqlite file:...?mode=ro). Nothing here writes to the DB.

USAGE (paths relative to $SAPOTE_ROOT)
  python tools/blastp_coverage_wave.py measure --out coverage/
  python tools/blastp_coverage_wave.py stage  --wave coverage/FIRST_WAVE.csv \
        --package-template '{cohort}/{strain}/package/{strain}_proteins.faa' \
        --queue-prefix _QUERIES_WAVE1 --out coverage/wave1/ [--nr-panel 8 --cl-panel 25]
  python tools/blastp_coverage_wave.py plot --ledgers _NR_RID_WAVE1_A,_NR_CLUSTER_RID_WAVE1_A --out plots/
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, hashlib, os, re, sqlite3, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from collections import defaultdict

def _find_root():
    r = os.environ.get("SAPOTE_ROOT")
    if r: return os.path.realpath(r)
    # walk up from this file until a dir carries the workspace markers (robust to nesting depth)
    d = os.path.dirname(os.path.realpath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, "BLASTp Database")) or os.path.isdir(os.path.join(d, "Blastp RESULTS")):
            return d
        parent = os.path.dirname(d)
        if parent == d: return os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        d = parent

ROOT = _find_root()
DB   = os.environ.get("SAPOTE_DB") or os.path.join(ROOT, "BLASTp Database", "blastp.sqlite")
BR   = os.path.join(ROOT, "Blastp RESULTS")
# v9.7.371 fix: this set was a hardcoded literal duplicating mamey/exclusions.py's SSOT (drifts
# silently if the registry ever changes, e.g. a new hard-excluded strain, or AS-XXX's raw-void
# status changes). This module reads the raw per-gene gene_coverage table, so the correct SSOT
# semantics are raw_analysis_excluded() | hard_excluded() = {AS-XXX, AS-XXX} | {AS-XXX, AS-XXX}
# = {AS-XXX, AS-XXX, AS-XXX} -- exactly the 3 real strains this literal already had. AS-XXX_CONSDARK
# is a synthetic pooled cross-strain "conserved dark protein" bucket (see deliverable_tools/
# conserved_dark_proteins.py and tests/test_widget_data.py's AS-XXX="unresolved" convention), not a
# real strain, so it is kept as an explicitly-named addition rather than pulled from the registry.
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey`
    from mamey.exclusions import raw_analysis_excluded, hard_excluded
    GOVERNED_EXCLUDE = raw_analysis_excluded() | hard_excluded() | {"AS-000_CONSDARK"}
except Exception:  # pragma: no cover - standalone fallback if mamey package unavailable
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    )
CORE_ROLES = {"core"}  # the sharp first-wave slice; callers may widen via --roles

def sha_text(s: str) -> str: return hashlib.sha256(s.encode()).hexdigest()
def sha_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def db_ro():
    if not os.path.exists(DB): sys.exit(f"DB not found: {DB}")
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

# ---------------------------------------------------------------- measure
def cmd_measure(a):
    con = db_ro(); cur = con.cursor()
    # gene_coverage is the canonical per-gene view (hit_ncbi/hit_clustered/hit_local/hit_ebi/hit_any)
    rows = list(cur.execute(
        "SELECT strain, bgc_id, gene, role, hit_ncbi, hit_clustered, hit_local, hit_ebi FROM gene_coverage"))
    con.close()
    os.makedirs(os.path.join(ROOT, a.out), exist_ok=True)
    per_strain = defaultdict(lambda: defaultdict(int))
    role_neither = defaultdict(int)
    both = nr_only = cl_only = neither = 0
    neither_rows = []
    for strain, bgc, gene, role, hn, hc, hl, he in rows:
        cls = ("both" if hn and hc else "nr_only" if hn else "cl_only" if hc else "neither")
        if cls == "both": both += 1
        elif cls == "nr_only": nr_only += 1
        elif cls == "cl_only": cl_only += 1
        else: neither += 1
        per_strain[strain][cls] += 1
        per_strain[strain]["total"] += 1
        if cls == "neither" and strain not in GOVERNED_EXCLUDE:
            role_neither[role or "none"] += 1
            neither_rows.append((strain, bgc, gene, role or "none",
                                 int(bool(hl)), int(bool(he))))
    with open(os.path.join(ROOT, a.out, "coverage_by_strain.csv"), "w", newline="") as f:
        w = _SafeWriter(f); w.writerow(["strain", "total", "both", "nr_only", "cl_only", "neither"])
        for s in sorted(per_strain):
            d = per_strain[s]; w.writerow([s, d["total"], d["both"], d["nr_only"], d["cl_only"], d["neither"]])
    with open(os.path.join(ROOT, a.out, "NEITHER_genes.csv"), "w", newline="") as f:
        w = _SafeWriter(f); w.writerow(["strain", "bgc_id", "gene", "role", "has_swissprot", "has_ebi"])
        w.writerows(sorted(neither_rows))
    with open(os.path.join(ROOT, a.out, "FIRST_WAVE_core_NEITHER.csv"), "w", newline="") as f:
        w = _SafeWriter(f); w.writerow(["strain", "bgc_id", "gene", "role"])
        w.writerows(sorted((s, b, g, r) for s, b, g, r, _, _ in neither_rows if r in CORE_ROLES))
    emit(f'genes: {len(rows)} | BOTH {both} nr-only {nr_only} cl-only {cl_only} NEITHER {neither}', f'NEITHER excl governed: {len(neither_rows)} | by role: ' + ' '.join((f'{k}={v}' for k, v in sorted(role_neither.items(), key=lambda x: -x[1]))), f'wrote {a.out}/coverage_by_strain.csv, NEITHER_genes.csv, FIRST_WAVE_core_NEITHER.csv', sep="\n")

# ---------------------------------------------------------------- stage
def _load_fasta(path):
    seqs = {}
    if not os.path.exists(path): return seqs, None
    raw = open(path, "rb").read(); fsha = sha_bytes(raw); g = None; buf = []
    for line in raw.decode(errors="replace").splitlines():
        if line.startswith(">"):
            if g: seqs[g] = "".join(buf)
            g = line[1:].split()[0]; buf = []
        else: buf.append(line.strip())
    if g: seqs[g] = "".join(buf)
    return seqs, fsha

def _node_of(gene):
    m = re.match(r"ctg(\d+)_", gene); return f"NODE_{m.group(1)}" if m else ""

def cmd_stage(a):
    wave = list(csv.DictReader(open(os.path.join(ROOT, a.wave))))
    by_strain = defaultdict(list)
    for r in wave: by_strain[r["strain"]].append(r)
    nrq = os.path.join(BR, f"{a.queue_prefix}_NR"); clq = os.path.join(BR, f"{a.queue_prefix}_CL")
    outd = os.path.join(ROOT, a.out); os.makedirs(outd, exist_ok=True)
    manifest, quarantine, staged = [], [], 0
    for s in sorted(by_strain):
        fpath = os.path.join(ROOT, a.package_template.format(strain=s, cohort=a.cohort))
        seqs, fsha = _load_fasta(fpath)
        matched = []
        for r in by_strain[s]:
            g = r["gene"]
            if g in seqs:
                seq = seqs[g]
                matched.append(dict(strain=s, bgc=r["bgc_id"], gene=g, role=r.get("role", "core"),
                                    aa=len(seq), node=_node_of(g), qsha=sha_text(seq),
                                    src=os.path.relpath(fpath, ROOT), src_sha=fsha, seq=seq))
            else:
                quarantine.append(dict(strain=s, bgc=r["bgc_id"], gene=g, role=r.get("role", "core"),
                                       reason="gene_id_not_in_package_fasta__resolve_source"))
        if not matched: continue
        # nr lane: per-BGC panels
        bybgc = defaultdict(list)
        for rec in matched: bybgc[rec["bgc"]].append(rec)
        for bgc, recs in sorted(bybgc.items()):
            for i in range(0, len(recs), a.nr_panel):
                chunk = recs[i:i + a.nr_panel]; pnl = f"{bgc}_wave_nr_p{i//a.nr_panel+1:02d}.faa"
                d = os.path.join(nrq, s, bgc); os.makedirs(d, exist_ok=True)
                _write_panel(os.path.join(d, pnl), s, chunk)
                for rec in chunk: manifest.append(_manrow(rec, "ncbi_nr", f"{s}/{bgc}/{pnl}", len(chunk)))
        # clustered lane: strain super-panels (multi-BGC)
        d = os.path.join(clq, s, "_wave"); os.makedirs(d, exist_ok=True)
        for i in range(0, len(matched), a.cl_panel):
            chunk = matched[i:i + a.cl_panel]; pnl = f"{s}_wave_cl_p{i//a.cl_panel+1:02d}.faa"
            _write_panel(os.path.join(d, pnl), s, chunk)
            for rec in chunk: manifest.append(_manrow(rec, "ncbi_clustered_nr", f"{s}/_wave/{pnl}", len(chunk)))
        staged += len(matched)
    cols = ["strain", "bgc", "gene", "role", "aa", "node", "qsha", "src", "src_sha", "channel", "panel", "panel_n"]
    with open(os.path.join(outd, "WAVE_QUEUE_MANIFEST.tsv"), "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=cols, delimiter="\t"); w.writeheader(); w.writerows(manifest)
    with open(os.path.join(outd, "WAVE_QUARANTINE.tsv"), "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=["strain", "bgc", "gene", "role", "reason"], delimiter="\t")
        w.writeheader(); w.writerows(quarantine)
    emit(f"staged (matched): {staged} | quarantined: {len(quarantine)} | manifest rows: {len(manifest)}", f"queues: {nrq}  |  {clq}", f"manifest+quarantine: {outd}/", sep="\n")

def _write_panel(path, strain, chunk):
    with open(path, "w") as f:
        for j, rec in enumerate(chunk, 1):
            f.write(f">{strain}|{rec['bgc']}|slot={j}|role={rec['role']}|gene={rec['gene']}"
                    f"|node={rec['node']}|aa={rec['aa']}|reason=coverage_wave\n{rec['seq']}\n")

def _manrow(rec, channel, panel, n):
    return {k: rec[k] for k in ("strain", "bgc", "gene", "role", "aa", "node", "qsha", "src", "src_sha")
            } | {"channel": channel, "panel": panel, "panel_n": n}

# ---------------------------------------------------------------- plot (optional; needs matplotlib)
def cmd_plot(a):
    import datetime as dt
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ledgers = [l.strip() for l in a.ledgers.split(",") if l.strip()]
    outd = os.path.join(ROOT, a.out); os.makedirs(outd, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    for base in ledgers:
        led = os.path.join(BR, base, "_ledger.csv")
        if not os.path.exists(led): continue
        qroot = os.path.join(BR, base.replace("_NR_CLUSTER_RID", "_QUERIES").replace("_NR_RID", "_QUERIES"))
        pts = []
        for r in csv.DictReader(open(led)):
            fi = (r.get("fetch_iso") or "").strip()
            if not fi: continue
            try: t = dt.datetime.strptime(fi, "%Y-%m-%d %H:%M:%S")
            except ValueError: continue
            fp = os.path.join(qroot, r.get("file", ""))
            n = sum(1 for ln in open(fp, errors="replace") if ln.startswith(">")) if os.path.exists(fp) else 0
            pts.append((t, n))
        pts.sort(); tot = 0; xs = []; ys = []
        for t, n in pts: tot += n; xs.append(t); ys.append(tot)
        ax.step(xs, ys, where="post", lw=2, label=f"{base} — {tot}")
    ax.set_ylabel("cumulative proteins fetched"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    p = os.path.join(outd, "coverage_wave_cumulative.png"); fig.savefig(p, dpi=130)
    emit(f"wrote {p}")

def main(argv=None):
    ap = argparse.ArgumentParser(description="BLASTp coverage-gap → wave staging → plot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure"); m.add_argument("--out", default="coverage"); m.set_defaults(fn=cmd_measure)
    s = sub.add_parser("stage")
    s.add_argument("--wave", required=True); s.add_argument("--out", default="coverage/wave")
    s.add_argument("--package-template", required=True,
                   help="relative path template with {strain} (and optional {cohort})")
    s.add_argument("--cohort", default=""); s.add_argument("--queue-prefix", default="_QUERIES_WAVE")
    s.add_argument("--nr-panel", type=int, default=8); s.add_argument("--cl-panel", type=int, default=25)
    s.set_defaults(fn=cmd_stage)
    p = sub.add_parser("plot"); p.add_argument("--ledgers", required=True); p.add_argument("--out", default="plots")
    p.set_defaults(fn=cmd_plot)
    a = ap.parse_args(argv); a.fn(a)

if __name__ == "__main__":
    main()
