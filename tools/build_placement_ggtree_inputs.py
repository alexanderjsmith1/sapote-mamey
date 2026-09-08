#!/usr/bin/env python3
"""build_placement_ggtree_inputs.py — the MISSING producer for tools/ggtree_placement.R.

ggtree_placement.R (shipped) renders a paper-ready EPA-ng placement figure from a pruned newick + an
annotation TSV, but its documented producer (an older unpackaged producer script) was never packaged into the bundle
— the R renderer was orphaned (consumer without producer). This restores the contract end-to-end.

From a grafted placement newick (phylo_place.py report → epa_result.newick) it:
  * classifies tips as query (AS/SID id) / outgroup / reference,
  * prunes to each query + its N nearest reference tips (patristic distance; the prune ladder),
  * writes <prefix>_pruned.nwk and <prefix>_ggtree_annotation.tsv with the columns ggtree_placement.R
    expects: tip, kind, as_id, host, region, accession, validation, label_withloc, label_noloc, ref_label.
Query host + GenBank 16S accession come from a strain table (default: the paper strain table /
OFFICIAL_DATA/STRAIN_METADATA.tsv); reference labels drop the redundant ingroup genus, keep the accession.

Usage:
  Tools/bin/python3 tools/build_placement_ggtree_inputs.py \
      --graft <epa_result.newick> --group Actinomadura --neighbors 3 \
      --host-table "September 6 2026/HOST_METADATA_CLEANED_2026-09-06.tsv" \
      --out-prefix <dir>/Actinomadura
Then:
  Rscript tools/ggtree_placement.R <prefix>_pruned.nwk <prefix>_ggtree_annotation.tsv <out> noloc

Needs biopython -> run with Tools/bin/python3. 16S = anchor/neighbourhood, not a species call; judgment deferred.
"""
import argparse, csv, os, re, sys


def _asid(n):
    m = re.search(r"AS[_-]?(\d+)", n or "")
    return f"AS-{m.group(1)}" if m else (n or "")


def _is_query(n):
    return bool(re.match(r"^(AS|SID)[-_]?\d", n or ""))  # anchored: query tip STARTS with the id; not an embedded "AS 4.xxxx" culture code (F4)


def _find_host_table(explicit):
    if explicit and os.path.exists(explicit):
        return explicit
    root = os.environ.get("SAPOTE_WORKSPACE_ROOT", "")
    cands = []
    if root:
        cands.append(os.path.join(root, "OFFICIAL_DATA", "STRAIN_METADATA.tsv"))
    d = os.getcwd()
    for _ in range(9):
        cands.append(os.path.join(d, "OFFICIAL_DATA", "STRAIN_METADATA.tsv"))
        d = os.path.dirname(d) or d
    for c in cands:
        if os.path.exists(c):
            return c
    return ""


def _load_hosts(path):
    """Return {AS-id: {host, region, acc}} from a strain table. Accepts the paper strain table
    (Host / Location / Strain Number / Genbank Accession) or STRAIN_METADATA.tsv (host_raw / location /
    tip_label / genbank_accession)."""
    hosts = {}
    if not path or not os.path.exists(path):
        return hosts
    with open(path) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            sid = (row.get("Strain Number") or row.get("tip_label") or row.get("strain") or "").strip()
            if not sid:
                continue
            host = (row.get("Host") or row.get("host_raw") or row.get("host_common") or "").strip()
            region = (row.get("Location") or row.get("location") or "").strip()
            acc = (row.get("Genbank Accession") or row.get("genbank_accession") or "").strip()
            hosts[_asid(sid)] = {"host": host, "region": region,
                                 "acc": ("" if acc.upper() in ("", "N/A") else acc)}
    return hosts


def _load_origins(path):
    """Return {"genus species".lower(): category} from a type-strain isolation-source TSV."""
    import csv as _csv
    out = {}
    if path and os.path.exists(path):
        with open(path) as fh:
            for row in _csv.DictReader(fh, delimiter="\t"):
                ts = (row.get("type_strain") or "").strip().lower()
                cat = (row.get("category") or "").strip()
                if ts and cat:
                    out[ts] = cat
    return out

def _species_of(name):
    p = (name or "").replace("_", " ")
    p = __import__("re").sub(r"^[A-Z]{2}[ _]?\d+(?:[ _.]?\d+)?\s+", "", p)
    m = __import__("re").match(r"([A-Z][a-z]+\s+[a-z]+)", p)
    return m.group(1).lower() if m else ""

def _ref_label(name, modal):
    p = (name or "").replace("_", " ")
    acc = ""
    m = re.match(r"\s*([A-Z]{2})\s?(\d+)(?:\s+(\d+))?\s+(.*)", p)
    rest = p
    if m:
        acc = m.group(1) + m.group(2) + ("." + m.group(3) if m.group(3) else "")
        rest = m.group(4)
    rest = re.sub(r"\s+16S.*$", "", rest)
    rest = re.sub(r"\s+strain[: ]+", " ", rest)
    toks = rest.split()
    if toks and modal and toks[0].lower() == modal.lower():
        toks[0] = toks[0][0] + "."
    lab = " ".join(toks)[:34]
    return (lab + f" ({acc})") if acc else lab




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
    ap.add_argument("--graft", required=True, help="grafted placement newick (epa_result.newick)")
    ap.add_argument("--group", default="cohort")
    ap.add_argument("--neighbors", type=int, default=3, help="N nearest reference tips kept per query")
    ap.add_argument("--host-table", default="", help="strain table (paper table or STRAIN_METADATA.tsv); auto-located")
    ap.add_argument("--outgroup-substr", default="outgroup",
                    help="substring identifying the outgroup tip (also matched: a genus != the modal ingroup genus)")
    ap.add_argument("--keep-all-refs", action="store_true")
    ap.add_argument("--family-level", action="store_true",
                    help="multi-genus (family) tree: prune/label every genus normally; only the "
                         "registry outgroup tip is treated as outgroup (keeps full genus names).")
    ap.add_argument("--origin-table", default="", help="TSV: type_strain\tcategory — colors reference tips by isolation origin")
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args()
    _require_readable(a.graft, "--graft")
    _require_writable_parent(a.out_prefix + "_pruned.nwk", "--out-prefix")

    t, tips = _read_tree_or_refuse(a.graft)
    from Bio import Phylo  # reader helper has already verified this dependency; writer also needs it

    def genus(x):
        pp = re.sub(r"^\s*[A-Z]{2}[ _]?\d+(?:[ _.]?\d+)?\s+", "", (x.name or "").replace("_", " "))
        m = re.match(r"([A-Za-z]+)", pp)
        return m.group(1) if m else ""

    q = [x for x in tips if _is_query(x.name)]
    non_q = [x for x in tips if not _is_query(x.name)]
    import collections
    genera = collections.Counter(genus(x) for x in non_q if genus(x))
    modal = genera.most_common(1)[0][0] if genera else ""
    # on a family tree keep full genus names (many genera → an initial like "A." is ambiguous);
    # on a single-genus tree drop the redundant modal genus to its initial.
    lab_modal = "" if a.family_level else modal

    def is_og(x):
        n = (x.name or "").lower()
        if a.family_level:
            # family-level (multi-genus) tree: ONLY the true registry outgroup is an outgroup;
            # every other genus is a legitimate reference to be pruned/labelled normally.
            return a.outgroup_substr.lower() in n
        return (a.outgroup_substr.lower() in n) or (genus(x) and genus(x) != modal)

    og = [x for x in non_q if is_og(x)]
    refs = [x for x in non_q if x not in og]

    if not a.keep_all_refs and q:
        keep = set(id(x) for x in q) | set(id(x) for x in og)
        for qq in q:
            for r in sorted(refs, key=lambda r: t.distance(qq, r))[:max(1, a.neighbors)]:
                keep.add(id(r))
        for x in list(refs):
            if id(x) not in keep:
                try:
                    t.prune(x)
                except Exception:
                    continue  # tip absent from tree — skip (best-effort prune)

    hosts = _load_hosts(_find_host_table(a.host_table))
    origins = _load_origins(a.origin_table)
    nwk_out = a.out_prefix + "_pruned.nwk"
    ann_out = a.out_prefix + "_ggtree_annotation.tsv"
    Phylo.write(t, nwk_out, "newick")
    hdr = ["tip", "kind", "as_id", "host", "region", "accession", "validation",
           "label_withloc", "label_noloc", "ref_label", "origin"]
    with open(ann_out, "w") as out:
        out.write("\t".join(hdr) + "\n")
        for x in t.get_terminals():
            n = x.name
            if _is_query(n):
                aid = _asid(n); h = hosts.get(aid, {})
                ho, rg, ac = h.get("host", ""), h.get("region", ""), h.get("acc", "")
                # never emit empty "()" when the query is absent from the host table (#5 supplies data)
                lw = " ".join([aid, f"({ho} · {rg})" if (ho or rg) else "", ac]).strip()
                ln = " ".join([aid, f"({ho})" if ho else "", ac]).strip()
                out.write("\t".join([n, "query", aid, ho, rg, ac, "NEIGHBORHOOD", lw, ln, "", ""]) + "\n")
            elif x in og or (a.outgroup_substr.lower() in (n or "").lower()):
                out.write("\t".join([n, "reference", "", "", "", "", "", "", "",
                                     _ref_label(n, lab_modal) + " (outgroup)", ""]) + "\n")
            else:
                _org = origins.get(_species_of(n), "")
                out.write("\t".join([n, "reference", "", "", "", "", "", "", "", _ref_label(n, lab_modal), _org]) + "\n")
    sys.stdout.write(f"[ggtree-inputs] {a.group}: {len(t.get_terminals())} tips "
                     f"({len(q)} queries) -> {nwk_out} + {ann_out}\n")


if __name__ == "__main__":
    sys.exit(main())
