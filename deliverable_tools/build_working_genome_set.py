#!/usr/bin/env python3
"""build_working_genome_set.py — one clean, content-deduplicated genome pool + provenance.

The problem: genomes are scattered across per-family `genomes/` dirs, the SAME assembly
appears under multiple labels (type-species name vs strain code vs accession), and a handful
of reference genomes are pathological long-branch refs. This builds the *working set*:

  * walk every phylo_work/*/genomes/*.fna
  * key each genome by NORMALIZED-SEQUENCE SHA-256 (labels ignored) -> true unique genomes
  * collapse all label aliases + which family pools + role (query/outgroup/reference)
  * flag: content-duplicate aliases, the 6 pathological long-branch refs, OFFICIAL_DATA exclusions
  * emit WORKING_GENOME_SET.csv (one row per UNIQUE genome) + DUPLICATE_ALIASES.csv + summary

This is the substrate the panel-selection method chooses from. It does NOT build trees.
Claim safety: a genome pool + provenance only; topology/taxonomy judgment deferred.
"""
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os, re, csv, hashlib, glob, argparse
from mamey.canonical_write_guard import guard_canonical_write, CanonicalOverwriteRefused
from collections import defaultdict


# Import-safe entry point with explicit portable inputs and canonical-write protection.
if __name__ == "__main__":   # v9.7.417 import safety — see tests/test_tools_import_safe_v97250.py

    ap = argparse.ArgumentParser(description="Build a content-addressed genome-set inventory")
    ap.add_argument("--input-root", required=True, help="Directory containing family/genomes/*.fna pools")
    ap.add_argument("--out", required=True, help="Additive output directory")
    ap.add_argument("--force", "--in-place", dest="force", action="store_true")
    args = ap.parse_args()
    PW, OUT = args.input_root, args.out
    if not os.path.isdir(PW):
        ap.error("input root is not a directory")
    try:
        for filename in ("WORKING_GENOME_SET.csv", "DUPLICATE_ALIASES.csv"):
            guard_canonical_write(os.path.join(OUT, filename), force=args.force)
    except CanonicalOverwriteRefused as exc:
        ap.error(str(exc))

    # 6 pathological long-branch REFERENCE genomes (AMBER_SHARED/LONG_BRANCH_ANALYSIS_MLSA_2026-08-03.md)
    # Match ONLY on the specific strain-code / accession — NOT the genus (Amycolatopsis/Sciscionella
    # genus tokens would over-flag every member of those genera, which is wrong).
    PATHOLOGICAL = [
        "WAC_04197",       # Amycolatopsis sp. WAC_04197 (328x)
        "GCA_017354445",   # Sciscionella sp.
        "GCF_039543365",   # Pseudonocardia eucalypti JCM18303
        "GCA_050701095",   # Sciscionella sp.
        "GCA_050701135",   # Sciscionella sp.
        "GCA_013361595",   # Nocardia sp013361595
    ]
    PATH_RE = re.compile("|".join(re.escape(x) for x in PATHOLOGICAL))
    import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    try:  # cohort exclusions come from the governed SSOT, never hardcoded here
        from mamey.exclusions import raw_analysis_excluded
        EXCL_RE = re.compile(
            "|".join(["AJS"] + [re.escape(s) for s in sorted(raw_analysis_excluded())]), re.I
        )
    except Exception as _exc:  # pragma: no cover - standalone use without mamey
        raise RuntimeError(
            "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
        ) from _exc
    QUERY_RE = re.compile(r"(^|/)(AS[-_]?\d+|AJS[-_]?\d+)", re.I)
    OUTGROUP_RE = re.compile(r"OUTGROUP", re.I)

    def norm_hash(path):
        h = hashlib.sha256(); n = 0
        with open(path) as f:
            for line in f:
                if line.startswith(">"): continue
                s = re.sub(r"\s", "", line).upper()
                h.update(s.encode()); n += len(s)
        return h.hexdigest(), n

    def role(basename):
        if OUTGROUP_RE.search(basename): return "outgroup"
        if QUERY_RE.search(basename): return "query"
        return "reference"

    genomes = defaultdict(lambda: {"aliases": set(), "pools": set(), "roles": set(), "nt": 0, "paths": []})
    n_files = 0
    for gdir in glob.glob(f"{PW}/*/genomes"):
        fam = gdir.split("/")[-2]
        for p in glob.glob(f"{gdir}/*.fna"):
            n_files += 1
            h, nt = norm_hash(p)
            base = os.path.basename(p)[:-4]
            g = genomes[h]
            g["aliases"].add(base); g["pools"].add(fam); g["roles"].add(role(base))
            g["nt"] = nt; g["paths"].append(p)

    if not genomes:
        ap.error("input root contains no genome files")
    os.makedirs(OUT, exist_ok=True)
    # WORKING_GENOME_SET.csv — one row per unique genome
    rows = []
    for h, g in genomes.items():
        aliases = sorted(g["aliases"])
        canonical = sorted(aliases, key=lambda a: (("__GC" not in a), len(a)))[0]  # prefer accession-bearing
        flags = []
        if len(aliases) > 1: flags.append(f"content-dup(x{len(aliases)})")
        if any(PATH_RE.search(a) for a in aliases): flags.append("PATHOLOGICAL_LONGBRANCH_prune")
        if any(EXCL_RE.search(a) for a in aliases): flags.append("OFFICIAL_DATA_excluded")
        rows.append({
            "genome_sha256": h[:16], "canonical_label": canonical, "n_aliases": len(aliases),
            "aliases": " | ".join(aliases), "family_pools": " | ".join(sorted(g["pools"])),
            "role": "/".join(sorted(g["roles"])), "length_nt": g["nt"], "flags": ";".join(flags) or "ok",
        })
    rows.sort(key=lambda r: (r["family_pools"], -r["length_nt"]))
    with open(f"{OUT}/WORKING_GENOME_SET.csv", "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # DUPLICATE_ALIASES.csv — only the content-dup clusters
    with open(f"{OUT}/DUPLICATE_ALIASES.csv", "w", newline="") as f:
        w = _SafeWriter(f); w.writerow(["genome_sha256", "length_nt", "family_pools", "aliases"])
        for h, g in genomes.items():
            if len(g["aliases"]) > 1:
                w.writerow([h[:16], g["nt"], " | ".join(sorted(g["pools"])), " | ".join(sorted(g["aliases"]))])

    n_dup = sum(1 for g in genomes.values() if len(g["aliases"]) > 1)
    n_path = sum(1 for r in rows if "PATHOLOGICAL" in r["flags"])
    n_excl = sum(1 for r in rows if "excluded" in r["flags"])
    emit(f"scanned {n_files} .fna files across per-family pools", f"UNIQUE genomes (by normalized-sequence hash): {len(genomes)}", f"  content-duplicate genomes (>=2 labels): {n_dup}", f"  pathological long-branch refs to prune:  {n_path}", f"  OFFICIAL_DATA-excluded present:          {n_excl}", f"written: {OUT}/WORKING_GENOME_SET.csv  +  DUPLICATE_ALIASES.csv", sep="\n")
