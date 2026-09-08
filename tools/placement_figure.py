#!/usr/bin/env python3
"""placement_figure.py — a paper-ready companion figure from a phylogenetic-placement grafted tree.

The raw grafted tree from phylo_place.py report shows every reference type strain, which for a large cohort
(e.g. 102 bee/wasp queries on a 133-ref backbone = ~235 tips) is scientifically correct but far too dense for
a manuscript page. This tool makes the legible companion:

  * HOST-COLOR the query tips (Bombus / Apis / Wasp / Andrena / Apidae / Moss), instead of all-red.
  * PRUNE to "queries + their neighborhoods": keep every query tip, plus only the reference tips that are the
    nearest reference to at least one query (read from the <group>_neighborhoods.tsv). Reference clades that no
    query lands near are dropped. Every AS strain and its named neighborhood stays; the tree just loses the
    refs that carry no query. The result is a pruned VIEW of the same placement — it is labeled as such and
    changes no placement result.
  * Keep the outgroup, re-root on it, ladderize.

This is a rendering/뷰 tool: it does not re-run placement and makes no new scientific claim. 16S stays an
anchor, not a species call; a pruned neighborhood view is still a neighborhood hypothesis.

Usage:
  Tools/bin/python3 Tools/placement_figure.py \
      --graft "<...>/placements/epa_result.newick" \
      --labelmap "<...>/refpkg/labelmap.tsv" \
      --neighborhoods "<...>/placements/<group>_neighborhoods.tsv" \
      --group streptomyces --title "Bee/wasp Streptomyces" \
      --out "<...>/placements/<group>_placement_tree_HOSTCOLOR_pruned.png"

Needs biopython + matplotlib -> run with Tools/bin/python3 (has both). Candidate Tools/ asset.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, sys, collections

HOST_COLORS = {
    "Bombus": "#1f77b4", "Apis": "#ff7f0e", "Wasp": "#d62728", "Andrena": "#9467bd",
    "Apidae": "#8c564b", "Moss": "#2ca02c", "host": "#e377c2",
}
REF_COLOR = "#4a4a4a"
OG_COLOR = "#9a9a9a"

def _host_class(hr):
    h = (hr or "").lower()
    if "andrena" in h: return "Andrena"
    if "bombus" in h or "bumble" in h: return "Bombus"
    if "apis" in h or "honey" in h: return "Apis"
    if "wasp" in h: return "Wasp"
    if "apidae" in h or "bee" in h: return "Apidae"
    if "moss" in h: return "Moss"
    return "host"

def _asid(p):
    m = re.search(r"(AS[-_]?\d+)", p or "")
    if not m: return p or ""
    return re.sub(r"^AS(?!-)", "AS-", m.group(1).replace("_", "-"))

def _find_ssot(explicit):
    if explicit and os.path.exists(explicit): return explicit
    cands = []
    root = os.environ.get("SAPOTE_WORKSPACE_ROOT", "")
    if root: cands.append(os.path.join(root, "OFFICIAL_DATA", "STRAIN_METADATA.tsv"))
    d = os.getcwd()
    for _ in range(9):
        cands.append(os.path.join(d, "OFFICIAL_DATA", "STRAIN_METADATA.tsv"))
        d = os.path.dirname(d) or d
    for c in cands:
        if os.path.exists(c): return c
    return ""

def _load_strain_meta(explicit):
    import csv
    meta = {}; path = _find_ssot(explicit)
    if not path: return meta
    try:
        with open(path) as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                tid = (row.get("tip_label") or row.get("strain") or "").strip()
                if not tid: continue
                acc = (row.get("genbank_accession") or "").strip()
                hr  = (row.get("host_raw") or row.get("host_common") or "").strip()
                meta[tid] = {"host": _host_class(hr),
                             "acc": ("" if acc.upper() in ("", "N/A") else acc)}
    except Exception:
        pass
    return meta

def _dedupe_genus(p):
    return re.sub(r"\b([A-Z][a-z]+)[ _]\1\b", r"\1", p or "")

def _ref_label(p, modal):
    # Drop the redundant ingroup genus (the tree is genus-scoped), keep species + strain + 16S accession.
    p = _dedupe_genus((p or "").replace("_", " "))
    acc = ""
    m = re.match(r"\s*([A-Z]{2}[ ]?\d+(?:\.\d+)?)\s+(.*)", p)
    rest = p
    if m:
        acc = m.group(1).replace(" ", ""); rest = m.group(2)
    rest = re.sub(r"\s+16S.*$", "", rest)
    rest = re.sub(r"\s+strain[: ]+", " ", rest)
    toks = rest.split()
    if toks and modal and toks[0].lower() == modal.lower():
        toks[0] = toks[0][0] + "."          # abbreviate the redundant genus
    lab = " ".join(toks)[:34]
    return (lab + " (" + acc + ")") if acc else lab[:46]


def _load_labelmap(path):
    m = {}
    if path and os.path.exists(path):
        for i, ln in enumerate(open(path)):
            if i == 0 or "\t" not in ln:
                continue
            s, o = ln.rstrip("\n").split("\t", 1)
            m[s] = o
    return m


def _is_query(name):
    # v9.7.374 fix: was AS-only. docs/phylogenomics.md names "focal AS/SID genome" as this
    # workflow's own convention -- a SID-prefixed query genome (a real, common category in this
    # cohort; see phylo_place.py's identical fix) was silently misclassified as a REFERENCE tip.
    # Reproduced live: this mislabels a SID query as a candidate for the reference-pruning pass
    # (which can silently DROP it from the figure entirely), and separately can pull it into the
    # `genus != modal` outgroup set (the letters preceding its digits, "SID", parse as a bogus
    # "genus" distinct from the ingroup's real genus) -- corrupting BOTH the re-rooting
    # (t.root_with_outgroup includes the query as if it were an outgroup taxon) and the rendered
    # label/color/legend (the query is drawn gray/unbolded as "outgroup" instead of host-colored).
    return bool(re.match(r"^(AS|SID)[-_]?\d", name or ""))  # anchored: real query tip STARTS with the id; not an embedded "AS 4.xxxx" culture code (F4)


def _host_of(pretty):
    m = re.search(r"from_([A-Za-z]+)", pretty or "")
    return m.group(1) if m else "host"




# v9.7.412 (hostile audit of the sealed .411, findings E1/E3): typed refusals instead of a raw
# traceback or a silent figure from garbage. A non-Newick file parsed as ONE tip and produced an
# exit-0 figure; a missing input or unwritable output raised FileNotFoundError / PermissionError.
def _refuse(code: str, detail: str) -> "NoReturn":
    import sys as _s
    _s.stderr.write(f"{code}: {detail}\n")
    raise SystemExit(2)


def _require_readable(path: str, what: str) -> None:
    import os as _o
    if not path or not _o.path.isfile(path):
        _refuse("INPUT_NOT_FOUND", f"{what} {path!r} is not a readable file")


def _require_writable_parent(path: str, what: str) -> None:
    import os as _o
    parent = _o.path.dirname(_o.path.abspath(path)) or "."
    if not _o.path.isdir(parent) or not _o.access(parent, _o.W_OK):
        _refuse("OUTPUT_NOT_WRITABLE", f"cannot write {what} under {parent!r}")


def _read_tree_or_refuse(path: str, what: str = "--graft"):
    try:
        from Bio import Phylo
    except ImportError:
        _refuse("DEPENDENCY_MISSING", "biopython is required for tree I/O (pip install biopython)")
    try:
        t = Phylo.read(path, "newick")
    except Exception as exc:
        _refuse("INPUT_NOT_A_TREE", f"{what} {path!r} did not parse as Newick ({type(exc).__name__}: {exc})")
    tips = t.get_terminals()
    if len(tips) < 2:
        _refuse("INPUT_NOT_A_TREE", f"{what} {path!r} parsed as {len(tips)} tip(s); a placement graft carries queries and references")
    return t, tips


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)  # v9.7.412: no silent prefix matching
    ap.add_argument("--graft", required=True, help="grafted newick from phylo_place report")
    ap.add_argument("--labelmap", default="")
    ap.add_argument("--neighborhoods", default="", help="<group>_neighborhoods.tsv (defines which refs to keep)")
    ap.add_argument("--group", default="cohort")
    ap.add_argument("--title", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-all-refs", action="store_true",
                    help="do NOT prune references (host-color only); default prunes to nearest-of-a-query refs")
    ap.add_argument("--strain-meta", default="", help="OFFICIAL_DATA/STRAIN_METADATA.tsv (auto-located if omitted)")
    ap.add_argument("--neighbors-per-query", type=int, default=1,
                    help="keep the N nearest reference tips per query (prune-ladder control; higher = more context)")
    a = ap.parse_args()
    _require_readable(a.graft, "--graft")
    _require_writable_parent(a.out, "--out")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from Bio import Phylo

    lm = _load_labelmap(a.labelmap)
    meta = _load_strain_meta(a.strain_meta)

    def pretty(n):
        if not n:
            return ""
        return lm.get(n, lm.get(re.sub(r"_\d+$", "", n), n))

    t, tips = _read_tree_or_refuse(a.graft)

    # genus of each ref tip -> modal genus = ingroup; the rest = outgroup
    def genus(x):
        pp = re.sub(r"^\s*[A-Z]{2}[ _]?\d+(?:\.\d+)?\s+", "", pretty(x.name) or "")  # drop leading 16S accession
        m = re.match(r"([A-Za-z]+)", pp)
        return m.group(1) if m else ""
    ref_tips = [x for x in tips if not _is_query(x.name)]
    genera = collections.Counter(genus(x) for x in ref_tips if genus(x))
    modal = genera.most_common(1)[0][0] if genera else ""
    og_tips = [x for x in ref_tips if genus(x) and genus(x) != modal]
    og_names = {x.name for x in og_tips}

    # PRUNE to a legible neighborhood view: keep every query + outgroup + the N nearest reference tips
    # per query (patristic distance on the grafted tree). N = --neighbors-per-query drives the prune ladder;
    # this is robust to label formatting (the old neighborhoods-file string match silently kept too few).
    q_tips = [x for x in tips if _is_query(x.name)]
    did_prune = False
    if not a.keep_all_refs and q_tips:
        cand = [x for x in ref_tips if x.name not in og_names]
        keep_ids = set()
        N = max(1, a.neighbors_per_query)
        for q in q_tips:
            near = sorted(cand, key=lambda r: t.distance(q, r))[:N]
            keep_ids.update(id(r) for r in near)
        drop = [x for x in cand if id(x) not in keep_ids]
        for x in drop:
            try:
                t.prune(x); did_prune = True
            except Exception:
                continue  # tip absent from tree — skip (best-effort prune)

    # re-root on outgroup
    try:
        og_now = [x for x in t.get_terminals() if x.name in og_names]
        if len(og_now) == 1:
            t.root_with_outgroup(og_now[0])
        elif og_now:
            t.root_with_outgroup(*og_now)
        else:
            t.root_at_midpoint()
    except Exception:
        try:
            t.root_at_midpoint()
        except Exception:
            pass
    t.ladderize()

    def lab(x):
        if not x.name:
            return ""
        p = pretty(x.name)
        if _is_query(x.name):
            asid = _asid(p)
            info = meta.get(asid, {})
            host = info.get("host", "") or _host_of(p)
            acc = info.get("acc", "")
            bits = [asid] + ([host] if host and host != "host" else []) + ([acc] if acc else [])
            return "  ".join(bits)
        return _ref_label(p, modal)

    n = len(t.get_terminals())
    fig, ax = plt.subplots(figsize=(11, max(5, n * 0.30)))
    Phylo.draw(t, axes=ax, do_show=False, label_func=lab, show_confidence=False)
    by = {}
    for x in t.get_terminals():
        by.setdefault(lab(x), x)
    hosts_seen = set()
    for txt in ax.texts:                 # uniform size FIRST: a label collision leaves a text unmatched below,
        txt.set_fontsize(8)              # and without this it keeps matplotlib's giant default (the bold-huge-tip bug)
    for txt in ax.texts:
        x = by.get(txt.get_text().strip())
        if x is None:
            continue
        if _is_query(x.name):
            h = meta.get(_asid(pretty(x.name)), {}).get("host") or _host_of(pretty(x.name))
            hosts_seen.add(h)
            txt.set_color(HOST_COLORS.get(h, HOST_COLORS["host"]))
            txt.set_fontweight("bold")
        elif x.name in og_names:
            txt.set_color(OG_COLOR)
        else:
            txt.set_color(REF_COLOR)
    pruned = ("pruned to queries + %d nearest ref(s) each" % max(1, a.neighbors_per_query)) if did_prune else "all references"
    ttl = a.title or a.group
    ax.set_title(f"{ttl} — 16S placement (host-colored; {pruned})\n"
                 "queries placed on a fixed type-strain backbone; 16S = anchor, not a species call; "
                 "neighborhood only; judgment deferred", fontsize=9)
    # host legend
    handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=HOST_COLORS[h], markersize=8, label=h)
               for h in sorted(hosts_seen)]
    handles.append(Line2D([0], [0], marker="o", color="w", markerfacecolor=REF_COLOR, markersize=8, label="type strain (ref)"))
    handles.append(Line2D([0], [0], marker="o", color="w", markerfacecolor=OG_COLOR, markersize=8, label="outgroup"))
    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=False)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_yticks([]); ax.set_xlabel("substitutions/site")
    fig.tight_layout()
    fig.savefig(a.out, dpi=200, bbox_inches="tight")
    svg = a.out.rsplit(".", 1)[0] + ".svg"
    fig.savefig(svg, bbox_inches="tight")
    import matplotlib.pyplot as _plt
    _plt.close(fig)
    emit(f"[placement_figure] wrote {a.out}  ({n} tips; {pruned})", f"[placement_figure] wrote {svg}", sep="\n")


if __name__ == "__main__":
    sys.exit(main())
