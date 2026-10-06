#!/usr/bin/env python3
"""Turn one gap-rescue comparison (<BGC>_vs_<reference>/gap_rescue.tsv) into a locus-comparison-v1 manifest and render it
with mamey.figures.locus_comparison.

Tracks, each one contig, never joined:
  1. the antiSMASH region (its CDS from the whole-genome GenBank of the strain's ZIP);
  2. the MIBiG reference cluster;
  3. at most two partner contigs, for reference genes the rescue found CLEARLY elsewhere with a SUPPORTED partner verdict
     (a window around those genes).
Links are the rescue table's best-hit correspondences: PRESENT_IN_CORE rows to the region, the partner rows to their
contig. Identity is the rescue's best-hit percent identity. The reference is reversed as a whole when most linked
pairs disagree in strand; the choice is recorded in the receipt. Labels: reference gene names; on AS tracks a gene-label
table's short label when given, else none. When labels collide the AS labels are dropped, then the reference labels.

Usage: python tools/rescue_locus_comparison.py --zip Z --label AS-n --rescue DIR/<BGC>_vs_<ref> --mibig-dir D
         [--gene-labels T.tsv] --out OUTDIR
Similarity only: a correspondence is a best protein hit, not orthology, function or product.
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import gap_directed_rescue as gdr  # noqa: E402
from mamey.figures import locus_comparison as lc  # noqa: E402
from _console import emit  # noqa: E402


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def aa_hash(aa):
    return hashlib.sha256("".join(str(aa).split()).upper().rstrip("*").encode()).hexdigest()


def compound_name(acc, index=None):
    """The MIBiG entry's first compound name ('streptophenazine B' -> 'streptophenazine B and others' when several)."""
    if not index or not Path(index).exists():
        return ""
    try:
        e = next((x for x in json.load(open(index))["entries"] if x.get("accession") == acc), None)
    except (OSError, ValueError):
        return ""
    c = (e or {}).get("compounds") or []
    return (c[0] + (" and others" if len(c) > 1 else "")) if c else ""


def short_gene_name(name):
    """A reference gene's own short name (phzB, ccrA); locus tags and protein accessions are not labels."""
    import re
    n = str(name)
    return n if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,7}(-[A-Za-z0-9]{1,3})?", n) else ""


def _mid_x(track, gene_id):
    """A gene's displayed midpoint (bp) on its track before any offset: orientation x (midpoint - anchor midpoint)."""
    g = {x["id"]: x for x in track["genes"]}
    a = g[track["anchor_gene"]]
    m = g[gene_id]
    return track["orientation"] * ((m["start"] + m["end"]) / 2 - (a["start"] + a["end"]) / 2)


def level_partners(tracks, ref, kb_per_in=None):
    """Partner contigs share one row under the reference, each shifted so its anchor gene sits under the reference gene
    it matches. A partner's heading may run right from its first gene or left from its last; the side that fits is
    chosen, and a partner is moved only when neither side fits, by the smallest distance either way, so it stays as
    close as possible to its match. Headings are short: strain, node, region and alias in bold, the full contig below."""
    parts = [t for t in tracks if t["id"].startswith("p")]
    if not parts:
        return
    span = max(abs(_mid_x(ref, g["id"])) for g in ref["genes"]) * 2 or 1
    kb_per_in = kb_per_in or span / 1000 / 15
    right_edge = max(max(_mid_x(x, g["id"]) + x.get("offset_bp", 0) for g in x["genes"]) for x in tracks if not x["id"].startswith("p"))
    placed = []
    for t in parts:
        grp = next(g["group"] for g in t["genes"] if g["id"] == t["anchor_gene"])
        rg = next(g["id"] for g in ref["genes"] if g["group"] == grp)
        t["row"] = "partners"
        t["offset_bp"] = int(_mid_x(ref, rg))
        ident = t["identity"]
        t["label"] = f"{ident['strain']} · {ident['contig'].split('_length')[0]} · {ident['region']} · {ident['bgc']}"
        t["subtitle"] = ident["contig"]
        xs = [_mid_x(t, g["id"]) + t["offset_bp"] for g in t["genes"]]
        glo, ghi = min(xs) - 1500, max(xs) + 1500
        head_bp = max(min(len(t["label"]), 34) * 12, min(len(t["subtitle"]), 48) * 9) * 0.62 / 72 * kb_per_in * 1000
        best = None
        for align in ("left", "right"):
            lo, hi = (glo, max(ghi, glo + head_bp)) if align == "left" else (min(glo, ghi - head_bp), ghi)
            shifts = [0] + [phi - lo + 1500 for _, phi in placed] + [plo - hi - 1500 for plo, _ in placed]
            ok = [s for s in shifts if all(not (lo + s < phi and hi + s > plo) for plo, phi in placed)]
            s = min(ok, key=abs)
            cost = (abs(s), align == "left" and hi + s > right_edge)  # nearest first; a heading past the right edge loses ties
            if best is None or cost < best[0]:
                best = (cost, align, s, lo + s, hi + s)
        _, align, s, lo, hi = best
        t["offset_bp"] += int(s)
        if align == "right":
            t["heading_align"] = "right"
        placed.append((lo, hi))


def sides(tracks, links):
    """Slide view: no text in the ribbon space. The region (top) labels above, the bottom row below; with partner
    contigs the reference is the middle row, so its heading goes to its left and its genes carry no labels. Each AS gene
    label ends with its best-hit identity, so the percentages stay on the outer rows."""
    pct = {(l["a"][0], l["a"][1]): l["identity_pct"] for l in links if "identity_pct" in l}
    for t in tracks:
        if t["kind"] == "bgc":
            for g in t["genes"]:
                p = pct.get((t["id"], g["id"]))
                if p is not None:
                    g["label"] = f"{g['label']} {p:.0f}%".strip()[:32]
    partners = any(t["id"].startswith("p") for t in tracks)
    for t in tracks:
        if t["id"] == "core":
            t["label_side"] = "above"
        elif t["id"] == "ref":
            t["label_side"], t["heading_side"] = ("none", "left") if partners else ("below", "below")
            if partners:
                for g in t["genes"]:
                    g["label"] = ""
        else:
            t["label_side"] = "below"


CONTIG_END_NEAR_BP = 6000  # mark contig ends only when both lie this close to the drawn genes


def with_contig_ends(track, contig_len):
    """Pass the contig length to the renderer, which then marks the contig start and end, only when both ends lie near
    the drawn genes. The renderer widens its axis to show both ends, so a long contig would squash the locus."""
    lo = min(g["start"] for g in track["genes"])
    hi = max(g["end"] for g in track["genes"])
    if contig_len and lo <= CONTIG_END_NEAR_BP and contig_len - hi <= CONTIG_END_NEAR_BP:
        track["sequence_length"] = int(contig_len)
    return track


def partner_region(rows):
    """Region and BGC alias for a partner track, copied from the rescue table's best_region_identity of the genes drawn.
    One region for every matched gene: that region. No region for any: none. Otherwise the identity is held, not guessed:
    the first region on the contig need not hold the matched genes (it often lies elsewhere on a long contig)."""
    found = {r.get("best_region_identity", "") for r in rows}
    named = {x for x in found if " / region" in x}
    if len(named) == 1 and named == found:
        parts = next(iter(named)).split(" / ")
        return parts[2], parts[3]
    if not named:
        return "no antiSMASH region", "no BGC alias"
    return f"matched genes in {len(found)} places", "identity held"


def manifest(zip_path, label, rescue, mibig_dir, gene_labels=None, genome=None, mibig_names=None):
    rows = list(csv.DictReader(open(rescue / "gap_rescue.tsv"), delimiter="\t"))
    bgc, ref_acc = rescue.name.split("_vs_")
    prots, regions = genome or gdr.load_genome(Path(zip_path), label)
    reg = next(r for r in regions if r["identity"].endswith(f"/ {bgc}"))
    ref_genes, ref_desc = gdr.load_reference(Path(mibig_dir) / f"{ref_acc}.gbk")
    by_tag = {p["tag"]: (q, p) for q, p in prots.items()}
    names = {}
    if gene_labels and Path(gene_labels).exists():
        names = {r["locus_tag"]: r.get("short_label", "") for r in csv.DictReader(open(gene_labels), delimiter="\t")}

    def as_gene(p, group=""):
        return {"id": p["tag"], "label": (names.get(p["tag"]) or "")[:32], "start": p["start"], "end": p["end"],
                "strand": p["strand"], "aa_sha256": aa_hash(p["aa"]), "group": group,
                "missing_stop_codon": bool(p.get("missing_stop", False))}

    ident = reg["identity"].split(" / ")
    core = [p for p in prots.values() if p["contig"] == reg["contig"] and p["start"] >= reg["start"] and p["end"] <= reg["end"]]
    links, groups = [], {}
    def one_per_gene(rs):  # an AS gene that is the best hit of several reference genes keeps its strongest one
        best = {}
        for r in rs:
            if r["best_locus"] not in best or float(r["best_identity_pct"] or 0) > float(best[r["best_locus"]]["best_identity_pct"] or 0):
                best[r["best_locus"]] = r
        return list(best.values())

    found = one_per_gene([r for r in rows if r["status"] == "PRESENT_IN_CORE" and r["best_locus"] in {p["tag"] for p in core}])
    if not found:
        return None
    for r in found:
        groups[r["best_locus"]] = f"G{r['reference_gene']}"
    core_track = {"id": "core", "label": f"{label} {ident[-1]}", "kind": "bgc",
                  "identity": {"strain": ident[0], "contig": ident[1], "region": ident[2], "bgc": ident[3]},
                  "orientation": 1, "genes": [as_gene(p, groups.get(p["tag"], "")) for p in sorted(core, key=lambda p: p["start"])]}
    used = {f"G{r['reference_gene']}" for r in found}
    partners = {}
    for r in rows:
        if r["status"] == "MISSING_FOUND_CLEAR" and r.get("partner_verdict") == "SUPPORTED" and r["best_locus"] in by_tag:
            partners.setdefault(by_tag[r["best_locus"]][1]["contig"], []).append(r)
    partners = {c: one_per_gene(rs) for c, rs in partners.items()}
    ptracks = []
    for contig, rs in sorted(partners.items(), key=lambda kv: -len(kv[1]))[:2]:
        hits = [by_tag[r["best_locus"]][1] for r in rs]
        lo, hi = min(p["start"] for p in hits) - 3000, max(p["end"] for p in hits) + 3000
        win = sorted([p for p in prots.values() if p["contig"] == contig and p["start"] >= lo and p["end"] <= hi], key=lambda p: p["start"])
        g = {r["best_locus"]: f"G{r['reference_gene']}" for r in rs}
        used |= set(g.values())
        node = contig.split("_cov")[0]
        p_region, p_bgc = partner_region(rs)  # not region/bgc: those name the core region, used in the title below
        ptracks.append((rs, {"id": f"p{len(ptracks) + 1}", "label": f"{label} {node.split('_length')[0]} (another contig)",
                             "kind": "bgc", "identity": {"strain": label, "contig": contig, "region": p_region, "bgc": p_bgc},
                             "orientation": 1, "genes": [as_gene(p, g.get(p["tag"], "")) for p in win]}))
    for t in [core_track] + [t for _, t in ptracks]:
        with_contig_ends(t, next(p["contig_len"] for p in prots.values() if p["tag"] == t["genes"][0]["id"]))
    cname = compound_name(ref_acc, mibig_names)
    ref_track = {"id": "ref", "label": f"MIBiG {ref_acc}" + (f": {cname}" if cname else ""), "kind": "reference",
                 "identity": {"accession": ref_acc, "description": ref_desc if len(ref_desc) <= 80 else ref_desc[:77].rstrip(" ,") + "..."}, "orientation": 1,
                 "genes": [{"id": g["id"], "label": short_gene_name(g["name"]), "start": g["start"], "end": g["end"], "strand": g["strand"],
                            "aa_sha256": aa_hash(g["aa"]), "group": f"G{g['i']}" if f"G{g['i']}" in used else ""} for g in ref_genes]}
    rg = {g["group"]: g for g in ref_track["genes"] if g["group"]}
    cg = {g["id"]: g for g in core_track["genes"]}
    agree = sum((cg[r["best_locus"]]["strand"] == rg[f"G{r['reference_gene']}"]["strand"]) for r in found)
    ref_track["orientation"] = 1 if agree * 2 >= len(found) else -1
    best = max(found, key=lambda r: float(r["best_identity_pct"] or 0))
    core_track["anchor_gene"] = best["best_locus"]
    ref_track["anchor_gene"] = rg[f"G{best['reference_gene']}"]["id"]
    ev = "gap-rescue best hit (DIAMOND, ultra-sensitive)"
    for r in found:
        links.append({"a": ["core", r["best_locus"]], "b": ["ref", rg[f"G{r['reference_gene']}"]["id"]], "evidence": ev,
                      "identity_pct": float(r["best_identity_pct"]), "query_coverage_pct": float(r["best_coverage_pct"] or 0)})
    tracks = [core_track, ref_track]
    for rs, t in ptracks:
        pg = {g["id"]: g for g in t["genes"]}
        a2 = sum(pg[r["best_locus"]]["strand"] * ref_track["orientation"] == rg[f"G{r['reference_gene']}"]["strand"] for r in rs)
        t["orientation"] = 1 if a2 * 2 >= len(rs) else -1
        t["anchor_gene"] = max(rs, key=lambda r: float(r["best_identity_pct"] or 0))["best_locus"]
        for r in rs:
            links.append({"a": [t["id"], r["best_locus"]], "b": ["ref", rg[f"G{r['reference_gene']}"]["id"]], "evidence": ev,
                          "identity_pct": float(r["best_identity_pct"]), "query_coverage_pct": float(r["best_coverage_pct"] or 0)})
        tracks.append(t)
    level_partners(tracks, ref_track)
    sides(tracks, links)
    wide = {2: (13, 9), 3: (17, 10.5), 4: (19, 11)}[len(tracks)]  # keep the figure wide as tracks are added
    src = [{"path": str(Path(zip_path).resolve()), "sha256": sha_file(zip_path)},
           {"path": str((Path(mibig_dir) / f"{ref_acc}.gbk").resolve()), "sha256": sha_file(Path(mibig_dir) / f"{ref_acc}.gbk")},
           {"path": str((rescue / "gap_rescue.tsv").resolve()), "sha256": sha_file(rescue / "gap_rescue.tsv")}]
    return {"schema": "locus-comparison-v1", "synthetic": False,
            "title": f"{label} {bgc} and {ref_track['label'][6:70]}",
            "display": {"label_rotation": 40, "font_size": wide[1], "width_in": wide[0], "axis_zero_track": "ref",
                        "axis_label": "kb along the MIBiG reference locus (0 = its first gene as drawn); same scale on every track"},
            "sources": src, "tracks": tracks, "links": links}


def crop_long_reference(spec, ratio=3, flank=3):
    """A reference more than `ratio` times the region's length is shown from its first to its last matched gene,
    plus `flank` genes each side, so the region is not drawn as a sliver beside a 100 kb cluster."""
    span = lambda t: max(g["end"] for g in t["genes"]) - min(g["start"] for g in t["genes"])
    core = next(t for t in spec["tracks"] if t["id"] == "core")
    ref = next(t for t in spec["tracks"] if t["id"] == "ref")
    if span(ref) > ratio * span(core):
        crop_reference(spec, flank)
        return True
    return False


def crop_reference(spec, flank=2):
    """Keep the reference genes from the first to the last linked one, plus flank genes each side (a narrower view;
    the unlinked ends stay in the reference itself)."""
    ref = next(t for t in spec["tracks"] if t["id"] == "ref")
    idx = [i for i, g in enumerate(ref["genes"]) if g["group"]]
    ref["genes"] = ref["genes"][max(0, min(idx) - flank):max(idx) + flank + 1]
    ref["label"] += " (genes around the matches)"


def thin(spec, gap_in=0.2):
    """Blank labels (and the identity numbers under reference genes) that would sit closer than gap_in inches on the
    drawn axis; matched genes keep theirs first. The full values stay in the rescue table."""
    d = spec.get("display") or {}
    rows = []
    for t in spec["tracks"]:
        a = next(g for g in t["genes"] if g["id"] == t["anchor_gene"])
        am = (a["start"] + a["end"]) / 2
        for g in t["genes"]:
            rows.append((t["id"], g, t["orientation"] * ((g["start"] + g["end"]) / 2 - am) + t.get("offset_bp", 0)))
    span = (max(x for *_, x in rows) - min(x for *_, x in rows)) or 1
    left = any(t.get("heading_side") == "left" for t in spec["tracks"])  # room kept for a heading at the left
    gap = span * gap_in / (d.get("width_in", 18) * (0.65 if left else 0.8))  # drawn axis share of the figure width
    for tid in {r[0] for r in rows}:
        rr = sorted([r for r in rows if r[0] == tid and r[1]["label"]], key=lambda r: (not r[1]["group"], r[2]))
        kept = []
        for _, g, x in rr:
            if all(abs(x - k) >= gap for k in kept):
                kept.append(x)
            else:
                g["label"] = ""
    pos = {g["id"]: x for tid, g, x in rows if tid == "ref"}
    kept = []
    for link in sorted(spec["links"], key=lambda l: -float(l.get("identity_pct") or 0)):
        x = pos.get(link["b"][1])
        if x is None or "identity_pct" not in link:
            continue
        if all(abs(x - k) >= gap for k in kept):
            kept.append(x)
        else:
            link["identity_pct_not_drawn"] = link.pop("identity_pct")


def render_with_fallback(spec, out):
    """Render the most informative view that the renderer accepts without overlapping text: all labels; no AS-track
    labels; the reference cropped to its matched span; no gene labels; no identity numbers under the reference (the
    numbers stay in input.json). Returns the step used."""
    import copy
    steps = ["all", "no_as_labels", "cropped", "no_labels", "no_identity"]
    s = copy.deepcopy(spec)
    crop_long_reference(s)
    thin(s)
    for step in steps:
        if step == "no_as_labels":
            for t in s["tracks"]:
                if t["kind"] == "bgc":
                    for g in t["genes"]:
                        g["label"] = ""
        if step == "cropped":
            crop_reference(s)
        if step == "no_labels":
            for t in s["tracks"]:
                for g in t["genes"]:
                    g["label"] = ""
        if step == "no_identity":
            for link in s["links"]:
                link["identity_pct_not_drawn"] = link.pop("identity_pct", None)
        out.mkdir(parents=True, exist_ok=True)
        (out / "input.json").write_text(json.dumps(s, indent=1))
        try:
            lc.render(out / "input.json", out / "render")
            (out / "VIEW.txt").write_text(step + "\n")
            return step
        except ValueError as e:
            emit(f"  {step}: {e}", file=sys.stderr)
            if "overlap" not in str(e).lower() and "outside" not in str(e).lower():
                raise
            (out / "input.json").unlink()
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for a in ("--zip", "--label", "--rescue", "--mibig-dir", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--gene-labels")
    ap.add_argument("--mibig-names", help="MIBiG reference index JSON, for compound names in the reference heading")
    a = ap.parse_args()
    spec = manifest(a.zip, a.label, Path(a.rescue), a.mibig_dir, a.gene_labels, mibig_names=a.mibig_names)
    if not spec:
        sys.exit("no reference gene in the region core: nothing to compare")
    emit(render_with_fallback(spec, Path(a.out)))
