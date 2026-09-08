#!/usr/bin/env python3
"""
bigscape_family_domains.py

Surface, for one or more BiG-SCAPE gene cluster families, the Pfam domain content of the
member BGCs and the family's FastTree phylogeny — the two things needed to *verify* a
novelty call. BiG-SCAPE stores its own Pfam-A scan in the `hsp` table (accession = PF#####,
the same models antiSMASH uses for Pfam annotation) and the per-family tree in `family.newick`.

Given a novel family (no MIBiG anchor), coherent recognizable machinery (a real halogenase,
lanthipeptide cyclase, siderophore synthetase...) plus a well-supported tree is what
distinguishes a genuine novel-architecture candidate from an annotation gap.

Outputs (per family): a TSV of Pfam accession · #member-BGCs-carrying-it, and — if
--newick-dir is given — the family's Newick tree with leaves relabelled strain:NODE.region
(MIBiG leaves labelled MIBiG:BGCxxxxxxx).

Usage:
  # a specific family by id
  python tools/bigscape_family_domains.py --db X.db --family 12646
  # every NOVEL cross-strain family at a cutoff, domains only
  python tools/bigscape_family_domains.py --db X.db --cutoff 0.5 --novel-only --out-dir fam_domains/
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, sqlite3, sys, collections
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import (
    NamespaceError, build_family_identity, normalize_cutoff, normalize_run_id,
    parse_family_identity, public_error, strain_from_gbk_name,
)

LOCNODE = re.compile(r"_(NODE_\d+)_")

# Conservative annotation for the biosynthetically diagnostic Pfams (extend as needed).
PFAM = {
    "PF00109": "KS (ketosynthase, PKS)", "PF02801": "KS-C (ketosynthase C-term)",
    "PF00698": "AT (acyltransferase)", "PF08659": "KR (ketoreductase)", "PF00550": "ACP/PCP carrier",
    "PF00975": "TE (thioesterase)", "PF00668": "C (condensation, NRPS)", "PF00501": "A (adenylation, NRPS)",
    "PF01494": "FAD-binding (flavin-dependent halogenase)", "PF04055": "Radical SAM",
    "PF01266": "FAD oxidoreductase (HCN-synthase signature)", "PF05147": "LanC (lanthipeptide cyclase)",
    "PF04738": "LanB dehydratase N", "PF14028": "LanB dehydratase C",
    "PF04183": "IucA/IucC (NIS siderophore synthetase)", "PF06276": "FhuF-like siderophore reductase",
}


def label(c, recid):
    r = c.execute("select g.path from bgc_record br join gbk g on g.id=br.gbk_id where br.id=?",
                  (int(recid),)).fetchone()
    if not r:
        return f"rec{recid}"
    b = os.path.basename(r[0])
    if b.upper().startswith("BGC"):
        return "MIBiG:" + b.split(".")[0]
    n = LOCNODE.search(b)
    return f"{strain_from_gbk_name(b)}.{n.group(1) if n else ''}"


def domains_for_record(c, recid):
    r = c.execute("select gbk_id, nt_start, nt_stop from bgc_record where id=?", (recid,)).fetchone()
    if not r:
        return []
    gid, a, b = r
    return [x for (x,) in c.execute(
        "select h.accession from hsp h join cds cd on cd.id=h.cds_id "
        "where cd.gbk_id=? and cd.nt_start>=? and cd.nt_stop<=? order by cd.nt_start, h.env_start",
        (gid, a, b))]


def relabel_newick(c, nw):
    return re.sub(r"(?<![.\d])(\d{1,7})(?=:)", lambda m: '"' + label(c, m.group(1)) + '"', nw)


def families(c, run_id, cutoff, novel_only, qualified_one):
    selected_run = normalize_run_id(run_id)
    selected_cutoff = normalize_cutoff(cutoff)
    selected_identity = parse_family_identity(qualified_one) if qualified_one else None
    if selected_identity and (selected_identity.run_id != selected_run or selected_identity.normalized_cutoff != selected_cutoff):
        raise NamespaceError("QUALIFIED_COMPONENT_MISMATCH", "family selector does not match requested run and cutoff")
    q = """select fam.cutoff, fam.id, fam.newick, br.id, g.path
           from bgc_record_family rf join family fam on fam.id=rf.family_id
           join bgc_record br on br.id=rf.record_id join gbk g on g.id=br.gbk_id
           where fam.run_id=?"""
    fam = collections.defaultdict(lambda: {"members": [], "newick": None, "mibig": 0})
    for cut, fid, nw, recid, path in c.execute(q, (selected_run,)):
        identity = build_family_identity(selected_run, cut, fid)
        if identity.normalized_cutoff != selected_cutoff:
            continue
        if selected_identity is not None and identity != selected_identity:
            continue
        b = os.path.basename(path)
        d = fam[identity]; d["newick"] = nw
        d["members"].append((recid, b))
        if b.upper().startswith("BGC"):
            d["mibig"] += 1
    for identity, d in fam.items():
        strains = set(strain_from_gbk_name(b) for _, b in d["members"]
                      if not b.upper().startswith("BGC"))
        if len(strains) < 2:
            continue
        if novel_only and d["mibig"] > 0:
            continue
        yield identity, d, strains


def main():
    ap = argparse.ArgumentParser(description="Surface Pfam domains + tree per BiG-SCAPE family")
    ap.add_argument("--db", required=True)
    ap.add_argument("--qualified-family", default=None, help="a complete qualified_family_id")
    ap.add_argument("--cutoff", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--novel-only", action="store_true")
    ap.add_argument("--out-dir", default=None, help="write per-family domain TSVs + .newick here")
    a = ap.parse_args()

    c = sqlite3.connect(a.db)
    selected = list(families(c, a.run_id, a.cutoff, a.novel_only, a.qualified_family))
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)

    n = 0
    for identity, d, strains in selected:
        n += 1
        dom = collections.Counter()
        for recid, b in d["members"]:
            if b.upper().startswith("BGC"):
                continue
            for x in sorted(set(domains_for_record(c, recid))):   # sorted: most_common() tie order in the printed report
                dom[x] += 1
        status = "NOVEL" if d["mibig"] == 0 else f"KNOWN({d['mibig']} ref)"
        # v9.7.405 rebase: the run-qualified identity must reach BOTH the printed header and the
        # OUTPUT FILENAMES. The upstream hunk rejected here, and a partial application is the
        # dangerous state: the file above already builds qualified identities, so leaving these
        # three sites on the bare `fid` would emit run-ambiguous filenames from a tree that
        # otherwise believes it is namespace-guarded — two BiG-SCAPE runs would silently
        # overwrite each other's family_<id>_domains.tsv.
        header = (f"family {identity.family_id} [{status}] {len(strains)} strains: "
                  f"{','.join(sorted(strains))} | {identity.qualified_family_id}")
        emit(f"# {header}")
        for acc, cnt in dom.most_common():
            emit(f"  {acc}\t{PFAM.get(acc, '(other/uncharacterized)')}\t{cnt}")
        if a.out_dir:
            safe_identity = quote(identity.qualified_family_id, safe="")
            with open(os.path.join(a.out_dir, f"family_{safe_identity}_domains.tsv"), "w") as fh:
                fh.write("# " + header + "\npfam\tfunction\tn_bgcs\n")
                for acc, cnt in dom.most_common():
                    fh.write(f"{acc}\t{PFAM.get(acc, '(other/uncharacterized)')}\t{cnt}\n")
            if d["newick"]:
                with open(os.path.join(a.out_dir, f"family_{safe_identity}.newick"), "w") as fh:
                    fh.write(relabel_newick(c, d["newick"]))
    emit(f"# {n} families reported", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        sys.exit(2)
