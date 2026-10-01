#!/usr/bin/env python3
"""gap_directed_rescue.py — what a core region's reference cluster has and the core lacks, looked for across the genome.

Reader-side and NON-SCORING. Start from one antiSMASH region (the core) and a reference cluster GenBank file (usually
MIBiG). Every reference protein is compared with every protein of the genome, not only those inside antiSMASH regions:
the missing part of a pathway split by the assembly often sits on a short contig antiSMASH did not flag, because it
holds tailoring genes and no core gene.

For each reference gene:
- PRESENT_IN_CORE: its best match inside the core region reaches 30% identity over 50% of the reference protein, or
  25% identity with e <= 1e-10 over 50% (a weak match inside the cluster itself; not used outside the core).
- MISSING_FOUND_CLEAR: missing from the core, and the genome's best match elsewhere beats the next candidate's
  bitscore by 20% or more (or has no rival) at >= 35% identity. Paralog families (halogenases, glycosyltransferases,
  methyltransferases) give several candidates; only a clear margin picks one.
- MISSING_FOUND_AMBIGUOUS, MISSING_NOT_FOUND.

Partners are other contigs carrying >= 2 clear finds. A partner is reported CONCENTRATED when the two leading partners
hold >= 60% of all clear finds (a missing piece puts the genes in one or two places; paralogs scatter them), and
SPLIT_PLAUSIBLE when the core runs to a contig end, or the partner contig is under 30 kb, or its region touches a
contig end. Reference genes are split by the reference's own antiSMASH gene_kind: only biosynthetic and
biosynthetic-additional finds count toward "biosynthetic clear finds" (some MIBiG entries carry flanking housekeeping
genes).

Split-gene check. The table above keeps one best genome protein per reference gene and needs 50% coverage, so a gene
broken by the assembly shows only its larger piece; the other piece reads as "no match". The check reads every hit
again, before those filters: a reference gene is SPLIT_ACROSS_CONTIG_ENDS when two proteins on different contigs each
cover >= 40 residues of it, neither covers 80% or more, their reference stretches overlap by <= 20 residues and
together cover >= 50% of it, and each piece's open end faces a contig end within 300 bp (the piece covering the
reference's start ends at a contig end; the piece covering its end starts at one). Each split gets a call:
MODULAR_UNRESOLVED when the reference gene or either piece is an assembly-line protein (a KS or condensation domain,
or two or more adenylation domains, read from the reference's aSDomain features and the genome's sec_met_domain
qualifiers), where module paralogy can fake complementary pieces; RIVAL_STRONGER when a whole-gene match
elsewhere is at least as identical as the weaker piece (likely paralog fragments); WEAK when the pieces beat it by
under 10 identity points; CLEAR otherwise. Only CLEAR splits are drawn. The check changes no status or partner; it
needs the reference coordinates (qstart, qend) of each hit and says it was not run when they are missing.

Outputs: gap_rescue.tsv (one row per reference gene), gap_rescue_partners.tsv, gap_rescue_split_genes.tsv,
gap_rescue_receipt.json, and gap_rescue.png / gap_rescue.pdf: a clinker-style locus map drawn by
tools/gap_rescue_locus_map.py. The reference sits above; the genome below starts with the core contig, then the contig
holding the other piece of a CLEAR split gene (red gap marker), then contigs with a clear match of >= 50% identity to a
named cluster gene. Ribbons are shaded by protein identity, and each matched gene is labelled with its match. The full
gene table stays in gap_rescue.tsv.

Claim-safety: homology is similarity, not product identity; a rescue candidate joins no contigs. A fragmented assembly
is never joined with full confidence.

CLI:
  python tools/gap_directed_rescue.py --zip <antiSMASH.zip> --label <strain> --core <contig>.regionNNN \
         --reference <MIBiG.gbk> [--reference-name "AT2433-A1"] --out <dir> [--hits hits.tsv] [--threads 4]
--hits: precomputed DIAMOND/BLAST tabular (qseqid = reference gene id g001..., sseqid = genome protein id from
gap_rescue_proteins.faa, pident, qcovhsp, bitscore, and optionally qstart, qend for the split-gene check and evalue
for the core-only 25% floor), for runs without DIAMOND.
--sensitivity: DIAMOND search mode, default ultra-sensitive; DIAMOND's own default (fast) misses pathway genes at
25-40% identity. 'default' restores it.
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
from gap_rescue_locus_map import draw_locus_map  # noqa: E402

import argparse
import io
import json
import re
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

try:
    from mamey import parsers
    from mamey.csv_safety import SafeWriter
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # bare-script run: bundle root is one level up
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey import parsers
    from mamey.csv_safety import SafeWriter
    from mamey.path_safety import assert_output_outside_bundle

# The gene table, the split-gene check, the partner checks, reference discovery and their thresholds live in
# mamey/ref_completion.py, shared with RG-GMCI's reference-guided completion and the standalone rggmci package, so the
# tool and the engine run one implementation. This tool keeps its loaders, its DIAMOND calls and its figure.
from mamey import ref_completion as _rc  # noqa: E402
from mamey.ref_completion import (BIOSYNTHETIC_KINDS, CLEAR_ID, CLEAR_RATIO, CONCENTRATION,  # noqa: E402,F401
                                  DISCOVERY_MAX_KB, DISCOVERY_MIN_COV, DISCOVERY_MIN_ID, DISCOVERY_MIN_PROTEINS,
                                  HOUSEKEEPING_MIN, HOUSEKEEPING_PFAM, MAX_EVALUE_CORE, MIN_COV, MIN_ID, MIN_ID_CORE,
                                  NEIGHBOUR_GENES, PARALOG_LIMIT, PARTNER_CHECK_COLS, PARTNER_COLS, PARTNER_MIN,
                                  PARTNER_WINDOW_BP, RECIPROCAL_MARGIN, RECIPROCAL_MIN, SHORT_CONTIG, SPLIT_COLS,
                                  SPLIT_END_BP, SPLIT_MAX_OVERLAP, SPLIT_MAX_PIECE_COV, SPLIT_MIN_AA, SPLIT_MIN_UNION,
                                  SPLIT_RIVAL_MARGIN, TABLE_COLS, _locus_kb, _open_end_distance, _pfam_names,
                                  region_of, search, split_genes)

def _say(*lines: str) -> None:
    emit(*lines, sep="\n")


def _seqio():
    return parsers._require_seqio()


def load_reference(gbk: Path) -> tuple[list[dict], str]:
    rec = next(_seqio().parse(str(gbk), "genbank"))
    cds = sorted([c for c in rec.features if c.type == "CDS" and "translation" in c.qualifiers],
                 key=lambda c: int(c.location.start))
    ks = [int(f.location.start) for f in rec.features if f.type == "aSDomain" and f.qualifiers.get("aSDomain") == ["PKS_KS"]]
    doms = [(int(f.location.start), f.qualifiers.get("aSDomain", [""])[0]) for f in rec.features if f.type == "aSDomain"]
    genes = []
    for i, c in enumerate(cds, 1):
        q = c.qualifiers
        n_ks = sum(1 for k in ks if int(c.location.start) <= k < int(c.location.end))
        mine = [d for s, d in doms if int(c.location.start) <= s < int(c.location.end)]
        # an assembly-line gene: module paralogy can fake two complementary pieces (split-gene check)
        modular = n_ks > 0 or any(d.startswith("Condensation") for d in mine) or mine.count("AMP-binding") >= 2
        genes.append({"id": f"g{i:03d}", "i": i, "start": int(c.location.start), "end": int(c.location.end), "ks": n_ks,
                      "modular": modular,
                      "strand": c.location.strand or 1,
                      "name": (q.get("gene") or q.get("locus_tag") or q.get("protein_id") or [f"g{i}"])[0],
                      "product": q.get("product", [""])[0], "kind": q.get("gene_kind", ["other"])[0],
                      "aa": q["translation"][0]})
    return genes, rec.description


def load_genome(zip_path: Path, label: str) -> tuple[dict, list]:
    """Every CDS of the whole-genome GenBank in the ZIP, and the antiSMASH regions with their full identities."""
    names = [n for n in zipfile.ZipFile(zip_path).namelist()
             if n.endswith(".gbk") and ".region" not in n and "__MACOSX" not in n and not Path(n).name.startswith("._")]
    if not names:
        raise SystemExit("no whole-genome GenBank file in the ZIP")
    # the engine parser is the bound source for contig names and aliases; the whole-genome GenBank can carry a
    # mangled record name (a SPAdes coverage suffix with a digit dropped), so regions are matched on
    # region number and coordinates, not on the name
    parsed = [(int(re.sub(r"\D", "", b.antismash_region or "0") or 0), int(b.start or 0), int(b.end or 0), b)
              for b in parsers.parse_bgcs_from_zip(zip_path, json_mode="off")]
    prots, regions = {}, []
    text = zipfile.ZipFile(zip_path).read(names[0]).decode(errors="replace")
    for rec in _seqio().parse(io.StringIO(text), "genbank"):
        dm = re.search(r"(\S+?),? whole genome", rec.description or "")
        node = dm.group(1) if dm and dm.group(1) not in rec.id and rec.id not in dm.group(1) else ""
        shown = f"{node} = {rec.id}" if node else rec.id
        for f in rec.features:
            if f.type == "region":
                n = int(f.qualifiers.get("region_number", ["0"])[0])
                s0, e0 = int(f.location.start), int(f.location.end)
                hits = [b for k, s, e, b in parsed if k == n and abs(s - s0) <= 1 and abs(e - e0) <= 1
                        and (b.contig[:12] == rec.id[:12])]
                b = hits[0] if len(hits) == 1 else None
                node = f"{shown.split(' = ')[0]} = " if " = " in shown else ""
                name = f"{node}{b.contig}" if b else shown
                regions.append({"contig": rec.id, "start": s0, "end": e0, "n": n,
                                "edge": f.qualifiers.get("contig_edge", [""])[0],
                                "identity": f"{label} / {name} / region{n:03d} / {b.bgc_id if b else 'IDENTITY_HOLD'}"})
            elif f.type == "CDS" and "translation" in f.qualifiers:
                pid = f"q{len(prots) + 1:06d}"
                doms = [d.split(" (")[0] for d in f.qualifiers.get("sec_met_domain", [])]
                prots[pid] = {"contig": rec.id, "shown": f"{label} / {shown}", "start": int(f.location.start),
                              "end": int(f.location.end), "strand": f.location.strand or 1,
                              "tag": f.qualifiers.get("locus_tag", [pid])[0], "aa": f.qualifiers["translation"][0],
                              "contig_len": len(rec.seq), "kind": f.qualifiers.get("gene_kind", [""])[0],
                              "modular": any(d == "PKS_KS" or d.startswith("Condensation") for d in doms)
                              or doms.count("AMP-binding") >= 2}
    return prots, regions


SENSITIVITY_DEFAULT = "ultra-sensitive"  # DIAMOND's fast default misses pathway genes at 25-40% identity


def run_diamond(ref: list, prots: dict, threads: int, sensitivity: str | None = SENSITIVITY_DEFAULT) -> list[dict]:
    from mamey import diamond_align
    with tempfile.TemporaryDirectory() as td:
        qf, rf = Path(td, "ref.faa"), Path(td, "genome.faa")
        qf.write_text("".join(f">{g['id']}\n{g['aa']}\n" for g in ref))
        rf.write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
        res = diamond_align.align_fasta(str(qf), str(rf), threads=threads, sensitivity=sensitivity)
    if not res.get("ok"):
        raise RuntimeError(f"DIAMOND unavailable: {res.get('reason')}; pass --hits with a precomputed table")
    return res["hits"]


def read_hits(path: Path) -> list[dict]:
    out = []
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 5:
            h = {"qseqid": p[0], "sseqid": p[1], "pident": float(p[2]), "qcovhsp": float(p[3]), "bitscore": float(p[4])}
            if len(p) >= 7 and p[5].strip() and p[6].strip():
                h.update(qstart=int(p[5]), qend=int(p[6]))
            if len(p) >= 8 and p[7].strip():
                h["evalue"] = float(p[7])
            out.append(h)
    return out


def _search_db(*args, **kwargs) -> dict:
    """The tool's MIBiG search: mamey.diamond_align.search_db, looked up at call time."""
    from mamey import diamond_align
    return diamond_align.search_db(*args, **kwargs)


def partner_checks(rows, prots, hits, core, ref_acc, mibig_db=None, pfam_hmm=None, threads=4, sensitivity=None,
                   compounds=None) -> dict:
    """mamey.ref_completion.partner_checks with this tool's DIAMOND search and Pfam scan (see there for the rules)."""
    return _rc.partner_checks(rows, prots, hits, core, ref_acc, mibig_db, pfam_hmm, threads, sensitivity,
                              search=_search_db, pfam_names=lambda *a, **k: _pfam_names(*a, **k), compounds=compounds)


def discover_references(queries: dict, prots: dict, mibig_db, mibig_dir, threads=4, sensitivity=None, hits=None) -> dict:
    """mamey.ref_completion.discover_references with this tool's DIAMOND search (see there for the rules)."""
    return _rc.discover_references(queries, prots, mibig_db, mibig_dir, threads, sensitivity, hits, search=_search_db)


def kcb_reference(zip_path: Path, core: dict, mibig_dir: Path):
    """The core region's KnownClusterBlast rank-1 MIBiG hit, when its GenBank file is in mibig_dir -> (path, name) or None."""
    from mamey import kcb_locusmap
    try:
        reg = kcb_locusmap.read_kcb_from_zip(Path(zip_path), core["contig"], f"region{core['n']:03d}")
    except (FileNotFoundError, KeyError, ValueError):
        return None
    top = reg.hits[0] if reg.hits else None
    m = re.match(r"(BGC\d{7})", (top.bgc_id if top else "") or "")
    if m and (Path(mibig_dir) / f"{m.group(1)}.gbk").exists():
        return Path(mibig_dir) / f"{m.group(1)}.gbk", top.compound or ""
    return None


def load_mibig_names(path) -> dict:
    """accession -> compound name(s), from a MIBiG index JSON ({"entries": [{"accession", "compounds"}]}) or a TSV."""
    if not path or not Path(path).exists():
        return {}
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if str(path).endswith(".json"):
        data = json.loads(text)
        entries = data.get("entries", data) if isinstance(data, dict) else data
        return {e["accession"]: "/".join(e.get("compounds") or [])[:60] for e in entries if isinstance(e, dict)}
    return {p[0]: p[1] for p in (line.split("\t") for line in text.splitlines()) if len(p) >= 2}


def resolve_core(regions: list, spec: str) -> dict:
    m = re.match(r"(.+)\.region(\d+)$", spec)
    if not m:
        raise SystemExit("--core must look like <contig>.regionNNN")
    matches = [r for r in regions if r["n"] == int(m.group(2)) and
               (r["contig"] == m.group(1) or
                (len(r["identity"].split(" / ")) == 4 and
                 m.group(1) in r["identity"].split(" / ")[1].split(" = ")))]
    if len(matches) != 1:
        raise SystemExit(f"core region {spec} not found or ambiguous; use an exact bound contig or node alias")
    core = matches[0]
    parts = core["identity"].split(" / ")
    if len(parts) != 4 or any(not x.strip() or x in {"None", "?", "IDENTITY_HOLD"} for x in parts):
        raise SystemExit(f"core region {spec} has an unresolved identity")
    return core


def choose_reference(zip_path, core, prots, reference=None, reference_name="", mibig_dir=None, mibig_db=None,
                     names=None, threads=4, sensitivity=None):
    """-> (reference GenBank path or None, display name, source). A given reference wins; then the region's
    KnownClusterBlast rank-1 MIBiG hit; then discovery by DIAMOND at >= 35% (see discover_references)."""
    names = names or {}
    if reference:
        return Path(reference), reference_name or names.get(Path(reference).stem, ""), "given"
    if not mibig_dir:
        return None, "", "no reference: give --reference, or --mibig-dir (and --mibig-db) to choose one"
    k = kcb_reference(zip_path, core, mibig_dir)
    if k:
        return k[0], reference_name or names.get(k[0].stem) or k[1], "KnownClusterBlast rank 1"
    if not mibig_db:
        return None, "", "no reference: no KnownClusterBlast hit, and no --mibig-db for discovery"
    in_core = [pid for pid, p in prots.items() if p["contig"] == core["contig"] and p["start"] < core["end"]
               and p["end"] > core["start"]]
    d = discover_references({"core": in_core}, prots, mibig_db, mibig_dir, threads, sensitivity).get("core")
    if not d:
        return None, "", ("no reference: no KnownClusterBlast hit and no MIBiG cluster with >= 2 core proteins at "
                          ">= 35% identity (one biosynthetic, reference <= 250 kb)")
    source = (f"DIAMOND >= 35% identity: {d['proteins']} core proteins (bitscore {d['bitscore']})"
              + (f"; runner-up {d['runner_up']}" if d["runner_up"] else "")
              + ("; tied: ambiguous reference" if d["tied"] else ""))
    return d["reference"], reference_name or names.get(d["reference"].stem, ""), source


def analyse_region(label, prots, regions, core, reference, ref_name, source, out, hits=None, threads=4,
                   sensitivity=SENSITIVITY_DEFAULT, mibig_db=None, pfam=None, figure=True, write_proteins=True) -> dict:
    """Search one core region against one reference and write every output; returns the receipt."""
    ref, desc = load_reference(reference)
    out.mkdir(parents=True, exist_ok=True)
    if write_proteins:  # the ids the hit tables use; the all-regions runner writes one shared copy instead
        (out / "gap_rescue_proteins.faa").write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
    sens = None if sensitivity == "default" else sensitivity
    homology = "precomputed hits" if hits is not None else f"DIAMOND ({sens or 'default fast'} mode)"
    if hits is None:
        hits = run_diamond(ref, prots, threads, sens)
    rows, partners = search(ref, prots, regions, hits, core)
    splits, split_check = split_genes(ref, prots, regions, hits)
    checks = partner_checks(rows, prots, hits, core, Path(reference).stem.split(".")[0], mibig_db, pfam, threads, sens)
    with open(out / "gap_rescue_split_genes.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(SPLIT_COLS)
        for s in splits:
            w.writerow([s[c] for c in SPLIT_COLS])
    with open(out / "gap_rescue.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(TABLE_COLS + PARTNER_CHECK_COLS)
        for r in rows:
            w.writerow([r.get(c, "") for c in TABLE_COLS + PARTNER_CHECK_COLS])
    with open(out / "gap_rescue_partners.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(PARTNER_COLS)
        for p in partners:
            w.writerow([p[c] for c in PARTNER_COLS])
    st = Counter(r["status"] for r in rows)
    receipt = {"tool": "gap_directed_rescue", "label": label, "core": core["identity"], "reference": Path(reference).name,
               "reference_name": ref_name or desc, "reference_source": source, "reference_genes": len(rows),
               **{k.lower(): st[k] for k in ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS",
                                              "MISSING_NOT_FOUND")},
               "partners": partners, "homology": homology, "partner_checks": checks,
               "split_gene_check": split_check,
               "split_genes": [{c: s[c] for c in SPLIT_COLS} for s in splits],
               "non_claims": ["homology is similarity, not product identity",
                              "a partner contig is a candidate missing piece; no contigs are joined",
                              "a fragmented assembly is never joined with full confidence",
                              "a split gene is two pieces at facing contig ends, not a joined sequence",
                              "a partner verdict is homology and context evidence, not proof of one pathway"]}
    (out / "gap_rescue_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if figure:
        draw_locus_map(reference, rows, splits, prots, regions, core, label, ref_name, out / "gap_rescue.png",
                       out / "gap_rescue.pdf")
    return receipt


def summary_line(receipt: dict, out) -> str:
    clear = [s for s in receipt["split_genes"] if s["split_call"] == "CLEAR"]
    split_note = (f"clear split genes: {'; '.join(s['name'] + ' (' + s['piece1_locus'] + ' + ' + s['piece2_locus'] + ')' for s in clear) or 'none'}"
                  if receipt["split_gene_check"] == "run" else f"split-gene check {receipt['split_gene_check']}")
    return (f"[gap_directed_rescue] {receipt['core']} vs {receipt['reference']} ({receipt['reference_source']}): "
            f"{receipt['present_in_core']} of {receipt['reference_genes']} reference genes in the core; "
            f"{receipt['missing_found_clear']} found clearly elsewhere; partner verdicts "
            f"{receipt['partner_checks']['verdicts'] or 'none'}; {split_note} -> {out}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--zip", required=True, type=Path)
    ap.add_argument("--label", required=True)
    ap.add_argument("--core", required=True, help="core region as <contig>.regionNNN")
    ap.add_argument("--reference", type=Path, help="reference cluster GenBank file (MIBiG); omit to choose one: the "
                                                   "KnownClusterBlast rank-1 hit, else DIAMOND discovery at >= 35%%")
    ap.add_argument("--reference-name", default="")
    ap.add_argument("--mibig-dir", type=Path, default=_os.environ.get("SAPOTE_MIBIG_GBK_DIR"),
                    help="folder of MIBiG GenBank files named <accession>.gbk (env SAPOTE_MIBIG_GBK_DIR)")
    ap.add_argument("--mibig-db", type=Path, default=_os.environ.get("SAPOTE_MIBIG_DMND"),
                    help="DIAMOND database of MIBiG proteins, ids starting with the accession (env SAPOTE_MIBIG_DMND); "
                         "used for reference discovery and the reciprocal partner check")
    ap.add_argument("--mibig-names", type=Path, default=_os.environ.get("SAPOTE_MIBIG_NAMES"),
                    help="MIBiG index JSON or accession<TAB>name TSV for figure titles (env SAPOTE_MIBIG_NAMES)")
    ap.add_argument("--pfam", type=Path, default=_os.environ.get("SAPOTE_PFAM_HMM"),
                    help="pressed Pfam-A.hmm for neighbour context of lone finds (env SAPOTE_PFAM_HMM; needs pyhmmer)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--hits", type=Path)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--sensitivity", default=SENSITIVITY_DEFAULT,
                    help="DIAMOND search mode (default ultra-sensitive; 'default' uses DIAMOND's own fast mode)")
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)
    assert_output_outside_bundle(a.out, __file__)
    prots, regions = load_genome(a.zip, a.label)
    core = resolve_core(regions, a.core)
    sens = None if a.sensitivity == "default" else a.sensitivity
    reference, name, source = choose_reference(a.zip, core, prots, a.reference, a.reference_name, a.mibig_dir,
                                               a.mibig_db, load_mibig_names(a.mibig_names), a.threads, sens)
    if reference is None:
        raise SystemExit(f"[gap_directed_rescue] {core['identity']}: {source}")
    receipt = analyse_region(a.label, prots, regions, core, reference, name, source, a.out,
                             read_hits(a.hits) if a.hits else None, a.threads, a.sensitivity, a.mibig_db, a.pfam,
                             not a.no_figure)
    _say(summary_line(receipt, a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
