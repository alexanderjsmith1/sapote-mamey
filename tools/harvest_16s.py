#!/usr/bin/env python3
"""harvest_16s.py — assemble the 16S inputs for a per-genus EPA-ng placement, ALL FROM LOCAL DATA.

Formalizes what was an ad-hoc step: getting (a) the query 16S for the lab's AS strains, (b) a genus
reference panel, and (c) the outgroup, WITHOUT any NCBI download (the sanctioned, offline-first path).

Sources (all local; see docs/EPA_NG_PLACEMENT_WORKFLOW.md):
  * QUERY 16S  → the curated authoritative FASTA (`AS_16S_authoritative.fasta`, headers `>AS-###`).
                 This is the governed 16S source — NOT genome-extracted, NOT .ab1. Never re-fetch it.
  * REFERENCE  → the local NCBI 16S RefSeq BLAST DB via `blastdbcmd` (no network). All records whose
                 title genus == the requested genus.
  * OUTGROUP   → resolved by `outgroup_registry.py` from `OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv`, taking the
                 cached 16S in `OFFICIAL_DATA/outgroup_cache/16S/` — phylo_place appends it via
                 `--add-outgroup <ingroup genus>`, so this tool only reports whether it is available.

Usage:
  Tools/bin/python3 tools/harvest_16s.py --genus Saccharopolyspora \\
      --strains <strain1>,<strain2>,<strain3>  --out-dir <run>/Saccharopolyspora
  # or --strain-table <paper table>  (auto-selects every strain whose "Genus (16S)" == --genus)

Emits <genus>_query.fasta, <genus>_reference.fasta, <genus>_metadata.tsv, and a harvest_receipt.txt.
Then: phylo_place.py all <genus>_reference.fasta --group <genus> --query <genus>_query.fasta \\
        --add-outgroup <genus> --one-per-species --bootstrap 10 --approved-by <name> --outdir placement
"""
import argparse, csv, os, re, subprocess, sys

DEF_AUTH = os.environ.get("PHYLO_AUTHORITATIVE_16S", "phylo_staging/authoritative_16S/authoritative_16S.fasta")
DEF_DB = "Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA"


def _root():
    return os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())


def _load_fasta(path):
    seqs, cur, buf = {}, None, []
    if not os.path.exists(path):
        return seqs
    for ln in open(path):
        if ln.startswith(">"):
            if cur:
                seqs[cur] = "".join(buf)
            cur = ln[1:].strip().split()[0]; buf = []
        else:
            buf.append(ln.strip())
    if cur:
        seqs[cur] = "".join(buf)
    return seqs


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)  # v9.7.412: no silent prefix matching
    ap.add_argument("--genus", required=True)
    ap.add_argument("--strains", default="", help="comma-separated AS ids; or use --strain-table")
    ap.add_argument("--strain-table", default="", help="paper strain table; selects rows whose Genus (16S)==--genus")
    ap.add_argument("--authoritative", default="", help="AS_16S_authoritative.fasta (auto-located)")
    ap.add_argument("--refseq-db", default="", help="local 16S RefSeq BLAST DB (auto-located)")
    ap.add_argument("--blastdbcmd", default="")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    root = _root()
    auth = a.authoritative or os.path.join(root, DEF_AUTH)
    db = a.refseq_db or os.path.join(root, DEF_DB)
    bdc = a.blastdbcmd or os.path.join(root, "miniconda3/envs/blast/bin/blastdbcmd")
    try:
        os.makedirs(a.out_dir, exist_ok=True)
    except OSError as exc:  # v9.7.412: typed refusal, not PermissionError
        sys.stderr.write(f"OUTPUT_NOT_WRITABLE: --out-dir {a.out_dir!r} ({type(exc).__name__})\n"); sys.exit(2)

    # 1. resolve strain list + metadata
    strains, meta = [], {}
    if a.strain_table and os.path.exists(a.strain_table):
        for r in csv.DictReader(open(a.strain_table), delimiter="\t"):
            g = re.sub(r"\s*sp\.?\s*$", "", (r.get("Genus (16S)") or "").strip())
            if g.lower() == a.genus.lower():
                sid = (r.get("Strain Number") or "").strip()
                if sid:
                    strains.append(sid)
                    meta[sid] = {"host": (r.get("Host") or "").strip(),
                                 "loc": (r.get("Location") or "").strip(),
                                 "acc": (r.get("Genbank Accession") or "").strip(),
                                 "near": (r.get("Closest Type Strain") or "").strip()}
    if a.strains:
        strains += [s.strip() for s in a.strains.split(",") if s.strip()]
    strains = sorted(set(strains))
    if not strains:
        sys.exit("no strains: pass --strains or a --strain-table containing this genus")

    # 2. query 16S from the authoritative FASTA (LOCAL)
    seqs = _load_fasta(auth)
    q_path = os.path.join(a.out_dir, f"{a.genus}_query.fasta")
    missing = []
    with open(q_path, "w") as qf:
        for s in strains:
            if s in seqs:
                qf.write(f">{s}\n{seqs[s]}\n")
            else:
                missing.append(s)
    nq = len(strains) - len(missing)

    # 3. reference panel from the local RefSeq DB (LOCAL, blastdbcmd)
    r_path = os.path.join(a.out_dir, f"{a.genus}_reference.fasta")
    nref = 0
    if os.path.exists(bdc):
        p = subprocess.run([bdc, "-db", db, "-entry", "all", "-outfmt", "%f"],
                           capture_output=True, text=True)
        with open(r_path, "w") as rf:
            keep = False
            for ln in p.stdout.splitlines():
                if ln.startswith(">"):
                    # genus = first alpha word after the accession token
                    title = re.sub(r"^>\S+\s+", "", ln)
                    keep = title.lower().startswith(a.genus.lower() + " ")
                    if keep:
                        nref += 1
                if keep:
                    rf.write(ln + "\n")
    else:
        sys.stderr.write(f"WARN blastdbcmd not found at {bdc}; reference panel not built\n")

    # 4. outgroup availability (report only; phylo_place appends it)
    og_status = "unknown"
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import outgroup_registry as OG  # noqa
        try:
            OG.get_16s(a.genus, scope="genus", quiet=True)
            og_status = "AVAILABLE (registry + cache)"
        except SystemExit:
            og_status = "NO registry row / not cached — add a row before building"
        except Exception as e:
            og_status = f"unresolved ({e})"
    except Exception:
        og_status = "outgroup_registry.py not importable here"

    # 5. metadata + receipt
    if meta:
        with open(os.path.join(a.out_dir, f"{a.genus}_metadata.tsv"), "w") as m:
            m.write("strain\thost\tlocation\tclosest_type_strain\tgenbank_accession\n")
            for s in strains:
                d = meta.get(s, {})
                m.write("\t".join([s, d.get("host", ""), d.get("loc", ""),
                                   d.get("near", ""), d.get("acc", "")]) + "\n")
    with open(os.path.join(a.out_dir, "harvest_receipt.txt"), "w") as rc:
        rc.write(f"genus={a.genus}\nquery_strains={len(strains)} found={nq} missing={','.join(missing) or '-'}\n"
                 f"reference_records={nref}\noutgroup={og_status}\n"
                 f"authoritative={auth}\nrefseq_db={db}\n")
    sys.stdout.write(f"[harvest_16s] {a.genus}: query {nq}/{len(strains)} (missing {missing or '-'}) · "
                     f"reference {nref} · outgroup {og_status}\n")


if __name__ == "__main__":
    sys.exit(main())
