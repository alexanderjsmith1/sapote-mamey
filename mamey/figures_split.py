"""figures_split.py — standalone (loaded by-path in tests, so not a shim)."""
import os, re, csv, glob, subprocess, sys



# permanent-downgrade / ubiquitous classes never auto-figured as leads (mirrors standing rules)
UBIQUITOUS = {"saccharide","napaa","ectoine","siderophore","melanin","terpene",
              "betalactone","butyrolactone","lanthipeptide","lassopeptide","hgle"}

def _tools_dir():
    # tools/ sits at the bundle root, one level up from mamey/
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(os.path.dirname(here), "tools")
    return cand if os.path.isdir(cand) else None

def _find_raw_run(pkg):
    """Locate a raw antiSMASH run co-located WITHIN the package (raw/ or antismash/ subdir,
       or the package itself). Must have knownclusterblast/ AND region GBKs. Deliberately does
       NOT search parent directories — that risks attaching a different strain's run to this
       package, which would produce wrong-strain figures."""
    for base in (pkg, os.path.join(pkg, "raw"), os.path.join(pkg, "antismash")):
        if not base or not os.path.isdir(base): continue
        for kdir in glob.glob(os.path.join(base, "**", "knownclusterblast"), recursive=True):
            run = os.path.dirname(kdir)
            if glob.glob(os.path.join(run, "*.region*.gbk")):
                return run
    return None

def _region_files(raw, contig):
    """Given a raw run dir + a contig stem (NODE_x_length_..), return (gbk, kcb_txt, cb_txt) or Nones."""
    gbk = glob.glob(os.path.join(raw, f"{contig}*.region*.gbk"))
    kcb = glob.glob(os.path.join(raw, "knownclusterblast", f"{contig}*_c*.txt"))
    cb  = glob.glob(os.path.join(raw, "clusterblast", f"{contig}*_c*.txt"))
    return (gbk[0] if gbk else None,
            kcb[0] if kcb else None,
            cb[0] if cb else None)

def _mibig_class(kcb_top):
    """Pull (accession, class-ish label) from an inventory KCB_top string."""
    m = re.search(r"(BGC\d{7})", kcb_top or "")
    acc = m.group(1) if m else None
    cls = ""
    low = (kcb_top or "").lower()
    for tok in ("bottromycin","indolocarbazole","enediyne","glycopeptide","thiopeptide",
                "lipopeptide","nucleoside","spirotetronate"):
        if tok in low: cls = tok; break
    return acc, cls

def render_split_figures(facts, stem, pkg, plt=None, log=lambda m: None):
    """Emit topology + alignment figures for split/high-KCB BGCs. Returns list of produced file paths."""
    produced = []
    tools = _tools_dir()
    if not tools:
        log("SPLIT_FIGS_SKIPPED: tools/ dir not found"); return produced
    raw = _find_raw_run(pkg)
    rows = facts.get("rows", [])
    inv_by_bgc = {r.get("BGC_ID"): r for r in rows}

    # ---- split-pathway candidates from RGGMCI ranked pairs ----
    ranked = glob.glob(os.path.join(pkg, "*_4A_RGGMCI_ranked_pairs.csv"))
    pairs_done = 0
    if ranked and raw:
        for pr in csv.DictReader(open(ranked[0])):
            if "HIGH" not in pr.get("rggmci_confidence","").upper(): continue
            a, b = pr.get("bgc_a"), pr.get("bgc_b")
            ra, rb = inv_by_bgc.get(a, {}), inv_by_bgc.get(b, {})
            acc_a, cls_a = _mibig_class(ra.get("KCB_top",""))
            acc_b, cls_b = _mibig_class(rb.get("KCB_top",""))
            # require SAME MIBiG anchor + a specific, non-ubiquitous class (the real-split test)
            if not (acc_a and acc_a == acc_b): continue
            if not cls_a or cls_a in UBIQUITOUS: continue
            ca = pr.get("contig_a","") or ra.get("Node_ID","")
            cb_ = pr.get("contig_b","") or rb.get("Node_ID","")
            sa = _region_files(raw, _stem(ca)); sb = _region_files(raw, _stem(cb_))
            if not (sa[0] and sb[0] and sa[1] and sb[1]):
                log(f"SPLIT_FIGS: pair {a}+{b} skipped (raw region files not found)"); continue
            out = f"{stem}_8g_split_{cls_a}_{_stem(ca)}_{_stem(cb_)}"
            produced += _run_alignment(tools, sa, sb, acc_a, cls_a,
                                       [f"{_stem(ca)} ({a})", f"{_stem(cb_)} ({b})"], out, log)
            produced += _run_topology(tools, [sa[0], sb[0]], f"{cls_a} split", out+"_topology", log)
            pairs_done += 1
            if pairs_done >= 4: break   # cap to keep brief lean
    elif not raw:
        log("SPLIT_FIGS_SKIPPED: no co-located raw antiSMASH run (knownclusterblast/) found")
    return [p for p in produced if p and os.path.exists(p)]

def _stem(contig):
    m = re.match(r"(NODE_\d+|[A-Za-z]{2,}_?\w*\d+\.\d+|\w+?)(?:_length|$)", contig or "")
    return m.group(1) if m else (contig or "x")[:24]

def _run_alignment(tools, sa, sb, acc, cls, names, out, log):
    cmd = [sys.executable, os.path.join(tools,"cluster_alignment.py"),
           "--kcb", sa[1], sb[1], "--gbk", sa[0], sb[0], "--ref", acc, "--ref-label", cls,
           "--class-token", cls, "--frag-names", names[0], names[1],
           "--title", f"{cls} split - fragments vs MIBiG reference", "--out", out]
    if sa[2] and sb[2]: cmd[ cmd.index("--kcb") : cmd.index("--gbk") ] = ["--kcb", sa[1], sb[1], "--cb", sa[2], sb[2]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if r.returncode == 0:
            return [out+".png", out+"_data.csv", out+"_support.csv"]
        log(f"SPLIT_FIGS align rc={r.returncode}: {r.stderr[-160:]}")
    except Exception as e:
        log(f"SPLIT_FIGS align err: {type(e).__name__}: {e}")
    return []

def _run_topology(tools, gbks, title, out, log):
    cmd = [sys.executable, os.path.join(tools,"gene_topology.py"),
           "--gbk", *gbks, "--title", title, "--split", "--out", out]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return [out+".png", out+"_data.csv"]
        log(f"SPLIT_FIGS topo rc={r.returncode}: {r.stderr[-160:]}")
    except Exception as e:
        log(f"SPLIT_FIGS topo err: {type(e).__name__}: {e}")
    return []
