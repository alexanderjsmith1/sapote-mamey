#!/usr/bin/env python3
"""tree_sanity_check.py — HARD pre-render gate. A tree must PASS this before it is rendered or shown.

Exists because a single pathological branch (a broken/chimeric sequence, or a wrong outgroup) can
dominate the x-scale and visually flatten every real branch — a figure that then looks fine at a glance
but is worthless. This gate FAILS (exit 2) on:

  1. LONG TERMINAL BRANCH  — any terminal branch length > --abs (default 0.25 subs/site) OR
     > --factor x the 90th-percentile terminal length (default 10x). These are bad reads / misalignments.
  2. DOMINATING BRANCH     — the single longest branch is > --dominate of the max root-to-tip depth
     (default 0.50). One branch eating half the tree width is a display-killer (usually a bad outgroup).
  3. NO OUTGROUP           — no tip carries the 'OUTGROUP' marker and no --outgroup substring was
     supplied, so the outgroup exemption this gate depends on was never applied. Standing rule
     (2026-09-07): a tree with no recognisable outgroup is itself a gate failure. Declare a
     deliberately outgroup-less tree (midpoint-rooted, or a within-class paralog panel) with
     --allow-no-outgroup; that is a declaration, not a silent degradation.

Exit 0 = PASS, 2 = FAIL (offenders listed with the exact tips to prune or the outgroup to replace).
Advisory judgment items still apply (see signoff_check.py). Class-level; judgment deferred.

Usage: tree_sanity_check.py <tree.treefile> [--abs 0.25] [--factor 10] [--dominate 0.50]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, argparse


class N:
    __slots__=('name','l','k','p')
    def __init__(s): s.name='';s.l=0.0;s.k=[];s.p=None
    def leaves(s):
        if not s.k: yield s
        for c in s.k: yield from c.leaves()
    def walk(s):
        yield s
        for c in s.k: yield from c.walk()


def _outgroup_terms(outgroup=None):
    """Normalize the --outgroup value to a list of lowercase substrings.

    Accepts None, a single string (possibly comma-separated), or a list/tuple of strings, so a
    MULTI-TAXON outgroup clade can be designated. v9.7.406: a two-taxon outgroup is standard
    practice (the fungal registry itself lists a primary AND an alternate, and breaking up a long
    outgroup branch is the textbook long-branch-attraction control) — but a single substring could
    only ever name ONE of them, leaving the clade's leaf set MIXED, so _all_leaves_outgroup() was
    False and the outgroup stem lost the exemption it was always meant to have."""
    if not outgroup:
        return []
    if isinstance(outgroup, (list, tuple, set)):
        raw = list(outgroup)
    else:
        raw = [outgroup]
    terms = []
    for item in raw:
        for part in str(item).split(","):
            part = part.strip().lower()
            if part:
                terms.append(part)
    return terms


def _outgroup_marker(name, outgroup=None):
    """Return the marker that made `name` an outgroup tip, or None. v9.7.413: the matched marker is
    reported in the gate output so a TRUNCATED marker ('..._outg' after a fixed-width tip-label cut)
    is visible as an absence rather than degrading silently to 'no exemptions'."""
    nm = (name or "").lower()
    if "outgroup" in nm:
        return "outgroup"
    for term in _outgroup_terms(outgroup):
        if term in nm:
            return term
    return None


def _is_outgroup_tip(name, outgroup=None):
    """A tip is an outgroup if its name contains 'OUTGROUP' (case-insensitive) or ANY of the
    explicit --outgroup substrings. Designated outgroups anchor the root; they are expected to be
    the longest branch on a tight ingroup and must not be treated as pathological."""
    return _outgroup_marker(name, outgroup) is not None


def _all_leaves_outgroup(node, outgroup=None):
    """True iff EVERY descendant leaf of `node` is an outgroup tip (so this branch is the outgroup
    stem or an outgroup tip itself). A mixed clade (root, ingroup+outgroup) is never outgroup-only."""
    lv = list(node.leaves())
    return bool(lv) and all(_is_outgroup_tip(t.name, outgroup) for t in lv)


def parse(t):
    s=open(t).read().strip().rstrip(';');pos=[0]
    def nd():
        n=N()
        if s[pos[0]]=='(':
            pos[0]+=1
            while True:
                c=nd();c.p=n;n.k.append(c)
                if s[pos[0]]==',':pos[0]+=1;continue
                if s[pos[0]]==')':pos[0]+=1;break
        st=pos[0]
        while pos[0]<len(s) and s[pos[0]] not in '(),:;':pos[0]+=1
        lab=s[st:pos[0]].strip().strip("'\"")
        if not n.k:n.name=lab
        if pos[0]<len(s) and s[pos[0]]==':':
            pos[0]+=1;st=pos[0]
            while pos[0]<len(s) and s[pos[0]] not in '(),;':pos[0]+=1
            try:n.l=float(s[st:pos[0]])
            except ValueError:n.l=0.0
        return n
    return nd()


def check(treefile, abs=0.25, factor=10.0, dominate=0.50, outgroup=None, require_outgroup=True):
    """Reusable HARD sanity gate. Returns (ok: bool, msg: str) — importable by the render tools so
    they can refuse a pathological tree BEFORE drawing. `msg` is the same multi-line report main()
    prints. ok=False (FAIL) when any NON-OUTGROUP terminal branch > max(abs, factor*p90-terminal) OR
    the single longest NON-OUTGROUP branch > `dominate` of the max root-to-tip depth.

    Outgroup awareness: a designated outgroup (tip name contains 'OUTGROUP', case-insensitive, or the
    explicit `outgroup` substring) is the intended root anchor and, on a tight ingroup, is ALWAYS the
    longest branch — so a *correct* sister-genus outgroup used to false-FAIL. Any branch whose
    descendant leaves are ALL outgroup tips is exempted from BOTH the LONG_TERMINAL and
    DOMINATING_BRANCH offender sets and reported as an informational line, never a FAIL. A dominating
    ingroup/query branch (a bad genome) still FAILs.

    v9.7.413 (standing rule, Alex 2026-09-07): with NO recognisable outgroup the gate no longer
    degrades silently to "no exemptions" — it FAILs with NO_OUTGROUP, because the exemption the tree
    depends on was never applied and the operator would otherwise be told to prune a legitimate
    outgroup stem. Two producers were found dropping the marker (a fixed-width tip-label truncation
    severing `_outgroup` to `_outg`, and a rooting taxon that was never tagged), so the absence is a
    real, recurring failure mode rather than a hypothetical one. `require_outgroup=False` is the
    declared exemption for a tree that has no outgroup BY CONSTRUCTION — midpoint-rooted, or a
    within-class paralog panel such as a KS/NRPS domain tree; the declaration is printed, so it is
    auditable rather than silent.

    `treefile` may be a path (read + parsed) or an already-parsed N node (so callers that already
    hold a tree needn't reserialize)."""
    r = treefile if isinstance(treefile, N) else parse(treefile)
    tips = list(r.leaves())
    term = sorted(t.l for t in tips)
    # v9.7.374 (audit lane): `term[int(len(term)*0.9)]` is not the 90th percentile -- for any n
    # where int(n*0.9) lands on n-1 (every n from 1 to 10, and again at exact multiples of 10),
    # this indexes the tree's own ABSOLUTE MAXIMUM terminal branch as "p90". Since `ceil =
    # max(abs, factor*p90)` with the default factor=10, that makes ceil = 10x the tree's own
    # longest branch -- a ceiling no branch can ever exceed, DISABLING the LONG_TERMINAL relative-
    # outlier check entirely for exactly the small/thin trees (n<=10) this project's own sign-off
    # gate calls out for extra caution. Live-reproduced: a 10-tip tree with one genuine 15x local
    # outlier branch (0.15 vs 0.01 siblings) reported p90=0.15 (its own max), ceiling=1.5, and
    # PASSED cleanly (exit 0) -- with DOMINATING_BRANCH also not catching it once the outlier no
    # longer dominates root-to-tip depth (verified with a deep unrelated backbone clade). Nearest-
    # rank 90th-percentile index instead: ceil(0.9*n) - 1, via exact integer arithmetic
    # (9*n + 9)//10 - 1) to avoid float-multiple-of-10 landing back on n-1.
    n_term = len(term)
    p90_idx = max(0, min(n_term - 1, (9 * n_term + 9) // 10 - 1)) if n_term else 0
    p90 = term[p90_idx] if term else 0.0
    ceil = max(abs, factor*p90)
    # max root-to-tip depth
    depth = {}
    def rec(n, acc):
        depth[n] = acc
        for c in n.k: rec(c, acc+c.l)
    rec(r, 0.0)
    maxdepth = (max(depth[t] for t in tips) if tips else 0.0) or 1.0
    # DOMINATING_BRANCH considers only NON-outgroup branches; the outgroup stem is the intended
    # root anchor and is exempt. Track the longest exempted outgroup branch for an info line.
    longest = max(((n.l, n.name or "(internal)") for n in r.walk()
                   if not _all_leaves_outgroup(n, outgroup)), default=(0.0, "(none)"))
    og_exempt = max(((n.l, n.name or "(internal)") for n in r.walk()
                     if _all_leaves_outgroup(n, outgroup)), default=None)

    markers = sorted({m for t in tips
                      if (m := _outgroup_marker(t.name, outgroup)) is not None})

    fails = []
    no_outgroup = not markers and require_outgroup
    # NO_OUTGROUP first: without a declared root anchor, LONG_TERMINAL/DOMINATING_BRANCH cannot
    # reliably tell a pathological branch from the (untagged, or truncated-tag) outgroup stem
    # itself -- exempting nothing is not neutral, it is guessing. v9.7.413 addendum: when
    # NO_OUTGROUP fires, suppress those two branch-length classes entirely rather than run them
    # un-exempted. Without this, the exact rect2 regression this rule exists to catch (a truncated
    # "..._outg" marker) reports NO_OUTGROUP *and* a DOMINATING_BRANCH block flagging that same tip
    # at "100% of tree depth" -- technically not the pruning ACTION text, but the offender block
    # itself still names the real outgroup stem as a branch-length pathology, which is the
    # "misleading DOMINATING_BRANCH on the outgroup's own stem" the standing rule was written to
    # stop (EGGPLANT_413_gate_outgroup_awareness, case H).
    if no_outgroup:
        fails.append(("NO_OUTGROUP", []))
    else:
        # LONG_TERMINAL exempts outgroup tips (a distant sister taxon legitimately has a long branch).
        long_tips = [(t.l, t.name) for t in tips if t.l > ceil and not _is_outgroup_tip(t.name, outgroup)]
        if long_tips:
            fails.append(("LONG_TERMINAL", long_tips))
        if longest[0] > dominate*maxdepth:
            fails.append(("DOMINATING_BRANCH", [(longest[0], longest[1]+f"  ({longest[0]/maxdepth*100:.0f}% of tree depth)")]))

    lines = [f"tree_sanity_check: {len(tips)} tips · terminal p90={p90:.5f} · ceiling={ceil:.5f} · "
             f"max depth={maxdepth:.4f} · longest non-outgroup branch={longest[0]:.4f} ({longest[1][:40]})"]
    lines.append("  [outgroup-marker] matched: " + (", ".join(markers) if markers else
                 "NONE" + ("" if require_outgroup else " (declared outgroup-less: --allow-no-outgroup)")))
    if og_exempt is not None:
        lines.append(f"  [outgroup-exempt] {og_exempt[0]:.4f}  {og_exempt[1][:60]}  "
                     f"(designated outgroup; exempt from LONG_TERMINAL/DOMINATING_BRANCH)")
    if not fails:
        lines.append("  PASS — no pathological/dominating branches.")
        return True, "\n".join(lines)
    lines.append("  ***** FAIL *****")
    for kind, items in fails:
        lines.append(f"  [{kind}]")
        if kind == "NO_OUTGROUP":
            # Not a branch-length offender: the finding is an ABSENCE, so it carries no length to
            # print. Rendering it through the numeric offender formatter would invent a "0.0000".
            lines.append("     no tip carries the 'OUTGROUP' marker and no --outgroup substring was "
                         "supplied — the outgroup exemption was never applied")
            continue
        for l, n in sorted(items, reverse=True):
            lines.append(f"     {l:.4f}  {n[:60]}")
    if any(kind == "NO_OUTGROUP" for kind, _ in fails):
        # Deliberately does NOT offer the pruning remedy: with no declared anchor, any branch listed
        # above may be the legitimate outgroup stem, and pruning it would damage the analysis.
        lines.append("  ACTION: tag the rooting taxon in its tip name (…_OUTGROUP), or pass "
                     "--outgroup <substring> at the call site; if the tree has no outgroup by "
                     "construction (midpoint-rooted, or a within-class paralog panel), declare it "
                     "with --allow-no-outgroup. Check for a TRUNCATED marker ('…_outg') from a "
                     "fixed-width tip-label cut before assuming the tag is missing. Do NOT present "
                     "a FAILing tree.")
    else:
        lines.append("  ACTION: prune the listed tip(s) (bad read/misalignment) or replace the dominating outgroup, "
                     "then rebuild/re-render and re-run this gate. Do NOT present a FAILing tree.")
    return False, "\n".join(lines)


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("treefile")
    ap.add_argument("--abs", type=float, default=0.25, help="absolute terminal-branch ceiling (subs/site)")
    ap.add_argument("--factor", type=float, default=10.0, help="x p90 terminal-branch ceiling")
    ap.add_argument("--dominate", type=float, default=0.50, help="max single-branch fraction of tree depth")
    ap.add_argument("--outgroup", action="append", default=None,
                    help="substring naming an untagged outgroup tip; REPEATABLE, and a single "
                         "value may be comma-separated, so a multi-taxon outgroup clade can be "
                         "designated and its stem correctly exempted "
                         "(tips containing 'OUTGROUP' are always recognized without this)")
    ap.add_argument("--allow-no-outgroup", action="store_true",
                    help="declare a tree that has NO outgroup by construction (midpoint-rooted, or a "
                         "within-class paralog panel); without this a tree with no recognisable "
                         "outgroup FAILs with NO_OUTGROUP (standing rule, v9.7.413)")
    a=ap.parse_args(argv)

    ok, msg = check(a.treefile, abs=a.abs, factor=a.factor, dominate=a.dominate, outgroup=a.outgroup,
                    require_outgroup=not a.allow_no_outgroup)
    emit(msg)
    return 0 if ok else 2


if __name__=="__main__":
    sys.exit(main())
