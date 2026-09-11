"""
bgc_figures — publication figures from antiSMASH output + the wheel stack.

Three figure types, each proven on real strain data:
  * gene_arrow_diagram  — a BGC's genes as colored arrows (dna-features-viewer)
  * genome_atlas        — circular contig/BGC map (pycirclize)
  * ani_heatmap         — all-vs-all ANI matrix across strains (pyskani + matplotlib)

Cross-strain similarity networks live in the analysis layer; this module is for the
per-strain / small-cohort figures a manuscript needs.

Heavy plotting deps (matplotlib, dna_features_viewer, pycirclize, pyskani) are in the
sapote-addons stack. Each function import-guards and raises a clear message if absent,
so a lean install is unaffected.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
from pathlib import Path

from .figure_save import save_figure

PUBLICATION_RASTER_DPI = 300


def _save_pair(fig, out_png, *, renderer: str, provenance: str):
    target = Path(out_png)
    save_figure(
        fig,
        figure_id=target.stem,
        out_stem=target.with_suffix(""),
        renderer=renderer,
        package_dir=target.parent,
        provenance=provenance,
    )


def _need(mod, addon="sapote-addons"):
    try:
        return __import__(mod)
    except ImportError:
        raise RuntimeError(f"bgc_figures needs {mod} (ship the {addon} addon). "
                           f"The rest of the pipeline is unaffected.")


def gene_arrow_diagram(region_gbk, out_png):
    """Draw a BGC's genes as function-colored arrows. Returns out_png."""
    _need("dna_features_viewer")
    from dna_features_viewer import GraphicFeature, GraphicRecord
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from Bio import SeqIO

    rec = next(SeqIO.parse(region_gbk, "genbank"))
    L = len(rec.seq)

    def color(feat):
        d = str(feat.qualifiers.get("sec_met_domain", [])).lower()
        if "condensation" in d or "amp-binding" in d:
            return "#C44E52"      # NRPS
        if "ks" in d or "acyl_transf" in d or "ketoacyl" in d:
            return "#4C72B0"      # PKS
        if "p450" in d or "halogen" in d or "methyltr" in d:
            return "#DD8452"      # tailoring
        if "transport" in d or "abc" in d:
            return "#8172B3"      # transport/resistance
        if feat.qualifiers.get("gene_kind", [""])[0] == "biosynthetic":
            return "#55A868"
        return "#CCCCCC"

    feats = []
    for feat in rec.features:
        if feat.type == "CDS":
            dom = feat.qualifiers.get("sec_met_domain", [])
            label = str(dom[0]).split(" ")[0][:10] if dom else None
            feats.append(GraphicFeature(
                start=int(feat.location.start), end=int(feat.location.end),
                strand=feat.location.strand, color=color(feat), label=label))
    gr = GraphicRecord(sequence_length=L, features=feats)
    fig, ax = plt.subplots(1, figsize=(16, 3))
    gr.plot(ax=ax, with_ruler=True)
    plt.tight_layout()
    _save_pair(fig, out_png, renderer="bgc_figures.gene_arrow_diagram",
               provenance=f"region_gbk={Path(region_gbk).name}")
    plt.close(fig)
    return out_png


def genome_atlas(strain_dir, out_png, top_n=20):
    """Circular contig/BGC map: top contigs as sectors, PKS/NRPS-bearing in red."""
    _need("pycirclize")
    from pycirclize import Circos
    import matplotlib
    matplotlib.use("Agg")
    from Bio import SeqIO

    contig_len, contig_bgc = {}, {}
    for f in glob.glob(f"{strain_dir}/**/*.region*.gbk", recursive=True):
        if "MACOSX" in f:
            continue
        for rec in SeqIO.parse(f, "genbank"):
            cname = f.split("/")[-1].split(".region")[0]
            prod = ";".join(q for ft in rec.features if ft.type == "region"
                            for q in ft.qualifiers.get("product", []))
            contig_len[cname] = len(rec.seq)
            contig_bgc.setdefault(cname, []).append(prod)
    if not contig_len:
        raise RuntimeError(f"no region GBKs found under {strain_dir}")
    top = sorted(contig_len.items(), key=lambda x: -x[1])[:top_n]
    sectors = {n.split("_length")[0].replace("NODE_", "c"): L for n, L in top}
    circos = Circos(sectors, space=3)
    for sector in circos.sectors:
        sector.axis(fc="none", ec="grey", lw=0.5)
        sector.text(sector.name, size=7, r=108)
        track = sector.add_track((90, 100))
        track.axis(fc="#E8E8E8")
        orig = [n for n in contig_len
                if n.split("_length")[0].replace("NODE_", "c") == sector.name]
        if orig:
            prods = contig_bgc.get(orig[0], [])
            col = "#C44E52" if any("NRPS" in p or "PKS" in p for p in prods) else "#55A868"
            track.rect(0, sector.size, fc=col, ec="none")
    fig = circos.plotfig()
    _save_pair(fig, out_png, renderer="bgc_figures.genome_atlas",
               provenance=f"region_gbk_count={sum(len(v) for v in contig_bgc.values())}")
    return out_png


def ani_heatmap(strain_dirs, out_png, species_boundary=95.0):
    """All-vs-all ANI heatmap across strains (pyskani). Flags intransitivity, a sign
    that fragmented drafts are giving unreliable ANI (report, don't hide)."""
    pyskani = _need("pyskani")
    import csv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from Bio import SeqIO

    names, fastas = [], {}
    for sd in strain_dirs:
        s = sd.rstrip("/").split("/")[-1]
        fa = [f for f in glob.glob(f"{sd}/**/*.fna", recursive=True)
              + glob.glob(f"{sd}/**/*.fasta", recursive=True) if "MACOSX" not in f]
        if fa:
            names.append(s)
            fastas[s] = fa[0]
    # v9.7.409 (DEEP_AUDIT2_resource_dos #3/#5): the ANI matrix fill is O(n^2) and the intransitivity
    # check below is O(n^3) in strain count, and the heatmap canvas grows ~1.4 in/strain. Bound the
    # strain count so a pathological --strain-dirs cannot blow up compute or canvas. Typed WARN.
    from .pair_scan_caps import cap_pair_scan_items, max_ani_strains
    names = cap_pair_scan_items(names, label="ani_heatmap strains", cap=max_ani_strains())
    dbs = {}
    for s in names:
        db = pyskani.Database()
        for r in SeqIO.parse(fastas[s], "fasta"):
            db.sketch(f"{s}:{r.id}", bytes(r.seq))
        dbs[s] = db
    if len(names) < 2:
        return {"out_png": None, "intransitive": False, "n_strains": len(names),
                "error": (f"ANI heatmap needs >=2 strain dirs each containing a genome FASTA "
                          f"(.fna/.fasta); found {len(names)}. Point --strain-dirs at antiSMASH "
                          "output dirs that include the input genome, or supply genome FASTAs.")}
    ani = np.zeros((len(names), len(names)))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                ani[i, j] = 100.0
                continue
            hits = []
            for r in SeqIO.parse(fastas[b], "fasta"):
                for h in dbs[a].query(f"q:{r.id}", bytes(r.seq)):
                    hits.append(h.identity * 100)
            ani[i, j] = float(np.mean(hits)) if hits else 0.0
    ani = (ani + ani.T) / 2  # symmetrize

    # intransitivity check
    intransitive = False
    for i in range(len(names)):
        for j in range(len(names)):
            for k in range(len(names)):
                if (ani[i, j] >= 97 and ani[j, k] >= 97 and ani[i, k] < 92):
                    intransitive = True
    fig, ax = plt.subplots(figsize=(1.4 * len(names) + 3, 1.2 * len(names) + 2))
    im = ax.imshow(ani, cmap="viridis", vmin=max(85, ani.min()), vmax=100)
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticklabels(names)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{ani[i, j]:.1f}", ha="center", va="center",
                    color="white" if ani[i, j] < 96 else "black", fontsize=9)
    plt.colorbar(im, label="ANI (%)")
    note = ("\nNOTE: values intransitive — fragmented drafts give approximate ANI; confirm with reassembly."
            if intransitive else "")
    ax.set_title(f"ANI (pyskani, symmetrized). {species_boundary:.0f}% = species boundary.{note}",
                 fontsize=9)
    plt.tight_layout()
    _save_pair(fig, out_png, renderer="bgc_figures.ani_heatmap",
               provenance=f"strain_count={len(names)};metric=nucleotide_ANI")
    plt.close(fig)
    # v9.7.409: persist the numeric ANI matrix so every plotted cell is traceable on disk.
    # The heatmap is a raster whose cell values are baked into glyph paths (not readable back),
    # and the only prior companion (ani.log) recorded a path, not the numbers. Write a labelled
    # matrix CSV (rows = query, cols = reference; 100.0 on the diagonal) next to the figure.
    matrix_csv = str(Path(out_png).with_suffix("")) + "_ani_matrix.csv"
    with open(matrix_csv, "w", newline="", encoding="utf-8") as _mf:
        _w = _SafeWriter(_mf)
        _w.writerow(["# provenance",
                     "pyskani nucleotide ANI, symmetrized; rows=query, cols=reference; "
                     "numeric source for ani_heatmap.png (100.0 on the diagonal)"])
        _w.writerow(["strain", *names])
        for _i, _rn in enumerate(names):
            _w.writerow([_rn, *[f"{ani[_i, _j]:.4f}" for _j in range(len(names))]])
    return {"out_png": out_png, "ani": ani.tolist(), "names": names,
            "intransitive": intransitive, "ani_matrix_csv": matrix_csv}


def figures_command(args):
    if args.fig_kind == "diagram":
        emit(gene_arrow_diagram(args.gbk, args.out))
        return 0
    if args.fig_kind == "atlas":
        emit(genome_atlas(args.strain_dir, args.out))
        return 0
    if args.fig_kind == "ani":
        res = ani_heatmap(args.strain_dirs, args.out)
        emit(f"{res['out_png']} (intransitive={res['intransitive']})")
        return 0
    if args.fig_kind == "gcf-network":
        # BiG-SCAPE GCF network from a BiG-SCAPE 2 DB. Membership is similarity, not identity.
        from mamey import bigscape_figures
        res = bigscape_figures.gcf_network(
            args.db, args.strain, args.run, args.cutoff,
            evidence=args.evidence, out=args.out,
        )
        emit(res)
        return 0 if isinstance(res, dict) and res.get("status") == "WRITTEN" else 1
    if args.fig_kind == "clinker":
        # clinker comparative alignment across region GBKs. Gene links are similarity, not identity.
        from mamey import bigscape_figures
        res = bigscape_figures.clinker_figure(args.gbks, out=args.out)
        emit(res)
        return 0 if isinstance(res, dict) and res.get("status") == "WRITTEN" else 1
    emit("figures: specify a kind (diagram | atlas | ani | gcf-network | clinker)")
    return 2
