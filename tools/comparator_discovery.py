#!/usr/bin/env python3
"""comparator_discovery.py — STEP 1 of discover -> download -> analyze (BB09 order).

Turn a strain's OWN antiSMASH evidence into a ranked set of comparator genomes to fetch, BEFORE running ANI. Parses
every ClusterBlast / KnownClusterBlast "Significant hits" list in the strain's antiSMASH output and aggregates the
source organisms/accessions: how many of the strain's regions point to each genome, and its best rank.

Why: a fixed pre-staged ANI pool can miss a strain's real relatives -> a misleading "no neighbor" pool artifact.
ClusterBlast is BGC-level (HGT-prone) so it is NOT a taxonomy call — but it is the right way to DISCOVER which
genomes to pull for a genome-level ANI. This tool only produces the comparator list + a fetch helper; the download
and the ANI are the next steps.

Usage:
  python Tools/comparator_discovery.py --zip "<antismash>/<STRAIN>.zip" --strain <STRAIN> --out <dir> [--top 40]
  python Tools/comparator_discovery.py --dir <extracted antismash dir> --strain <STRAIN> --out <dir>

Outputs: <strain>_comparators.tsv (ranked), <strain>_comparator_genera.tsv (genus rollup),
         fetch_<strain>_comparators.sh (NCBI datasets/efetch commands; no email), README.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, sys, glob, zipfile, tempfile, collections, datetime
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # local repo root before mamey import
from mamey.ziputil import safe_extract_all

HIT_RE = re.compile(r"^\s*(\d+)\.\s+(\S+)\s+(.*\S)\s*$")

# v9.7.409 (CLAUDE_409_mibig_comparator_fixes): a MIBiG reference-cluster accession
# (KnownClusterBlast), e.g. `BGC0001522`/`BGC0001522.5`. These are CHARACTERISED reference
# BGCs, NOT genomes to fetch: `efetch -db nuccore -id BGC0001522.5` is a dead command (MIBiG
# ids are not nuccore records), and a MIBiG hit's description is a METABOLITE name (auroramycin,
# coelichelin), never an organism -- so genus_species() mis-parses it into a bogus "genus".
# They are split into their own known-cluster table and excluded from the genome comparator
# rollup and the efetch fetch list. Detected by accession shape (robust regardless of which
# subdir the hit came from), the same identifier that is dead for efetch.
MIBIG_ACC = re.compile(r"^BGC\d+", re.I)


def iter_hit_files(root):
    for sub in ("clusterblast", "knownclusterblast"):
        for f in glob.glob(os.path.join(root, "**", sub, "*.txt"), recursive=True):
            yield sub, f


def parse_hits(path):
    """yield (rank, accession, organism_desc) from the 'Significant hits:' block."""
    inblock = False
    for line in open(path, encoding="utf-8", errors="ignore"):
        s = line.rstrip("\n")
        if s.strip() == "Significant hits:":
            inblock = True; continue
        if inblock and s.strip().startswith("Details"):
            break
        if inblock and s.strip():
            m = HIT_RE.match(s.replace("\t", " "))
            if m:
                yield int(m.group(1)), m.group(2), m.group(3)


def genus_species(desc):
    toks = desc.split()
    genus = toks[0] if toks else "?"
    sp = toks[1] if len(toks) > 1 else ""
    named = bool(sp) and not re.match(r"sp\.?$", sp, re.I)
    return genus, (f"{genus} {sp}" if named else f"{genus} sp."), named


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--zip"); g.add_argument("--dir")
    ap.add_argument("--strain", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    tmp = None
    root = args.dir
    if args.zip:
        tmp = tempfile.mkdtemp(prefix="cmpdisc_")
        with zipfile.ZipFile(args.zip) as z:
            safe_extract_all(z, tmp)  # fail-closed: reject ../ and absolute members
        root = tmp

    # accession -> record. v9.7.409: genome comparators (`acc`, fetchable + genus-rollupable) are
    # kept strictly separate from MIBiG reference-cluster hits (`mibig`, characterised BGCs that are
    # NOT genomes). A MIBiG accession's description is a metabolite name, so it never touches
    # genus_species() and never enters the genus counter or the efetch list.
    acc = {}
    mibig = {}
    genera = collections.Counter()
    n_files = 0
    for source, f in iter_hit_files(root):
        region = os.path.basename(f).replace(".txt", "")
        hits = list(parse_hits(f))
        if hits:
            n_files += 1
        for rank, accession, desc in hits:
            if MIBIG_ACC.match(accession):
                # MIBiG reference cluster: keep the metabolite/description verbatim; do NOT parse it
                # as an organism, do NOT count a genus, do NOT emit an efetch line.
                mrec = mibig.setdefault(accession, dict(accession=accession, metabolite=desc.strip(),
                                                        regions=set(), best_rank=rank, sources=set()))
                mrec["regions"].add(region)
                mrec["best_rank"] = min(mrec["best_rank"], rank)
                mrec["sources"].add(source)
                if desc.strip() and not mrec["metabolite"]:
                    mrec["metabolite"] = desc.strip()
                continue
            genus, disp, named = genus_species(desc)
            rec = acc.setdefault(accession, dict(accession=accession, organism=disp, genus=genus, named=named,
                                                 regions=set(), best_rank=rank, sources=set()))
            rec["regions"].add(region)
            rec["best_rank"] = min(rec["best_rank"], rank)
            rec["sources"].add(source)
            if named and not rec["named"]:
                rec["organism"], rec["named"] = disp, True
            genera[genus] += 1

    rows = sorted(acc.values(), key=lambda r: (-len(r["regions"]), r["best_rank"]))
    comp = os.path.join(args.out, f"{args.strain}_comparators.tsv")
    with open(comp, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(["rank_by_support", "accession", "organism", "genus", "named", "n_regions", "best_hit_rank", "sources"])
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["accession"], r["organism"], r["genus"], "yes" if r["named"] else "no",
                        len(r["regions"]), r["best_rank"], "+".join(sorted(r["sources"]))])

    gen = os.path.join(args.out, f"{args.strain}_comparator_genera.tsv")
    with open(gen, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t"); w.writerow(["genus", "hit_count"])
        for gname, n in genera.most_common():
            w.writerow([gname, n])

    # v9.7.409: MIBiG KnownClusterBlast reference clusters in their own table -- the genuine
    # "which characterised MIBiG clusters do this strain's BGCs resemble" coverage. These are
    # NOT genomes to fetch, so they never enter the comparator/genera/fetch outputs above.
    mibig_rows = sorted(mibig.values(), key=lambda r: (-len(r["regions"]), r["best_rank"]))
    mib = os.path.join(args.out, f"{args.strain}_mibig_known_clusters.tsv")
    with open(mib, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(["rank_by_support", "mibig_accession", "metabolite", "n_regions", "best_hit_rank", "sources"])
        for i, r in enumerate(mibig_rows, 1):
            w.writerow([i, r["accession"], r["metabolite"], len(r["regions"]), r["best_rank"],
                        "+".join(sorted(r["sources"]))])

    top = rows[: args.top]
    fetch = os.path.join(args.out, f"fetch_{args.strain}_comparators.sh")
    with open(fetch, "w") as fh:
        fh.write("#!/usr/bin/env bash\n# STEP 2 (download) — fetch the discovered comparator genomes, THEN run ANI.\n")
        fh.write("# No email / personal ID on requests. Check local pools first (Tools/find_asset.py).\n")
        fh.write("# ClusterBlast accessions are nucleotide (NZ_*); map to assembly or efetch the nucleotide.\n")
        fh.write(f"# Top {len(top)} comparators by region-support for {args.strain}.\n\n")
        fh.write("set -euo pipefail\nOUT=comparator_genomes; mkdir -p \"$OUT\"\n\n")
        for r in top:
            fh.write(f"# {r['organism']} — {len(r['regions'])} region(s), best rank {r['best_rank']}\n")
            fh.write(f"efetch -db nuccore -id {r['accession']} -format fasta > \"$OUT/{r['accession']}.fna\" || echo 'FAILED {r['accession']}'\n")
    os.chmod(fetch, 0o755)

    readme = os.path.join(args.out, f"README_comparator_discovery_{args.strain}.md")
    now = datetime.date.today().isoformat()
    with open(readme, "w") as fh:
        fh.write(f"# Comparator discovery — {args.strain} (STEP 1 of discover→download→analyze)\n\n")
        fh.write(f"**Date:** {now}. Parsed **{n_files}** ClusterBlast/KnownClusterBlast hit lists from the strain's "
                 f"antiSMASH output → **{len(acc)}** unique comparator genomes across **{len(genera)}** genera, "
                 f"plus **{len(mibig)}** MIBiG reference clusters (KnownClusterBlast) held separately.\n\n")
        fh.write("**Top comparator genera (BGC-level, genomes only):** " +
                 (", ".join(f"{g}({n})" for g, n in genera.most_common(8)) or "(none)") + ".\n\n")
        fh.write(f"**MIBiG reference clusters:** {len(mibig)} characterised clusters this strain's BGCs resemble "
                 f"(see `{args.strain}_mibig_known_clusters.tsv`). These are reference clusters, NOT genomes — they "
                 "are excluded from the comparator/genus rollup and the fetch script (a MIBiG id is not a nuccore "
                 "record; resemblance is BGC-level homology, not product identity).\n\n")
        fh.write("**Claim-safety:** ClusterBlast = BGC-level relatedness (HGT-prone), NOT a taxonomy call. These are "
                 "the genomes to DOWNLOAD and then ANI (STEP 3) so a novelty call is against the strain's real "
                 "relatives — not a fixed pool. 'No neighbor in a fixed pool' was never novelty.\n\n")
        fh.write(f"## Files\n- `{args.strain}_comparators.tsv` — ranked by how many regions support each genome.\n"
                 f"- `{args.strain}_comparator_genera.tsv` — genus rollup (genomes only).\n"
                 f"- `{args.strain}_mibig_known_clusters.tsv` — MIBiG reference clusters (KnownClusterBlast); not fetched.\n"
                 f"- `fetch_{args.strain}_comparators.sh` — STEP 2 download (efetch; no email; check local first).\n\n")
        fh.write("## Next (in order)\n1. Run the fetch script (or map NZ_* → assembly and use `datasets`).\n"
                 "2. skani/ANIm the strain vs the downloaded comparators.\n"
                 "3. Then a candidate-novel call is meaningful (reliable AF required).\n")
    emit(f"[comparator_discovery] {args.strain}: {n_files} hit-lists -> {len(acc)} genome comparators / "
         f"{len(genera)} genera; {len(mibig)} MIBiG reference clusters (held separately, not fetched)")
    emit(f'[comparator_discovery] top genera: ' + (', '.join((f'{g}({n})' for g, n in genera.most_common(6))) or '(none)'), f'[comparator_discovery] -> {comp}', sep="\n")
    if tmp:
        import shutil; shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
