#!/usr/bin/env python3
"""Per-strain assembly statistics table (catalog Q01), from each genome's antiSMASH result ZIP.

Inputs
  --strains       TSV with columns strain, genus (as deposited), group, zip (path to the strain's antiSMASH result ZIP; for a
                  cleaned or decontaminated genome, the ZIP of that assembly). Optional column order sets the table order.
  --completeness  optional TSV with strain and completeness_pct (single-copy-gene completeness); a strain without a row keeps a
                  blank cell, never 0
  --title         table title, e.g. "Moss-paper genomes: assembly statistics"
  --out           a new output directory (refused if it exists)
Per genome, from the whole-result GenBank in the ZIP (the antiSMASH input sequence): size (Mb), GC %, contigs, N50 (kb), L50,
largest contig (kb). Writes ASSEMBLY_STATS.tsv, the table as PDF and PNG (7.0 in wide, 8 pt text, pages of at most --rows-per-page
rows), CAPTION.md and RECEIPT.json with input sha256 values. Drawing follows the 5 Oct talk table (build_assembly_slides.py):
light header band, alternating row shading, italic genus, numbers right-aligned.
"""

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse, csv, hashlib, io, json, sys, zipfile
from pathlib import Path

COLS = [("strain", "Strain", "l"), ("genus", "Genus", "l"), ("group", "Group", "l"), ("size_mb", "Size Mb", "r"),
        ("gc_pct", "GC %", "r"), ("contigs", "Contigs", "r"), ("contigs_1kb", "Contigs ≥1 kb", "r"), ("n50_kb", "N50 kb", "r"), ("l50", "L50", "r"),
        ("largest_kb", "Largest kb", "r"), ("completeness_pct", "Complete %", "r")]
INK, SUB, BAND, ALT = "#17212E", "#54637A", "#EEF1F5", "#F7F8FA"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def zip_lengths(zp):
    """Contig lengths and GC/ACGT counts of the full assembly: the input FASTA antiSMASH keeps in the ZIP (input/*.fasta|fna).
    antiSMASH analyses only contigs of at least 1,000 bp, so its whole-result GenBank under-counts contigs and size; it is used
    only when the ZIP holds no input FASTA, and the returned source says so."""
    with zipfile.ZipFile(zp) as zf:
        fa = [n for n in zf.namelist() if n.startswith("input/") and n.lower().endswith((".fasta", ".fna", ".fa", ".fas"))]
        if len(fa) == 1:
            L, gc, acgt, cur = [], 0, 0, []
            def close():
                nonlocal gc, acgt
                if cur:
                    x = "".join(cur).upper(); L.append(len(x)); gc += x.count("G") + x.count("C"); acgt += sum(x.count(b) for b in "ACGT")
            for line in io.TextIOWrapper(zf.open(fa[0]), encoding="utf-8", errors="replace"):
                if line.startswith(">"):
                    close(); cur = []
                else:
                    cur.append(line.strip())
            close()
            return sorted(L, reverse=True), gc, acgt, f"input FASTA ({fa[0]})"
        try:
            from Bio import SeqIO
        except ImportError:  # biopython absent: the bundle's GenBank shim reads the same records
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from mamey._gbk_shim import SeqIO
        top = [n for n in zf.namelist() if n.endswith(".gbk") and n.count("/") <= 1 and ".region" not in n
               and not n.startswith("__MACOSX")]
        def read(name):
            return list(SeqIO.parse(io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace"), "genbank"))
        inp = [n for n in top if n.startswith("input/")]; res = [n for n in top if "/" not in n]
        if len(top) == 2 and len(inp) == 1 and len(res) == 1:
            # Route-A web results keep the submitted GenBank under input/ beside the whole-result record (M5_452_q01_input_gbk_first,
            # 13 Oct 2026). The input record is the full assembly, as the input FASTA is; the result record drops contigs < 1 kb. They
            # must agree on contigs >= 1 kb (count and total length), else the ZIP is refused.
            recs, chk = read(inp[0]), read(res[0])
            a = sorted(len(r.seq) for r in recs if len(r.seq) >= 1000); b = sorted(len(r.seq) for r in chk if len(r.seq) >= 1000)
            if (len(a), sum(a)) != (len(b), sum(b)):
                raise ValueError(f"ZIP_INPUT_AND_RESULT_GBK_DISAGREE_ON_CONTIGS_GE_1KB:{zp}:input {len(a)}/{sum(a)} result {len(b)}/{sum(b)}")
            source = f"input GenBank ({inp[0]}); agrees with the antiSMASH record on contigs >= 1 kb"
        elif len(top) == 1:
            recs = read(top[0]); source = "antiSMASH records only (contigs >= 1 kb; no input FASTA in ZIP)"
        else:
            raise ValueError(f"ZIP_NO_INPUT_FASTA_AND_WHOLE_RESULT_GBK_NOT_UNIQUE:{zp}:{top}")
    L = sorted((len(r.seq) for r in recs), reverse=True)
    x = "".join(str(r.seq).upper() for r in recs)
    return L, x.count("G") + x.count("C"), sum(x.count(b) for b in "ACGT"), source


TOOL = "assembly_stats_table"


def stats(L, gc, acgt, source):
    tot = sum(L); run = 0; n50 = l50 = None
    for i, x in enumerate(L, 1):
        run += x
        if run >= tot / 2:
            n50, l50 = x, i; break
    return dict(size_mb=f"{tot / 1e6:.2f}", gc_pct=f"{100 * gc / acgt:.1f}" if acgt else "", contigs=str(len(L)),
                contigs_1kb=str(sum(1 for x in L if x >= 1000)), n50_kb=f"{n50 / 1e3:.1f}", l50=str(l50),
                largest_kb=f"{L[0] / 1e3:.0f}", sequence_source=source)


def draw(rows, title, out, rows_per_page):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mamey.figure_stamp import savefig_metadata
    plt.rcParams.update({"font.family": "Arial", "font.size": 8})
    widths = [0.075, 0.165, 0.085, 0.07, 0.06, 0.07, 0.11, 0.07, 0.05, 0.1, 0.115]
    pages = [rows[i:i + rows_per_page] for i in range(0, len(rows), rows_per_page)] or [[]]
    files = []
    with PdfPages(out / "ASSEMBLY_STATS_TABLE.pdf", metadata=savefig_metadata(out / "ASSEMBLY_STATS_TABLE.pdf", TOOL)) as pdf:
        for k, page in enumerate(pages, 1):
            h = 0.55 + 0.21 * (len(page) + 1)
            fig = plt.figure(figsize=(7.0, h)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
            ax.set_xlim(0, 1); ax.set_ylim(0, h)
            t = title + (f" ({k} of {len(pages)})" if len(pages) > 1 else "")
            ax.text(0.01, h - 0.2, t, fontsize=10, fontweight="bold", color=INK, va="center")
            y = h - 0.5; x0 = 0.01
            ax.add_patch(plt.Rectangle((x0, y - 0.105), 0.98, 0.21, color=BAND, lw=0))
            x = x0
            for (key, lab, al), w in zip(COLS, widths):
                ax.text(x + (w - 0.008 if al == "r" else 0.006), y, lab, ha="right" if al == "r" else "left", va="center",
                        fontweight="bold", color=INK, fontsize=8)
                x += w
            for i, r in enumerate(page):
                y -= 0.21
                if i % 2:
                    ax.add_patch(plt.Rectangle((x0, y - 0.105), 0.98, 0.21, color=ALT, lw=0))
                x = x0
                for (key, lab, al), w in zip(COLS, widths):
                    v = r.get(key, "")
                    ax.text(x + (w - 0.008 if al == "r" else 0.006), y, v, ha="right" if al == "r" else "left", va="center",
                            color=INK, fontsize=8, fontstyle="italic" if key == "genus" and v and " " not in v else "normal")
                    x += w
            pdf.savefig(fig)
            png = out / (f"ASSEMBLY_STATS_TABLE_p{k}.png" if len(pages) > 1 else "ASSEMBLY_STATS_TABLE.png")
            fig.savefig(png, dpi=300, metadata=savefig_metadata(png, TOOL)); files.append(png.name); plt.close(fig)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--strains", required=True)
    ap.add_argument("--completeness")
    ap.add_argument("--title", default="Per-strain assembly statistics")
    ap.add_argument("--rows-per-page", type=int, default=22)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        sys.exit(f"OUTPUT_EXISTS: {out}")
    strains = list(csv.DictReader(open(a.strains), delimiter="\t"))
    need = {"strain", "genus", "group", "zip"}
    if not strains or not need <= set(strains[0]):
        sys.exit("STRAIN_TABLE_COLUMNS: need " + ", ".join(sorted(need)))
    comp = {}
    if a.completeness:
        comp = {r["strain"]: (r.get("completeness_pct") or "").strip() for r in csv.DictReader(open(a.completeness), delimiter="\t")}
    rows, inputs = [], {a.strains: sha256(a.strains)}
    if a.completeness:
        inputs[a.completeness] = sha256(a.completeness)
    for s in strains:
        zp = s["zip"]
        if not Path(zp).is_file():
            sys.exit(f"ZIP_NOT_FOUND:{s['strain']}:{zp}")
        inputs[zp] = sha256(zp)
        r = dict(strain=s["strain"], genus=s["genus"], group=s["group"], **stats(*zip_lengths(zp)))
        r["completeness_pct"] = comp.get(s["strain"], "")
        rows.append(r)
    out.mkdir(parents=True)
    with open(out / "ASSEMBLY_STATS.tsv", "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=[c[0] for c in COLS] + ["sequence_source"], delimiter="\t"); w.writeheader(); w.writerows(rows)
    pngs = draw(rows, a.title, out, a.rows_per_page)
    n_blank = sum(1 for r in rows if not r["completeness_pct"])
    (out / "CAPTION.md").write_text(
        f"{a.title}. Statistics of the {len(rows)} genome assemblies (the input sequence of each antiSMASH analysis): total size, "
        f"GC content, number of contigs, contigs of at least 1 kb (the contigs antiSMASH analyses), N50 and L50, and the largest contig. "
        f"Complete %: single-copy-gene completeness"
        + (f"; blank for {n_blank} genome(s) without a score." if n_blank else ".") + "\n")
    rec = dict(tool="assembly_stats_table.py", genomes=len(rows), inputs=inputs,
               outputs={p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()})
    (out / "RECEIPT.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(f"wrote {out}: {len(rows)} genomes, pages: {', '.join(pngs)}")


if __name__ == "__main__":
    main()
