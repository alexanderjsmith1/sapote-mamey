#!/usr/bin/env python3
"""gap_rescue_gene_table.py — the per-gene table of a gap-rescue run, paired with its locus map.

Reader-side and NON-SCORING. One row per reference gene, in reference order:
- the strain protein that best matches it (reciprocal search over the whole genome), its length and its protein family
  (antiSMASH smCOG, else the antiSMASH Pfam descriptions);
- the reference gene's name and a short annotation (its GenBank note, else smCOG, else product);
- amino-acid identity;
- where the protein lies: in the core region (naming its contig), on the core contig outside the region, on another
  contig (with the partner-check flag: paralog family, ambiguous, single gene), or not found. Rows say when one
  strain protein is the best match for several reference genes, and when the tool called a reference gene split
  across contig ends (or found only a weaker split candidate).

Writes, into the run folder: gene_table.tsv (always), gene_table.png/.pdf (with matplotlib), and map_and_table.png
(the map above the table) and map_and_table.pdf (page 1 the map, page 2 the table) when gap_rescue.png/.pdf exist and
Pillow and pypdf are installed. A missing optional library skips that output with a message; it never fails a run.

gap_directed_rescue.analyse_region calls write_gene_table after drawing the map. Run alone to rebuild the table of
an earlier run folder:
  python tools/gap_rescue_gene_table.py --run <gap-rescue folder> --zip <antiSMASH.zip> --reference <reference .gbk>

Claim safety: identity to a characterised gene is similarity, not proof of the same function or product. The
reference annotation describes the reference gene, not the strain protein. Genes on another contig are linked by
homology to one reference, not by assembly; no contigs are joined.
"""
from __future__ import annotations

import argparse
import csv
import re
import textwrap
from pathlib import Path

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401

from mamey.logging_setup import get_logger as _get_logger

_OUT = _get_logger(__name__)

# These are saved full-protein lengths; their ratio is not alignment coverage.
COLS = ["CDS", "Size (aa)", "Protein family (antiSMASH)", "Reference gene", "Reference size (aa)", "Local/reference size ratio",
        "Reference annotation", "Identity (%)", "Location"]
FLAG = {"SUPPORTED": "", "PARALOG_FAMILY": "; paralog family", "SINGLE_GENE": "; single gene"}



def protein_families(prots: dict) -> dict:
    """Map generated protein IDs and locus tags without silently replacing a family.

    Equal aliases retain the existing lookup behavior. Conflicting annotations cannot
    be assigned safely to a shared key, so refuse before writing a gene table.
    """
    families = {key: value.get("family", "") for key, value in prots.items()}
    for value in prots.values():
        key, family = value["tag"], value.get("family", "")
        if key in families and families[key] != family:
            raise ValueError(f"Ambiguous protein-family key {key!r}: generated IDs and locus tags "
                             "have conflicting family annotations")
        families[key] = family
    return families


def smcog(gene_functions: list) -> str:
    """The smCOG description from antiSMASH /gene_functions, or ''."""
    for g in gene_functions or []:
        m = re.search(r"SMCOG\d+:\s*(.+?)(?:\s*\(Score|$)", " ".join(str(g).split()))
        if m:
            return m.group(1).strip()
    return ""


def tidy_annotation(note: str) -> str:
    """Shorten a reference annotation for a table cell: a COG string gives its last COG description, a Sanger-style
    note ('SC6A5.08, probable phytoene synthase, len: ...') gives its description, anything else is capped at 90
    characters."""
    note = " ".join((note or "").split())
    # A GenBank evidence note describes how the record was annotated, not what the gene does. Letting it through
    # filled the annotation column with "Derived by automated computational analysis..." and hid the smCOG or
    # product that would have carried a function. The clause is cut wherever it sits, because a note can open
    # with something real ("frameshifted; Derived by automated computational analysis...") that is worth keeping.
    note = re.sub(r"\s*derived by automated computational analysis[^;]*;?", "", note, flags=re.I)
    note = re.sub(r"^\s*(evidence:|##)[^;]*;?\s*", "", note, flags=re.I)
    note = note.strip(" ;,")
    m = re.findall(r"COG:?\s*COG\d+\s+([^.]+)", note)
    if m:
        return m[-1].strip()
    m = re.match(r"^[A-Z][\w.]*\d[\w.]*,\s*(.+?),\s*len:", note)
    if m:
        return m.group(1).strip()
    return note if len(note) <= 90 else note[:87].rsplit(" ", 1)[0] + "..."


def reference_annotations(reference_gbk) -> dict:
    """gene name (and locus tag, protein id) -> short annotation, from the reference GenBank."""
    from mamey import parsers
    out = {}
    for rec in parsers._require_seqio().parse(str(reference_gbk), "genbank"):
        for f in rec.features:
            if f.type != "CDS":
                continue
            q = f.qualifiers
            text = tidy_annotation(q.get("note", [""])[0]) or smcog(q.get("gene_functions")) or q.get("product", [""])[0]
            keys = [q.get(k, [""])[0] for k in ("gene", "locus_tag", "protein_id")]
            for k in keys:
                if k:
                    out.setdefault(k, text)
    return out


def _node(text: str) -> str:
    m = re.search(r"(NODE_\d+)", text or "")
    return m.group(1) if m else (text or "").split("_length")[0].split(" ")[0]


def _location(r: dict, core_bgc: str, core_contig: str) -> str:
    st, reg, v = r.get("status", ""), r.get("best_region_identity", "") or "", r.get("partner_verdict", "") or ""
    if st == "PRESENT_IN_CORE":
        return f"{core_bgc}, {_node(r.get('best_contig', ''))} (core)"
    if st.startswith("MISSING_FOUND"):
        flag = FLAG.get(v, f"; {v.lower().replace('_', ' ')}" if v else "")
        amb = "; ambiguous" if st == "MISSING_FOUND_AMBIGUOUS" else ""
        if core_contig and r.get("best_contig") == core_contig:
            return f"{_node(core_contig)}, same contig, outside the region{amb}{flag}"
        bits = reg.split(" / ")
        where = f"{bits[-1]}, {_node(bits[1])}" if len(bits) == 4 else f"{_node(r.get('best_contig', ''))}, no antiSMASH region"
        return f"{where}, other contig{amb}{flag}"
    if st and st != "MISSING_NOT_FOUND":   # a status this table does not know: name it, never call it "not found"
        return f"status {st.lower().replace('_', ' ')}"
    return "not found"


def split_notes(splits) -> dict:
    """reference gene name -> note, from the tool's split-gene rows (status SPLIT_ACROSS_CONTIG_ENDS).

    Only a CLEAR call reads "split across"; the map draws only CLEAR splits. WEAK and RIVAL_STRONGER are named as
    candidates. MODULAR_UNRESOLVED (an assembly-line gene, where repeated modules can fake two pieces) is named as
    unresolved, without contigs.
    """
    out = {}
    for x in splits or []:
        if x.get("status") != "SPLIT_ACROSS_CONTIG_ENDS":
            continue
        nodes = " + ".join(_node(x.get(k, "")) for k in ("piece1_region_identity", "piece2_region_identity") if x.get(k))
        call = x.get("split_call", "")
        if call == "CLEAR":
            out[x["name"]] = f"; split across {nodes}"
        elif call == "RIVAL_STRONGER":
            out[x["name"]] = f"; weaker split candidate on {nodes}"
        elif call == "WEAK":
            out[x["name"]] = f"; weak split candidate on {nodes}"
        elif call == "MODULAR_UNRESOLVED":
            out[x["name"]] = "; modular gene, split not resolved"
    return out


def _num(v) -> str:
    try:
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return str(v or "")


def _len(v) -> str:
    """A saved positive whole-protein length in aa, or blank if absent or invalid."""
    try:
        n = float(v)
        return str(int(n)) if n > 0 and n.is_integer() else ""
    except (TypeError, ValueError, OverflowError):
        return ""


def _ratio(ours, ref) -> str:
    """Dimensionless local/reference full-protein length ratio, not alignment coverage.

    No single ratio is assigned to two separate split pieces.
    """
    a, b = _len(ours), _len(ref)
    if not a or not b:
        return ""
    try:
        return f"{int(a) / int(b):.2f}"
    except (ValueError, OverflowError):
        return ""


def edge_shares(rows, prots: dict, core: dict | None) -> dict:
    """best_locus -> percent of that gene inside the core region, for PRESENT_IN_CORE genes that only partly lie in it.

    Region membership is decided by coordinate overlap, so a gene that straddles the region boundary is still "in the
    core"; the table says so. Coordinates are those of the genome records the run read."""
    if not core:
        return {}
    by_tag = {v.get("tag"): v for v in prots.values()}
    out = {}
    for r in rows:
        if r.get("status") != "PRESENT_IN_CORE" or not r.get("best_locus"):
            continue
        p = prots.get(r.get("best_protein", "")) or by_tag.get(r["best_locus"])
        if not p or p.get("contig") != core.get("contig") or p["end"] <= p["start"]:
            continue
        inside = max(0, min(p["end"], core["end"]) - max(p["start"], core["start"]))
        if inside < p["end"] - p["start"]:
            out[r["best_locus"]] = round(100 * inside / (p["end"] - p["start"]))
    return out


def table_rows(rows, splits, core_identity: str, families: dict, annotations: dict, edge: dict | None = None,
               known_tags=None) -> list[dict]:
    """One dict per reference gene (COLS keys). `rows` are the gap-rescue table rows (gap_rescue.tsv); `families` maps
    a strain protein (best_protein id or best_locus tag) to its family; `known_tags` are this genome's locus tags, so a
    split whose pieces are not both in it is not shown as one."""
    rows = sorted(rows, key=lambda r: int(r.get("reference_gene") or 0))
    core_bgc = core_identity.split(" / ")[-1] if core_identity else "core"
    cc = [r.get("best_contig") for r in rows if r.get("status") == "PRESENT_IN_CORE"]
    core_contig = max(set(cc), key=cc.count) if cc else ""
    sn, first, out = split_notes(splits), {}, []
    import os as _o, sys as _s
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from gap_rescue_locus_map import split_display
    # the rule the map and the counts share: which genes are shown as one split row, which keep their core row with the
    # split noted, and which keep their own status because a piece is not in this genome
    disp = split_display(rows, splits, core_identity, known_tags)
    unplaced = {i: e for i, e in split_display(rows, splits, core_identity).items() if i not in disp}

    def _piece(x, k):
        bits = (x.get(k + "_region_identity") or "").split(" / ")
        return ((bits[-1] + ", " if len(bits) == 4 else "") + _node(x.get(k + "_region_identity", ""))
                + (" (core)" if core_identity and x.get(k + "_region_identity") == core_identity else ""))
    clear = {i for i, e in disp.items() if e["shown"]}
    # When one protein is the best match for several reference genes, the map draws a ribbon for every one of those
    # rows and marks the protein "matches N reference genes". The table names one row as the primary (reciprocal best
    # first, then highest identity) and the others read "same protein as <primary>". A shared match is an observation;
    # whether it reflects a fused gene, a duplication or a paralog is a hypothesis the table does not decide.
    by = {}
    for i, r in enumerate(rows):
        if r.get("status") != "MISSING_NOT_FOUND" and r.get("best_locus") and i not in clear:
            by.setdefault(r["best_locus"], []).append(r)
    for locus, rs in by.items():
        if len(rs) > 1:
            first[locus] = max(rs, key=lambda r: (str(r.get("reciprocal_best")) == "True",
                                                  float(r.get("best_identity_pct") or 0))).get("name", "")
    for i, r in enumerate(rows):
        if i in clear:   # the map draws the two pieces of this split, so the row names them, not the best whole-gene hit
            x = disp[i]["record"]
            fams = [families.get(x.get(k + "_locus", ""), "") for k in ("piece1", "piece2")]
            out.append({"CDS": f"{x.get('piece1_locus', '')} + {x.get('piece2_locus', '')}", "Size (aa)": "",
                        "Protein family (antiSMASH)": " / ".join(f or "-" for f in fams) if any(fams) else "",
                        "Reference gene": r.get("name", ""),
                        "Reference size (aa)": _len(r.get("reference_len_aa")),
                        "Local/reference size ratio": "",
                        "Reference annotation": annotations.get(r.get("name", "")) or r.get("reference_product", ""),
                        "Identity (%)": f"{_num(x.get('piece1_identity_pct'))} / {_num(x.get('piece2_identity_pct'))}",
                        "Location": "split across " + " + ".join(_piece(x, k) for k in ("piece1", "piece2"))})
            continue
        found = r.get("status") != "MISSING_NOT_FOUND" and bool(r.get("best_locus"))
        loc = _location(r, core_bgc, core_contig)
        if found and first.get(r["best_locus"], r.get("name", "")) != r.get("name", ""):
            loc += f"; same protein as {first[r['best_locus']]}"
        if found and r.get("status") == "PRESENT_IN_CORE" and (edge or {}).get(r["best_locus"]) is not None:
            loc += f"; crosses the region edge ({edge[r['best_locus']]}% of the gene inside)"
        if i in disp:   # a split never overrides a core call: the core row stands and the split is noted
            loc += "; also a clear split across " + " + ".join(_piece(disp[i]["record"], k) for k in ("piece1", "piece2"))
        elif i in unplaced:   # the gene keeps its own status: a piece of the reported split is not in this genome
            x = unplaced[i]["record"]
            loc += ("; a clear split across " + " + ".join(_node(x.get(k + "_region_identity", "")) for k in
                                                           ("piece1", "piece2")) + " was reported, but a piece is not in this genome")
        else:
            loc += sn.get(r.get("name", ""), "")
        fam = families.get(r.get("best_protein", "")) or families.get(r.get("best_locus", "")) or ""
        out.append({"CDS": r["best_locus"] if found else ("not found" if r.get("status") in ("MISSING_NOT_FOUND", "", None)
                                                          else "-"),
                    "Size (aa)": str(r.get("best_len_aa") or "") if found else "",
                    "Protein family (antiSMASH)": fam if found else "",
                    "Reference gene": r.get("name", ""),
                    "Reference size (aa)": _len(r.get("reference_len_aa")),
                    "Local/reference size ratio": _ratio(r.get("best_len_aa"), r.get("reference_len_aa")) if found else "",
                    "Reference annotation": annotations.get(r.get("name", "")) or r.get("reference_product", ""),
                    "Identity (%)": _num(r.get("best_identity_pct")) if found else "",
                    "Location": loc})
    return out


def _draw(table: list[dict], title: str, label: str, png: Path, pdf: Path, caption: str = "") -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        _OUT.warning("[gap_rescue_gene_table] matplotlib absent: gene_table.png/.pdf not drawn")
        return False
    ink, sub, rule = "#17212E", "#54637A", "#D5DAE1"
    heads = [f"CDS\n({label})", "Size (aa)", "Protein family (antiSMASH)", "Reference gene", "Reference\nsize (aa)",
             "Local/ref.\nsize ratio", "Reference annotation", "Identity\n(%)", f"In\n{label}"]
    widths, wraps = [0.085, 0.05, 0.17, 0.08, 0.065, 0.075, 0.185, 0.06, 0.24], [12, 6, 27, 14, 6, 6, 30, 6, 38]
    cells = [[textwrap.fill(str(v), w) for v, w in zip(row.values(), wraps)] for row in table]
    nlines = [max(c.count("\n") + 1 for c in row) for row in cells]
    cap = textwrap.fill(caption, 175) if caption else ""
    cap_h = 0.22 * (cap.count("\n") + 1) + 0.1 if cap else 0.0
    H = 1.32 + cap_h + 0.2 * sum(nlines) + 0.12 * len(cells)
    with plt.rc_context({"font.family": ["Arial", "DejaVu Sans"], "pdf.fonttype": 42}):
        fig = plt.figure(figsize=(13.3, H))
        fig.text(0.02, 1 - 0.25 / H, title, fontsize=13, fontweight="bold", color=ink, va="top")
        if cap:   # the same counts, in the same words, as the map's footnote
            fig.text(0.02, 1 - 0.62 / H, cap, fontsize=9, color=sub, va="top", linespacing=1.25)
        y, x = 1 - (0.7 + cap_h) / H, 0.02
        for c, wd in zip(heads, widths):
            fig.text(x, y, c, fontsize=9, fontweight="bold", color=ink, va="top"); x += wd * 0.96 / sum(widths)
        y -= (0.32 + 0.17 * max(h.count("\n") for h in heads)) / H
        fig.add_artist(plt.Line2D([0.02, 0.98], [y + 0.06 / H] * 2, color=ink, linewidth=0.8))
        for row, n in zip(cells, nlines):
            x = 0.02
            for v, wd in zip(row, widths):
                fig.text(x, y, v, fontsize=8.5, color=sub if v == "not found" else ink, va="top", linespacing=1.15)
                x += wd * 0.96 / sum(widths)
            y -= (0.2 * n + 0.12) / H
            fig.add_artist(plt.Line2D([0.02, 0.98], [y + 0.06 / H] * 2, color=rule, linewidth=0.5))
        fig.savefig(png, dpi=200)
        fig.savefig(pdf)
        plt.close(fig)
    return True


def pair_with_map(out: Path) -> list[Path]:
    """map_and_table.png/.pdf from gap_rescue.png/.pdf and gene_table.png/.pdf in `out`, when all four exist."""
    m_png, m_pdf, t_png, t_pdf = (out / "gap_rescue.png", out / "gap_rescue.pdf", out / "gene_table.png",
                                  out / "gene_table.pdf")
    if not all(p.exists() for p in (m_png, m_pdf, t_png, t_pdf)):
        return []
    made = []
    try:
        from PIL import Image
        a, b = Image.open(m_png).convert("RGB"), Image.open(t_png).convert("RGB")
        w = max(a.width, b.width)
        a = a.resize((w, round(a.height * w / a.width))); b = b.resize((w, round(b.height * w / b.width)))
        c = Image.new("RGB", (w, a.height + b.height), "white"); c.paste(a, (0, 0)); c.paste(b, (0, a.height))
        c.save(out / "map_and_table.png", dpi=(200, 200)); made.append(out / "map_and_table.png")
    except ImportError:
        _OUT.warning("[gap_rescue_gene_table] Pillow absent: map_and_table.png not made")
    try:
        from pypdf import PdfReader, PdfWriter
        w = PdfWriter()
        for src in (m_pdf, t_pdf):
            for pg in PdfReader(str(src)).pages:
                w.add_page(pg)
        w.write(str(out / "map_and_table.pdf")); made.append(out / "map_and_table.pdf")
    except ImportError:
        _OUT.warning("[gap_rescue_gene_table] pypdf absent: map_and_table.pdf not made")
    return made


def write_gene_table(out, rows, splits, core_identity: str, label: str, reference, families: dict,
                     ref_name: str = "", edge: dict | None = None, known_tags=None, *, pair_map: bool = True) -> dict:
    """Write table outputs; returns {"rows": n, "files": [...]}, counts and captions.

    pair_map keeps saved-map pairing for standalone replay by default. A fresh caller
    must explicitly admit a successfully rendered current map before pairing it.
    """
    out = Path(out)
    table = table_rows(rows, splits, core_identity, families, reference_annotations(reference), edge, known_tags)
    with open(out / "gene_table.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(table)
    files = [out / "gene_table.tsv"]
    core_bgc = core_identity.split(" / ")[-1] if core_identity else "core"
    title = f"{label} {core_bgc} genes against the {ref_name or Path(reference).stem} reference ({Path(reference).stem}), by gap rescue"
    # The counts come from the renderer's count_summary, so the table caption and the map footnote cannot disagree.
    import os as _o, sys as _s
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from gap_rescue_locus_map import count_summary, count_sentence
    counts = count_summary(rows, splits, core_identity, known_tags)
    caption = count_sentence(counts, core_identity or "the core") + "."
    rendered_caption = caption + " Size ratio = local/reference full-protein length; not alignment coverage."
    with open(out / "gene_table_counts.tsv", "w", newline="") as fh:   # one row per pair, for inventories to read
        w = _SafeDictWriter(fh, fieldnames=list(counts), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerow(counts)
    files.append(out / "gene_table_counts.tsv")
    if _draw(table, title, label, out / "gene_table.png", out / "gene_table.pdf", rendered_caption):
        files += [out / "gene_table.png", out / "gene_table.pdf"]
        # The table must be current, and its caller must admit the map separately.
        if pair_map:
            files += pair_with_map(out)
    return {"rows": len(table), "files": [str(f) for f in files], "counts": counts, "caption": caption,
            "rendered_caption": rendered_caption}


# ---- Genes in the window (card attine_452_locus_gene_tables) ------------------------------------------------------
# A second table per run, read from the strain side: every CDS in the cropped map window (matched genes on the core
# contig plus trim on each side), with its antiSMASH role and domains, the reference gene it matches, and its BLASTp
# top-10 name bound by protein. The reference-side table above is unchanged.
WINDOW_COLS = ["locus_tag", "start", "end", "strand", "aa", "antiSMASH_role", "domains_E_value", "smCOG",
               "reference_gene_match", "BLASTp_name", "BLASTp_db", "BLASTp_top10_mean_id", "BLASTp_name_share"]
SUMMARY_COLS = ["identity", "antiSMASH_product", "reference", "reference_name", "reference_genes", "in_region",
                "distinct_proteins_in_region", "median_identity_in_region", "found_clearly_elsewhere",
                "supported_elsewhere", "window_contig", "window_start", "window_end", "genes_in_window",
                "genes_matched_in_window", "biosynthetic_in_window", "BLASTp_named_in_window"]
WINDOW_STATUSES = ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR")
_SEC_MET = re.compile(r"(\S+) \(E-value: ([^,]+)")
_NRPS_PKS = re.compile(r"Domain: (\S+) \(\d+-\d+\)\. E-value: ([^.]+?\.?\d*e?-?\d*)\.")


def genome_cds(zip_path) -> tuple[dict, dict]:
    """-> ({locus tag: CDS facts}, {(contig, region number): antiSMASH product}) from the whole-genome GenBank of an
    antiSMASH ZIP. Domains are the rule-based sec_met domains and the NRPS/PKS domains, each with its E-value."""
    import io
    import zipfile
    try:
        from Bio import SeqIO
    except ImportError:  # biopython absent: the bundle's GenBank shim reads the same records
        from mamey._gbk_shim import SeqIO
    z = zipfile.ZipFile(zip_path)
    gbk = next(n for n in z.namelist() if n.endswith(".gbk") and ".region" not in n and not Path(n).name.startswith("._"))
    cds, products = {}, {}
    for rec in SeqIO.parse(io.StringIO(z.read(gbk).decode(errors="replace")), "genbank"):
        for f in rec.features:
            q = f.qualifiers
            if f.type == "region":
                products[(rec.id, int(q.get("region_number", ["0"])[0]))] = "; ".join(q.get("product", []))
            if f.type != "CDS":
                continue
            doms = []
            for d in q.get("sec_met_domain", []):
                m = _SEC_MET.match(d)
                doms.append(f"{m.group(1)} ({m.group(2)})" if m else d.split(" (")[0])
            for d in q.get("NRPS_PKS", []):
                m = _NRPS_PKS.match(d)
                if m:
                    doms.append(f"{m.group(1)} ({m.group(2)})")
            cds[q.get("locus_tag", [""])[0]] = {
                "contig": rec.id, "start": int(f.location.start) + 1, "end": int(f.location.end),
                "strand": "+" if (f.location.strand or 1) > 0 else "−", "aa": len(q.get("translation", [""])[0]),
                "role": q.get("gene_kind", [""])[0], "domains": "; ".join(dict.fromkeys(doms)),
                "smcog": smcog(q.get("gene_functions", []))}
    return cds, products


def _contig_key(contig: str) -> str:
    """An assembler contig name up to its length (NODE_7_length_5000), which is unique within an assembly; other names
    are returned unchanged."""
    m = re.match(r"(NODE_\d+_length_\d+)_", contig or "")
    return m.group(1) if m else (contig or "")


def window_rows(rows, cds: dict, core_identity: str, names=None, trim_bp: int = 2000) -> tuple[list[dict], dict]:
    """The genes in the window -> (table rows, window facts). The window is the core contig from the first to the last
    gene that matches a reference gene there (in the region, or found clearly elsewhere on it), plus trim_bp each side.
    names: {locus tag: BLASTp name row} (load_gene_names, bound by protein)."""
    names = names or {}
    core_contig = core_identity.split(" / ")[1]
    match = {}
    for r in rows:
        if r.get("status") in WINDOW_STATUSES and r.get("best_locus"):
            match.setdefault(r["best_locus"], []).append(f'{r["name"]} {float(r["best_identity_pct"]):.0f}%')
    # antiSMASH can rewrite the coverage part of an assembler contig name in its GenBank record ids
    # (cov_54.074455 -> cov_54.74455), so contigs are matched on the name before the coverage.
    core_key = _contig_key(core_contig)
    on_core = [t for t in match if t in cds and _contig_key(cds[t]["contig"]) == core_key]
    if not on_core:
        raise ValueError(f"GENE_WINDOW: no matched gene on the core contig {core_contig}")
    lo = min(cds[t]["start"] for t in on_core) - trim_bp
    hi = max(cds[t]["end"] for t in on_core) + trim_bp
    tags = sorted((t for t, c in cds.items() if _contig_key(c["contig"]) == core_key and c["end"] > lo and c["start"] < hi),
                  key=lambda t: cds[t]["start"])
    out = []
    for t in tags:
        c, n = cds[t], names.get(t) or {}
        out.append({"locus_tag": t, "start": c["start"], "end": c["end"], "strand": c["strand"], "aa": c["aa"],
                    "antiSMASH_role": c["role"], "domains_E_value": c["domains"], "smCOG": c["smcog"],
                    "reference_gene_match": "; ".join(match.get(t, [])),
                    "BLASTp_name": n.get("top10_consensus_name", ""), "BLASTp_db": n.get("db", ""),
                    "BLASTp_top10_mean_id": n.get("top10_mean_identity", ""),
                    "BLASTp_name_share": n.get("consensus_share", "")})
    facts = {"window_contig": core_contig, "window_start": lo, "window_end": hi, "genes_in_window": len(out),
             "genes_matched_in_window": sum(1 for o in out if o["reference_gene_match"]),
             "biosynthetic_in_window": sum(1 for o in out if o["antiSMASH_role"] == "biosynthetic"),
             "BLASTp_named_in_window": sum(1 for o in out if o["BLASTp_name"])}
    return out, facts


def run_summary(rows, receipt: dict, products: dict, facts: dict) -> dict:
    """One summary row for a run: the four-part identity, the antiSMASH product, the reference, and the counts."""
    import statistics
    ident = receipt["core"]
    parts = ident.split(" / ")
    m = re.match(r"region(\d+)", parts[2]) if len(parts) > 2 else None
    core = [r for r in rows if r.get("status") == "PRESENT_IN_CORE"]
    ids = [float(r["best_identity_pct"]) for r in core if r.get("best_identity_pct")]
    return {"identity": ident, "antiSMASH_product": products.get((parts[1], int(m.group(1))), "") if m else "",
            "reference": Path(receipt.get("reference", "")).stem, "reference_name": receipt.get("reference_name", ""),
            "reference_genes": len(rows), "in_region": len(core),
            "distinct_proteins_in_region": len({r["best_protein"] for r in core if r.get("best_protein")}),
            "median_identity_in_region": f"{statistics.median(ids):.1f}" if ids else "",
            "found_clearly_elsewhere": sum(1 for r in rows if r.get("status") == "MISSING_FOUND_CLEAR"),
            "supported_elsewhere": sum(1 for r in rows if r.get("status") == "MISSING_FOUND_CLEAR"
                                       and r.get("partner_verdict") == "SUPPORTED"),
            **facts}


PRINT_HEADS = ["Locus tag", "Position, strand", "aa", "antiSMASH role", "Domains (E-value)", "Reference gene matched",
               "BLASTp top-10 name (db, mean identity)"]
PRINT_SHARE = [0.085, 0.13, 0.045, 0.12, 0.24, 0.13, 0.25]
PRINT_PT = 8.0
CHAR_IN = 0.062   # wrap estimate for 8 pt Arial; the drawn text is measured afterwards and an overflow is refused


def _print_cells(r: dict) -> list[str]:
    name = r["BLASTp_name"]
    if name:
        try:
            name = f'{name} ({r["BLASTp_db"]} {float(r["BLASTp_top10_mean_id"]):.1f}%)'
        except ValueError:
            name = f'{name} ({r["BLASTp_db"]})'
    return [r["locus_tag"], f'{r["start"]:,}–{r["end"]:,} {r["strand"]}', str(r["aa"]), r["antiSMASH_role"],
            r["domains_E_value"] or "–", r["reference_gene_match"], name]


def draw_window_table(table: list[dict], title: str, pdf: Path, png_prefix: Path, width_in: float = 10.0,
                      page_h_in: float = 7.5) -> list[Path]:
    """The genes in the window as a print table: every text at 8 pt, pages of at most page_h_in. The title, headers and
    cells are wrapped to their columns and then measured; any text wider than its space is refused
    (GENE_WINDOW_PRINT), never shrunk. -> the files written."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import os as _o, sys as _s
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from gap_rescue_locus_map import savefig_metadata
    ink, rule = "#17212E", "#D5DAE1"
    margin, line_in, pad_in = 0.3, PRINT_PT * 1.25 / 72, 0.06
    usable = width_in - 2 * margin
    cols = [s * usable for s in PRINT_SHARE]
    wraps = [max(4, int((c - 0.08) / CHAR_IN)) for c in cols]
    heads = [textwrap.fill(h, max(4, int((c - 0.08) / (CHAR_IN * 1.12)))) for h, c in zip(PRINT_HEADS, cols)]
    title_w = textwrap.fill(title, max(20, int(usable / (CHAR_IN * 1.12))))
    t_lines, h_lines = title_w.count("\n") + 1, max(h.count("\n") + 1 for h in heads)
    head_in = 0.12 + t_lines * line_in + 0.12 + h_lines * line_in + 0.1
    cells = [[textwrap.fill(v, w, break_long_words=True) if v else "" for v, w in zip(_print_cells(r), wraps)]
             for r in table]
    heights = [max(c.count("\n") + 1 for c in row) * line_in + pad_in for row in cells]
    pages, cur, h = [], [], head_in
    for row, rh in zip(cells, heights):
        if cur and h + rh > page_h_in - margin:
            pages.append(cur); cur, h = [], head_in
        cur.append((row, rh)); h += rh
    if cur:
        pages.append(cur)

    def place(fig, rend, x, y, H, text, space, **kw):
        txt = fig.text(x / width_in, y / H, text, fontsize=PRINT_PT, va="top", linespacing=1.25, **kw)
        w_in = txt.get_window_extent(rend).width / fig.dpi
        if w_in > space + 1e-6:
            raise ValueError(f"GENE_WINDOW_PRINT: {text[:40]!r} is {w_in:.2f} in wide in {space:.2f} in")

    written = []
    # savefig.bbox pinned: a global "tight" left by another module would crop the page off the print width
    with plt.rc_context({"font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "pdf.fonttype": 42,
                         "savefig.bbox": "standard"}), \
            PdfPages(pdf, metadata=savefig_metadata(pdf, "gap_rescue_gene_table")) as book:
        for pi, page in enumerate(pages, 1):
            H = head_in + sum(rh for _, rh in page) + margin
            fig = plt.figure(figsize=(width_in, H))
            rend = fig.canvas.get_renderer()
            try:
                t = title_w + (f" ({pi} of {len(pages)})" if len(pages) > 1 else "")
                place(fig, rend, margin, H - 0.12, H, t, usable, fontweight="bold", color=ink)
                y, x = H - 0.12 - t_lines * line_in - 0.12, margin
                for hd, cw in zip(heads, cols):
                    place(fig, rend, x, y, H, hd, cw - 0.04, fontweight="bold", color=ink); x += cw
                y -= h_lines * line_in + 0.04
                fig.add_artist(plt.Line2D([margin / width_in, 1 - margin / width_in], [y / H] * 2, color=ink, lw=0.8))
                y -= 0.06
                for row, rh in page:
                    x = margin
                    for v, cw in zip(row, cols):
                        if v:
                            place(fig, rend, x, y, H, v, cw - 0.04, color=ink)
                        x += cw
                    y -= rh
                    fig.add_artist(plt.Line2D([margin / width_in, 1 - margin / width_in], [(y + 0.02) / H] * 2,
                                              color=rule, lw=0.5))
            except ValueError:
                plt.close(fig)
                raise
            book.savefig(fig, facecolor="white")
            png = png_prefix.with_name(png_prefix.name + (f"_page{pi}.png" if len(pages) > 1 else ".png"))
            fig.savefig(png, dpi=300, facecolor="white", metadata=savefig_metadata(png, "gap_rescue_gene_table"))
            written.append(png)
            plt.close(fig)
    return [pdf] + written


def write_window_table(out, run: Path, zip_path, names=None, trim_bp: int = 2000, label: str = "",
                       draw: bool = True, width_in: float = 10.0) -> dict:
    """gene_window_table.tsv (+ gene_window_table.pdf/png, 8 pt) and gene_window_summary.tsv for one gap-rescue run
    folder, written to out (the run folder is only read)."""
    import json
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((Path(run) / "gap_rescue_receipt.json").read_text())
    with open(Path(run) / "gap_rescue.tsv", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    cds, products = genome_cds(zip_path)
    table, facts = window_rows(rows, cds, receipt["core"], names, trim_bp)
    with open(out / "gene_window_table.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=WINDOW_COLS, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(table)
    summary = run_summary(rows, receipt, products, facts)
    with open(out / "gene_window_summary.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=SUMMARY_COLS, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerow(summary)
    files = [out / "gene_window_table.tsv", out / "gene_window_summary.tsv"]
    if draw:
        ref = receipt.get("reference_name") or Path(receipt.get("reference", "")).stem
        title = (f"Genes in the window: {receipt['core']}, against the {ref} reference "
                 f"({Path(receipt.get('reference', '')).stem}); matched genes ± {trim_bp / 1000:g} kb")
        files += draw_window_table(table, title, out / "gene_window_table.pdf", out / "gene_window_table", width_in)
    return {"rows": len(table), "summary": summary, "files": [str(f) for f in files]}


def merge_summaries(folders, out_tsv) -> int:
    """One summary table from the gene_window_summary.tsv of each folder, in the order given."""
    rows = []
    for f in folders:
        with open(Path(f) / "gene_window_summary.tsv", newline="") as fh:
            rows += list(csv.DictReader(fh, delimiter="\t"))
    with open(out_tsv, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=SUMMARY_COLS, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    return len(rows)


def window_main(argv) -> int:
    ap = argparse.ArgumentParser(description="Genes in the window of gap-rescue runs, and one summary table.")
    ap.add_argument("--window", action="store_true", help="write the genes-in-the-window table of --run into --out")
    ap.add_argument("--summary", nargs="+", type=Path, help="folders written by --window: merge their summaries into --out")
    ap.add_argument("--run", type=Path, help="a gap_directed_rescue output folder (read only)")
    ap.add_argument("--zip", type=Path, help="the antiSMASH ZIP the run used")
    ap.add_argument("--label", default="", help="strain label (default: the run receipt's)")
    ap.add_argument("--gene-names", nargs="*", type=Path, default=[], help="BLASTp name tables; rows bind by protein")
    ap.add_argument("--prefer-db", nargs="*", default=["nr"], help="database priority for genes named twice (default nr)")
    ap.add_argument("--length-fallback", default="query_aa_length", help="column read as a name row's protein length when "
                    "aa_length is empty (default query_aa_length; '' for none). The tag binds only within 1 aa")
    ap.add_argument("--trim-kb", type=float, default=2.0, help="window margin each side (default 2 kb, as the maps)")
    ap.add_argument("--print-width", type=float, default=10.0, help="print table width, inches (default 10, landscape)")
    ap.add_argument("--no-print", action="store_true", help="TSV only")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.summary:
        n = merge_summaries(a.summary, a.out)
        _OUT.info(f"[gap_rescue_gene_table] summary of {n} runs -> {a.out}")
        return 0
    if not (a.run and a.zip):
        raise SystemExit("--window needs --run and --zip")
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gap_directed_rescue as gdr
    from gap_rescue_locus_map import load_gene_names
    label = a.label or json.loads((a.run / "gap_rescue_receipt.json").read_text())["label"]
    names = None
    if a.gene_names:
        prots, _ = gdr.load_genome(a.zip, label)
        names = load_gene_names(a.gene_names, label, prots, prefer_db=a.prefer_db or None,
                                length_fallback=a.length_fallback or None)
    res = write_window_table(a.out, a.run, a.zip, names, int(round(a.trim_kb * 1000)), label, not a.no_print,
                             a.print_width)
    if names is not None:
        (a.out / "gene_names_binding.json").write_text(json.dumps(
            {"strain": label, "names_bound": len(names), "names_unbound": names.names_unbound,
             "binding": names.binding, "prefer_db": a.prefer_db, "length_fallback": a.length_fallback}, indent=1) + "\n")
    _OUT.info(f"[gap_rescue_gene_table] {res['rows']} genes in the window -> {a.out}")
    return 0


def main(argv=None) -> int:
    import sys
    args = sys.argv[1:] if argv is None else list(argv)
    if "--window" in args or "--summary" in args:   # the genes-in-the-window table (card attine_452_locus_gene_tables)
        return window_main(args)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True, type=Path, help="a gap_directed_rescue output folder")
    ap.add_argument("--zip", required=True, type=Path, help="the antiSMASH ZIP the run used (for protein families)")
    ap.add_argument("--reference", required=True, type=Path, help="the reference GenBank the run used")
    ap.add_argument("--reference-name", default="")
    a = ap.parse_args(args)
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gap_directed_rescue as gdr
    receipt = json.loads((a.run / "gap_rescue_receipt.json").read_text())
    prots, regions = gdr.load_genome(a.zip, receipt["label"])
    core = next((g for g in regions if g.get("identity") == receipt["core"]), None)
    if core is None:
        raise SystemExit(f"{receipt['core']} is not a region of this zip; check --zip and the saved run receipt")
    fams = protein_families(prots)
    rows = list(csv.DictReader(open(a.run / "gap_rescue.tsv"), delimiter="\t"))
    splits = list(csv.DictReader(open(a.run / "gap_rescue_split_genes.tsv"), delimiter="\t")) \
        if (a.run / "gap_rescue_split_genes.tsv").exists() else []
    known_tags = {v["tag"] for v in prots.values()}
    missing = sorted({r["best_locus"] for r in rows
                      if r.get("status") != "MISSING_NOT_FOUND" and r.get("best_locus")
                      and r["best_locus"] not in known_tags})
    if missing:
        raise SystemExit("Saved gap-rescue found loci are not in this zip: " + ", ".join(missing)
                         + "; check --zip and the saved run receipt")
    res = write_gene_table(a.run, rows, splits, receipt["core"], receipt["label"], a.reference, fams,
                           a.reference_name or receipt.get("reference_name", ""), edge_shares(rows, prots, core),
                           known_tags)
    _OUT.info(f"[gap_rescue_gene_table] {res['rows']} rows -> {a.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
