#!/usr/bin/env python3
"""TYGS figures: dDDH with the closest type strain (catalog T05) and 16S similarity against dDDH (T06).

Inputs
  --tygs          a TYGS results PDF (Table 3 is parsed locally with pdftotext -layout) or an already parsed TSV with the
                  columns comp_type, query_genome, subject_genome, digital_ddh_d4, confidence_interval_d4
  --strain-table  TSV (the cohort to draw) with isolate, genus (as deposited), group (host or source as deposited); optional similarity
                  (16S % to the closest type strain) and closest_16s
  --out           a new output directory (refused if it exists)
Steps: parse TYGS -> keep user-vs-type rows -> closest type strain per isolate = highest d4 -> join the strain table ->
draw T05 and T06 with tygs_figures.R (bee 2A/2B drawing, text at 8 pt or more, nothing interpretive on the canvas) ->
write the data tables, a caption with the counts, and a receipt with input sha256 values.
The species-boundary reading (d4 below 70%) is stated in the caption only, never on the canvas.
"""
import argparse, csv, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

HERE = Path(__file__).resolve().parent
NUM = r"(\d+(?:\.\d+)?)"
FIRST = re.compile(rf"^\s*'([\w.-]+?)(?:\.fna|\.fasta|\.fa)?'\s+(.*?)\s+{NUM}\s+\[{NUM}\s*-\s+{NUM}\s+\[{NUM}\s*-\s+{NUM}\s+\[{NUM}\s*-\s+{NUM}\s*$")
UPPER = re.compile(rf"^(.*?)\s*{NUM}\]\s+{NUM}\]\s+{NUM}\]\s*$")


def num(x):
    """A strain-table number, or None for blank / NA / n.d. (missing stays missing, never 0)."""
    x = (x or "").strip()
    try:
        return float(x)
    except ValueError:
        return None


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def join_wrapped(head, tail):
    """Join a name that pdftotext wrapped over two lines: no space after a trailing hyphen ("NRRL B-" + "24058")."""
    head, tail = head.strip(), tail.strip()
    if not head:
        return tail
    return head + tail if head.endswith("-") else head + " " + tail


def tidy_subject(name):
    """Undo a wrap space left inside a collection number by an earlier parse ("NRRL B- 24058" -> "NRRL B-24058")."""
    return re.sub(r"(?<=[A-Za-z])- (?=\d)", "-", name.strip())


def host_label(host):
    """Second row-label line for T05 (markdown): the host in brackets. A one-word host is a genus, "(<i>Atta</i> sp.)";
    a trailing "?" (an uncertain genus) stays after the name, "(<i>Trachymyrmex</i>? sp.)"; anything else is printed
    upright as given. Blank: no second line."""
    h = (host or "").strip()
    if not h:
        return ""
    m = re.fullmatch(r"([A-Z][a-z]+)(\?)?", h)
    return f"(<i>{m.group(1)}</i>{m.group(2) or ''} sp.)" if m else f"({h})"


def row_label(genus, isolate, host=""):
    """Row label for T05 (markdown). A family-level name (ending in -aceae) takes no "sp.", which is genus rank only.
    With a host, the host goes on a second line (host_label)."""
    g = (genus or "").strip()
    lab = f"<i>{g}</i> {isolate}" if g.endswith("aceae") else f"<i>{g}</i> sp. {isolate}"
    h = host_label(host)
    return f"{lab}<br>{h}" if h else lab


def reference_label(name, strain, accession):
    """House rule 6 label (markdown): deposited name in italics (subsp. upright), strain, then the assembly accession,
    without its version, in brackets on a second line. No accession gives the name and strain only."""
    nm = (name or "").strip().replace(" subsp. ", "</i> subsp. <i>")
    lab = f"<i>{nm}</i> {(strain or '').strip()}".strip()
    acc = re.sub(r"\.[0-9]+$", "", (accession or "").strip())
    return f"{lab}<br>({acc})" if acc else lab


def load_reference_names(path):
    """TSV keyed by the TYGS type-strain string: tygs_closest_type_strain, name, strain, accession[, name_source]."""
    out = {}
    for r in csv.DictReader(open(path), delimiter="\t"):
        key = tidy_subject(r["tygs_closest_type_strain"])
        if key in out:
            sys.exit(f"REFERENCE_NAMES_DUPLICATE: {key}")
        out[key] = r
    return out


def parse_tygs_pdf(pdf, pdftotext):
    """Table 3 of a TYGS results PDF -> one dict per pairwise row (query is a user genome)."""
    txt = subprocess.run([pdftotext, "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout.splitlines()
    a = next(i for i, l in enumerate(txt) if l.startswith("Table 3:"))
    b = next(i for i, l in enumerate(txt) if l.startswith("Table 4:"))
    rows, cur = [], None
    for line in txt[a:b]:
        m = FIRST.match(line)
        if m:
            q, subj, d0, d0l, d4, d4l, d6, d6l, gc = m.groups()
            cur = dict(query=q, subject=subj.strip(), d4=float(d4), d4_lo=float(d4l), d4_hi=None)
            rows.append(cur)
            continue
        if cur and cur["d4_hi"] is None:
            u = UPPER.match(line)
            if u:
                rest, _hi0, hi4, _hi6 = u.groups()
                if rest.strip():
                    cur["subject"] = join_wrapped(cur["subject"], rest)
                cur["d4_hi"] = float(hi4)
            elif line.strip():
                cur["subject"] = join_wrapped(cur["subject"], line)
    for r in rows:
        r["user_vs_type"] = not re.match(r"^'?AS-", r["subject"])
    return rows


def parse_tygs_tsv(path):
    rows = []
    for r in csv.DictReader(open(path), delimiter="\t"):
        lo, hi = re.findall(r"[0-9.]+", r["confidence_interval_d4"])[:2]
        rows.append(dict(query=r["query_genome"].strip("'").removesuffix(".fna"), subject=tidy_subject(r["subject_genome"]),
                         d4=float(r["digital_ddh_d4"]), d4_lo=float(lo), d4_hi=float(hi),
                         user_vs_type=r.get("comp_type", "U vs. T").strip() == "U vs. T"))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tygs", required=True)
    ap.add_argument("--strain-table", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--palette", default=str(HERE.parent / "mamey/data/genus_palette.json"))
    ap.add_argument("--pdftotext", default=shutil.which("pdftotext") or "pdftotext")
    ap.add_argument("--rscript", default=shutil.which("Rscript") or "Rscript")
    ap.add_argument("--reference-names", help="optional TSV: tygs_closest_type_strain, name, strain, accession[, name_source]; "
                    "draws each type strain by that name and strain with its accession (house rule 6)")
    ap.add_argument("--palette-set", default="", help="named set in the palette file drawn over its default colours (e.g. a paper's set)")
    ap.add_argument("--legend-title", default="Genus (16S rRNA)", help="colour key title (default 'Genus (16S rRNA)')")
    ap.add_argument("--host-column", default=None, help="strain-table column holding each isolate's host; printed "
                    "under the T05 row label, e.g. '(Atta sp.)' (default: no host line)")
    ap.add_argument("--width-a", type=float, default=7.0)
    ap.add_argument("--width-b", type=float, default=3.4)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        sys.exit(f"OUTPUT_EXISTS: {out}")
    rows = parse_tygs_pdf(a.tygs, a.pdftotext) if a.tygs.lower().endswith(".pdf") else parse_tygs_tsv(a.tygs)
    rows = [r for r in rows if r["user_vs_type"] and r["d4_hi"] is not None]
    if not rows:
        sys.exit("TYGS_NO_USER_VS_TYPE_ROWS")
    strains = {r["isolate"]: r for r in csv.DictReader(open(a.strain_table), delimiter="\t")}
    if a.host_column and any(a.host_column not in r for r in strains.values()):
        sys.exit(f"HOST_COLUMN_MISSING: {a.host_column} is not a strain-table column")
    best = {}
    for r in rows:
        if r["query"] not in best or r["d4"] > best[r["query"]]["d4"]:
            best[r["query"]] = r
    # The strain table selects the cohort: TYGS jobs often hold several projects' genomes. Genomes not in the table are
    # left out and listed in the receipt; isolates in the table with no TYGS row are listed too.
    not_drawn = sorted(set(best) - set(strains)); no_tygs = sorted(set(strains) - set(best))
    best = {q: r for q, r in best.items() if q in strains}
    if not best:
        sys.exit("NO_STRAIN_TABLE_ISOLATE_IN_TYGS")
    refs = load_reference_names(a.reference_names) if a.reference_names else {}
    missing_ref = sorted({best[q]["subject"] for q in best} - set(refs)) if refs else []
    if missing_ref:
        sys.exit(f"REFERENCE_NAMES_MISSING: {missing_ref}")
    out.mkdir(parents=True)
    data = out / "T05_T06_data.tsv"
    with open(data, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(["isolate", "genus", "group", "closest_type_strain", "d4", "d4_ci_low", "d4_ci_high", "similarity_16s", "closest_16s",
                    "row_label", "reference_label"])
        for q in sorted(best, key=lambda k: best[k]["d4"]):
            r, s = best[q], strains[q]
            w.writerow([q, s["genus"], s.get("group", ""), r["subject"], r["d4"], r["d4_lo"], r["d4_hi"],
                        "" if num(s.get("similarity")) is None else num(s.get("similarity")), s.get("closest_16s", ""),
                        row_label(s["genus"], q, s.get(a.host_column, "") if a.host_column else ""),
                        reference_label(refs[r["subject"]]["name"], refs[r["subject"]]["strain"], refs[r["subject"]].get("accession"))
                        if refs else ""])
    subprocess.run([a.rscript, str(HERE / "tygs_figures.R"), str(data), a.palette, str(out), str(a.width_a), str(a.width_b),
                    a.legend_title, a.palette_set], check=True)
    n = len(best)
    below = sum(1 for r in best.values() if r["d4"] < 70)
    with_16s = [q for q in best if num(strains[q].get("similarity")) is not None]
    disc = sum(1 for q in with_16s if num(strains[q]["similarity"]) >= 98.65 and best[q]["d4"] < 70)
    cap = (f"T05 dDDH to the closest type strain. Digital DNA–DNA hybridisation (formula d4, TYGS) of each of the {n} genomes "
           f"with its closest type strain, with the confidence interval; the dashed line marks 70%, the species boundary. "
           f"{below} of {n} genomes fall below 70%.\n\n"
           f"T06 16S similarity against dDDH. 16S rRNA gene similarity to the closest type strain against dDDH (d4) for the "
           f"{len(with_16s)} genomes with a 16S value. Dashed lines mark 98.65% (16S) and 70% (dDDH). {disc} of {len(with_16s)} "
           f"are at or above 98.65% by 16S yet below 70% by dDDH.\n")
    (out / "CAPTION.md").write_text(cap)
    ins = {a.tygs: sha256(a.tygs), a.strain_table: sha256(a.strain_table), a.palette: sha256(a.palette)}
    if a.reference_names:
        ins[a.reference_names] = sha256(a.reference_names)
    no_acc = sorted(q for q in best if refs and not (refs[best[q]["subject"]].get("accession") or "").strip())
    receipt = dict(tool="tygs_figures.py", inputs=ins, reference_names_without_accession=no_acc,
                   genomes=n, below_70=below, tygs_genomes_not_in_strain_table=not_drawn, strain_table_isolates_without_tygs=no_tygs, with_16s=len(with_16s), discordant=disc,
                   outputs={p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "RECEIPT.json"})
    (out / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {out}: {n} genomes, {below} below 70%")


if __name__ == "__main__":
    main()
