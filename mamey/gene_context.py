"""gene_context.py — normalized per-CDS gene context, sealed into the package (v9.7.88).

THE PROBLEM THIS SOLVES (roadmap #1 / AS-XXX finding E)
-------------------------------------------------------
The sealed package did not retain gene-level context. The gene-by-gene builder therefore
could not walk CDS features post-seal and fell back to one synthetic `<bgc>_NOLOCUS` row per
BGC with BGC-level fields under a per-gene header — not gene-resolved at all. Mode B could not
do true gene-by-gene biosynthetic walkthroughs without re-opening the original antiSMASH ZIP,
which is unavailable in a sealed/ChatGPT context.

THE FIX
-------
At run time (GBKs still in hand as parsed CDSFeature/DomainFeature objects) we serialize a
compact, normalized per-CDS table into the package as `<strain>_gene_context.jsonl` — one row
per CDS that falls within a BGC, keyed by bgc_id, carrying the real locus_tag, coordinates,
strand, aa_length, product, sec_met domains, and TTA-codon count. This is the normalized gene
context roadmap #1 asks for: small (no full GBK bloat), self-contained, and the durable source
the gene-by-gene builder and Mode B read post-seal.

Claim-safety note: this is structural/source-derived gene context only (what the GenBank
features say). It asserts no product identity or activity — those remain capacity-level calls
made elsewhere.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os as _os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def _aa_length(translation: str, start: int, end: int) -> int | None:
    if translation:
        return len(translation)
    # fall back to nucleotide span / 3 - 1 (stop) when no translation is present
    if start is not None and end is not None and end > start:
        return max(0, (end - start + 1) // 3 - 1)
    return None


def _tta_codons(nt: str) -> int:
    if not nt:
        return 0
    nt = nt.upper()
    return sum(1 for i in range(0, len(nt) - 2, 3) if nt[i:i + 3] == "TTA")


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    if None in (a_start, a_end, b_start, b_end):
        return False
    return not (a_end < b_start or a_start > b_end)


def build_gene_context(bgcs: Iterable[Any], cds_list: Iterable[Any],
                       domains: Iterable[Any] | None = None) -> dict[str, Any]:
    """Build the normalized per-CDS gene-context structure.

    Returns {"schema_version", "bgcs": {bgc_id: [cds_row, ...]}, "n_cds", "n_bgcs_with_cds"}.
    A CDS is assigned to a BGC when it shares the BGC's contig AND its coordinates overlap the
    BGC span. A CDS may map to more than one BGC only if BGCs overlap (rare); it is listed under
    each. CDS with no BGC overlap are not emitted (gene context is per-lead, not whole-genome).
    """
    bgcs = list(bgcs)
    cds_list = list(cds_list)
    domains = list(domains or [])

    # index domains by locus_tag (primary) for fast per-CDS attachment
    dom_by_locus: dict[str, list] = defaultdict(list)
    for d in domains:
        lt = getattr(d, "locus_tag", "") or ""
        if lt:
            dom_by_locus[lt].append(d)

    # group BGCs by contig so we only test CDS against same-contig BGCs
    bgcs_by_contig: dict[str, list] = defaultdict(list)
    for b in bgcs:
        bgcs_by_contig[getattr(b, "contig", "") or ""].append(b)

    out: dict[str, list] = defaultdict(list)
    n_cds = 0
    for cds in cds_list:
        c_contig = getattr(cds, "contig", "") or ""
        c_start = getattr(cds, "start", None)
        c_end = getattr(cds, "end", None)
        same_contig_bgcs = bgcs_by_contig.get(c_contig, [])
        if not same_contig_bgcs:
            continue
        hit_bgcs = [b for b in same_contig_bgcs
                    if _overlaps(c_start, c_end, getattr(b, "start", None), getattr(b, "end", None))]
        if not hit_bgcs:
            continue

        locus = getattr(cds, "locus_tag", "") or ""
        translation = getattr(cds, "translation", "") or ""
        nt = getattr(cds, "nucleotide_seq", "") or ""
        # sec_met domains for this CDS: by locus_tag, else coordinate overlap on same contig
        doms = dom_by_locus.get(locus, [])
        if not doms and locus == "":
            doms = [d for d in domains
                    if (getattr(d, "contig", "") or "") == c_contig
                    and _overlaps(c_start, c_end, getattr(d, "start", None), getattr(d, "end", None))]
        sec_met = sorted({getattr(d, "domain", "") for d in doms if getattr(d, "domain", "")})

        # v9.7.90: capture the antiSMASH gene_functions/sec_met_domain/note blob so the post-seal
        # locus-map re-render classifies genes identically to the in-run path (closes the K0 gap).
        _q = getattr(cds, "qualifiers", {}) or {}
        _gf_blob = " ".join(_q.get("gene_functions", []) + _q.get("sec_met_domain", [])
                            + _q.get("note", []))
        _gene_kind = (_q.get("gene_kind", [""]) or [""])[0]  # P-CBDB v9.7.100: kept for functional-role profiling

        row = {
            "locus_tag": locus or None,
            "contig": c_contig,
            "start": c_start,
            "end": c_end,
            "strand": getattr(cds, "strand", None),
            "length_bp": (c_end - c_start + 1) if (c_start is not None and c_end is not None) else None,
            "aa_length": _aa_length(translation, c_start, c_end),
            "product": getattr(cds, "product", "") or "",
            "sec_met_domains": sec_met,
            "gene_functions": _gf_blob,
            "gene_kind": _gene_kind,
            "tta_codons": _tta_codons(nt),
            "has_translation": bool(translation),
        }
        for b in hit_bgcs:
            out[b.bgc_id].append(row)
        n_cds += 1

    # deterministic ordering: per BGC, sort CDS by start coordinate
    for bid in out:
        out[bid].sort(key=lambda r: (r["start"] if r["start"] is not None else 0,
                                     r["locus_tag"] or ""))

    return {
        "schema_version": "gene_context/1.0",
        "claim_safety": "Structural gene context from GenBank CDS features; no product-identity "
                        "or activity claim. aa_length from translation when present.",
        "bgcs": dict(out),
        "n_cds": n_cds,
        "n_bgcs_with_cds": len(out),
    }


def write_gene_context(package_dir: str | Path, strain_id: str,
                       bgcs, cds_list, domains=None) -> dict[str, Any]:
    """Write `<strain>_gene_context.jsonl` AND a flat `<strain>_cds_table.csv` into the package.

    The .jsonl is the per-BGC structured form (one line per BGC); the .csv is the flat per-CDS
    table the v9.7.88-K0 patch asks for (bgc_id, contig, region, locus_tag, order, start, end,
    strand, length_aa, sec_met_domains, tta_codons) — easier for figure/render consumers. Both are
    derived from the same build_gene_context call. Returns a summary dict. Never raises."""
    import csv as _csv
    from .crosswalk import assembly_locator as _assembly_locator
    pdir = Path(package_dir)
    # v9.7.409 (CLAUDE_409 provenance anchors): the flat per-CDS / per-domain tables shipped with a
    # bare `bgc_id` (+contig), so a row could not be traced to a strain/region. Build the same
    # bgc_id -> {strain, assembly_locator, contig, region} anchor master_workbook.py leads its sheets
    # with, and prepend it to `_cds_table.csv` and `_domains.csv`.
    _anchor_by_id = {getattr(b, "bgc_id", ""): b for b in (bgcs or [])}
    def _bgc_anchor(bid) -> dict:
        b = _anchor_by_id.get(bid)
        if b is None:
            return {"strain": strain_id, "assembly_locator": "", "contig": "", "region": ""}
        return {
            "strain": strain_id,
            "assembly_locator": _assembly_locator(b),
            "contig": (getattr(b, "node_id", "") or getattr(b, "contig", "") or ""),
            "region": (getattr(b, "antismash_region", "") or ""),
        }
    try:
        ctx = build_gene_context(bgcs, cds_list, domains)
        path = pdir / f"{strain_id}_gene_context.jsonl"
        # Atomic write (.tmp + os.replace): a killed process must not leave a truncated jsonl that
        # load_gene_context() would silently read as fewer rows.
        tmp_path = pdir / f"{strain_id}_gene_context.jsonl.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            header = {k: ctx[k] for k in ("schema_version", "claim_safety",
                                          "n_cds", "n_bgcs_with_cds")}
            fh.write(json.dumps(header) + "\n")
            for bid in sorted(ctx["bgcs"]):
                fh.write(json.dumps({"bgc_id": bid, "cds": ctx["bgcs"][bid]}) + "\n")
        _os.replace(tmp_path, path)

        # flat per-CDS CSV (K0)
        csv_path = pdir / f"{strain_id}_cds_table.csv"
        # v9.7.409: lead with strain/assembly_locator/region (contig already present) so every CDS
        # row is traceable to its durable locus.
        cols = ["strain", "assembly_locator", "region",
                "bgc_id", "contig", "locus_tag", "order", "start", "end", "strand",
                "length_bp", "length_aa", "product", "sec_met_domains", "gene_functions",
                "tta_codons"]
        tmp_csv = pdir / f"{strain_id}_cds_table.csv.tmp"
        with open(tmp_csv, "w", newline="", encoding="utf-8") as cf:
            w = _SafeWriter(cf)
            w.writerow(cols)
            for bid in sorted(ctx["bgcs"]):
                _a = _bgc_anchor(bid)
                for order, r in enumerate(ctx["bgcs"][bid], 1):
                    w.writerow([_a["strain"], _a["assembly_locator"], _a["region"],
                                bid, r.get("contig", ""), r.get("locus_tag") or "",
                                order, r.get("start", ""), r.get("end", ""),
                                r.get("strand", ""), r.get("length_bp", ""),
                                r.get("aa_length", ""), r.get("product", ""),
                                "; ".join(r.get("sec_met_domains", [])),
                                (r.get("gene_functions", "") or "")[:300], r.get("tta_codons", 0)])
        _os.replace(tmp_csv, csv_path)

        # v9.7.325+ (Blue F-domdata): carry the FULL antiSMASH domain annotation + BGC protein
        # sequences INTO the package, so cross-strain / cohort figures can annotate every gene without
        # re-parsing region GBKs (which the sealed package cannot do offline). antiSMASH already
        # computed these (PFAM_domain + aSDomain features via clusterhmmer, and /translation on each
        # CDS) — this is pure pass-through carry-over, NO new HMM/hmmer run. The existing cds_table
        # keeps only the biosynthetic sec_met_domain subset + aa_length; these two files add the rest.
        locus_to_bgc: dict[str, str] = {}
        for bid in ctx["bgcs"]:
            for r in ctx["bgcs"][bid]:
                lt = r.get("locus_tag") or ""
                if lt:
                    locus_to_bgc.setdefault(lt, bid)

        # (a) full per-domain table — every PFAM_domain / aSDomain on a BGC-member gene
        dpath = pdir / f"{strain_id}_domains.csv"
        tmp_d = pdir / f"{strain_id}_domains.csv.tmp"
        n_dom = 0
        with open(tmp_d, "w", newline="", encoding="utf-8") as ddf:
            dw = _SafeWriter(ddf)
            # v9.7.409: lead with the strain/assembly_locator/contig/region anchor (was bgc_id only).
            dw.writerow(["strain", "assembly_locator", "contig", "region",
                         "bgc_id", "locus_tag", "feature_type", "domain", "pfam_acc",
                         "database", "start", "end", "strand", "bitscore", "evalue", "substrate"])
            for d in (domains or []):
                lt = getattr(d, "locus_tag", "") or ""
                bid = locus_to_bgc.get(lt)
                if bid is None:
                    continue  # domain on a non-BGC gene — package is BGC-scoped
                q = getattr(d, "qualifiers", {}) or {}
                pfam = next((str(x) for x in q.get("db_xref", []) if str(x).startswith("PF")), "")
                _a = _bgc_anchor(bid)
                dw.writerow([_a["strain"], _a["assembly_locator"], _a["contig"], _a["region"],
                             bid, lt, getattr(d, "feature_type", ""), getattr(d, "domain", ""),
                             pfam, getattr(d, "database", ""), getattr(d, "start", ""),
                             getattr(d, "end", ""), getattr(d, "strand", ""),
                             getattr(d, "bitscore", None) if getattr(d, "bitscore", None) is not None else "",
                             getattr(d, "evalue", "") or "", getattr(d, "substrate_consensus", "") or ""])
                n_dom += 1
        _os.replace(tmp_d, dpath)

        # (b) BGC-member protein FASTA — translations antiSMASH already carried (for offline HMM/BLASTp reuse)
        fpath = pdir / f"{strain_id}_proteins.faa"
        tmp_f = pdir / f"{strain_id}_proteins.faa.tmp"
        n_prot = 0
        with open(tmp_f, "w", encoding="utf-8") as ff:
            for cds in cds_list:
                lt = getattr(cds, "locus_tag", "") or ""
                tr = getattr(cds, "translation", "") or ""
                bid = locus_to_bgc.get(lt)
                if bid and tr:
                    ff.write(f">{lt} bgc={bid}\n")
                    for i in range(0, len(tr), 60):
                        ff.write(tr[i:i + 60] + "\n")
                    n_prot += 1
        _os.replace(tmp_f, fpath)

        return {"status": "WRITTEN", "file": path.name, "csv": csv_path.name,
                "domains_csv": dpath.name, "proteins_faa": fpath.name,
                "n_domains": n_dom, "n_proteins": n_prot,
                "n_cds": ctx["n_cds"], "n_bgcs_with_cds": ctx["n_bgcs_with_cds"]}
    except Exception as e:
        return {"status": "SKIPPED", "reason": str(e)}


def load_gene_context(package_dir: str | Path, strain_id: str) -> dict[str, list]:
    """Read the sealed gene context back: {bgc_id: [cds_row, ...]}. Empty dict if absent.

    A malformed/corrupted .jsonl fails closed — returns whatever parsed successfully before the
    bad line — but reports it to stderr rather than silently returning a partial dict that's
    indistinguishable from "genuinely sparse gene context" to any of this function's 8 callers."""
    pdir = Path(package_dir)
    path = pdir / f"{strain_id}_gene_context.jsonl"
    if not path.exists():
        return {}
    out: dict[str, list] = {}
    try:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if i == 0 and "bgc_id" not in obj:
                continue  # header line
            if "bgc_id" in obj:
                out[obj["bgc_id"]] = obj.get("cds", [])
    except Exception as exc:
        import sys
        emit(f"[gene_context] WARN: {path.name} failed to load cleanly "
              f"({type(exc).__name__}: {exc}); returning {len(out)} BGC(s) parsed before the "
              f"failure, not the full file.", file=sys.stderr)
        return out
    return out
