#!/usr/bin/env python3
"""phylo_postflight.py — validate a FINISHED tree before it becomes a figure.

Companion to phylo_preflight.py. Preflight validates the inputs; postflight validates the output,
and catches the one class of error preflight cannot: a taxon that entered legitimately but lands in
the wrong place. On 2026-08-26 that was AS-XXX — a Streptomyces sitting on a long basal branch in a
Pseudonocardiaceae tree. Alex caught it by eye; check P4 catches it mechanically.

    CHECK  WHAT IT PROVES
    P1     The tree is actually rooted on the declared outgroup (outgroup is a child of the root,
           not buried mid-string). IQ-TREE output order left several trees effectively unrooted.
    P2     Every tip carries a resolvable label — no bare AS-#### with unknown taxonomy.
    P3     Support values are present and parseable (SH-aLRT/UFBoot), and weak nodes are reported.
    P4     No tip's genus contradicts its clade neighbourhood — the misplacement detector.
    P5     Branch-length sanity: flags any tip whose terminal branch is a gross outlier (the
           long-branch signature of a misplaced or low-quality genome).
    P6     Tip count matches the input genome count (nothing silently dropped by the SCG filter).

Usage
-----
    phylo_postflight.py <treefile> [--outgroup SUBSTR] [--genomes-dir DIR] [--json out.json]

Read-only. Exit 0 = clean (warnings allowed), 1 = at least one FAIL.
"""
from __future__ import annotations
import sys, os, re, csv, json, glob, argparse, statistics
from _wbio import atomic_dump_json_owned as _atomic_write_json

# Portable root (see phylo_preflight): env override, else script grandparent, else workstation.
def _data_root():
    """Resolve an explicit data root, an exact CWD data root, or the portable bundle root.

    The CWD check is deliberately exact: do not search parent directories or bind nearby data.
    """
    env = os.environ.get("MAMEY_DATA_ROOT")
    if env:
        return env
    rel = "strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
    if os.path.exists(os.path.join(os.getcwd(), rel)):
        return os.getcwd()
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = _data_root()
SSOT = f"{ROOT}/strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
sys.path.insert(0, os.path.join(ROOT, "Tools"))
try:
    from phylo_preflight import TAXA, FAMILY_LEVEL, rank_of          # single source of truth
except Exception:
    TAXA, FAMILY_LEVEL = {}, {}
    def rank_of(t): return None

def load_tax():
    tax = {}
    if os.path.exists(SSOT):
        for r in csv.DictReader(open(SSOT), delimiter="\t"):
            s = (r.get("strain") or "").strip()
            if s: tax[s] = (r.get("taxonomy") or "").strip()
    return tax

def tips_of(nwk):
    return re.findall(r"[(,]([^(),:]+):", nwk)

def token_genus(tip, tax):
    """Genus (or family token) for a tip label, however it was written."""
    t = tip.replace("_OUTGROUP", "")
    m = re.search(r"(AS-\d+)", t)
    if m:
        s = tax.get(m.group(1), "")
        if s: return s.split()[0]
        # label may already carry the genus, e.g. Streptomyces_AS-XXX_Atta
        head = t.split("_")[0]
        return head if rank_of(head) else None
    head = re.split(r"[_\s.]+", t)[0]
    return head if head[:1].isupper() else None

class Rep:
    def __init__(self): self.items=[]
    def add(self,c,s,m,d=""): self.items.append({"check":c,"status":s,"message":m,"detail":d})
    def fails(self): return [i for i in self.items if i["status"]=="FAIL"]
    def warns(self): return [i for i in self.items if i["status"]=="WARN"]

def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)  # v9.7.412: no silent prefix matching
    ap.add_argument("treefile"); ap.add_argument("--outgroup", default="OUTGROUP")
    ap.add_argument("--genomes-dir", default=""); ap.add_argument("--json", default="")
    ap.add_argument("--placement", action="store_true",
                    help="input is an EPA-ng placement graft; P3 reads per-query LWR + backbone FBP, not tree-wide UFBoot")
    ap.add_argument("--scope", default="", choices=["", "family", "order"],
                    help="rank the tree is scoped at; P4 allows mixed families under --scope order")
    a = ap.parse_args()
    if not os.path.isfile(a.treefile):  # v9.7.412: typed refusal, not FileNotFoundError
        sys.stderr.write(f"INPUT_NOT_FOUND: treefile {a.treefile!r} is not a readable file\n"); sys.exit(2)
    nwk = open(a.treefile).read().strip()
    _tdir = os.path.dirname(os.path.abspath(a.treefile)) or "."
    try:
        _has_jplace = any(f.endswith(".jplace") for f in os.listdir(_tdir))
    except OSError:
        _has_jplace = False
    is_placement = bool(a.placement or _has_jplace
                        or re.search(r"epa_result|placement|graft", os.path.basename(a.treefile), re.I))
    tax = load_tax(); rep = Rep()
    tips = tips_of(nwk)
    if not tips:
        rep.add("P0","FAIL","No tips parsed from newick",a.treefile); _emit(rep,a); sys.exit(1)

    # P1 rooted on the declared outgroup: it must sit at depth 1 from the root
    og = [t for t in tips if a.outgroup.lower() in t.lower()]
    if not og:
        rep.add("P1","FAIL","Declared outgroup not present in the tree",a.outgroup)
    else:
        depth, i, d = None, 0, 0
        pos = nwk.find(og[0])
        for ch in nwk[:pos]:
            if ch == "(": d += 1
            elif ch == ")": d -= 1
        depth = d
        if depth == 1:
            rep.add("P1","PASS","Tree is rooted on the declared outgroup",f"{og[0]} at depth 1")
        else:
            rep.add("P1","FAIL","Tree is NOT rooted on the declared outgroup",
                    f"{og[0]} sits at depth {depth}; re-root before rendering")

    # P2 label resolution.
    # Two different problems used to share one FAIL, which made the check cry wolf on every raw
    # GToTree treefile (GToTree labels tips with the bare accession by design; the renderer maps
    # them afterwards). Split them: a bare id whose taxonomy IS in the SSOT is fine in a raw tree
    # and only blocks a figure; a tip nothing can resolve is the AS-XXX defect and always FAILs.
    unres = sorted({t for t in tips if token_genus(t, tax) is None})
    bare  = [t for t in tips if re.fullmatch(r"AS-\d+", t) and t not in unres]
    if unres:
        rep.add("P2","FAIL","Tips whose taxonomy cannot be resolved at all",
                ", ".join(unres) + "  — fix the SSOT before this tree becomes a figure")
    elif bare:
        rep.add("P2","WARN","Raw GToTree labels — every tip resolves, none are rendered yet",
                f"{len(bare)} bare AS id(s): " + ", ".join(bare[:8]) +
                ("..." if len(bare) > 8 else "") + " — relabel before rendering")
    else:
        rep.add("P2","PASS","Every tip carries a resolvable genus/family",f"{len(tips)} tips")

    # P3 support values
    sup = re.findall(r"\)(\d+\.?\d*)/(\d+\.?\d*):", nwk)
    if not sup and is_placement:
        # An EPA-ng placement graft carries no tree-wide SH-aLRT/UFBoot by construction: queries are
        # placed on a FIXED backbone, so confidence is the per-query likelihood-weight ratio (LWR) plus
        # the reference backbone's own bootstrap support -- NOT an IQ-TREE support tree. Do not FAIL it.
        rep.add("P3","PASS","EPA-ng placement — tree-wide SH-aLRT/UFBoot not applicable",
                "confidence = per-query LWR (placements TSV) + reference backbone bootstrap "
                "(ref.raxml.raxml.support); a placement graft is not an IQ-TREE support tree")
    elif not sup:
        # FAIL, not WARN: the project's standard command always requests -B 1000 -alrt 1000, so a
        # treefile with no SH-aLRT/UFBoot labels is not an unsupported-by-choice tree -- it is an
        # IQ-TREE run that was killed before the bootstrap finished (a foreground timeout mid-run
        # leaves exactly this: correct tip count, ends with ';', no support). That tree looks
        # publishable and is not. Re-run to completion (iqtree.contree is the done-marker).
        rep.add("P3","FAIL","No SH-aLRT/UFBoot support values — bootstrap did not finish",
                "IQ-TREE was almost certainly killed mid-run (e.g. a foreground timeout); "
                "re-run to completion and confirm iqtree.contree exists before rendering")
    else:
        weak = [f"{x}/{y}" for x,y in sup if float(x) < 80 or float(y) < 95]
        rep.add("P3","PASS",f"Support values present on {len(sup)} nodes",
                (f"{len(weak)} weak node(s) (SH-aLRT<80 or UFBoot<95): " + ", ".join(weak[:6])) if weak
                else "all nodes well supported")

    # P4 misplacement detector: genus vs the composition of the ingroup.
    # Scope-aware, because "more than one family" is a defect in a family tree and the whole
    # point of an order tree. Without --scope the check assumes family (the common case) but
    # says so, rather than asserting a misplacement it cannot actually distinguish.
    fams, ords = {}, {}
    for t in tips:
        if a.outgroup.lower() in t.lower(): continue
        g = token_genus(t, tax); rk = rank_of(g) if g else None
        if rk:
            fams.setdefault(rk[0], []).append(t)
            ords.setdefault(rk[1], []).append(t)
    if fams:
        level = (a.scope or "family").lower()
        groups = ords if level == "order" else fams
        major = max(groups, key=lambda k: len(groups[k]))
        odd = {f: v for f, v in groups.items() if f != major}
        if odd:
            rep.add("P4","FAIL",f"Tip(s) whose {level} contradicts the tree's majority {level}",
                    f"majority={major}; " + "; ".join(f"{f}: {', '.join(v)}" for f, v in odd.items()) +
                    "  — this is the AS-XXX signature: wrong tree, long basal branch" +
                    ("" if a.scope else "  (no --scope given; checked at family level — pass "
                                        "--scope order if this is deliberately an order tree)"))
        else:
            detail = f"{len(groups[major])} tips"
            if level == "order" and len(fams) > 1:
                detail += f"; {len(fams)} families within it: " + ", ".join(sorted(fams))
            rep.add("P4","PASS",f"All ingroup tips are {major} ({level} scope)", detail)

    # P5 terminal branch-length outliers
    bl = [(t, float(v)) for t, v in re.findall(r"[(,]([^(),:]+):(\d+\.?\d*(?:[eE]-?\d+)?)", nwk)]
    ing = [(t,v) for t,v in bl if a.outgroup.lower() not in t.lower()]
    if len(ing) >= 5:
        vals = [v for _,v in ing]; med = statistics.median(vals)
        out = [(t,v) for t,v in ing if med > 0 and v > 5*med]
        rep.add("P5","WARN" if out else "PASS","Terminal branch-length outliers",
                "; ".join(f"{t} ({v:.3f} = {v/med:.1f}x median)" for t,v in out) if out
                else f"median {med:.4f}, no tip >5x")

    # P6 tip count vs input genomes
    if a.genomes_dir:
        n_in = len(glob.glob(os.path.join(a.genomes_dir,"*.fna")))
        if n_in and n_in != len(tips):
            rep.add("P6","WARN","Tip count differs from input genome count",
                    f"{len(tips)} tips vs {n_in} genomes — genomes dropped by the SCG filter?")
        else:
            rep.add("P6","PASS","Tip count matches input genomes",f"{len(tips)}")

    _emit(rep,a); sys.exit(1 if rep.fails() else 0)

def _emit(rep,a):
    print(f"=== phylo_postflight: {os.path.basename(a.treefile)} ===")
    for i in rep.items:
        print({"PASS":"  ok ","WARN":"  ~  ","FAIL":" FAIL"}[i["status"]] + f" [{i['check']}] {i['message']}")
        if i["detail"] and i["status"]!="PASS": print(f"        {i['detail']}")
    nf,nw = len(rep.fails()), len(rep.warns())
    print(f"--- {len(rep.items)-nf-nw} pass / {nw} warn / {nf} FAIL ---")
    if nf: print("    DO NOT PUBLISH this figure until FAILs are resolved.")
    if a.json:
        _atomic_write_json(rep.items, a.json, owner_dir=os.path.dirname(os.path.abspath(a.json)), indent=1)

if __name__ == "__main__":
    main()
