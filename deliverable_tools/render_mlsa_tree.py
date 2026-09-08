#!/usr/bin/env python3
"""render_mlsa_tree.py — render an MLSA/GToTree .treefile to a clean, rooted PNG.

MERGED renderer (the phylogenomics lane + TREE_GALLERY house style, 2026-08-03). Sign-off-grade rendering:
  * REROOT on the outgroup (_OUTGROUP tip) so the outgroup sits at the base, not mid-tree;
  * ladderize (smallest clade up) for a tidy comb;
  * a real "substitutions/site" x-axis with true tick values (the gallery look) — on by
    default; hide with --no-axis. Because uncapped drawn positions equal true cumulative
    distance, the axis reads honestly for the main tree;
  * tip LABELS sit at the branch tip by default (--labels branchend, the "before"/gallery
    style the Developer or User preferred). --labels aligned restores the right-margin+dotted-leader style;
  * long-branch handling: a terminal branch longer than the robust cap is drawn CAPPED with a
    "//" break and its TRUE length annotated in the label (orange) — one bad reference genome
    can't crush the whole figure, and nothing is silently hidden. --no-cap draws true lengths
    (full gallery honesty; a pathological outgroup will stretch the axis);
  * role colour: AS/AJS query = crimson, outgroup = grey, reference = black;
  * strong support (SH-aLRT>=80 & UFBoot>=95) marked with a blue node dot.

RENDERS an existing treefile (no tree building, no cores). CLAIM SAFETY: topology only;
ANI delimits species; capped/long branches flagged, not trusted; judgment deferred.

Usage:
  python render_mlsa_tree.py <tree.treefile> <out.png> [--title T] [--cap 25]
      [--labels branchend|aligned] [--no-axis] [--no-cap] [--cladogram] [--exclude s1,s2]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, re, argparse
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
try:
    from mamey.render_safe import safe_savefig_dpi as _safe_dpi
except ImportError:  # bare-script run from another cwd: bundle root is one level up
    import os as _rs_os, sys as _rs_sys
    _rs_sys.path.insert(0, _rs_os.path.dirname(_rs_os.path.dirname(_rs_os.path.abspath(__file__))))
    from mamey.render_safe import safe_savefig_dpi as _safe_dpi

QUERY = re.compile(r'^(AS[-_]\d+|AJS[-_]\d+)', re.I)
OUTGROUP = re.compile(r'OUTGROUP', re.I)


class Node:
    __slots__ = ('name', 'length', 'support', 'children', 'parent', 'x', 'y', 'nleaf')

    def __init__(self):
        self.name = ''; self.length = 0.0; self.support = ''
        self.children = []; self.parent = None
        self.x = 0.0; self.y = 0.0; self.nleaf = 0

    def leaves(self):
        if not self.children:
            yield self
        for c in self.children:
            yield from c.leaves()

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def parse(text):
    s = text.strip().rstrip(';'); pos = [0]

    def node():
        n = Node()
        if s[pos[0]] == '(':
            pos[0] += 1
            while True:
                c = node(); c.parent = n; n.children.append(c)
                if s[pos[0]] == ',': pos[0] += 1; continue
                if s[pos[0]] == ')': pos[0] += 1; break
        st = pos[0]
        while pos[0] < len(s) and s[pos[0]] not in '(),:;': pos[0] += 1
        lab = s[st:pos[0]].strip().strip("'\"")
        if n.children: n.support = lab
        else: n.name = lab
        if pos[0] < len(s) and s[pos[0]] == ':':
            pos[0] += 1; st = pos[0]
            while pos[0] < len(s) and s[pos[0]] not in '(),;': pos[0] += 1
            try: n.length = float(s[st:pos[0]])
            except ValueError: n.length = 0.0
        return n
    return node()


def reroot_on_outgroup(root):
    """Reroot so the outgroup tip is sister to the rest. Classic edge-reversal reroot;
    branch lengths move with the flipped edges. Returns the new root (or the old one if no
    outgroup / already basal)."""
    og = next((t for t in root.leaves() if OUTGROUP.search(t.name)), None)
    if og is None or og.parent is None:
        return root
    anc = []
    n = og.parent
    while n is not None:
        anc.append(n); n = n.parent
    # anc = [p0(=og.parent), p1, ..., old_root]
    p0 = anc[0]
    if p0.parent is None and len(p0.children) == 2:
        return root  # already effectively rooted next to outgroup
    p0.children.remove(og)
    chain = anc[::-1]  # [old_root, ..., p1, p0]
    for i in range(len(chain) - 1):
        par, ch = chain[i], chain[i + 1]
        par.children.remove(ch)
        ch.children.append(par)
        par.parent = ch
        par.length = ch.length          # branch length rides the reversed edge
    ingroup = chain[-1]                  # p0, now top of the flipped ingroup
    new = Node()
    bl = og.length if og.length > 0 else 0.0
    og.parent = new; ingroup.parent = new
    og.length = ingroup.length = bl / 2.0
    new.children = [ingroup, og]
    new.parent = None; new.length = 0.0
    return new


def prune_tips(root, substrings):
    """Drop leaves whose name matches any substring, collapsing now-unifurcating parents.
    Adds the removed edge's length onto the surviving child so distances stay honest."""
    def keep(n):
        if not n.children:
            return not any(s in n.name for s in substrings)
        n.children = [c for c in n.children if keep(c)]
        for c in n.children:
            c.parent = n
        return len(n.children) > 0
    keep(root)
    # collapse single-child internal nodes
    def collapse(n):
        newkids = []
        for c in n.children:
            collapse(c)
            while len(c.children) == 1:
                g = c.children[0]
                g.length += c.length
                g.parent = n
                c = g
            newkids.append(c)
        n.children = newkids
    collapse(root)
    return root


def ladderize(root):
    def count(n):
        n.nleaf = 1 if not n.children else sum(count(c) for c in n.children)
        return n.nleaf
    count(root)
    for n in root.walk():
        n.children.sort(key=lambda c: c.nleaf)
    return root


def median(xs):
    xs = sorted(xs); n = len(xs)
    return 0.0 if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def layout(root, cap_len, cladogram=False):
    tips = list(root.leaves())
    for i, t in enumerate(tips):
        t.y = i
    def setx(n, acc):
        draw = 1.0 if cladogram else min(n.length, cap_len)
        n.x = acc + draw
        for c in n.children:
            setx(c, n.x)
    setx(root, 0.0)
    def sety(n):
        if n.children:
            for c in n.children: sety(c)
            n.y = sum(c.y for c in n.children) / len(n.children)
    sety(root)
    return tips


def role_color(name):
    if OUTGROUP.search(name): return "#888888"
    if QUERY.match(name): return "#c0392b"
    return "#222222"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("treefile"); ap.add_argument("out")
    ap.add_argument("--title", default="")
    ap.add_argument("--cap", type=float, default=25.0, help="cap terminal draw length at CAP x median")
    ap.add_argument("--exclude", default="", help="comma-sep substrings; drop matching tips before layout")
    ap.add_argument("--labels", choices=["branchend", "aligned"], default="branchend",
                    help="branchend = labels at the branch tip (gallery/'before' look, default); "
                         "aligned = right-margin column with dotted leaders")
    ap.add_argument("--no-axis", action="store_true", help="hide the substitutions/site x-axis")
    ap.add_argument("--no-cap", action="store_true", help="draw true branch lengths, no outlier cap")
    ap.add_argument("--cladogram", action="store_true")
    a = ap.parse_args(argv)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = parse(open(a.treefile).read())
    drops = [s.strip() for s in a.exclude.split(",") if s.strip()]
    if drops:
        root = prune_tips(root, drops)
    root = reroot_on_outgroup(root)
    root = ladderize(root)

    tips = list(root.leaves())
    tl = sorted(t.length for t in tips if t.length > 0) or [1e-4]
    med = median(tl)
    p90 = tl[min(len(tl) - 1, int(0.90 * len(tl)))]
    # Robust cap: only GROSS outliers. Use the larger of (cap x median) and (4 x P90) so a
    # core-genome tree's normal spread isn't capped while a 100-300x MLSA branch still is.
    # --no-cap disables capping entirely (full gallery-honest true-length draw).
    cap_len = float("inf") if a.no_cap else max(a.cap * med, 4.0 * p90)
    tips = layout(root, cap_len, cladogram=a.cladogram)
    n = len(tips)
    maxx = max(t.x for t in root.walk()) or 1.0
    aligned = (a.labels == "aligned")
    label_x = maxx * 1.02  # only used in aligned mode
    capped = [t for t in tips if (not a.cladogram) and t.length > cap_len]
    show_axis = (not a.no_axis) and (not a.cladogram)

    fig_h = max(4, 0.16 * n)
    fig, ax = plt.subplots(figsize=(12, fig_h))
    for node in root.walk():
        for c in node.children:
            ax.plot([node.x, c.x], [c.y, c.y], color="#555", lw=0.6)
            if c in capped:  # break glyph near the capped branch end
                ax.text(c.x - (maxx * 0.006), c.y, "//", fontsize=7, color="#e07b00",
                        va="center", ha="center", fontweight="bold")
        if node.children:
            ys = [c.y for c in node.children]
            ax.plot([node.x, node.x], [min(ys), max(ys)], color="#555", lw=0.6)
    q = 0
    longest_lab = 0
    for t in tips:
        col = role_color(t.name)
        if col == "#c0392b": q += 1
        lab = t.name.replace("_", " ")
        if t in capped:
            lab += f"  [branch {t.length:.2f} ≫, capped]"; col = "#e07b00"
        longest_lab = max(longest_lab, len(lab))
        if aligned:
            ax.plot([t.x, label_x], [t.y, t.y], color="#bbb", lw=0.3, ls=(0, (1, 2)))  # leader
            ax.text(label_x + maxx * 0.005, t.y, lab, va="center", ha="left", fontsize=6, color=col)
        else:  # branch-end (gallery/"before" style): label right at the tip, no leader
            ax.text(t.x + maxx * 0.008, t.y, lab, va="center", ha="left", fontsize=6, color=col)
    for node in root.walk():
        if node.children and node.support:
            m = re.match(r"(\d+\.?\d*)/(\d+\.?\d*)", node.support)
            if m and float(m.group(1)) >= 80 and float(m.group(2)) >= 95:
                ax.plot([node.x], [node.y], marker="o", ms=2.2, color="#2c7fb8")

    # Right margin: leave room for the longest label (rough char-width estimate in data units).
    label_start = label_x if aligned else maxx
    right = label_start + maxx * 0.012 + longest_lab * (maxx * 0.010)
    ax.set_xlim(-maxx * 0.01, right); ax.set_ylim(-1, n)
    ax.invert_yaxis()
    if show_axis:
        # keep only the bottom "substitutions/site" spine; hide the rest and the y ticks.
        ax.set_xlabel("substitutions/site", fontsize=8)
        ax.set_yticks([])
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="x", labelsize=7)
    else:
        ax.axis("off")
    title = a.title or os.path.basename(a.treefile)
    capnote = f" · {len(capped)} branch(es) capped (true length in label)" if capped else ""
    ax.set_title(f"{title}  (n={n} tips · {q} AS/AJS in crimson · rooted on outgroup · "
                 f"blue dot = SH-aLRT≥80 & UFBoot≥95{capnote})", fontsize=9)
    fig.text(0.5, 0.004,
             "MLSA topology (5-locus), rooted on the outgroup and ladderized. Strengthens placement "
             "only; whole-genome ANI delimits species; capped/long branches are flagged, not trusted "
             "(bad reference genome or fragmentation). Class-level; judgment deferred.",
             ha="center", fontsize=6, style="italic", color="#555")
    fig.tight_layout(rect=[0, 0.02, 1, 1])
    fig.savefig(a.out, dpi=_safe_dpi(fig, 200))
    plt.close(fig)
    emit(f"rendered {n} tips (rooted; {len(capped)} capped; labels={a.labels}; "
          f"axis={'on' if show_axis else 'off'}) -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
