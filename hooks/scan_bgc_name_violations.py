#!/usr/bin/env python3
"""Scan strain_data for AS-strain per-BGC files/folders named with a bare BGC<nnn>
and NO node/contig identifier (the wrong-attribution risk the Developer or User flagged 2026-08-06),
plus (v9.7.401) any .md/.csv file whose own CONTENT bare-cites a strain+BGC-number with no
node/contig token, regardless of what the file itself is named.

Non-destructive: reports counts + writes a TSV of violations. Never renames/moves.

v9.7.401 EXTENSION (BC2, ROSTER_401_SEEDS.md item 3 follow-through -- same gap, sibling tool):
this scanner is the offline/census sibling of hooks/bgc_node_name_guard.sh (the live
PostToolUse hook), which had the identical name-only blindness fixed this round. A
generically-named file (e.g. "notes.md") whose BODY cites a bare strain+BGC with no node token
was invisible to a census run of this script, exactly as it was invisible to the live hook --
reproduced live: 0 violations reported for a real, seeded content-only citation. Fixed by
reusing the bundle's own authoritative gate, mamey.bgc_citation_gate.find_nodeless_bgc_citations
(the same logic backing `mamey verify-citations` and the hook's own fix), for a new "CONTENT"
violation kind with a 4th `detail` column (line number + snippet) -- additive to the existing
TSV schema; DIR/FILE rows are unaffected and their existing 3 columns are unchanged in meaning.

Usage:
  python3 scan_bgc_name_violations.py [--root "<strain_data path>"] [--out violations.tsv] [--limit N]
"""
import os, re, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from mamey.bgc_citation_gate import find_nodeless_bgc_citations
except Exception:
    find_nodeless_bgc_citations = None  # fail open: content scan simply skips, name scan unaffected

BGC_RE  = re.compile(r'BGC[_-]?\d{1,4}', re.I)
NODE_RE = re.compile(r'NODE[_-]?\d|contig[_-]?\d|scaffold[_-]?\d|(?:^|[^A-Za-z])tig\d|N[CZ]_\d|CP\d{5}', re.I)
STRAIN_DIR_RE = re.compile(r'(^|/)AS-\d+(/|$)')
# heavy raw dirs we skip (not per-BGC deliverables)
SKIP_DIRS = {"antiSMASH", "__pycache__", ".git", "raw", "raw_json", "blastp_raw"}
CONTENT_SCAN_SUFFIXES = (".md", ".csv")

def in_as_strain_subtree(path, root):
    rel = os.path.relpath(path, root)
    return rel.startswith("AS-") and "/" in rel or bool(STRAIN_DIR_RE.search("/"+rel))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join((os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()), "strain_data"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    root = a.root
    out = a.out or os.path.join(root, "_MIGRATION", "BGC_NAME_VIOLATIONS_2026-08-06.tsv")

    violations = []          # (strain, kind, path, detail)
    per_strain = {}
    # walk only AS-<n> strain dirs at the top of root
    try:
        strain_dirs = sorted(d for d in os.listdir(root) if re.match(r'AS-\d+$', d))
    except FileNotFoundError:
        print(f"root not found: {root}", file=sys.stderr); return 2

    for sd in strain_dirs:
        base = os.path.join(root, sd)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            # folders named by BGC without node
            for d in list(dirnames):
                if BGC_RE.search(d) and not NODE_RE.search(d):
                    violations.append((sd, "DIR", os.path.join(dirpath, d), ""))
                    per_strain[sd] = per_strain.get(sd, 0) + 1
            for f in filenames:
                if BGC_RE.search(f) and not NODE_RE.search(f):
                    violations.append((sd, "FILE", os.path.join(dirpath, f), ""))
                    per_strain[sd] = per_strain.get(sd, 0) + 1
                if find_nodeless_bgc_citations is not None and f.lower().endswith(CONTENT_SCAN_SUFFIXES):
                    fpath = os.path.join(dirpath, f)
                    try:
                        text = open(fpath, encoding="utf-8", errors="replace").read()
                    except OSError:
                        text = ""
                    for ln, line in find_nodeless_bgc_citations(text):
                        violations.append((sd, "CONTENT", fpath, f"line {ln}: {line[:120]}"))
                        per_strain[sd] = per_strain.get(sd, 0) + 1
            if a.limit and len(violations) >= a.limit:
                break
        if a.limit and len(violations) >= a.limit:
            break

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write("strain\tkind\tpath\tdetail\n")
        for s, k, p, detail in violations:
            fh.write(f"{s}\t{k}\t{os.path.relpath(p, root)}\t{detail}\n")

    print(f"VIOLATIONS (bare BGC<nnn>, no node token -- name or content) under AS-strain subtrees: {len(violations)}")
    print(f"  strains affected: {len(per_strain)}")
    top = sorted(per_strain.items(), key=lambda x: -x[1])[:15]
    for s, n in top:
        print(f"    {s}: {n}")
    print(f"  full list -> {out}")

if __name__ == "__main__":
    raise SystemExit(main())
