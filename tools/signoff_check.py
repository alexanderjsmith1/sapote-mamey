#!/usr/bin/env python3
"""signoff_check.py — the "would a master's student sign off?" gate, mechanised.

Folded into the Sapote-Mamey bundle (FA4, prototype) from the session tool
`Tools/signoff_check.py`. ADVISORY ONLY: it never blocks and always exits 0.
It mechanises the OBJECTIVE items of the analysis sign-off gate (CLAUDE.md,
"Analysis sign-off gate") so a human/Claude does not have to catch them by hand;
the JUDGMENT items (outgroup *choice*, comparator provenance, host traceability)
still need an eye and are printed as reminders.

Scope: phylogeny artefacts only (Newick `*.treefile` / `*_relabeled.treefile`).
It reads a tree, it does not run the tree — no engine import, no package needed.

Objective checks on a Newick tree:
  1. Outgroup present      — at least one tip tagged _OUTGROUP / (outgroup)
  2. Rogue-taxon guard     — no non-Actinomycetota contaminant as a tip
                             (the E. coli-as-S.-griseus / wrong-accession catch)
  3. Label integrity       — no contig/assembly cruft leaked into tip labels
  4. Duplicate / bare tips  — a truncated strain designation signature
  5. Branch support        — internal-node support values are present
  6. Sampling depth        — flag thin trees (< 12 tips) for cautious reading

Usage:
  signoff_check.py [--minutes N] [--root DIR] [--quiet-if-clean] [FILE ...]
With no FILE, scans --root (default: current working directory) for tree files
modified in the last N minutes. Exit code is ALWAYS 0 (advisory).
"""
import sys, os, re, time, glob
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

CRUFT = re.compile(r'(ctg|contig|scaffold|node|assembly|shotgun|BV-?BRC|\.fna|whole_genome)', re.I)
OUTGROUP = re.compile(r'(?<![A-Za-z0-9])outgroup(?![A-Za-z0-9])', re.I)


def _outgroup_terms(outgroup=None):
    """Normalize --outgroup to case-folded tokens or complete identities — PARITY with
    tree_sanity_check._outgroup_terms() (v9.7.406 made that flag repeatable / comma-separated for
    multi-taxon outgroup clades). Accepts None, a string, a comma-separated string, or a sequence."""
    if not outgroup:
        return []
    raw = list(outgroup) if isinstance(outgroup, (list, tuple, set)) else [outgroup]
    terms = []
    for item in raw:
        for part in str(item).split(","):
            part = part.strip().casefold()
            if part:
                terms.append(part)
    return terms


def _contains_token_or_identity(name, term):
    """Mirror the hard gate's case-insensitive, two-sided boundary rule."""
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


def _is_outgroup_tip(name, outgroup=None):
    """Mirror tree_sanity_check.check(): a tip is an outgroup if its name carries a bounded
    'OUTGROUP' token OR matches an explicit `outgroup` token/identity, case-insensitively. Keeps this advisory gate in parity
    with the HARD tree_sanity gate, so the two never disagree about which tip is the outgroup — a
    correct-but-untagged sister taxon named to tree_sanity via --outgroup must not be reported here
    as 'no outgroup present'.

    v9.7.407 REPAIR: .406 made tree_sanity_check's --outgroup repeatable but left this mirror
    single-valued, so the same tree with the same flags PASSED the hard gate and FAILED here —
    exactly the disagreement this function exists to prevent."""
    if _contains_token_or_identity(name, "outgroup"):
        return True
    return any(_contains_token_or_identity(name, term) for term in _outgroup_terms(outgroup))
# common non-Actinomycetota contaminants / wrong-accession downloads that must never
# appear as a tip in an actinomycete tree (the 2026-07-23 E. coli-as-S.-griseus catch)
NONTARGET = re.compile(r'\b(Escherichia|Salmonella|Klebsiella|Pseudomonas|Bacillus|Staphylococcus|'
                       r'Enterococcus|Acinetobacter|Vibrio|Clostridium|Listeria|Shigella|Yersinia|'
                       r'Campylobacter|Helicobacter|Neisseria|Haemophilus|Saccharomyces|Homo|coli)\b', re.I)
# Metagenome-assembled bins and unclassified placeholders. A named blocklist can
# never cover these — an uncultivated MAG has no genus to blocklist. Caught by
# SHAPE instead: an alphanumeric bin code, or a GTDB `spNNNNNNN` placeholder
# where a species epithet belongs. (The 2026-07-28 CAJCJE01_sp963818685 catch —
# a Candidatus Melainabacteria MAG sitting in a Pseudonocardiaceae tree.)
MAGLIKE = re.compile(r'(^[A-Z]{4,}\d{2,}[_ ]|[_ ]sp\d{6,}|Candidatus|'
                     r'metagenome|uncultured|[_ ]bin[_ .]?\d+)', re.I)
# Portable default: scan the current working directory. Override with --root.
ROOT_DEFAULT = os.getcwd()

# v9.7.412 (Razzle Dazzle Rose): the scan used to be `glob("**/*.treefile", recursive=True)` from
# --root, which defaults to cwd. The shipped Stop hook runs it from the WORKSPACE root on every
# turn-end of every chat, so each call crawled the entire workspace (an 18 GB tree here: conda envs,
# an 18 GB reference-genome pool, BiG-SCAPE, GTDB, wheelhouses) — ~2 min at ~50% CPU per call, and
# with many chats ending turns together they stacked (3 observed at once, load avg 39/179/143,
# fseventsd at 90% CPU). Tree artefacts never live under those subtrees. This bounded walk prunes
# them by name (extend with SIGNOFF_PRUNE_DIRS, comma-separated) and returns the same result set.
PRUNE_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "envs", "site-packages",
    "miniconda3", "anaconda3", "conda", "Wheelhouse", "wheels", "wheelhouse",
    "reference_genomes", "gtotree_gtdb", "GTDB", "gtdb", "BigSCAPE", "BiG-SCAPE", "blastp_db",
    "databases", "Pfam", "pfam", ".Trash",
} | {d.strip() for d in os.environ.get("SIGNOFF_PRUNE_DIRS", "").split(",") if d.strip()})
TREE_SUFFIXES = (".treefile",)


def find_recent_trees(root, minutes, prune=PRUNE_DIRS):
    """Tree artefacts (*.treefile) under `root` modified in the last `minutes`, via a pruned walk.
    Directories named in `prune` are never descended (in-place dirs[:] edit), so a workspace-root
    scan touches only the folders that can hold trees. Sorted, de-duplicated absolute paths."""
    cutoff = time.time() - float(minutes) * 60
    found = set()
    def scan_error(exc):
        raise exc

    for dirpath, dirnames, filenames in os.walk(root, onerror=scan_error):
        dirnames[:] = [d for d in dirnames if d not in prune and not d.startswith(".")]
        for name in filenames:
            if name.endswith(TREE_SUFFIXES):
                f = os.path.join(dirpath, name)
                if os.path.getmtime(f) >= cutoff:
                    found.add(os.path.abspath(f))
    return sorted(found)

CHECKLIST_REMINDERS = [
    "outgroup is a genuine SISTER group (same family, one rank out) — not a distant taxon",
    "ANI within ~1% of 95% = boundary/indeterminate, NOT confident same-species; AAI != ANI",
    "draft/fragmented assemblies get a caption flag (branch lengths untrustworthy)",
    "one documented comparator-selection criterion; 'closest = sibling query' is circular",
    "host/provenance traces to the authoritative strain table, not a folder label",
    "class-level hypotheses, judgment deferred — no bioactivity/structure claims",
]


def leaves(nwk):
    return re.findall(r'[(,]([^(),:]+):', nwk)


def internal_labels(nwk):
    # support labels sit as )LABEL: after a clade close
    return re.findall(r'\)([^(),:;]+):', nwk)


def check_tree_text(nwk, outgroup=None):
    """Objective checks on the text of one Newick tree.

    Returns (tips, issues, notes). `issues` are things a master's student would
    send back (contaminant tip, no support, cruft); `notes` are cautions
    (thin tree, missing strain designation). Pure/importable for tests.

    `outgroup`: optional exact token or complete tip identity naming an untagged outgroup, matching
    tree_sanity_check's --outgroup, so both gates recognize the same root anchor.
    """
    tips = leaves(nwk)
    issues, notes = [], []
    # v9.7.416: an EMPTY or unparseable file yields zero tips, and every check below then passes
    # vacuously -- the report read "x <file> (n=0) ... ~ thin tree (n=0) - report low-support nodes
    # cautiously", which describes a SMALL TREE. There was no tree. The advisory gate never said the
    # word "empty", so an operator sweeping a directory (89 zero-byte .newick files exist here, one
    # per BiG-SCAPE singleton GCF) saw ordinary QC cautions instead of "this file holds no tree".
    # Return immediately: the downstream checks cannot say anything true about an absent tree.
    if not tips:
        issues.append("file holds NO TREE (no tips parsed — empty, truncated, or not Newick); "
                      "nothing below could be checked. This is an ABSENCE, not a thin tree.")
        return tips, issues, notes
    if not any(_is_outgroup_tip(t, outgroup) for t in tips):
        issues.append("no _OUTGROUP-tagged tip found (unrooted or outgroup not marked)")
    cruft = sorted({t for t in tips if CRUFT.search(t)})
    if cruft:
        issues.append(f"{len(cruft)} tip(s) with contig/assembly cruft: {cruft[:3]}{'...' if len(cruft) > 3 else ''}")
    rogue = sorted({t for t in tips if NONTARGET.search(t.replace('_', ' '))})
    if rogue:
        issues.append(f"ROGUE non-target taxon as tip (wrong/contaminant genome?): {rogue}")
    mags = sorted({t for t in tips if MAGLIKE.search(t)})
    if mags:
        issues.append(f"MAG / unclassified bin as tip (no named organism — verify it belongs): {mags}")
    # Two tips that read the same are unreadable and usually mean a strain
    # designation was truncated away (the 2026-07-26 'antibioticus DSM' catch).
    dupes = sorted({t for t in tips if tips.count(t) > 1})
    if dupes:
        issues.append(f"DUPLICATE tip label(s) — strain designation lost?: {dupes}")
    # A bare 'Genus species' with no strain, alongside a sibling that has one,
    # is the truncation signature even when the labels are not yet identical.
    bare = sorted({t for t in tips
                   if re.match(r'^[A-Z][a-z]+_[a-z]+$', t) and not _is_outgroup_tip(t, outgroup)})
    if bare:
        notes.append(f"tip(s) with no strain designation: {bare[:4]}"
                     f"{'...' if len(bare) > 4 else ''}")
    # More than one AUTO-named "_OUTGROUP" tip: usually a leftover from an earlier
    # staging (the 2026-07-29 Streptosporangium_roseum_OUTGROUP-next-to-a-real-
    # Nocardiopsis-outgroup catch). Scoped to name-based auto-detection only — an
    # operator-designated multi-taxon outgroup CLADE (v9.7.406, `--outgroup` given
    # more than once) legitimately matches several tips by design, so it must not
    # trip this check (v9.7.407: the parity repair fixed the genus-mismatch false
    # positive but left this sibling check counting explicit matches too, which
    # fired on every correct multi-outgroup designation — reproduced live).
    auto_ogs = sorted({t for t in tips if OUTGROUP.search(t or "")})
    if len(auto_ogs) > 1:
        issues.append(f"{len(auto_ogs)} tips tagged _OUTGROUP (expected 1) by name: {auto_ogs}")
    ogs = sorted({t for t in tips if _is_outgroup_tip(t, outgroup)})
    # An _OUTGROUP tip that shares its genus with an ingroup tip is not an
    # outgroup at all — it is an ingroup member mislabelled, so the tree is
    # effectively unrooted while looking rooted.
    ingroup_genera = {t.split('_')[0] for t in tips if not _is_outgroup_tip(t, outgroup)}
    mis = sorted({t for t in ogs if t.split('_')[0] in ingroup_genera})
    if mis:
        issues.append(f"_OUTGROUP tip whose genus is also in the ingroup (not a true outgroup): {mis}")
    # Same assembly present as both GCA_ and GCF_ (RefSeq mirror of GenBank): the
    # numeric accession core is identical. Keeps the tree from double-weighting one genome.
    acc = {}
    for t in tips:
        m = re.search(r'GC[AF][_.](\d+)', t)
        if m:
            acc.setdefault(m.group(1), []).append(t)
    twins = {k: v for k, v in acc.items() if len(v) > 1}
    if twins:
        ex = next(iter(twins.values()))
        issues.append(f"{len(twins)} assembly(ies) present as both GCA and GCF (duplicate genome): e.g. {sorted(ex)}")
    sup = [s for s in internal_labels(nwk) if re.search(r'\d', s)]
    if not sup:
        issues.append("no internal-node support values detected")
    if len(tips) < 12:
        notes.append(f"thin tree (n={len(tips)}) — report low-support nodes cautiously")
    return tips, issues, notes


def check_tree(path, outgroup=None):
    """Read a Newick file and run check_tree_text on it."""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return check_tree_text(fh.read(), outgroup=outgroup)


def main():
    args = sys.argv[1:]
    minutes, root, quiet, files, outgroup = 90, ROOT_DEFAULT, False, [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--minutes": i += 1; minutes = float(args[i])
        elif a == "--root": i += 1; root = args[i]
        elif a == "--outgroup":
            i += 1
            # REPEATABLE (v9.7.407): accumulate, never overwrite — a second --outgroup used to
            # silently discard the first, which is how the .406 parity break went unnoticed.
            outgroup = (outgroup or []) + [args[i]]
        elif a == "--quiet-if-clean": quiet = True
        else: files.append(a)
        i += 1

    if not files:
        try:
            files = find_recent_trees(root, minutes)
        except OSError as exc:
            emit(f"signoff_check: inspection incomplete ({type(exc).__name__}: {exc}); no clean-check conclusion.")
            return 0  # advisory, but incomplete must remain visible even in quiet mode

    if not files:
        if not quiet:
            emit("signoff_check: no recent tree artefacts to check.")
        return 0

    any_issue = False
    lines = []
    for f in files:
        try:
            tips, issues, notes = check_tree(f, outgroup=outgroup)
        except Exception as e:
            any_issue = True
            lines.append(f"  ? {os.path.relpath(f, root)} — could not parse ({e})")
            continue
        rel = os.path.relpath(f, root)
        if issues:
            any_issue = True
            lines.append(f"  x {rel} (n={len(tips)})")
            for it in issues: lines.append(f"      - {it}")
        else:
            lines.append(f"  ok {rel} (n={len(tips)}) — objective checks pass")
        for n in notes: lines.append(f"      ~ {n}")

    if quiet and not any_issue:
        return 0
    emit("=== signoff_check: master's-student QC gate (advisory) ===",
         "\n".join(lines),
         "  Judgment items to eyeball (not machine-checkable):", sep="\n")
    for r in CHECKLIST_REMINDERS:
        emit(f"      - {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
