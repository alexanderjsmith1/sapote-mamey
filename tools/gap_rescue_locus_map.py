"""gap_rescue_locus_map.py — the clinker-style figure for tools/gap_directed_rescue.py.

Two rows. Top: the reference cluster, gene names above, matched genes coloured. Bottom: the genome, starting with the core
region's contig, then the contig holding the other piece of any CLEAR split gene (a red gap marker between the two pieces),
then contigs carrying a clear match to a named cluster gene, each cut to the part that carries it. Ribbons join each
reference gene to its match, shaded by protein identity; matched genes share the reference gene's colour, and each is
labelled below with its match and identity.

Which contigs are drawn:
- always the core contig and the contigs holding the pieces of a CLEAR split gene;
- otherwise a contig only when it carries a reciprocal-best clear match to a named cluster gene: a primary contig at 50%
  identity or more, a secondary contig at 35-50%. Secondary contigs are drawn after the primary ones and marked as such;
  real clusters with low homology to MIBiG sit in this range.
  A MIBiG entry names its cluster genes (valA, asuD3 ...) and leaves flanking genes under accession numbers (integrases,
  transposases, unknowns), so accession-named genes do not pull a contig into the figure. When fewer than three reference
  genes carry names, every gene counts as a cluster gene.
- never a contig whose find the partner checks call PARALOG_FAMILY or HOUSEKEEPING_CONTEXT; a lone find that passes
  them is drawn with the label "single-gene find";
- at most five such contigs, primary before secondary, best-matching first. Every other find stays in gap_rescue.tsv,
  and the footnote says how many were not drawn.

Claim-safety: homology is similarity, not product identity. A gap marker is two pieces of one reference protein at facing
contig ends, not a joined sequence.
"""
from __future__ import annotations

import collections
import re
import statistics

PRIMARY_MIN_ID, SECONDARY_MIN_ID = 50.0, 35.0
EXCLUDED_VERDICTS = {"PARALOG_FAMILY", "HOUSEKEEPING_CONTEXT"}
MAX_EXTRA = 5
NEAR_GAP_KB = 30.0     # matches farther apart than this along one contig are separate blocks
REACH_KB = 100.0       # a block farther than this from the contig's anchor block is left off the map and counted
CONTEXT_FLANK = 3      # genes either side of an off-region match shown on an opt-in context row
CONTEXT_ROWS_MAX = 3   # at most this many context rows on one map
SPLIT_GAP_KB, CUT_GAP_KB = 0.6, 1.8
SEG_BREAK_KB = 15.0    # a stretch longer than this with no drawn gene on it is cut out of a contig's window
BREAK_GAP_KB = 2.4     # drawing width of that cut; the omitted length is printed on it
SPLIT_LABEL_KB = 10.0  # a split gene gets one label when its two drawn pieces are this close; otherwise one label per piece
GREY, LINE = "#D5D9DF", "#6B7280"
PAL = ["#56B4E9", "#D55E00", "#CC79A7", "#8FBC5A", "#009E73", "#F0E442", "#E69F00", "#0072B2", "#B07AA1", "#9C755F",
       "#76B7B2", "#EDC948", "#FF9DA7", "#59A14F", "#4E79A7", "#F28E2B", "#E15759", "#BAB0AC"]
ACCESSION = re.compile(r"^([A-Z]{1,6}_?\d{3,}(\.\d+)?|orf\d+[a-z]?)$")
ORF = re.compile(r"^orf\d+[a-z]?$", re.I)
MOBILE = re.compile(r"transposase|integrase|excisionase|excisonase|recombinase|resolvase|insertion element|insertion sequence", re.I)
BIOSYNTHETIC = {"biosynthetic", "biosynthetic-additional"}
H = 0.32
EDGE_BP = 1000          # a region within this many bp of a contig end touches that end
LINK = "#6D28D9"        # the RG-GMCI link marker: homology-guided linkage, not a joined sequence


def _true(v) -> bool:
    return v is True or str(v) == "True"


def reference_genes(gbk_path) -> tuple[list[dict], float]:
    """Reference CDSs in record order (kb from the record start) and the record length in kb."""
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError("the locus map needs the optional Biopython package to read the reference GenBank file") from exc
    rec = next(SeqIO.parse(str(gbk_path), "genbank"))
    cds = sorted([c for c in rec.features if c.type == "CDS" and "translation" in c.qualifiers],
                 key=lambda c: int(c.location.start))
    out = []
    for i, c in enumerate(cds, 1):
        q = c.qualifiers
        out.append({"i": i, "name": (q.get("gene") or q.get("locus_tag") or q.get("protein_id") or [f"g{i}"])[0],
                    "product": q.get("product", [""])[0], "kind": q.get("gene_kind", [""])[0],
                    "s": int(c.location.start) / 1000,
                    "e": int(c.location.end) / 1000, "strand": c.location.strand or 1})
    return out, len(rec.seq) / 1000


def named(g: dict) -> bool:
    """A curated gene name (valC, asuD3, polH), not an accession, a locus tag or an orf number."""
    return not (ACCESSION.match(g["name"]) or ORF.match(g["name"]))


def cluster_genes(ref: list[dict]) -> set[int]:
    """Reference genes that may pull a contig into the figure: named genes; when a reference names fewer than three,
    the genes antiSMASH calls biosynthetic; never a mobile-element gene."""
    keep = {k for k, g in enumerate(ref) if named(g)}
    if len(keep) < 3:
        keep = {k for k, g in enumerate(ref) if g.get("kind") in BIOSYNTHETIC}
    if len(keep) < 3:
        keep = set(range(len(ref)))
    return {k for k in keep if not MOBILE.search(ref[k].get("product") or "")}


def short(g: dict) -> str:
    """A gene's label: its name with a capital (ValC), else the accession the gene table prints for it, with a
    short product in brackets. The table's Reference gene column prints the accession, so a map that showed only
    the product left a reader unable to match a row to an arrow."""
    if named(g):
        return g["name"][:1].upper() + g["name"][1:]
    p = re.sub(r"\s+(protein|family protein)$", "", g["product"] or "", flags=re.I)
    acc = g.get("name") or ""
    if not p:
        return acc
    if len(p) > 28:
        p = p[:27] + "…"
    return f"{acc} ({p})" if acc else p


def anchor_gene(ref, drawn, prots, core_contig, name=None):
    """The reference gene both rows are centred on, as (ref index, protein id), or None.

    A named gene when one is asked for; otherwise the longest matched reference gene that antiSMASH calls biosynthetic
    (the PKS, NRPS or other core enzyme), on the core contig first, then anywhere; then the longest matched gene on the
    core contig, then the longest matched gene anywhere. The longest core enzyme is the gene a reader looks for first;
    a transporter or a hypothetical protein is a poor centre even when it sits on the core contig."""
    on_core = [(k, pid) for k, pid, _ in drawn if prots[pid]["contig"] == core_contig]
    length = lambda m: ref[m[0]]["e"] - ref[m[0]]["s"]
    if name:
        hit = [(k, pid) for k, pid, _ in drawn if ref[k]["name"].lower() == name.lower()]
        if hit:
            return max(hit, key=lambda m: (prots[m[1]]["contig"] == core_contig, length(m)))
    every = [(k, pid) for k, pid, _ in drawn]
    core_enzyme = lambda ms: [m for m in ms if ref[m[0]].get("kind") == "biosynthetic"]
    for pool in (core_enzyme(on_core), core_enzyme(every), on_core, every):
        if pool:
            return max(pool, key=length)
    return None


def choose(ref, rows, splits, prots, core_contig, partner_contig=None, partner_rows=None):
    """-> (matches [(ref index, protein id, identity)], split info {ref index: (pid1, pid2, id1, id2)},
    ordered contig list, number of clear finds not drawn, secondary contigs).
    partner_contig: an RG-GMCI pair map. The partner contig is drawn next to the core and no other contig is pulled in,
    so the figure shows the pair and nothing else; every other find is counted as not drawn.
    partner_rows: the same gene table searched from the partner's side. Its in-region matches are drawn too, so a
    reference gene matched in both fragments gets two ribbons: overlap shows as overlap, complement as complement."""
    # an unnamed find stays off a new contig even when SUPPORTED: partner support is adjacency, and a conserved housekeeping
    # operon from the reference's flanks is adjacent too (6 Oct screen: NADH dehydrogenase and topoisomerase genes on
    # phosphonoglycan maps). Tagging reference-flank finds is a separate step.
    cluster = cluster_genes(ref)
    tag_to_pid = {p["tag"]: pid for pid, p in prots.items()}
    found, verdict = [], {}
    pid_of = lambda r: r.get("best_protein") if r.get("best_protein") in prots else tag_to_pid.get(r.get("best_locus"))
    # When partner checks ran, a contig other than the core is drawn only if it holds a SUPPORTED find; a set-aside
    # gene beside a supported one on the same contig is drawn with it.
    checked = any(r.get("partner_verdict") for r in rows)
    anchored = {prots[pid_of(r)]["contig"] for r in rows if r.get("partner_verdict") == "SUPPORTED" and pid_of(r)}
    for k, r in enumerate(rows):
        pid = pid_of(r)
        if checked and r.get("status") != "PRESENT_IN_CORE" and pid and prots[pid]["contig"] != core_contig \
                and prots[pid]["contig"] not in anchored and prots[pid]["contig"] != partner_contig:
            continue
        if r.get("partner_verdict") in EXCLUDED_VERDICTS and not (pid and prots[pid]["contig"] in anchored):
            continue  # a housekeeping gene or a paralog-family member never pulls a contig in (partner checks)
        # A reciprocal-best test is the right guard for a match pulled in from elsewhere in the genome, where a
        # paralog can pose as the missing gene. Inside the core region it is the wrong guard: the table has already
        # decided the row is present, and when one protein is the best match for two reference genes only one of
        # those rows can be reciprocal best, so the other was dropped and its reference gene drawn grey while the
        # table still counted it. Draw one ribbon per core row the table counts.
        if (r.get("status") == "PRESENT_IN_CORE"
                or (r.get("status") == "MISSING_FOUND_CLEAR" and _true(r.get("reciprocal_best")))):
            pid = r.get("best_protein") if r.get("best_protein") in prots else tag_to_pid.get(r.get("best_locus"))
            if pid:
                found.append((k, pid, float(r["best_identity_pct"])))
                verdict[pid] = r.get("partner_verdict") or ""
    if partner_rows:
        have = {pid for _, pid, _ in found}
        for k, r in enumerate(partner_rows):
            pid = r.get("best_protein")
            if (r.get("status") == "PRESENT_IN_CORE" and _true(r.get("reciprocal_best")) and pid in prots
                    and prots[pid]["contig"] == partner_contig and pid not in have):
                found.append((k, pid, float(r["best_identity_pct"])))
    # the shared rule (split_display): only a split the table shows as a split row is drawn as one; a gene already
    # called core keeps its core match, and a split whose pieces are not both in this genome is not drawn
    split_info = {}
    for k, e in split_display(rows, splits, "", tag_to_pid).items():
        if e["shown"]:
            s = e["record"]
            split_info[k] = (tag_to_pid[s["piece1_locus"]], tag_to_pid[s["piece2_locus"]],
                             float(s["piece1_identity_pct"]), float(s["piece2_identity_pct"]))
    found = [m for m in found if m[0] not in split_info]
    for k, (p1, p2, i1, i2) in split_info.items():
        found += [(k, p1, i1), (k, p2, i2)]
    fixed = [core_contig]
    if partner_contig and partner_contig != core_contig:
        fixed.append(partner_contig)
    for p1, p2, _, _ in split_info.values():
        for pid in (p1, p2):
            if prots[pid]["contig"] not in fixed:
                fixed.append(prots[pid]["contig"])
    best_by_contig = {}
    for k, pid, ident in found:
        c = prots[pid]["contig"]
        if c not in fixed and k in cluster and ident >= SECONDARY_MIN_ID:
            best_by_contig[c] = max(best_by_contig.get(c, 0), ident)
    extra = [] if partner_contig else \
        sorted(best_by_contig, key=lambda c: (best_by_contig[c] < PRIMARY_MIN_ID, -best_by_contig[c]))[:MAX_EXTRA]
    secondary = {c for c in extra if best_by_contig[c] < PRIMARY_MIN_ID}
    shown = set(fixed) | set(extra)
    drawn = [m for m in found if prots[m[1]]["contig"] in shown and
             (prots[m[1]]["contig"] in fixed or (m[0] in cluster and m[2] >= SECONDARY_MIN_ID))]
    not_drawn = len({(k, pid) for k, pid, _ in found} - {(k, pid) for k, pid, _ in drawn})
    ref_mid = lambda c: statistics.median((ref[k]["s"] + ref[k]["e"]) / 2 for k, pid, _ in drawn if prots[pid]["contig"] == c)
    order = fixed + sorted(extra, key=ref_mid)
    return drawn, split_info, order, not_drawn, secondary


def _arrow(ax, x0, x1, y, strand, fc):
    from matplotlib.patches import Polygon
    hd = min(0.5, (x1 - x0) * 0.35); h = H / 2
    pts = ([(x0, y - h), (x1 - hd, y - h), (x1, y), (x1 - hd, y + h), (x0, y + h)] if strand >= 0 else
           [(x1, y - h), (x0 + hd, y - h), (x0, y), (x0 + hd, y + h), (x1, y + h)])
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec="#333333", lw=0.6, zorder=3))


NOTE_WRAP = 140  # footnote characters per line


def bulk_offset(ref, drawn, xpos, prots, core_contig):
    """Horizontal shift that lines the core contig's matches up under their reference genes: the median, over matches,
    of (reference gene mid - match mid). None when the core contig has no drawn match."""
    d = sorted((ref[k]["s"] + ref[k]["e"]) / 2 - (xpos[pid][0] + xpos[pid][1]) / 2
               for k, pid, _ in drawn if pid in xpos and prots[pid]["contig"] == core_contig)
    return statistics.median(d) if d else None


def edge_side(region: dict, contig_len: int) -> str | None:
    """Which contig end a region touches: "left", "right", or None (interior, or both ends: a whole-contig region)."""
    left, right = region["start"] <= EDGE_BP, region["end"] >= contig_len - EDGE_BP
    return "left" if left and not right else "right" if right and not left else None


STATUS_ORDER = ("PRESENT_IN_CORE", "MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS", "MISSING_NOT_FOUND")
SPLIT_STATUS = "SPLIT_ACROSS_CONTIG_ENDS"


def split_eligible(x: dict) -> bool:
    """Whether a split-gene record can be drawn and counted as a split at all. split_display, the rule the map, the
    counts and the gene table share, then binds an eligible record to its row and applies the core-call and genome checks.

    Eligible: a CLEAR call with both piece loci named, and a status that is the split status or absent (older and
    synthetic records carry no status column). A record with a CLEAR call but another status, or with a piece missing,
    is inconsistent and is neither drawn nor counted as a split."""
    return (x.get("split_call") == "CLEAR" and bool(x.get("piece1_locus")) and bool(x.get("piece2_locus"))
            and (x.get("status") or SPLIT_STATUS) == SPLIT_STATUS)


def split_display(rows, splits, core_identity: str = "", known_tags=None) -> dict:
    """The one split rule the map, the counts and the gene table share, so the three cannot disagree.

    Returns {row index in `rows`: entry} for each reference gene with an eligible split record (split_eligible):
      entry["record"]      the record; duplicate records for one gene count once (the last one is kept)
      entry["shown"]       True when the table shows the gene as one split row and the map draws its two pieces.
                           False when the gene is already called core: a split never overrides a PRESENT_IN_CORE call,
                           so the core row stands and the split is noted beside it.
      entry["core_piece"]  the locus of a piece lying in the core region, or None. A shown split counts once: in the core
                           when a piece is there, otherwise as found clearly elsewhere, never as not found.
    A record binds to the row with its reference-gene number (by position when rows carry no number), and only when the
    two name the same gene. A record with no number, or a number this run does not have, binds by name when exactly one
    row has that name. A record that binds to no row, or (when `known_tags` is given) whose pieces are not both in this
    genome, is left out: its gene keeps its own status everywhere."""
    by_ref = {str(r.get("reference_gene")): i for i, r in enumerate(rows) if str(r.get("reference_gene") or "")}
    by_name = collections.defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("name"):
            by_name[r["name"]].append(i)
    out = {}
    for x in splits or []:
        if not split_eligible(x):
            continue
        ref = str(x.get("reference_gene") or "")
        i = by_ref.get(ref) if by_ref else (int(ref) - 1 if ref.isdigit() else None)
        if i is not None and not 0 <= i < len(rows):
            i = None
        if i is None and len(by_name.get(x.get("name") or "", [])) == 1:
            i = by_name[x["name"]][0]
        if i is None:
            continue
        if x.get("name") and rows[i].get("name") and x["name"] != rows[i]["name"]:
            continue
        if known_tags is not None and not (x["piece1_locus"] in known_tags and x["piece2_locus"] in known_tags):
            continue
        core_piece = next((x[f"piece{n}_locus"] for n in (1, 2)
                           if core_identity and x.get(f"piece{n}_region_identity") == core_identity), None)
        out[i] = {"record": x, "shown": rows[i].get("status") != "PRESENT_IN_CORE", "core_piece": core_piece}
    return out


def count_summary(rows, splits=(), core_identity: str = "", known_tags=None) -> dict:
    """The counts every caption of a gap-rescue run prints, as one partition of the reference genes.

    Each reference gene is counted once, as the gene table shows it, so core + clear + ambiguous + not found (+ other) is
    always the number of reference genes. A gene shown as a split (split_display) counts in the core when a piece lies
    there, otherwise as found clearly elsewhere; every other gene counts under its own status. "Set aside by partner
    checks" is a partner verdict, not a status: it is a subset of those genes and is printed as one, never beside them as
    a peer (the old footnote added it in and a reader got 31 + 20 + 16 = 67 of 60). The core count is of reference genes;
    core_proteins counts the distinct local proteins behind them (by locus tag), because one protein can be the best
    match for several reference genes. The owner's ruling (7 Oct): print both. The split count is the number of reference
    genes shown as split rows."""
    disp = split_display(rows, splits, core_identity, known_tags)
    st, prot = collections.Counter(), set()
    for i, r in enumerate(rows):
        e = disp.get(i)
        if e and e["shown"]:
            st["PRESENT_IN_CORE" if e["core_piece"] else "MISSING_FOUND_CLEAR"] += 1
            if e["core_piece"]:
                prot.add(e["core_piece"])
            continue
        st[r.get("status") or ""] += 1
        if r.get("status") == "PRESENT_IN_CORE":
            prot.add(r.get("best_locus") or r.get("best_protein"))
    prot.discard(None); prot.discard("")
    return {"reference_genes": len(rows), "core": st["PRESENT_IN_CORE"], "core_proteins": len(prot),
            "clear": st["MISSING_FOUND_CLEAR"], "ambiguous": st["MISSING_FOUND_AMBIGUOUS"],
            "not_found": st["MISSING_NOT_FOUND"], "other": len(rows) - sum(st[k] for k in STATUS_ORDER),
            "set_aside": sum(1 for r in rows if r.get("partner_verdict") in EXCLUDED_VERDICTS),
            "split": sum(1 for e in disp.values() if e["shown"])}


def count_sentence(c: dict, where: str = "the core") -> str:
    """count_summary as one sentence: '12 of 27 reference genes in <where>, on 7 distinct proteins; ...'."""
    s = f"{c['core']} of {c['reference_genes']} reference genes in {where}"
    if c["core"]:
        s += f", on {c['core_proteins']} distinct protein{'' if c['core_proteins'] == 1 else 's'}"
    parts = [f"{c['clear']} found clearly elsewhere", f"{c['ambiguous']} found ambiguously", f"{c['not_found']} not found"]
    if c["other"]:
        parts.append(f"{c['other']} with another status")
    s += "; " + "; ".join(parts)
    if c["set_aside"]:
        s += (f". Of these, {c['set_aside']} {'was' if c['set_aside'] == 1 else 'were'} set aside by partner checks "
              "(housekeeping or paralog family)")
    if c["split"]:
        # the gene table lists both pieces together in one row per reference gene (table_rows), so say exactly that
        s += (f". {c['split']} reference gene{' is' if c['split'] == 1 else 's are'} split across contigs, with both "
              "pieces listed together in one row per reference gene")
    return s


def contig_parts(lo, hi, L, spans, gap_kb=SEG_BREAK_KB, pad=2500):
    """One contig's drawn window, cut into parts wherever the drawn genes leave a stretch longer than gap_kb with
    nothing on it. -> [(lo, hi), ...] in contig order; the window unchanged when nothing is that far apart.

    spans: (start, end) of every drawn gene on the contig, plus the core region on the core contig. One distant match
    used to set the whole window, so a 10 kb cluster was drawn as slivers across a 150 kb axis. The parts are drawn
    as separate segments of the same contig with the omitted length printed on the cut: they are one molecule, the
    stretch between them is simply not drawn, and nothing about the drawing joins them."""
    if L <= 12000 or not spans:
        return [(lo, hi)]
    blocks = []
    for a, b in sorted(spans):
        if blocks and a - blocks[-1][1] <= gap_kb * 1000:
            blocks[-1][1] = max(blocks[-1][1], b)
        else:
            blocks.append([a, b])
    if len(blocks) == 1:
        return [(lo, hi)]
    return [(max(0, a - pad), min(L, b + pad)) for a, b in blocks]


def main_blocks(drawn, prots, core, split_info, gap_kb=NEAR_GAP_KB, reach_kb=REACH_KB):
    """Keep, on each contig, the matches near its anchor block; return (kept, number dropped).
    Matches form blocks where consecutive matches lie within gap_kb of each other. The anchor on the core contig is every block
    inside the core region, or the nearest block when none is inside; on another contig it is the block with the most matches
    (then the highest summed identity). Every block within reach_kb of an anchor block (or, on the core contig, of the core region)
    is kept with it, and so is a block holding a split-gene piece, so the split marker keeps both its pieces. Only matches farther away are dropped.
    6 Oct screen of 617 maps: the drops 107-534 kb from the core region were housekeeping genes from the reference's flanks
    (helicase, topoisomerase, proton pump); those within 70 kb included named cluster genes (CmnP, PauY4)."""
    pieces = {pid for p1, p2, _, _ in split_info.values() for pid in (p1, p2)}
    lo = lambda b: min(prots[x[1]]["start"] for x in b)
    hi = lambda b: max(prots[x[1]]["end"] for x in b)
    by = {}
    for m in drawn:
        by.setdefault(prots[m[1]]["contig"], []).append(m)
    kept = []
    for c, ms in by.items():
        ms = sorted(ms, key=lambda m: prots[m[1]]["start"])
        blocks, cur = [], [ms[0]]
        for m in ms[1:]:
            if prots[m[1]]["start"] - hi(cur) > gap_kb * 1000:
                blocks.append(cur); cur = [m]
            else:
                cur.append(m)
        blocks.append(cur)
        if c == core["contig"]:
            dist = lambda b: max(0, lo(b) - core["end"], core["start"] - hi(b))
            anchor = [b for b in blocks if dist(b) == 0] or [min(blocks, key=lambda b: (dist(b), -len(b)))]
        else:
            anchor = [max(blocks, key=lambda b: (len(b), sum(x[2] for x in b)))]
        near = lambda b: any(max(0, lo(b) - hi(a), lo(a) - hi(b)) <= reach_kb * 1000 for a in anchor) or \
            (c == core["contig"] and dist(b) <= reach_kb * 1000)
        kept += [m for b in blocks if near(b) or any(x[1] in pieces for x in b) for m in b]
    return kept, len(drawn) - len(kept)


def context_contigs(rows, prots, drawn, core_contig, flank=CONTEXT_FLANK, max_rows=CONTEXT_ROWS_MAX):
    """-> {contig: (lo, hi, number of matches on it)} for off-region matches the map does not draw.
    A context row shows what sits around such a match on its own contig, because a reader cannot otherwise tell whether
    the match stands alone or inside a neighbourhood. It is NOT a rescue and never becomes one: its genes are not
    ribboned to a reference gene, not coloured, not added to `drawn`, and not counted in any caption. An excluded
    verdict (paralog family, housekeeping context) stays excluded from every count; the row only lets the reader see
    where it sits. Contigs already on the map are skipped. Ranked by number of matches, then summed identity."""
    shown = {prots[pid]["contig"] for _, pid, _ in drawn} | {core_contig}
    by = {}
    for r in rows:
        pid = r.get("best_protein")
        if not pid or pid not in prots or not _true(r.get("reciprocal_best")):
            continue
        if r.get("status") not in ("MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS"):
            continue
        c = prots[pid]["contig"]
        if c in shown:
            continue
        try:
            ident = float(r.get("best_identity_pct") or 0)
        except (TypeError, ValueError):
            ident = 0.0
        by.setdefault(c, []).append((pid, ident))
    out = {}
    for c in sorted(by, key=lambda c: (-len(by[c]), -sum(i for _, i in by[c]), c))[:max_rows]:
        genes = sorted((p for p in prots.values() if p["contig"] == c), key=lambda p: p["start"])
        at = [i for i, p in enumerate(genes) if any(p is prots[pid] for pid, _ in by[c])]
        if not at:
            continue
        window = genes[max(0, min(at) - flank):max(at) + flank + 1]
        out[c] = (min(g["start"] for g in window), max(g["end"] for g in window), len(by[c]))
    return out


def draw_locus_map(ref_gbk, rows, splits, prots, regions, core, label, ref_name, out_png, out_pdf=None, pdf_pages=None,
                   partner=None, pair_note="", partner_rows=None, link_label="RG-GMCI link", link_colour=LINK,
                   anchor=None, context_partners=False):
    """rows, splits: gap_directed_rescue tables (dicts; strings or typed). prots, regions, core: its genome structures.
    partner: a second region (same keys as core) for an RG-GMCI pair map. Fragment A (the core) is turned so its contig
    end faces right, fragment B so its contig end faces left, with a link marker between them. The marker is
    homology-guided linkage, never a joined sequence. pair_note opens the footnote. link_label and link_colour let the
    caller say what the pair is: a purple link for complementary fragments, a grey "overlap" marker for two copies of
    the same part of the reference, which is not a rescue. anchor: the reference gene both rows are centred on
    (anchor_gene). context_partners: add a context row for each off-region match this map does not draw (see
    context_contigs). Off by default; it changes nothing that is drawn, ribboned or counted."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.patches import Polygon

    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"]
    ref, ref_len = reference_genes(ref_gbk)
    core_contig = core["contig"]
    drawn, split_info, order, not_drawn, secondary = choose(ref, rows, splits, prots, core_contig,
                                                            partner["contig"] if partner else None, partner_rows)
    if partner:  # a pair map shows the two regions only: a match elsewhere on either contig is counted, not drawn
        win = {core_contig: (core["start"] - 2500, core["end"] + 2500),
               partner["contig"]: (partner["start"] - 2500, partner["end"] + 2500)}
        inside = [m for m in drawn if prots[m[1]]["contig"] in win
                  and prots[m[1]]["end"] > win[prots[m[1]]["contig"]][0] and prots[m[1]]["start"] < win[prots[m[1]]["contig"]][1]]
        not_drawn += len(drawn) - len(inside)
        drawn = inside
    far = 0
    if not partner:   # 6 Oct: one far match stretched a 1.2 Mb core contig across the figure, so every gene became a sliver
        drawn, far = main_blocks(drawn, prots, core, split_info)
        not_drawn += far
    verdict_of = {r.get("best_protein"): r.get("partner_verdict") for r in rows if r.get("best_protein")}
    single_gene = {c for c in order[1:] if c not in {prots[p]["contig"] for s in split_info.values() for p in s[:2]}
                   and not (partner and c == partner["contig"])
                   and all(verdict_of.get(pid) == "SINGLE_GENE" for k, pid, _ in drawn if prots[pid]["contig"] == c)}
    by_contig = {c: [m for m in drawn if prots[m[1]]["contig"] == c] for c in order}
    # a contig whose matches all fell outside a pair map's window has nothing to draw (min() of nothing)
    order = [c for c in order if c == core_contig or (partner and c == partner["contig"]) or by_contig[c]]
    # opt-in context rows: a contig holding a match this map does not draw, shown so the reader can see what sits
    # around that match. Never a rescue: nothing here enters `drawn`, `not_drawn` or any caption count.
    ctx = context_contigs(rows, prots, drawn, core_contig) if (context_partners and not partner) else {}
    for c in ctx:
        by_contig.setdefault(c, [])
        order.append(c)
    L = {c: next((p["contig_len"] for p in prots.values() if p["contig"] == c), 0) for c in order}
    seg = []
    for c in order:
        ms = by_contig[c]
        if c == core_contig or (partner and c == partner["contig"]):
            base = core if c == core_contig else partner
            lo, hi = base["start"], base["end"]
            for _, pid, _ in ([] if partner else ms):   # a pair map keeps each fragment to its own region
                lo, hi = min(lo, prots[pid]["start"]), max(hi, prots[pid]["end"])
        elif c in ctx:
            lo, hi, _ = ctx[c]
        else:
            lo = min(prots[pid]["start"] for _, pid, _ in ms); hi = max(prots[pid]["end"] for _, pid, _ in ms)
        lo, hi = (0, L[c]) if L[c] <= 12000 else (max(0, lo - 2500), min(L[c], hi + 2500))
        mids = [((prots[pid]["start"] + prots[pid]["end"]) / 2, (ref[k]["s"] + ref[k]["e"]) / 2) for k, pid, _ in ms]
        # strand first (2 Oct: after an order-based flip a siderophore map had every arrow pointing the wrong way): the
        # length-weighted share of matches whose strand disagrees with their reference gene decides; gene order (length-
        # weighted correlation) decides only when the strand evidence is split evenly
        w = [max(1, prots[pid]["end"] - prots[pid]["start"]) for _, pid, _ in ms]
        agree = sum(k for (kk, pid, _), k in zip(ms, w) if (prots[pid]["strand"] >= 0) == (ref[kk]["strand"] >= 0))
        disagree = sum(w) - agree
        if ms and agree != disagree:
            flip = disagree > agree
        elif len({a for a, _ in mids}) >= 2 and len({b for _, b in mids}) >= 2:
            ma = sum(a * k for (a, _), k in zip(mids, w)) / sum(w); mb = sum(b * k for (_, b), k in zip(mids, w)) / sum(w)
            flip = sum(k * (a - ma) * (b - mb) for (a, b), k in zip(mids, w)) < 0
        else:
            flip = False
        seg.append({"contig": c, "lo": lo, "hi": hi, "L": L[c], "flip": flip, "by_strand": bool(ms) and agree != disagree})
    # contigs run left to right in the order their matches fall on the reference, the core included, so ribbons do not
    # cross the figure (the owner, 3 Oct: a bottromycin-like BGC's NODE_8 holds botT and botOMT, the reference's first genes, yet was
    # drawn after the core). A pair map keeps its core-then-partner order for the link.
    if not partner:
        def ref_pos(s):
            xs = [(ref[k]["s"] + ref[k]["e"]) / 2 for k, _, _ in by_contig[s["contig"]]]
            return statistics.median(xs) if xs else float("inf")
        seg.sort(key=ref_pos)
    # the two pieces of a split gene face each other across the gap, and the two ends of a pair link face each other, but
    # neither may turn a contig whose strand evidence decided it (the owner, 3 Oct: a bottromycin-like BGC's core was drawn backwards
    # against the bottromycin reference because a split-gene piece on the next contig re-flipped it)
    pair_of = {}
    for k, (p1, p2, _, _) in split_info.items():
        a, b = prots[p1]["contig"], prots[p2]["contig"]
        if not {a, b} <= {s["contig"] for s in seg}:
            continue  # a piece whose contig is not drawn (a pair map keeps only its two fragments)
        ia = next(i for i, s in enumerate(seg) if s["contig"] == a); ib = next(i for i, s in enumerate(seg) if s["contig"] == b)
        if abs(ia - ib) != 1:
            continue
        pair_of[(min(ia, ib), max(ia, ib))] = k
        for i, pid, want_right in ((min(ia, ib), p1 if ia < ib else p2, True), (max(ia, ib), p2 if ia < ib else p1, False)):
            s = seg[i]; mid = (prots[pid]["start"] + prots[pid]["end"]) / 2
            if ((s["hi"] - mid < mid - s["lo"]) != s["flip"]) != want_right and not s["by_strand"]:
                s["flip"] = not s["flip"]
    link = bool(partner) and len(seg) > 1 and seg[1]["contig"] == partner["contig"]
    if link and (0, 1) not in pair_of:  # the two contig ends face each other across the link
        for s, base, want in ((seg[0], core, "right"), (seg[1], partner, "left")):
            side = edge_side(base, s["L"])
            if side and not s["by_strand"]:
                s["flip"] = side != want
    # A contig whose drawn genes lie far apart is drawn as several parts (contig_parts). Order, turning and split-gene
    # facing are all decided above for the whole contig, so every part of a contig shares its turn; the parts are then
    # laid out in the order the turned contig reads, and a split-gene gap that sat between two contigs now sits between
    # the last part of the one and the first part of the next. A pair map keeps its two windows whole.
    if not partner:
        parted, first, last = [], {}, {}
        for i, s in enumerate(seg):
            c = s["contig"]
            spans = [(prots[pid]["start"], prots[pid]["end"]) for _, pid, _ in by_contig[c]]
            if c == core_contig:
                spans.append((core["start"], core["end"]))
            parts = contig_parts(s["lo"], s["hi"], s["L"], spans)
            if s["flip"]:
                parts = parts[::-1]
            first[i] = len(parted)
            for j, (plo, phi) in enumerate(parts):
                parted.append(dict(s, lo=plo, hi=phi, part=j + 1, parts=len(parts)))
            last[i] = len(parted) - 1
        pair_of = {(last[i], first[j]): k for (i, j), k in pair_of.items()}
        seg = parted
    x, xpos = 0.0, {}
    for i, s in enumerate(seg):
        if i:
            if (i - 1, i) in pair_of or (link and i == 1):
                x += SPLIT_GAP_KB
            elif seg[i - 1]["contig"] == s["contig"]:
                x += BREAK_GAP_KB
            else:
                x += CUT_GAP_KB
        s["x0"], s["w"] = x, (s["hi"] - s["lo"]) / 1000
        x += s["w"]
        for pid, p in prots.items():
            if p["contig"] == s["contig"] and p["end"] > s["lo"] and p["start"] < s["hi"]:
                a, b = (max(p["start"], s["lo"]) - s["lo"]) / 1000, (min(p["end"], s["hi"]) - s["lo"]) / 1000
                if s["flip"]:
                    a, b = s["w"] - b, s["w"] - a
                xpos[pid] = (s["x0"] + a, s["x0"] + b, -p["strand"] if s["flip"] else p["strand"])
    end = x
    ks = sorted({k for k, _, _ in drawn})
    colour = {k: PAL[j % len(PAL)] for j, k in enumerate(ks)}
    # the rows are lined up on the majority of the matched genes: the offset is the median of (reference mid - match
    # mid) over the core contig's matches (bulk_offset). Centring on one anchor gene (v3) left most genes fanned out
    # whenever the locus has an insertion or a different spacing (2 Oct). The anchor is still chosen, but no longer
    # marked; it sets the offset only when the core contig has no match of its own.
    anc = anchor_gene(ref, drawn, prots, core_contig, anchor)
    off = bulk_offset(ref, drawn, xpos, prots, core_contig)
    if off is None:
        if anc:
            k, pid = anc
            off = (ref[k]["s"] + ref[k]["e"]) / 2 - (xpos[pid][0] + xpos[pid][1]) / 2
        else:
            off = 0.0
    xmin, xmax = min(0.0, off) - 0.6, max(ref_len, end + off) + 0.6
    Y_V, Y_A = 2.3, 0.0
    fig, ax = plt.subplots(figsize=(13.5, 6.2))
    ax.set_xlim(xmin, xmax); ax.set_ylim(-3.6, 3.7); ax.axis("off")
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    cmap = LinearSegmentedColormap.from_list("id", ["#EEF1F5", "#1F4E79"]); norm = Normalize(30, 100)
    for k, pid, ident in drawn:
        a, b, _ = xpos[pid]; g = ref[k]
        ax.add_patch(Polygon([(g["s"], Y_V - H / 2), (g["e"], Y_V - H / 2), (b + off, Y_A + H / 2), (a + off, Y_A + H / 2)],
                             closed=True, fc=cmap(norm(ident)), ec="none", alpha=0.85, zorder=1))
    ax.plot([0, ref_len], [Y_V, Y_V], color=LINE, lw=0.8, zorder=2)
    # labels at 60 degrees are parallel lines: keep their anchors far enough apart that neighbours cannot touch
    line_px = 7.5 * fig.dpi / 72 * 1.3
    min_dx = abs(inv.transform((line_px / 0.866, 0))[0] - inv.transform((0, 0))[0])
    highs, last = [], None
    for k, g in enumerate(ref):
        _arrow(ax, g["s"], g["e"], Y_V, g["strand"], colour.get(k, GREY))
    for k, g in enumerate(ref):
        if not (named(g) or k in colour):
            continue
        mx = lx = (g["s"] + g["e"]) / 2
        if last is not None and lx < last + min_dx:
            lx = last + min_dx
        last = lx
        if lx - mx > 0.05:  # a label pushed sideways keeps a thin lead to its gene
            ax.plot([mx, lx], [Y_V + H / 2 + 0.02, Y_V + H / 2 + 0.07], color="#9CA3AF", lw=0.5, zorder=3)
        t = ax.text(lx, Y_V + H / 2 + 0.08, short(g) if k in colour else g["name"], ha="left", va="bottom", fontsize=7.5,
                    rotation=60, rotation_mode="anchor", style="italic" if named(g) else "normal",
                    weight="bold" if k in colour else "normal", color="#111827" if k in colour else "#6B7280")
        highs.append(t.get_window_extent(rend).transformed(inv).y1)
    top = max(highs + [Y_V + H / 2 + 0.3]) + 0.2
    acc = str(ref_gbk).replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
    # the accession is only a MIBiG id when it looks like one: a reference taken from a GenBank record was being
    # titled "MIBiG <GenBank accession>", which names the wrong database
    kind = "MIBiG " if re.match(r"^BGC\d+", acc) else ""
    if ref_name:
        name = ref_name[:1].upper() + ref_name[1:]
        # a compound list is wrapped, never cut: the cut used to land mid-word ("everninomici cluster")
        if len(name) > 70:
            parts, line, out_lines = name.split("/"), "", []
            for q in parts:
                line = q if not line else (line + "/" + q)
                if len(line) > 70:
                    out_lines.append(line); line = ""
            if line:
                out_lines.append(line)
            name = "/\n".join(x.strip("/") for x in out_lines if x)
        head = f"{name} cluster ({kind}{acc}, {ref_len:.1f} kb)"
    else:
        head = f"Reference cluster {acc} ({ref_len:.1f} kb)"
    ax.text(0, top, head, fontsize=9, weight="bold", va="bottom")

    for i, s in enumerate(seg):
        a, b = s["x0"] + off, s["x0"] + s["w"] + off
        ax.plot([a, b], [Y_A, Y_A], color=LINE, lw=0.8, zorder=2)
        if i and (i - 1, i) in pair_of:
            ax.text(a - SPLIT_GAP_KB / 2, Y_A, "//", ha="center", va="center", fontsize=10, color="#B91C1C",
                    weight="bold", zorder=4)
            ax.text(a - SPLIT_GAP_KB / 2, Y_A + H / 2 + 0.12, "gap" + (" (RG-GMCI pair)" if link and i == 1 else ""),
                    ha="center", va="bottom", fontsize=7, color="#B91C1C")
        elif link and i == 1:
            ax.text(a - SPLIT_GAP_KB / 2, Y_A, "//", ha="center", va="center", fontsize=10, color=link_colour, weight="bold",
                    zorder=4)
            ax.text(a - SPLIT_GAP_KB / 2, Y_A + H / 2 + 0.12, link_label, ha="center", va="bottom", fontsize=7,
                    color=link_colour)
        elif i and seg[i - 1]["contig"] == s["contig"]:
            p = seg[i - 1]
            omitted = (max(p["lo"], s["lo"]) - min(p["hi"], s["hi"])) / 1000
            ax.text(a - BREAK_GAP_KB / 2, Y_A, "//", ha="center", va="center", fontsize=10, color=LINE, zorder=4)
            ax.text(a - BREAK_GAP_KB / 2, Y_A + H / 2 + 0.12, f"{omitted:.0f} kb\nnot drawn", ha="center", va="bottom",
                    fontsize=6.5, color=LINE, linespacing=1.1)
        elif i:
            ax.text(a - CUT_GAP_KB / 2, Y_A, "//", ha="center", va="center", fontsize=10, color=LINE, zorder=4)
    for pid, (a, b, st) in xpos.items():
        k = next((k for k, q, _ in drawn if q == pid), None)
        _arrow(ax, a + off, b + off, Y_A, st, colour.get(k, GREY) if k is not None else GREY)
    # labels at 60 degrees are parallel lines: keep their anchors far enough apart that neighbours cannot touch
    line_px = 7 * fig.dpi / 72 * 1.3
    min_dx = abs(inv.transform((line_px / 0.866, 0))[0] - inv.transform((0, 0))[0])
    lows, done, last = [], set(), None
    for k, pid, ident in sorted(drawn, key=lambda m: xpos[m[1]][0]):
        a, b, _ = xpos[pid]
        mid = lambda p: (xpos[p][0] + xpos[p][1]) / 2
        if k in split_info and all(p in xpos for p in split_info[k][:2]) \
                and abs(mid(split_info[k][0]) - mid(split_info[k][1])) <= SPLIT_LABEL_KB:  # pieces side by side: one label
            if k in done:
                continue
            done.add(k)
            p1, p2, i1, i2 = split_info[k]
            lx = (mid(p1) + mid(p2)) / 2
            lab = f"{short(ref[k])}-like, split {i1:.0f}% | {i2:.0f}%"
        elif k in split_info and all(p in xpos for p in split_info[k][:2]):
            # pieces drawn far apart (6 Oct: a spectinomycin-like map put one label between pieces 20 kb apart, and the
            # spreading pass pushed the next gene's label along with it): each piece is labelled under itself
            n = split_info[k][:2].index(pid) + 1
            lx, lab = (a + b) / 2, f"{short(ref[k])}-like, split piece {n} of 2, {split_info[k][1 + n]:.0f}%"
        else:
            lx, lab = (a + b) / 2, f"{short(ref[k])}-like {ident:.0f}%"
        if last is not None and lx < last + min_dx:
            lx = last + min_dx
        last = lx
        # the reference row already leads a displaced label back to its gene; the strain row did not, so a label
        # spread sideways by min_dx could sit several genes away from the gene it names with nothing joining them
        mx = (a + b) / 2
        if lx - mx > 0.05:
            ax.plot([mx + off, lx + off], [Y_A - H / 2 - 0.02, Y_A - H / 2 - 0.07],
                    color="#9CA3AF", lw=0.5, zorder=3)
        t = ax.text(lx + off, Y_A - H / 2 - 0.08, lab, ha="right", va="top", fontsize=7, rotation=60,
                    rotation_mode="anchor", color="#111827")
        lows.append(t.get_window_extent(rend).transformed(inv).y0)
    # Where two or more ribbons meet one local gene, say so under it: a reader should not have to infer a shared
    # match from crossing ribbons. The count is of reference-gene rows the table counts, not of ribbons drawn.
    shared = {}
    for k, pid, _ in drawn:
        shared.setdefault(pid, set()).add(k)
    # Shared genes often sit next to each other, so these notes are stacked in rows rather than overprinted: each
    # one goes on the lowest row whose last note ends clear of it.
    note_w = None
    row_end = []
    note_pos = []   # (text, left, right, row), returned for tests
    for pid in sorted((p for p, ks_here in shared.items() if len(ks_here) >= 2 and p in xpos),
                      key=lambda p: xpos[p][0]):
        a, b, _ = xpos[pid]
        cx = (a + b) / 2 + off
        txt = f"matches {len(shared[pid])} reference genes"
        if note_w is None:   # measure once; every note is the same length bar the digit
            probe = ax.text(0, 0, txt, fontsize=6)
            bb = probe.get_window_extent(rend).transformed(inv)
            note_w = bb.x1 - bb.x0
            probe.remove()
        lo = cx - note_w / 2
        # a note must clear the last note on its row by a visible gap: two notes that merely did not overlap were drawn
        # flush, and read as one run-on line ("matches 2 reference genesmatches 9 reference genes")
        r = next((i for i, x_end in enumerate(row_end) if lo > x_end + 0.15 * note_w), len(row_end))
        if r == len(row_end):
            row_end.append(cx + note_w / 2)
        else:
            row_end[r] = cx + note_w / 2
        note_pos.append((txt, cx - note_w / 2, cx + note_w / 2, r))
        t = ax.text(cx, Y_A + H / 2 + 0.06 + r * 0.13, txt,
                    ha="center", va="bottom", fontsize=6, color="#6B7280")
        lows.append(t.get_window_extent(rend).transformed(inv).y0)
    ylab = min(lows + [Y_A - 0.5]) - 0.2
    seg_labels = []
    for s in seg:
        a, b = s["x0"] + off, s["x0"] + s["w"] + off
        node = re.match(r"(NODE_\d+)", s["contig"]); node = node.group(1) if node else s["contig"][:18]
        regs = [r for r in regions if r["contig"] == s["contig"] and r["end"] > s["lo"] and r["start"] < s["hi"]]
        alias = ", ".join(r["identity"].split(" / ")[-1] for r in regs if len(r["identity"].split(" / ")) == 4)
        if s.get("parts", 1) > 1:   # one of several parts of this contig
            extra = ", ".join(t for t in ("reversed" if s["flip"] else "", f"part {s['part']} of {s['parts']}") if t)
        else:
            extra = ", ".join(t for t in ("reversed" if s["flip"] else "", "part" if s["hi"] - s["lo"] < s["L"] else "") if t)
        in_core = s["contig"] == core_contig and core["end"] > s["lo"] and core["start"] < s["hi"]
        if partner and s["contig"] == core_contig:
            who = "fragment A, " + core["identity"].split(" / ")[-1]
        elif partner and s["contig"] == partner["contig"]:
            who = "fragment B, " + partner["identity"].split(" / ")[-1]
        else:
            # only the part holding the core region is called the core; another part of the core contig is named by
            # its own region, or by none
            who = "core, " + core["identity"].split(" / ")[-1] if in_core else (alias or "no antiSMASH region")
        if s["contig"] in ctx:
            who += "\ncontext only, not a rescue"
        if s["contig"] in secondary:
            who += "\nsecondary (35-50%)"
        if s["contig"] in single_gene:
            who += "\nsingle-gene find"
        s["caption"] = f"{node}{' (' + extra + ')' if extra else ''}\n{who}"
        t = ax.text((a + b) / 2, ylab, s["caption"], ha="center", va="top",
                    fontsize=7.2, color="#374151", linespacing=1.3)
        bb = t.get_window_extent(rend).transformed(inv)
        seg_labels.append((t, bb.x0, bb.x1, bb.y1 - bb.y0, (a + b) / 2))
    step = max((h for *_, h, _ in seg_labels), default=0.5) + 0.12
    placed = []
    for t, x0, x1, h, cx in seg_labels:  # a label that would touch its neighbour drops one level
        lvl = 0
        while any(l == lvl and not (x1 + 0.3 < p0 or x0 - 0.3 > p1) for p0, p1, l in placed):
            lvl += 1
        placed.append((x0, x1, lvl))
        t.set_position((cx, ylab - lvl * step))
    # The isolate label sits left of the plot, level with the isolate row. Drawn above the row at xmin, it fell inside the
    # ribbon band whenever the isolate genes started at the left edge (seen on a candicidin-like map).
    ax.text(xmin - 0.4, Y_A, label, fontsize=9, weight="bold", va="center", ha="right", clip_on=False)
    # the counts use split_display with this genome's locus tags, the rule the gene table uses, so the map footnote,
    # the table caption and the table's rows agree
    note = count_sentence(count_summary(rows, splits, core["identity"], {p["tag"] for p in prots.values()}),
                          core["identity"])
    if partner:  # one count per figure: the pair line carries the counts, the second line only what is not drawn
        note = (pair_note + "\n" if pair_note else "") + (
            f"{not_drawn} matches elsewhere in the genome are not drawn; see rggmci_pair_map.tsv" if not_drawn else
            "Every match to this reference lies in the two fragments drawn")
    elif not_drawn:
        # a sentence of its own: after "Of these, N were set aside", a trailing "; 2 more not drawn" read as part of it
        note += (f". {not_drawn} match{' found is' if not_drawn == 1 else 'es found are'} not drawn (flanking or unnamed reference genes, under {SECONDARY_MIN_ID:.0f}% identity, "
                 f"beyond {MAX_EXTRA} contigs" + (f", or {far} more than {REACH_KB:.0f} kb along a contig from the drawn genes"
                 if far else "") + "; see gap_rescue.tsv)")
    if ctx:
        # named, so a reader can check the contig; counted separately, so a context row can never be read as a rescue
        note += (". Context row" + ("s" if len(ctx) > 1 else "") + " for "
                 + ", ".join(f"{(re.match(r'NODE_\d+', c) or re.match(r'.{1,18}', c)).group(0)} "
                             f"({n} match{'' if n == 1 else 'es'} not drawn)" for c, (_, _, n) in ctx.items())
                 + ": the genes around a match that this map does not draw, shown for context only. They are not"
                 " matched to a reference gene and are in no count on this figure")
    if any(s.get("parts", 1) > 1 for s in seg):
        note += ". A long stretch of a contig with no matched gene is cut out, and its length is printed at the cut"
    if anc:
        note += ". Rows are lined up on the majority of matched genes"  # no anchor arrow (3 Oct: "why are they there?")
    ybot = ylab - (max((l for *_, l in placed), default=0) + 1) * step - 0.05
    # wrapped, so the footnote never runs past the drawing and widens the saved figure (the owner, 2 Oct: "wrap the long line
    # of text so the locus maps can be larger")
    import textwrap
    footnote = note   # returned unwrapped, so callers compare text, not line breaks
    note = "\n".join(textwrap.fill(part, NOTE_WRAP) for part in note.split("\n"))
    ax.text(xmin + 0.1, ybot, note, fontsize=6.8, color="#4B5563", va="top")
    ybar = ybot - 0.3 - 0.25 * (note.count("\n") + 1)
    ax.plot([xmax - 5.6, xmax - 0.6], [ybar, ybar], color="#111827", lw=1.2)
    ax.text(xmax - 3.1, ybar - 0.07, "5 kb", ha="center", va="top", fontsize=7.5)
    y0, y1 = ybar - 0.75, top + 0.5
    ax.set_ylim(y0, y1)
    fig.set_size_inches(13.5, 6.2 * (y1 - y0) / 7.3)  # grow the page, never squeeze the text
    cax = ax.inset_axes([xmin + 0.1, ybar - 0.07, 0.2 * (xmax - xmin), 0.14], transform=ax.transData)
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
    cb.set_label("Protein identity (%)", fontsize=7.5, labelpad=2); cb.ax.tick_params(labelsize=7)
    fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor="white")
    if out_pdf:
        fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    if pdf_pages is not None:
        pdf_pages.savefig(fig, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"contigs_drawn": list(dict.fromkeys(s["contig"] for s in seg)), "not_drawn": not_drawn, "link_drawn": link,
            "segments": [{"contig": s["contig"], "lo": s["lo"], "hi": s["hi"], "part": s.get("part", 1),
                          "parts": s.get("parts", 1), "flip": s["flip"], "caption": s.get("caption", "")} for s in seg],
            "split_gaps": sorted(pair_of), "footnote": footnote, "shared_notes": note_pos,
            "flipped": {s["contig"]: s["flip"] for s in seg},
            "anchor": short(ref[anc[0]]) if anc else "", "anchor_contig": prots[anc[1]]["contig"] if anc else ""}
