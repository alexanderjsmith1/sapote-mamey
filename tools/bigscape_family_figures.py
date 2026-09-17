#!/usr/bin/env python3
"""bigscape_family_figures — batch gene-cluster-family figures from a BiG-SCAPE 2 database.

Drives `tools/render_gcf_synteny_tree.py` (the v9.7.433 tool with reference-layer rows and the pruned view) over
two selections and files the outputs so a reader finds them by strain:

  --private-tsv <verdicts.tsv>   every family whose verdict starts with QUERY_PRIVATE (from bigscape_family_verdicts.py)
                                 -> <out>/private_families/_all/GCF<id>_c<cutoff>_<product>.{pdf,png,_rows.tsv,_gene_roles.tsv,_caption.txt}
                                    with the PDF and PNG hard-linked into <out>/private_families/<strain>/ for every member strain
  --focus <strain> (repeatable)  every family at --cutoff holding one of that strain's regions
                                 -> <out>/strain_focus/<strain>/family_trees_c<cutoff>/…; with --fallback-cutoff, a region unplaced
                                    at --cutoff but placed at the fallback cutoff gets that family under family_trees_c<fallback>/
                                 plus BGC_TO_FAMILY_FIGURE.tsv (one row per region: alias, family ids, figure or "singleton at every cutoff")

Families above --max-tips are drawn as the tool's pruned view anchored on the focal strain. Class-level architecture
only; shared genes are homology, not compound identity. Judgment deferred.
"""
from __future__ import annotations
import argparse, collections, csv, glob, os, re, shutil, sqlite3, subprocess, sys, time
from pathlib import Path

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run outside an editable install
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from _console import emit
except ImportError:
    emit = print
TOOL = os.path.join(HERE, "render_gcf_synteny_tree.py")


def family_table(db, cutoff):
    con = sqlite3.connect(db)
    fam = collections.defaultdict(list)
    for fid, rid, path, prod in con.execute(
            "select f.id, r.id, g.path, r.product from family f join bgc_record_family bf on bf.family_id=f.id "
            "join bgc_record r on r.id=bf.record_id join gbk g on g.id=r.gbk_id where abs(f.cutoff-?)<1e-6 and r.record_type='region'", (cutoff,)):
        fam[fid].append((rid, os.path.basename(path), prod or ""))
    con.close()
    return fam


def strain_records(db, strain):
    con = sqlite3.connect(db)
    rows = [(rid, os.path.basename(p), prod or "") for rid, p, prod in con.execute(
        "select r.id, g.path, r.product from bgc_record r join gbk g on g.id=r.gbk_id where r.record_type='region'")
            if os.path.basename(p).startswith(strain + "_")]
    con.close()
    return rows


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:40] or "na"


def product_summary(members):
    return ";".join(p for p, _n in collections.Counter(p for _r, _b, p in members).most_common(2))


def link_or_copy(src, dst):
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def write_tsv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def render(a, fid, cutoff, stem, title, focal):
    cmd = [sys.executable, TOOL, "--db", a.db, "--family", str(fid), "--title", title, "--out", str(stem), "--max-tips", str(a.max_tips)]
    for d in a.gbk_dir: cmd += ["--gbk-dir", d]
    for p in a.identity: cmd += ["--identity", p]
    for f in focal: cmd += ["--focal", f]
    for p in a.layer_prefix or []: cmd += ["--reference-prefix", p]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else f"exit {r.returncode}")
    rows = list(csv.DictReader(open(str(stem) + "_rows.tsv", encoding="utf-8"), delimiter="\t"))
    m = re.search(r"(\d+) links, (\d+) identity holds", r.stdout)
    return {"drawn": len(rows), "links": int(m.group(1)) if m else -1, "holds": int(m.group(2)) if m else -1}


def query_strains(members, query_rx):
    out = set()
    for _r, b, _p in members:
        m = query_rx.match(b)
        if m:
            out.add(m.group(1))
    return sorted(out)


def job_private(a, log):
    fam = family_table(a.db, a.cutoff)
    root = Path(a.out) / "private_families"; allp = root / "_all"; allp.mkdir(parents=True, exist_ok=True)
    fids = [int(r["family_id"]) for r in csv.DictReader(open(a.private_tsv, encoding="utf-8"), delimiter="\t") if r.get("verdict", "QUERY_PRIVATE").startswith("QUERY_PRIVATE")]
    index = []
    for fid in fids:
        members = fam.get(fid, []); strains = query_strains(members, a.query_rx); prod = product_summary(members)
        stem = allp / f"GCF{fid}_c{a.cutoff:g}_{slug(prod)}"
        t0 = time.time()
        try:
            res = render(a, fid, a.cutoff, stem, f"GCF {fid} (cutoff {a.cutoff:g})  {prod}  private: {', '.join(strains)}", strains)
        except RuntimeError as e:
            log(f"private GCF{fid}: FAILED {e}"); index.append({"family_id": fid, "status": f"FAILED {e}"}); continue
        for s in strains:
            d = root / s; d.mkdir(exist_ok=True)
            for ext in (".pdf", ".png"):
                link_or_copy(str(stem) + ext, str(d / (stem.name + ext)))
        index.append({"family_id": fid, "members": len(members), "query_strains": ";".join(strains), "products": prod, "links": res["links"],
                      "identity_holds": res["holds"], "figure": os.path.relpath(str(stem) + ".pdf", a.out), "status": "OK"})
        log(f"private GCF{fid}: {res['drawn']} rows, {res['links']} links, {res['holds']} holds, {time.time()-t0:.0f}s")
    write_tsv(root / "INDEX.tsv", index, ["family_id", "members", "query_strains", "products", "links", "identity_holds", "figure", "status"])


def job_focus(a, log):
    fam_main = family_table(a.db, a.cutoff)
    fam_fb = family_table(a.db, a.fallback_cutoff) if a.fallback_cutoff else {}
    r2f_main = {rid: fid for fid, ms in fam_main.items() for rid, _b, _p in ms}
    r2f_fb = {rid: fid for fid, ms in fam_fb.items() for rid, _b, _p in ms}
    for strain in a.focus:
        sroot = Path(a.out) / "strain_focus" / strain; sroot.mkdir(parents=True, exist_ok=True)
        recs = strain_records(a.db, strain); per_bgc = []; todo = {}
        for rid, base, prod in recs:
            row = {"record_id": rid, "file": base, "product": prod, "family_main": r2f_main.get(rid, ""), "family_fallback": r2f_fb.get(rid, ""), "figure": ""}
            key = (a.cutoff, r2f_main[rid]) if rid in r2f_main else ((a.fallback_cutoff, r2f_fb[rid]) if rid in r2f_fb else None)
            if key is None:
                row["figure"] = "singleton at every cutoff: no family tree exists"
            else:
                todo.setdefault(key, set()).add(rid); row["_key"] = key
            per_bgc.append(row)
        findex = []
        for (cut, fid) in sorted(todo, key=lambda k: (k[0], k[1])):
            members = fam_main[fid] if cut == a.cutoff else fam_fb[fid]
            prod = product_summary(members)
            d = sroot / f"family_trees_c{cut:g}"; d.mkdir(parents=True, exist_ok=True)
            stem = d / f"GCF{fid}_c{cut:g}_{slug(prod)}"
            t0 = time.time()
            try:
                res = render(a, fid, cut, stem, f"{strain}  GCF {fid} (cutoff {cut:g})  {prod}  {len(members)} members", [strain])
            except RuntimeError as e:
                log(f"{strain} GCF{fid} c{cut:g}: FAILED {e}"); findex.append({"family_id": fid, "cutoff": cut, "status": f"FAILED {e}"}); continue
            rel = os.path.relpath(str(stem) + ".pdf", a.out)
            for row in per_bgc:
                if row.get("_key") == (cut, fid):
                    row["figure"] = rel
            findex.append({"family_id": fid, "cutoff": cut, "members": len(members), "drawn": res["drawn"], "strain_records": len(todo[(cut, fid)]),
                           "products": prod, "links": res["links"], "identity_holds": res["holds"], "figure": rel, "status": "OK"})
            log(f"{strain} GCF{fid} c{cut:g}: {res['drawn']}/{len(members)} rows, {res['links']} links, {res['holds']} holds, {time.time()-t0:.0f}s")
        for row in per_bgc:
            row.pop("_key", None)
        write_tsv(sroot / "BGC_TO_FAMILY_FIGURE.tsv", per_bgc, ["record_id", "file", "product", "family_main", "family_fallback", "figure"])
        write_tsv(sroot / "FAMILY_FIGURES_INDEX.tsv", findex, ["family_id", "cutoff", "members", "drawn", "strain_records", "products", "links", "identity_holds", "figure", "status"])
        log(f"{strain}: {len(recs)} regions, {sum(1 for r in per_bgc if r['figure'] and not r['figure'].startswith('singleton'))} with a family figure, {len(findex)} families")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", required=True); ap.add_argument("--gbk-dir", action="append", required=True)
    ap.add_argument("--identity-glob", action="append", default=[], help="glob(s) for Mamey *_2_inventory.csv files")
    ap.add_argument("--out", required=True); ap.add_argument("--cutoff", type=float, default=0.3); ap.add_argument("--fallback-cutoff", type=float, default=None)
    ap.add_argument("--max-tips", type=int, default=40); ap.add_argument("--query-regex", default=r"^([A-Za-z]+-\d+)_")
    ap.add_argument("--layer-prefix", action="append", default=None)
    ap.add_argument("--private-tsv"); ap.add_argument("--focus", action="append", default=[]); ap.add_argument("--log")
    a = ap.parse_args(argv)
    a.identity = sorted(p for g in a.identity_glob for p in glob.glob(g)); a.query_rx = re.compile(a.query_regex)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    logf = open(a.log, "a", encoding="utf-8") if a.log else None

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"; emit(line, flush=True)
        if logf: logf.write(line + "\n"); logf.flush()
    log(f"db={a.db} identity files={len(a.identity)} tool={TOOL}")
    if a.private_tsv: job_private(a, log)
    if a.focus: job_focus(a, log)
    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
