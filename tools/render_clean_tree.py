#!/usr/bin/env python3
"""Shared clean renderer for the GToTree 138-SCG core-genome ML trees.

Fixes the three readability problems flagged on the first-pass figures:
  1. a fixed pixel gap between every branch tip (and its dot) and its label;
  2. accurate per-node y-positions + a white halo behind support values, so
     stacked SH-aLRT/UFBoot labels stop piling up on the backbone;
  3. the caption sits well below the x-axis tick numbers (no overlap).

Usage:
    render_clean_tree.py <treefile> <out.png> <"Title line 1||Title line 2"> \
        <outgroup1[,outgroup2...]> [tag_json]

Leaf-name convention: underscores -> spaces; a trailing "_OUTGROUP" is stripped
and annotated "(outgroup)". Genus+species are italicised, any trailing strain
code stays upright. AS-#### query strains are bold + coloured. `tag_json` is an
optional JSON map {leaf_name: " — short call tag"} appended after the name.
"""
import sys, json, re, os
if __name__ == "__main__":
    TRE, OUT, TITLE = sys.argv[1], sys.argv[2], sys.argv[3]
    OUTGROUPS = [s for s in sys.argv[4].split(",") if s]
    TAGS = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}

    # HARD pre-render gate (PHYLOGENETICS_WORKFLOW.md step 6): a tree MUST PASS tree_sanity_check
    # before it is drawn. Run it BEFORE loading the heavy render libraries so a pathological tree is
    # refused fast (exit 2) and never reaches a figure. Outgroup-aware (tree_sanity_check exempts the
    # designated outgroup); the resolved outgroup is passed through so a correct sister taxon PASSes.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tree_sanity_check as _tsc
    _ok, _msg = _tsc.check(TRE, outgroup=(OUTGROUPS[0] if OUTGROUPS else None))
    print(_msg)
    if not _ok:
        print("REFUSED: tree_sanity_check FAILED — not rendering (prune the offender or fix the "
              "outgroup, then re-run). PHYLOGENETICS_WORKFLOW.md step 6.", file=sys.stderr)
        sys.exit(2)

    # HARD pre-render FIGURE gate (AMBER_400/401): tree_sanity_check gates the TREE above; this
    # gates what the renderer will DRAW — marker coverage, category vocabulary, label hygiene/
    # verbosity, declared omissions. Env-driven so call sites need no signature change:
    #   FIGCHECK_HOSTMAP=<hostmap.json>  enables marker checks (F1/F2)
    #   GG_OMITTED="AS-XXX (...)"        acknowledges TREE_SPEC omitted_strains for the caption (F5)
    #   FIGCHECK_SKIP=1                  documented escape hatch for non-figure debug renders
    import os as _os
    if _os.environ.get("FIGCHECK_SKIP") != "1":
        import figure_check as _fc
        _hm = _os.environ.get("FIGCHECK_HOSTMAP") or None
        _fok, _fmsg = _fc.check(TRE, hostmap=_hm, omitted=_os.environ.get("GG_OMITTED", ""),
                                marker_checks=bool(_hm))
        print(_fmsg)
        if not _fok:
            print("REFUSED: figure_check FAILED — not rendering. A known figure defect is a stop, "
                  "not a caption footnote; fix the inputs and re-run.", file=sys.stderr)
            sys.exit(2)

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from Bio import Phylo

    AS_RE = re.compile(r"^AS[-_]\d+$")
    # Accession junk that is NOT a strain name: GCF/GCA prefixes+accessions, IMG OIDs (Ga#####),
    # ASM ids, bare digit runs, contig cruft. Real codes (DSM43461/NRRL8057/JCM) carry letters.
    _ACC_JUNK = re.compile(r"^(GC[AF]|GC[AF][_.]?\d.*|ASM\w+|Ga\d{5,}|\d{4,}|v\d+|"
                           r"contig\w*|scaffold\w*|node\w*|tig\d+)$", re.I)

    def is_query(name):
        return bool(AS_RE.match(name or ""))

    def label_parts(name):
        """Return (main, suffix, italic_main) for a leaf name."""
        outg = name.endswith("_OUTGROUP")
        n = name[:-9] if outg else name
        if is_query(n):
            main = n.replace("_", "-")
            suf = TAGS.get(name, TAGS.get(n, ""))
            if outg:
                suf = (suf + "  (outgroup)").strip()
            return main, suf, False
        toks = n.split("_")
        main = " ".join(toks[:2])                     # Genus species (italic)
        rest = " ".join(t for t in toks[2:]
                        if not _ACC_JUNK.match(t) and t.upper() != "DNA")  # drop GCF/Ga#/ASM junk
        suf = ((" " + rest) if rest else "") + TAGS.get(name, TAGS.get(n, ""))
        if outg:
            suf = (suf + "  (outgroup)").rstrip()
        return main, suf, True

    tree = Phylo.read(TRE, "newick")
    if OUTGROUPS:
        try:
            tree.root_with_outgroup(*[{"name": g} for g in OUTGROUPS])
        except Exception:
            tree.root_with_outgroup({"name": OUTGROUPS[0]})
    tree.ladderize()

    n = len(tree.get_terminals())
    fig, ax = plt.subplots(figsize=(13.5, max(6.0, 0.42 * n + 2.2)))
    Phylo.draw(tree, do_show=False, axes=ax, label_func=lambda c: "", show_confidence=False)
    depths = tree.depths(); terms = tree.get_terminals()
    tindex = {t: i + 1 for i, t in enumerate(terms)}
    ypos = {t: float(tindex[t]) for t in terms}
    for cl in tree.find_clades(order="postorder"):
        if not cl.is_terminal():
            ypos[cl] = sum(ypos[c] for c in cl.clades) / len(cl.clades)

    TIPGAP = 10
    for t in terms:
        x, y = depths[t], ypos[t]
        main, suf, italic = label_parts(t.name)
        q = is_query(t.name.replace("_OUTGROUP", ""))
        color, weight = ("#c00000", "bold") if q else ("#1a1a1a", "normal")
        txt = ax.annotate(main, xy=(x, y), xytext=(TIPGAP, 0), textcoords="offset points",
                          va="center", ha="left", fontsize=9.5,
                          fontstyle=("italic" if italic else "normal"),
                          color=color, fontweight=weight, annotation_clip=False)
        if suf:
            ax.annotate(suf, xycoords=txt, xy=(1, 0.5), va="center", ha="left", fontsize=8,
                        color=(color if q else "#555"), fontweight=weight, annotation_clip=False)
        if q:
            ax.scatter([x], [y], s=42, color=color, zorder=6)

    for cl in tree.get_nonterminals():
        lab = cl.confidence if cl.confidence is not None else (cl.name if cl.name and str(cl.name).strip() else None)
        if lab is None or not cl.branch_length:
            continue
        x, y = depths[cl], ypos[cl]
        ax.annotate(str(lab), xy=(x, y), xytext=(-3, 3), textcoords="offset points",
                    va="bottom", ha="right", fontsize=6.2, color="#0057b8", annotation_clip=False,
                    bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.72))

    ax.set_title(TITLE.replace("||", "\n"), fontsize=9.5)
    ax.set_xlabel("substitutions per site", labelpad=6); ax.set_ylabel(""); ax.set_yticks([])
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    xr = ax.get_xlim(); ax.set_xlim(xr[0], xr[1] * 1.95)
    # scale bar
    xspan = xr[1] - xr[0]
    sb = 0.05 if xspan > 0.15 else round(xspan / 4, 3)
    ax.plot([xr[0] + 0.005, xr[0] + 0.005 + sb], [n - 0.2, n - 0.2], color="k", lw=1.6)
    ax.text(xr[0] + 0.005 + sb / 2, n - 0.2 + 0.3, "%g subs/site" % sb, ha="center", fontsize=8)
    fig.text(0.5, 0.015,
             "Node labels = SH-aLRT/UFBoot support (%).   ᵀ = type strain.   "
             "Red = AS query strains.   Species names italic.",
             ha="center", fontsize=7, color="#555")
    plt.tight_layout(rect=(0, 0.05, 1, 1))
    plt.savefig(OUT, dpi=200, bbox_inches="tight")
    print("wrote", OUT)
