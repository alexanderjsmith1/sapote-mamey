#!/usr/bin/env python3
"""tree_sanity_check.py — HARD pre-render gate. A tree must PASS this before it is rendered or shown.

Exists because a single pathological branch (a broken/chimeric sequence, or a wrong outgroup) can
dominate the x-scale and visually flatten every real branch — a figure that then looks fine at a glance
but is worthless. This gate FAILS (exit 2) on:

  1. LONG TERMINAL BRANCH  — any terminal branch length > --abs (default 0.25 subs/site) OR
     > --factor x the 90th-percentile terminal length (default 10x). These are bad reads / misalignments.
  2. DOMINATING BRANCH     — the single longest branch is > --dominate of the max root-to-tip depth
     (default 0.50). One branch eating half the tree width is a display-killer (usually a bad outgroup).
  3. NO OUTGROUP           — no tip carries an 'OUTGROUP' token and no --outgroup token or exact
     tip identity was
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


#: Minimum tips before any branch-length statistic in this gate is meaningful (v9.7.416).
MIN_ASSESSABLE_TIPS = 3


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
    """Normalize --outgroup to case-folded tokens or complete tip identities.

    Accepts None, a single string (possibly comma-separated), or a list/tuple of strings, so a
    MULTI-TAXON outgroup clade can be designated. v9.7.406: a two-taxon outgroup is standard
    practice (the fungal registry itself lists a primary AND an alternate, and breaking up a long
    outgroup branch is the textbook long-branch-attraction control) — but a single term could
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
            part = part.strip().casefold()
            if part:
                terms.append(part)
    return terms


def _contains_token_or_identity(name, term):
    """True when ``term`` is bounded on both sides, or equals the complete name.

    Tip-label separators are any non-alphanumeric characters, including the
    underscores normally emitted by phylogeny tools. Requiring both boundaries
    prevents one genus or marker from matching inside a longer word while still
    accepting full tip identities and multi-token terms.
    """
    nm = (name or "").casefold()
    token = (term or "").casefold()
    if not token:
        return False
    start = nm.find(token)
    while start != -1:
        end = start + len(token)
        if ((start == 0 or not nm[start - 1].isalnum())
                and (end == len(nm) or not nm[end].isalnum())):
            return True
        start = nm.find(token, start + 1)
    return False


def _outgroup_marker(name, outgroup=None):
    """Return the marker that made `name` an outgroup tip, or None. v9.7.413: the matched marker is
    reported in the gate output so a TRUNCATED marker ('..._outg' after a fixed-width tip-label cut)
    is visible as an absence rather than degrading silently to 'no exemptions'."""
    if _contains_token_or_identity(name, "outgroup"):
        return "outgroup"
    for term in _outgroup_terms(outgroup):
        if _contains_token_or_identity(name, term):
            return term
    return None


def _is_outgroup_tip(name, outgroup=None):
    """True for a bounded OUTGROUP token or an explicit --outgroup token/identity.

    Matching is case-insensitive and bounded on both sides. Designated outgroups
    anchor the root; they are expected to be the longest branch on a tight
    ingroup and must not be treated as pathological.
    """
    return _outgroup_marker(name, outgroup) is not None


def _all_leaves_outgroup(node, outgroup=None):
    """True iff EVERY descendant leaf of `node` is an outgroup tip (so this branch is the outgroup
    stem or an outgroup tip itself). A mixed clade (root, ingroup+outgroup) is never outgroup-only."""
    lv = list(node.leaves())
    return bool(lv) and all(_is_outgroup_tip(t.name, outgroup) for t in lv)


class MalformedTree(ValueError):
    """The input holds no parseable Newick tree (empty, whitespace-only, or truncated).

    v9.7.416: `parse()` indexed `s[pos]` unguarded, so an EMPTY file raised a bare
    `IndexError: string index out of range` out of a HARD gate whose documented contract is
    "exit 0 = PASS, 2 = FAIL". The process exited 1 with a parser traceback instead. This is not
    hypothetical: BiG-SCAPE writes a 0-byte `<FAM>.newick` for every singleton GCF, and 89 such
    files exist in this workspace, so gating a `GCF_trees/` directory died at the first one. A
    truncated tree ("(A:0.1,B:0.2" — no closing paren) hit the same index, and a genuinely absent
    file raised FileNotFoundError from `open()`. All three are now ONE typed refusal that `check()`
    turns into a normal FAIL, so a sweep reports the bad file and keeps going."""


def parse(t):
    s=open(t).read().strip().rstrip(';').strip();pos=[0]
    if not s:
        raise MalformedTree("file contains no Newick tree (empty or whitespace-only)")
    def at(i):
        # Every read of `s` goes through here: running off the end is a MALFORMED TREE, a verdict
        # this gate can report, not an IndexError the caller has to guess at.
        if i>=len(s):
            raise MalformedTree("truncated Newick: input ended mid-tree "
                                "(unbalanced parentheses, or a partial write?)")
        return s[i]
    def nd():
        n=N()
        if at(pos[0])=='(':
            pos[0]+=1
            while True:
                c=nd();c.p=n;n.k.append(c)
                if at(pos[0])==',':pos[0]+=1;continue
                if at(pos[0])==')':pos[0]+=1;break
                # Neither ',' nor ')' after a child: the old loop re-entered nd() forever on input
                # that never advanced (a HANG in a gate is worse than a crash). Refuse it instead.
                raise MalformedTree(
                    f"malformed Newick at offset {pos[0]}: expected ',' or ')' after a child, "
                    f"found {at(pos[0])!r}")
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


def _no_tree_report(treefile, detail):
    """A FAIL report for input that never became a tree. Deliberately shaped like every other
    FAIL (banner + bracketed class + ACTION) so batch callers and log greps treat it uniformly,
    and deliberately NOT carrying a branch length -- the finding is an ABSENCE, and rendering it
    through the numeric offender formatter would invent a '0.0000' (same reasoning as NO_OUTGROUP).
    """
    return "\n".join([
        f"tree_sanity_check: {treefile}",
        "  ***** FAIL *****",
        "  [NO_TREE]",
        f"     {detail}",
        "  ACTION: this file was never a tree, so nothing about it can be gated. Check that the "
        "upstream inference actually wrote one (a 0-byte file is the usual sign it did not -- "
        "BiG-SCAPE emits one per singleton GCF), then re-run. Do NOT present a figure for it.",
    ])


def check(treefile, abs=0.25, factor=10.0, dominate=0.50, outgroup=None, require_outgroup=True):
    """Reusable HARD sanity gate. Returns (ok: bool, msg: str) — importable by the render tools so
    they can refuse a pathological tree BEFORE drawing. `msg` is the same multi-line report main()
    prints. ok=False (FAIL) when any NON-OUTGROUP terminal branch > max(abs, factor*p90-terminal) OR
    the single longest NON-OUTGROUP branch > `dominate` of the max root-to-tip depth.

    Outgroup awareness: a designated outgroup (tip name contains a bounded 'OUTGROUP' token,
    case-insensitive, or matches an explicit `outgroup` token/identity) is the intended root anchor
    and, on a tight ingroup, is ALWAYS the
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
    if isinstance(treefile, N):
        r = treefile
    else:
        # v9.7.416: a file that holds no usable tree is a GATE VERDICT, not an exception. Before
        # this, an empty/truncated file raised IndexError and a missing one raised FileNotFoundError
        # -- both escaped `check()`, which is documented as "importable by the render tools so they
        # can refuse a pathological tree BEFORE drawing" and therefore must RETURN (False, msg).
        # Callers differ in how they cope: run_planned_tree.py wraps and treats the exception as
        # FAIL, but render_clean_tree.py and phylo_place.py::_graft_sane do not, so the traceback
        # surfaced instead of the actionable refusal. Fails closed either way; this makes it legible.
        try:
            r = parse(treefile)
        except MalformedTree as exc:
            return False, _no_tree_report(treefile, str(exc))
        except OSError as exc:
            return False, _no_tree_report(treefile, f"cannot read the tree file: {exc.strerror}")
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
    # v9.7.416: a tree with fewer than three tips cannot be assessed by ANY check this gate runs,
    # and before this it could report "PASS -- no pathological/dominating branches" on one. Live:
    # a single-tip tree `A_OUTGROUP:0.1;` PASSED -- its only tip is outgroup-exempt from
    # LONG_TERMINAL, and `longest` (max over non-all-outgroup nodes) falls through to its default
    # 0.0, so DOMINATING_BRANCH compares 0.0 > 0.05 and clears. A clean PASS on a tree with no
    # ingroup at all is a vacuous verdict: the gate answered a question it never actually asked.
    # Three tips is the floor for the statistics themselves -- a p90 of one or two terminal
    # branches is that same branch, and root-to-tip depth on a 2-tip tree is one branch.
    # Corpus check before shipping: 18,834 tree files here, of which 23 have <=2 tips and ZERO of
    # those currently PASS (they FAIL NO_OUTGROUP), so no real verdict flips -- this closes a
    # latent hole rather than reclassifying existing results.
    degenerate = len(tips) < MIN_ASSESSABLE_TIPS
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
    if degenerate:
        fails.append(("DEGENERATE_TREE", []))
    elif no_outgroup:
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
        if kind == "DEGENERATE_TREE":
            lines.append(f"     this tree has {len(tips)} tip(s); at least {MIN_ASSESSABLE_TIPS} are "
                         "needed before any branch-length statistic means anything (a p90 over one "
                         "or two terminal branches is just that branch). No check was run — this is "
                         "NOT a clean bill of health.")
            continue
        if kind == "NO_OUTGROUP":
            # Not a branch-length offender: the finding is an ABSENCE, so it carries no length to
            # print. Rendering it through the numeric offender formatter would invent a "0.0000".
            lines.append("     no tip carries an 'OUTGROUP' token and no --outgroup token or exact "
                         "tip identity was "
                         "supplied — the outgroup exemption was never applied")
            # v9.7.415: say that the branch-length classes were skipped. The .413 addendum suppresses
            # them (correctly — un-exempted they flag the undeclared outgroup's own stem), but it did
            # so SILENTLY. Measured on the 168 in-scope EPA-ng/placement trees the engine gates at
            # tools/phylo_place.py: 8 of them carry a genuine LONG_TERMINAL *and* DOMINATING_BRANCH
            # that this report no longer mentions at all. The operator sees "no outgroup marker" and
            # cannot tell whether anything else is wrong. This line does not restore the checks or
            # change any verdict — it states that they did not run, and how to get them.
            # Deliberately lowercase/hyphenated: three shipped tests assert the bare offender tokens
            # are absent from a NO_OUTGROUP report, and they are right to — this notice says these
            # checks did NOT run, which must never read as them firing.
            lines.append("     [branch-length checks SKIPPED] the long-terminal and dominating-branch "
                         "checks did NOT run: without a declared anchor they cannot tell a "
                         "pathological branch from the undeclared outgroup's own stem. Declare the "
                         "outgroup (tag the tip, --outgroup, or --allow-no-outgroup) and re-run to "
                         "get them.")
            continue
        for l, n in sorted(items, reverse=True):
            lines.append(f"     {l:.4f}  {n[:60]}")
    if any(kind == "DEGENERATE_TREE" for kind, _ in fails):
        lines.append("  ACTION: this is a degenerate tree, not a pathological one — there is nothing "
                     "to prune. Confirm the upstream inference kept the taxa you expected (a "
                     "singleton/pair GCF or an over-pruned panel is the usual cause). Do NOT present "
                     "it as a phylogeny.")
    elif any(kind == "NO_OUTGROUP" for kind, _ in fails):
        # Deliberately does NOT offer the pruning remedy: with no declared anchor, any branch listed
        # above may be the legitimate outgroup stem, and pruning it would damage the analysis.
        lines.append("  ACTION: tag the rooting taxon in its tip name (…_OUTGROUP), or pass an "
                     "exact token or complete tip identity with --outgroup at the call site; if "
                     "the tree has no outgroup by "
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
                    help="case-insensitive exact token or complete identity naming an untagged "
                         "outgroup tip; REPEATABLE, and a single "
                         "value may be comma-separated, so a multi-taxon outgroup clade can be "
                         "designated and its stem correctly exempted "
                         "(tips carrying a bounded 'OUTGROUP' token are recognized without this)")
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
