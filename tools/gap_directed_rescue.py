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
again, before the one-best-protein and coverage filters (the 30% identity floor still applies): a reference gene is SPLIT_ACROSS_CONTIG_ENDS when two proteins on different contigs each
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
named cluster gene. Ribbons are shaded by protein identity, and each matched gene is labelled with its match. The two
rows are centred on one anchor gene, as in clinker: the reference gene named by --anchor, else the longest matched
core enzyme on the core contig (see anchor_gene in the renderer). The full gene table stays in gap_rescue.tsv.

Claim-safety: homology is similarity, not product identity; a rescue candidate joins no contigs. A fragmented assembly
is never joined with full confidence.

CLI:
  python tools/gap_directed_rescue.py --zip <antiSMASH.zip> --label <strain> --core <contig>.regionNNN \
         --reference <MIBiG.gbk> [--reference-name "AT2433-A1"] --out <dir> [--hits hits.tsv] [--threads 4]
--hits: precomputed DIAMOND/BLAST tabular (qseqid = reference gene id g001..., sseqid = genome protein id from
gap_rescue_proteins.faa, pident, qcovhsp, bitscore, and optionally qstart, qend for the split-gene check and evalue
for the core-only 25% floor), for runs without DIAMOND.
--anchor <gene>: the reference gene (MIBiG name, e.g. sanG) both rows are centred on.
--redraw <folder>: redraw the figure of an earlier run from its saved tables, without DIAMOND. Needs --zip, --label and
--mibig-dir; --core, --reference and --out are taken from the folder. Writes gap_rescue.png/.pdf into --out when given,
else into the folder.
--sensitivity: DIAMOND search mode, default ultra-sensitive; DIAMOND's own default (fast) misses pathway genes at
25-40% identity. 'default' restores it.
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
from gap_rescue_locus_map import draw_locus_map, load_gecco, load_gene_names, load_other_references  # noqa: E402

import argparse
import hashlib
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
# mamey/ref_completion.py, shared with RG-GMCI's reference-guided completion and the standalone rggmci package. The
# tool and the engine still differ: DIAMOND mode (ultra-sensitive here, sensitive in the engine), alignment limits
# (the engine sets e <= 1e-5 and no target cap), reference choice (KnownClusterBlast rank 1 here, the best-ranked
# held MIBiG hit in the engine) and the partner rule. This tool keeps its loaders, its DIAMOND calls and its figure.
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


STOP_CODONS = {"TAA", "TAG", "TGA"}


def lacks_stop(last_codon: str) -> bool:
    """True when a CDS does not end in a stop codon. antiSMASH writes no fuzzy (<, >) ends for draft contigs, so a gene
    cut by a contig end shows up here; on one draft genome, all 412 such genes run off a contig end."""
    return last_codon.upper() not in STOP_CODONS


def load_genome(zip_path: Path, label: str) -> tuple[dict, list]:
    """Every CDS of the whole-genome GenBank in the ZIP, and the antiSMASH regions with their full identities."""
    names = [n for n in zipfile.ZipFile(zip_path).namelist()
             if n.endswith(".gbk") and ".region" not in n and "__MACOSX" not in n and not Path(n).name.startswith("._")]
    if not names:
        raise SystemExit("no whole-genome GenBank file in the ZIP")
    # the engine parser is the bound source for contig names and aliases. Regions are matched on region number and
    # coordinates, not on the name. A record's contig name comes from the engine's rule (parsers._record_contig_id):
    # Biopython's rec.id is the VERSION line, which drops a 0 right after the point of a SPAdes coverage
    # (cov_65.032271 reads cov_65.32271); the LOCUS name keeps it
    parsed = [(int(re.sub(r"\D", "", b.antismash_region or "0") or 0), int(b.start or 0), int(b.end or 0), b)
              for b in parsers.parse_bgcs_from_zip(zip_path, json_mode="off")]
    prots, regions = {}, []
    pfam_desc = {}   # locus tag -> antiSMASH Pfam descriptions, for the gene table's protein family
    text = zipfile.ZipFile(zip_path).read(names[0]).decode(errors="replace")
    for rec in _seqio().parse(io.StringIO(text), "genbank"):
        cid = parsers._record_contig_id(rec)
        dm = re.search(r"(\S+?),? whole genome", rec.description or "")
        node = dm.group(1) if dm and dm.group(1) not in cid and cid not in dm.group(1) else ""
        shown = f"{node} = {cid}" if node else cid
        for f in rec.features:
            if f.type == "region":
                n = int(f.qualifiers.get("region_number", ["0"])[0])
                s0, e0 = int(f.location.start), int(f.location.end)
                hits = [b for k, s, e, b in parsed if k == n and abs(s - s0) <= 1 and abs(e - e0) <= 1
                        and (b.contig[:12] == cid[:12])]
                b = hits[0] if len(hits) == 1 else None
                node = f"{shown.split(' = ')[0]} = " if " = " in shown else ""
                name = f"{node}{b.contig}" if b else shown
                regions.append({"contig": cid, "start": s0, "end": e0, "n": n,
                                "edge": f.qualifiers.get("contig_edge", [""])[0],
                                "identity": f"{label} / {name} / region{n:03d} / {b.bgc_id if b else 'IDENTITY_HOLD'}"})
            elif f.type == "PFAM_domain":
                d = f.qualifiers.get("description", [""])[0]
                if d:
                    pfam_desc.setdefault(f.qualifiers.get("locus_tag", [""])[0], []).append(" ".join(d.split()))
            elif f.type == "CDS" and "translation" in f.qualifiers:
                pid = f"q{len(prots) + 1:06d}"
                doms = [d.split(" (")[0] for d in f.qualifiers.get("sec_met_domain", [])]
                prots[pid] = {"contig": cid, "shown": f"{label} / {shown}", "start": int(f.location.start),
                              "end": int(f.location.end), "strand": f.location.strand or 1,
                              "tag": f.qualifiers.get("locus_tag", [pid])[0], "aa": f.qualifiers["translation"][0],
                              "contig_len": len(rec.seq), "kind": f.qualifiers.get("gene_kind", [""])[0],
                              "missing_stop": lacks_stop(str(f.extract(rec.seq)[-3:])),
                              "family": _smcog(f.qualifiers.get("gene_functions", [])),
                              "modular": any(d == "PKS_KS" or d.startswith("Condensation") for d in doms)
                              or doms.count("AMP-binding") >= 2}
    for p in prots.values():   # no smCOG: the antiSMASH Pfam descriptions, in order, without repeats
        if not p["family"]:
            p["family"] = "; ".join(dict.fromkeys(pfam_desc.get(p["tag"], [])))
    return prots, regions


def _smcog(gene_functions) -> str:
    from gap_rescue_gene_table import smcog
    return smcog(gene_functions)


SENSITIVITY_DEFAULT = "ultra-sensitive"  # DIAMOND's fast default misses pathway genes at 25-40% identity


class _AlignmentHits(list):
    """Keep list compatibility while carrying the forward execution record to the receipt."""
    def __init__(self, hits, provenance):
        super().__init__(hits)
        self.provenance = provenance


def run_diamond(ref: list, prots: dict, threads: int, sensitivity: str | None = SENSITIVITY_DEFAULT) -> list[dict]:
    from mamey import diamond_align
    with tempfile.TemporaryDirectory() as td:
        qf, rf = Path(td, "ref.faa"), Path(td, "genome.faa")
        qf.write_text("".join(f">{g['id']}\n{g['aa']}\n" for g in ref))
        rf.write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
        res = diamond_align.align_fasta(str(qf), str(rf), threads=threads, sensitivity=sensitivity)
    if not res.get("ok"):
        raise RuntimeError(f"DIAMOND unavailable: {res.get('reason')}; pass --hits with a precomputed table")
    return _AlignmentHits(res["hits"], res.get("provenance", {"capture_state": "NOT_RECORDED"}))


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
        # the compound list is kept whole: a [:60] cut landed mid-word and the figure title showed the cut text
        # ("everninomici cluster"). The renderer wraps a long name instead.
        return {e["accession"]: "/".join(e.get("compounds") or []) for e in entries if isinstance(e, dict)}
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
                   sensitivity=SENSITIVITY_DEFAULT, mibig_db=None, pfam=None, figure=True, write_proteins=True,
                   anchor=None, gene_table=True, compounds=None, print_width="double", row_label=None) -> dict:
    """Search one core region against one reference and write every output; returns the receipt. `compounds` (accession
    -> compound names, as load_mibig_names gives) lets the partner check count sibling MIBiG entries of the reference's
    compound as its family."""
    ref, desc = load_reference(reference)
    out.mkdir(parents=True, exist_ok=True)
    if write_proteins:  # the ids the hit tables use; the all-regions runner writes one shared copy instead
        (out / "gap_rescue_proteins.faa").write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
    sens = None if sensitivity == "default" else sensitivity
    homology = "precomputed hits" if hits is not None else f"DIAMOND ({sens or 'default fast'} mode)"
    forward_alignment = getattr(hits, "provenance", {"capture_state": "PRECOMPUTED_UNVERIFIED", "backend": None})
    if hits is None:
        hits = run_diamond(ref, prots, threads, sens)
        forward_alignment = getattr(hits, "provenance", {"capture_state": "NOT_RECORDED"})
    rows, partners = search(ref, prots, regions, hits, core)
    splits, split_check = split_genes(ref, prots, regions, hits)
    # compounds only when names were given, so a caller without names makes exactly the call it made before
    checks = partner_checks(rows, prots, hits, core, Path(reference).stem.split(".")[0], mibig_db, pfam, threads, sens,
                            **({"compounds": compounds} if compounds else {}))
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
               "forward_alignment": forward_alignment,
               "split_gene_check": split_check, "map_outputs": [],
               "split_genes": [{c: s[c] for c in SPLIT_COLS} for s in splits],
               "non_claims": ["homology is similarity, not product identity",
                              "a partner contig is a candidate missing piece; no contigs are joined",
                              "a fragmented assembly is never joined with full confidence",
                              "a split gene is two pieces at facing contig ends, not a joined sequence",
                              "a partner verdict is homology and context evidence, not proof of one pathway"]}
    (out / "gap_rescue_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if figure:
        # print_width (11 Oct card .451): maps are drawn at a journal column width with text >= 8 pt; "none" (None)
        # keeps the 13.5 in screen layout. A map whose text would touch at print size is refused and held in the
        # receipt, never written; the gene table still lists every gene.
        try:
            rendered = draw_locus_map(reference, rows, splits, prots, regions, core, label, ref_name,
                                      out / "gap_rescue.png", out / "gap_rescue.pdf", anchor=anchor,
                                      print_width=print_width, **({"row_label": row_label} if row_label else {}))
        except ValueError as exc:
            if not str(exc).startswith(("GAP_RESCUE_MAP_TEXT_OVERLAP", "GAP_RESCUE_MAP_PRINT_WIDTH")):
                raise
            rendered = None
            receipt["map_hold"] = str(exc)
            (out / "gap_rescue_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if isinstance(rendered, dict) and "print_width_in" in rendered:
            receipt["map_print"] = {k: rendered[k] for k in ("print_width_in", "saved_width_in", "min_font_pt",
                                                             "text_overlaps", "labels_omitted", "shrink_level")}
        # The renderer returns its metadata dict only after both savefig calls complete.
        # A skipped/failed drawing never admits pre-existing files as current outputs.
        if isinstance(rendered, dict):
            for path in (out / "gap_rescue.png", out / "gap_rescue.pdf"):
                try:
                    payload = path.read_bytes()
                except OSError as exc:
                    raise ValueError(f"GAP_RESCUE_MAP_OUTPUT_UNREADABLE: {path}") from exc
                receipt["map_outputs"].append({"path": path.name, "sha256": hashlib.sha256(payload).hexdigest(),
                                               "bytes": len(payload)})
            (out / "gap_rescue_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if gene_table:   # the per-gene table, paired with the map (gene_table.*, map_and_table.*)
        from gap_rescue_gene_table import edge_shares, protein_families, write_gene_table
        fams = protein_families(prots)
        write_gene_table(out, rows, splits, core["identity"], label, reference, fams, ref_name or desc,
                         edge_shares(rows, prots, core), pair_map=bool(receipt["map_outputs"]), prots=prots)
    return receipt


def apply_adjudication(rows, folder: Path):
    """When a later adjudication of this run sits beside its folder (<folder>_ADJUDICATION.tsv: reference_gene,
    candidate_locus, verdict), its verdicts replace the partner_verdict the run wrote. Returns the rows."""
    import csv
    adj = folder.parent / f"{folder.name}_ADJUDICATION.tsv"
    if not adj.exists():
        return rows
    with open(adj) as fh:
        v = {(r.get("reference_gene", ""), r.get("candidate_locus", "")): r.get("verdict", "")
             for r in csv.DictReader(fh, delimiter="\t")}
    for r in rows:
        key = (r.get("name", ""), r.get("best_locus", ""))
        if v.get(key):
            r["partner_verdict"] = v[key]
    return rows


def redraw(folder: Path, prots, regions, label, mibig_dir: Path, out: Path | None = None, anchor=None,
           gene_names=None, context_rows=False, other_maps=False, print_width="double", row_label=None,
           trim_kb=None, panel=False, key=True, named_contigs=None, genome_zip=None,
           genome_zip_parse_sha256=None, gecco=None, scale_bar_up=False) -> dict:
    """Redraw an earlier run's figure from its saved tables (no DIAMOND). panel, key: see draw_locus_map."""
    import csv
    named_inputs = []
    named_sources = []
    if named_contigs:
        named_sources = [{"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in (Path(__file__), Path(__file__).with_name("gap_rescue_locus_map.py"))]
        if out is None or out.is_symlink() or out.exists() or out.resolve().is_relative_to(folder.resolve()) or folder.resolve().is_relative_to(out.resolve()):
            raise ValueError("NAMED_CONTIG_OUTPUT_HOLD: choose a fresh disjoint external output")
        if genome_zip is None or not Path(genome_zip).is_file():
            raise ValueError("NAMED_CONTIG_INPUT_HOLD: bind the supplied genome ZIP")
        paths = [Path(genome_zip), folder / "gap_rescue_receipt.json", folder / "gap_rescue.tsv", folder / "gap_rescue_split_genes.tsv"]
        adj = folder.parent / f"{folder.name}_ADJUDICATION.tsv"
        if adj.is_file():
            paths.append(adj)
        named_inputs = [{"path": str(p.resolve()), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
        if genome_zip_parse_sha256 is not None and named_inputs[0]["sha256"] != genome_zip_parse_sha256:
            raise ValueError("NAMED_CONTIG_INPUT_CHANGED: genome ZIP differs from the parsed input")
    receipt = json.loads((folder / "gap_rescue_receipt.json").read_text())
    core = next((r for r in regions if r["identity"] == receipt["core"]), None)
    if core is None:
        raise SystemExit(f"{receipt['core']} is not a region of this zip; check --zip and --label")
    with open(folder / "gap_rescue.tsv") as fh:
        rows = apply_adjudication(list(csv.DictReader(fh, delimiter="\t")), folder)
    with open(folder / "gap_rescue_split_genes.tsv") as fh:
        splits = list(csv.DictReader(fh, delimiter="\t"))
    if named_contigs:
        if receipt.get("label") != label:
            raise ValueError("NAMED_CONTIG_IDENTITY_HOLD: source receipt strain differs")
        core_parts = core["identity"].split(" / ")
        if len(core_parts) != 4 or any(not p.strip() or p != p.strip() or p == "IDENTITY_HOLD" for p in core_parts) or core_parts[0] != label:
            raise ValueError("NAMED_CONTIG_IDENTITY_HOLD: core four-part identity is unresolved")
        if core_parts[1] != core["contig"]:
            raise ValueError("NAMED_CONTIG_IDENTITY_HOLD: core identity node differs from its contig")
        reference = (Path(mibig_dir) / receipt["reference"]).resolve()
        if reference.parent != Path(mibig_dir).resolve() or not reference.is_file():
            raise ValueError("NAMED_CONTIG_INPUT_HOLD: reference must be one file inside --mibig-dir")
        from gap_rescue_locus_map import named_ambiguous_contexts, choose, reference_genes
        ref, _ = reference_genes(reference)
        matched = choose(ref, rows, splits, prots, core["contig"])[0]
        named_ambiguous_contexts(named_contigs, label, prots, regions, rows, matched, core["contig"])
        named_inputs.append({"path": str(reference.resolve()), "bytes": reference.stat().st_size,
                             "sha256": hashlib.sha256(reference.read_bytes()).hexdigest()})
        if any(not Path(x["path"]).is_file() or hashlib.sha256(Path(x["path"]).read_bytes()).hexdigest() != x["sha256"] for x in named_inputs):
            raise ValueError("NAMED_CONTIG_INPUT_CHANGED: supplied input changed before rendering")
    out = out or folder
    out.mkdir(parents=True, exist_ok=True)
    if gene_names is not None and getattr(gene_names, "binding", None):
        # receipt of how the name rows bound to this genome (by protein, by length, or not at all)
        (out / "gene_names_binding.json").write_text(json.dumps(
            {"strain": label, "names_bound": len(gene_names), "names_unbound": gene_names.names_unbound,
             "binding": gene_names.binding}, indent=1) + "\n")
    drawn = draw_locus_map(Path(mibig_dir) / receipt["reference"], rows, splits, prots, regions, core, label,
                          receipt.get("reference_name", ""), out / "gap_rescue.png", out / "gap_rescue.pdf", anchor=anchor,
                          context_partners=context_rows, gene_names=gene_names,
                          other_refs=load_other_references(folder, core["identity"]) if other_maps else None,
                          print_width=print_width, row_label=row_label, trim_kb=trim_kb,
                          **({"panel": True, "key": key} if panel else {}),
                          **({"named_contigs": named_contigs} if named_contigs else {}),
                          **({"gecco": gecco} if gecco else {}), **({"scale_bar_up": True} if scale_bar_up else {}))
    if gecco:   # what the GECCO track drew and how its genes bound to this genome
        (out / "gecco_track.json").write_text(json.dumps(drawn.get("gecco", {}), indent=1) + "\n")
    if panel:   # the footnote is off the page: keep it beside the map for the caption
        (out / "gap_rescue_footnote.txt").write_text(drawn["footnote"].rstrip(".") + ".\n")
        # the classes this map fills, for one shared key across the panels (tools/gap_rescue_panel_figure.py)
        (out / "gap_rescue_key.json").write_text(json.dumps(
            {"classes": drawn["key_classes"], "class_unclear": drawn["key_class_unclear"], "key": key,
             **({"gecco": True} if gecco else {})}, indent=1) + "\n")
    if named_contigs:
        if any(not Path(x["path"]).is_file() or hashlib.sha256(Path(x["path"]).read_bytes()).hexdigest() != x["sha256"] for x in named_inputs + named_sources):
            raise ValueError("NAMED_CONTIG_INPUT_CHANGED: preserve partial render as incomplete")
        model = json.dumps({"proteins": prots, "regions": regions}, sort_keys=True, separators=(",", ":")).encode()
        review = {"schema": "sapote.named-contig-review.v1", "scope": "REVIEW_CONTEXT_ONLY", "core_identity": core["identity"],
                  "selections": drawn["named_contig_contexts"], "inputs": named_inputs,
                  "genome_model_sha256": hashlib.sha256(model).hexdigest(),
                  "genome_parse_binding": ({"state": "ZIP_HASH_VERIFIED_BEFORE_AND_AFTER_PARSE", "sha256": genome_zip_parse_sha256}
                                           if genome_zip_parse_sha256 is not None else {"state": "OPERATOR_SUPPLIED_MODEL"}),
                  "historical_alignment_binding": "NOT_ESTABLISHED_BY_REDRAW",
                  "outputs": [{"path": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                              for p in sorted(out.iterdir()) if p.is_file()],
                  "source_bindings": named_sources}
        (out / "named_contig_review.json").write_text(json.dumps(review, indent=2) + "\n")
    return drawn


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
    ap.add_argument("--core", help="core region as <contig>.regionNNN (required unless --redraw)")
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
                    help="pressed Pfam-A.hmm for the housekeeping check of every partner find (env SAPOTE_PFAM_HMM; needs pyhmmer)")
    ap.add_argument("--out", type=Path, help="output folder (required unless --redraw)")
    ap.add_argument("--anchor", help="reference gene name the two figure rows are centred on (default: the longest "
                                     "matched core enzyme on the core contig)")
    ap.add_argument("--redraw", type=Path, help="redraw the figure of an earlier run folder from its saved tables")
    ap.add_argument("--gene-names", type=Path, nargs="+", help="one or more gene-name tables (GENE_BLASTP_NAMES.tsv "
                                                               "columns): name and colour strain genes that match no "
                                                               "reference gene; the first table naming a gene wins. "
                                                               "Rows bind by protein_sha256, else by tag when aa_length "
                                                               "agrees within 1 aa; others are left out and counted in "
                                                               "gene_names_binding.json (redraw only)")
    ap.add_argument("--length-fallback", default=None, help="with --gene-names: a column read as a name row's protein "
                                                             "length when its aa_length is empty, e.g. query_aa_length "
                                                             "(the length of the protein the search sent). The row still "
                                                             "binds by tag only when that length agrees within 1 aa. "
                                                             "Default: none, so such rows are left out (redraw only)")
    ap.add_argument("--context-rows", action="store_true", help="also draw the contigs around matches the map does not "
                                                               "draw, as context only (redraw only)")
    ap.add_argument("--other-maps", action="store_true", help="label strain genes that another reference matched in a "
                                                             "sibling run of the same region (redraw only)")
    ap.add_argument("--print-width", choices=("double", "single", "page6.0", "page6.5", "none"), default="double",
                    help="draw the map at a journal column width with all text >= 8 pt: double = 7.2 in (default), "
                         "single = 3.5 in, page6.0 / page6.5 = a 6.0 or 6.5 in text column; none = the 13.5 in screen "
                         "layout of earlier maps, unchanged")
    ap.add_argument("--trim-kb", type=float, help="with --redraw: crop both rows to the matched genes plus this margin "
                    "(kb) on each side; the title and footnote say so. Default: no crop")
    ap.add_argument("--panel", action="store_true", help="with --redraw and a print width: draw the map as a panel of a "
                    "multi-panel figure: no footnote on the page (it goes in the caption; the receipt keeps it) and "
                    "reference genes with no name labelled by accession alone (the gene table keeps the product)")
    ap.add_argument("--no-key", action="store_true", help="with --panel: leave out the identity colour bar and the "
                    "gene-class legend, for a figure with one shared key")
    ap.add_argument("--row-label", help="text left of the strain row (default --label). House rule 6: a reference strain "
                                        "by its deposited name and strain, accession in brackets, e.g. "
                                        "'Saccharothrix coeruleofusca JCM 3313 [GCF_014648515.1]'; isolates keep AS-xxx")
    ap.add_argument("--named-contig", action="append", default=[], metavar="FOUR_PART_IDENTITY",
                    help="redraw only: add an undrawn ambiguous contig as review context, never a rescue; repeatable. "
                         "Exact 'strain / full contig / regionNNN / BGC###', or explicitly "
                         "'strain / full contig / NO_ANTISMASH_REGION / NO_BGC_ALIAS' for a contig without a region. "
                         "Requires a fresh --out; preserves statuses/counts and adds no reference ribbons")
    ap.add_argument("--gecco-genes", type=Path, help="redraw only: GECCO *.genes.tsv of this genome; draws a GECCO track "
                    "(per-gene probability) under the strain row")
    ap.add_argument("--gecco-clusters", type=Path, help="with --gecco-genes: GECCO *.clusters.tsv of this genome; a line "
                    "under the track spans the drawn genes of each GECCO cluster")
    ap.add_argument("--scale-bar-up", action="store_true", help="redraw only: put the 5 kb bar on the contig-caption line, "
                    "at the right, when it touches no caption")
    ap.add_argument("--hits", type=Path)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--sensitivity", default=SENSITIVITY_DEFAULT,
                    help="DIAMOND search mode (default ultra-sensitive; 'default' uses DIAMOND's own fast mode)")
    ap.add_argument("--no-figure", action="store_true")
    ap.add_argument("--no-gene-table", action="store_true", help="skip gene_table.* and map_and_table.*")
    a = ap.parse_args(argv)
    if a.named_contig and not a.redraw:
        raise SystemExit("--named-contig needs --redraw; it does not run or alter the rescue analysis")
    if a.named_contig and not a.out:
        raise SystemExit("--named-contig needs a fresh --out")
    if (a.gecco_genes or a.gecco_clusters or a.scale_bar_up) and not a.redraw:
        raise SystemExit("--gecco-genes, --gecco-clusters and --scale-bar-up are redraw options; add --redraw")
    if a.gecco_clusters and not a.gecco_genes:
        raise SystemExit("--gecco-clusters needs --gecco-genes")
    if a.no_key and not a.panel:
        raise SystemExit("--no-key is for a figure panel; add --panel")
    if a.panel and (not a.redraw or a.print_width == "none"):
        raise SystemExit("--panel needs --redraw and a print width (double or single)")
    if a.redraw:
        if not a.mibig_dir:
            raise SystemExit("--redraw needs --mibig-dir (or SAPOTE_MIBIG_GBK_DIR) to read the reference GenBank file")
        assert_output_outside_bundle(a.out or a.redraw, __file__)
        try:
            parsed_zip_sha256 = hashlib.sha256(a.zip.read_bytes()).hexdigest() if a.named_contig else None
            prots, regions = load_genome(a.zip, a.label)
            if a.named_contig and hashlib.sha256(a.zip.read_bytes()).hexdigest() != parsed_zip_sha256:
                raise ValueError("NAMED_CONTIG_INPUT_CHANGED: genome ZIP changed during parsing")
            redraw(a.redraw, prots, regions, a.label, a.mibig_dir, a.out, a.anchor,
                   load_gene_names(a.gene_names, a.label, prots, length_fallback=a.length_fallback or None),
                   a.context_rows, a.other_maps,
                   None if a.print_width == "none" else a.print_width, a.row_label, a.trim_kb, a.panel, not a.no_key,
                   **({"named_contigs": a.named_contig, "genome_zip": a.zip,
                       "genome_zip_parse_sha256": parsed_zip_sha256} if a.named_contig else {}),
                   gecco=load_gecco(a.gecco_genes, a.gecco_clusters, prots, a.label) if a.gecco_genes else None,
                   scale_bar_up=a.scale_bar_up)
        except ValueError as exc:
            if a.named_contig and str(exc).startswith("NAMED_CONTIG_"):
                _say(f"[gap_directed_rescue] HOLD: {exc}")
                return 2
            raise
        except OSError as exc:
            if a.named_contig:
                _say(f"[gap_directed_rescue] HOLD: NAMED_CONTIG_IO_HOLD: {exc}; "
                     "preserve any incomplete output")
                return 2
            raise
        _say(f"[gap_directed_rescue] redrew {a.redraw} -> {a.out or a.redraw}")
        return 0
    if not (a.core and a.out):
        raise SystemExit("--core and --out are required (unless --redraw)")
    assert_output_outside_bundle(a.out, __file__)
    prots, regions = load_genome(a.zip, a.label)
    core = resolve_core(regions, a.core)
    sens = None if a.sensitivity == "default" else a.sensitivity
    names = load_mibig_names(a.mibig_names)
    reference, name, source = choose_reference(a.zip, core, prots, a.reference, a.reference_name, a.mibig_dir,
                                               a.mibig_db, names, a.threads, sens)
    if reference is None:
        raise SystemExit(f"[gap_directed_rescue] {core['identity']}: {source}")
    receipt = analyse_region(a.label, prots, regions, core, reference, name, source, a.out,
                             read_hits(a.hits) if a.hits else None, a.threads, a.sensitivity, a.mibig_db, a.pfam,
                             not a.no_figure, anchor=a.anchor, gene_table=not a.no_gene_table, compounds=names,
                             print_width=None if a.print_width == "none" else a.print_width, row_label=a.row_label)
    _say(summary_line(receipt, a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
