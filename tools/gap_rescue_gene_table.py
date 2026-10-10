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

COLS = ["CDS", "Size (aa)", "Protein family (antiSMASH)", "Reference gene", "Reference annotation", "Identity (%)",
        "Location"]
FLAG = {"SUPPORTED": "", "PARALOG_FAMILY": "; paralog family", "SINGLE_GENE": "; single gene"}


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
    heads = [f"CDS ({label})", "Size (aa)", "Protein family (antiSMASH)", "Reference gene", "Reference annotation",
             "Identity (%)", f"In {label}"]
    widths, wraps = [0.09, 0.055, 0.21, 0.08, 0.25, 0.065, 0.25], [12, 6, 34, 14, 40, 6, 40]
    cells = [[textwrap.fill(str(v), w) for v, w in zip(row.values(), wraps)] for row in table]
    nlines = [max(c.count("\n") + 1 for c in row) for row in cells]
    cap = textwrap.fill(caption, 175) if caption else ""
    cap_h = 0.22 * (cap.count("\n") + 1) + 0.1 if cap else 0.0
    H = 1.15 + cap_h + 0.2 * sum(nlines) + 0.12 * len(cells)
    with plt.rc_context({"font.family": ["Arial", "DejaVu Sans"], "pdf.fonttype": 42}):
        fig = plt.figure(figsize=(13.3, H))
        fig.text(0.02, 1 - 0.25 / H, title, fontsize=13, fontweight="bold", color=ink, va="top")
        if cap:   # the same counts, in the same words, as the map's footnote
            fig.text(0.02, 1 - 0.62 / H, cap, fontsize=9, color=sub, va="top", linespacing=1.25)
        y, x = 1 - (0.7 + cap_h) / H, 0.02
        for c, wd in zip(heads, widths):
            fig.text(x, y, c, fontsize=9, fontweight="bold", color=ink, va="top"); x += wd * 0.96 / sum(widths)
        y -= 0.32 / H
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
                     ref_name: str = "", edge: dict | None = None, known_tags=None) -> dict:
    """Write gene_table.tsv (+ .png/.pdf) and the map pairing into `out`; returns {"rows": n, "files": [...]}."""
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
    with open(out / "gene_table_counts.tsv", "w", newline="") as fh:   # one row per pair, for inventories to read
        w = _SafeDictWriter(fh, fieldnames=list(counts), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerow(counts)
    files.append(out / "gene_table_counts.tsv")
    if _draw(table, title, label, out / "gene_table.png", out / "gene_table.pdf", caption):
        files += [out / "gene_table.png", out / "gene_table.pdf"]
    files += pair_with_map(out)
    return {"rows": len(table), "files": [str(f) for f in files], "counts": counts, "caption": caption}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True, type=Path, help="a gap_directed_rescue output folder")
    ap.add_argument("--zip", required=True, type=Path, help="the antiSMASH ZIP the run used (for protein families)")
    ap.add_argument("--reference", required=True, type=Path, help="the reference GenBank the run used")
    ap.add_argument("--reference-name", default="")
    a = ap.parse_args(argv)
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gap_directed_rescue as gdr
    receipt = json.loads((a.run / "gap_rescue_receipt.json").read_text())
    prots, regions = gdr.load_genome(a.zip, receipt["label"])
    core = next((g for g in regions if g.get("identity") == receipt["core"]), None)
    fams = {k: v.get("family", "") for k, v in prots.items()}
    fams.update({v["tag"]: v.get("family", "") for v in prots.values()})
    rows = list(csv.DictReader(open(a.run / "gap_rescue.tsv"), delimiter="\t"))
    splits = list(csv.DictReader(open(a.run / "gap_rescue_split_genes.tsv"), delimiter="\t")) \
        if (a.run / "gap_rescue_split_genes.tsv").exists() else []
    res = write_gene_table(a.run, rows, splits, receipt["core"], receipt["label"], a.reference, fams,
                           a.reference_name or receipt.get("reference_name", ""), edge_shares(rows, prots, core),
                           {v["tag"] for v in prots.values()})
    _OUT.info(f"[gap_rescue_gene_table] {res['rows']} rows -> {a.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
