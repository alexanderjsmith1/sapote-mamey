"""Independent evidence layers for one candidate split pair, read from the antiSMASH result archive.

Used by the class-routed two-proof policy (`nonks_second_proof.py`, policy `class_routed_v1`) for clusters without a
ketosynthase. Two layers, both computed from the archive the package was built from, never from a supplied table:

- Class logic (antiSMASH core-HMM hits and NRPS/PKS domains on each region record):
  * a single-copy marker (terpene synthase, LanC-like, YcaO, IucA/IucC, type II KS/CLF, chalcone synthase) that is a
    complete gene on BOTH pieces, or a terminal TE/TD core gene or a starter condensation domain on both, means two
    clusters (CONFLICT). A copy cut at the contig end (`<` or `>` in its location) does not count, because the rest of
    that gene may be on the other piece;
  * COMPLEMENTS_CORE: together the pieces carry a class's core set that neither carries alone.
- Intact relative (antiSMASH ClusterBlast): the reference both pieces hit with the highest summed score. Each piece's
  main locus is its densest 40-gene window of hits. CONSISTENT when the two loci lie within 50 genes; APART_CLOSE when
  farther apart in a complete relative matched at >= 70% mean identity by both sides; APART_WEAK otherwise.

The intact-relative layer reads the same ClusterBlast hits as RG-GMCI, so it is a stricter reading of homology, not an
independent channel; the class-logic layer is independent of homology. Both are report-only here: the policy decides.
A verdict is a candidate for adjudication, never a join. Ported from the RG-GMCI benchmark scorecard (its 50-gene and
70% values were set on that benchmark's three public lineages; they are not validated on held-out data).
"""
from __future__ import annotations

import re
import zipfile
from collections import Counter
from pathlib import PurePosixPath

ADJACENT_GENES = 50
LOCUS_WINDOW = 40
APART_MIN_IDENTITY = 70.0
COMPLETE_WORDS = ("complete genome", "chromosome", "complete sequence")

# class -> core requirements; each requirement is a set of alternative HMM / domain names (any one fulfils it)
CORE = {
    "T1PKS": [{"PKS_KS"}, {"PKS_AT"}, {"ACP", "PKS_PP", "PP-binding"}],
    "NRPS": [{"Condensation", "Condensation_LCL", "Condensation_DCL", "Condensation_Starter", "Condensation_Dual",
              "Cglyc", "Heterocyclization"}, {"AMP-binding"}, {"PCP", "PP-binding"}],
    "T2PKS": [{"t2ks", "t2ks2"}, {"t2clf"}, {"ACP", "PP-binding"}],
    "T3PKS": [{"Chal_sti_synt_N", "Chal_sti_synt_C"}],
    "terpene": [{"Terpene_synth", "Terpene_synth_C", "phytoene_synt", "T1TS", "T2TS", "PT_FPPS_like",
                 "PT_phytoene_like", "Terpene_syn_C_2"}],
    "lanthipeptide": [{"LANC_like", "DUF4135", "Lant_dehydr_N", "Lant_dehydr_C"}],
    "NI-siderophore": [{"IucA_IucC"}],
    "thiopeptide": [{"YcaO", "TIGR03882", "thiostrepton"}],
    "LAP": [{"YcaO", "TIGR03882"}],
}
SINGLE_COPY = frozenset({"t2ks", "t2ks2", "t2clf", "Chal_sti_synt_N", "Terpene_synth", "Terpene_synth_C",
                         "phytoene_synt", "T1TS", "T2TS", "Terpene_syn_C_2", "LANC_like", "DUF4135", "IucA_IucC",
                         "YcaO"})
CORE_GENE_DOMAINS = frozenset({"PKS_KS", "Condensation", "Condensation_LCL", "Condensation_DCL",
                               "Condensation_Starter", "Condensation_Dual", "AMP-binding"})
VERDICTS = ("CONFLICT", "CONSISTENT", "APART_CLOSE", "APART_WEAK", "NOT_READ")


def region_inventory(text: str) -> dict:
    """Core-HMM and domain names in one region record; `whole` counts complete CDSs only."""
    names, whole, per_gene, partial = Counter(), Counter(), {}, set()
    features = re.split(r"\n     (?=\S)", text)
    for feat in features:
        if feat.startswith("CDS"):
            loc = feat.split("\n", 1)[0]
            tag = re.search(r'/locus_tag="([^"]+)"', feat)
            cut = "<" in loc or ">" in loc
            if cut and tag:
                partial.add(tag.group(1))
            for m in re.finditer(r'/sec_met_domain="([^" (]+)', feat):
                names[m.group(1)] += 1
                if not cut:
                    whole[m.group(1)] += 1
    for feat in features:
        if feat.startswith("aSDomain"):
            d = re.search(r'/aSDomain="([^"]+)"', feat)
            t = re.search(r'/locus_tag="([^"]+)"', feat)
            if d:
                names[d.group(1)] += 1
                if t:
                    per_gene.setdefault(t.group(1), set()).add(d.group(1))
    terminal = sum(1 for g, doms in per_gene.items()
                   if g not in partial and doms & CORE_GENE_DOMAINS and doms & {"Thioesterase", "TD"})
    starter = sum(1 for g, doms in per_gene.items() if g not in partial and "Condensation_Starter" in doms)
    return {"names": names, "whole": whole, "terminal": terminal, "starter": starter}


def classes_of(products) -> set[str]:
    toks = {p.strip() for p in (products if isinstance(products, (list, tuple)) else
                                re.split(r"[;,|]", products or "")) if p and p.strip()}
    out = {c for c in CORE if c in toks}
    if toks & {"NRPS-like", "NRP-metallophore"}:
        out.add("NRPS")
    if toks & {"PKS-like", "hglE-KS", "transAT-PKS"}:
        out.add("T1PKS")
    return out


def _complete(names: Counter, cls: str) -> bool:
    return all(any(names.get(n, 0) for n in req) for req in CORE[cls])


def duplicated_markers(inv_a: dict, inv_b: dict) -> list[str]:
    dup = sorted(n for n in SINGLE_COPY if inv_a["whole"].get(n) and inv_b["whole"].get(n))
    if inv_a["terminal"] and inv_b["terminal"]:
        dup.append("terminal TE/TD")
    if inv_a["starter"] and inv_b["starter"]:
        dup.append("starter C")
    return dup


def completes_core(inv_a: dict, inv_b: dict, products_a, products_b) -> list[str]:
    union = classes_of(products_a) | classes_of(products_b)
    both = inv_a["names"] + inv_b["names"]
    return sorted(c for c in union if _complete(both, c)
                  and not _complete(inv_a["names"], c) and not _complete(inv_b["names"], c))


def _tag_number(tag: str):
    m = re.search(r"_RS0*(\d+)$", tag) or re.search(r"(\d+)$", tag)
    return int(m.group(1)) if m else None


def _main_locus(nums, step):
    xs = sorted(n / step for n in nums)
    best = max(((sum(1 for y in xs if x <= y <= x + LOCUS_WINDOW), x) for x in xs), default=None)
    if not best:
        return None
    lo = best[1]
    inside = [y for y in xs if lo <= y <= lo + LOCUS_WINDOW]
    return min(inside), max(inside)


def locus_distance(genes_a, genes_b):
    """Gap in genes between the two main loci in one relative (negative when they overlap), or None."""
    na = [n for n in map(_tag_number, genes_a) if n is not None]
    nb = [n for n in map(_tag_number, genes_b) if n is not None]
    if not na or not nb:
        return None
    step = 5 if all(n % 5 == 0 for n in na + nb) else 1
    la, lb = _main_locus(na, step), _main_locus(nb, step)
    return max(la[0], lb[0]) - min(la[1], lb[1]) - 1


def clusterblast_relatives(zf: zipfile.ZipFile, region_gbk: str) -> dict:
    """{reference accession: (source line, cumulative score, {reference gene: best identity})} for one region."""
    path = PurePosixPath(region_gbk)
    m = re.match(r"(.+)\.region(\d+)\.gbk$", path.name)
    if not m:
        return {}
    folder = "" if str(path.parent) == "." else f"{path.parent}/"
    name = f"{folder}clusterblast/{m.group(1)}_c{int(m.group(2))}.txt"
    if name not in zf.namelist():
        return {}
    text = zf.read(name).decode(errors="replace").split("Details:", 1)
    out = {}
    for block in (text[1].split(">>")[1:] if len(text) > 1 else []):
        acc = re.search(r"^\s*\d+\.\s+(\S+)", block, re.M)
        src = re.search(r"^Source:\s*(.*)$", block, re.M)
        score = re.search(r"Cumulative BLAST score:\s*([\d.]+)", block)
        table = block.split("coverage, e-value):", 1)
        genes = {}
        for line in (table[1].strip().splitlines() if len(table) > 1 else []):
            f = line.split("\t")
            if len(f) >= 3 and f[2].replace(".", "").isdigit():
                genes[f[1]] = max(genes.get(f[1], 0.0), float(f[2]))
        if acc and genes:
            out[acc.group(1)] = (src.group(1).strip() if src else "", float(score.group(1)) if score else 0.0, genes)
    return out


class RegionCache:
    """One archive, read once per region record."""

    def __init__(self, zf: zipfile.ZipFile):
        self.zf, self._inv, self._cb = zf, {}, {}

    def inventory(self, gbk: str) -> dict:
        if gbk not in self._inv:
            self._inv[gbk] = region_inventory(self.zf.read(gbk).decode(errors="replace"))
        return self._inv[gbk]

    def relatives(self, gbk: str) -> dict:
        if gbk not in self._cb:
            self._cb[gbk] = clusterblast_relatives(self.zf, gbk)
        return self._cb[gbk]


def score_pair(cache: RegionCache, gbk_a: str, gbk_b: str, products_a=(), products_b=()) -> dict:
    """Both layers for one pair. Keys match the external scorecard the policy already reads."""
    ia, ib = cache.inventory(gbk_a), cache.inventory(gbk_b)
    dup = duplicated_markers(ia, ib)
    ca, cb = cache.relatives(gbk_a), cache.relatives(gbk_b)
    shared = set(ca) & set(cb)
    row = {"duplicated_markers": "; ".join(dup), "completes_core": "; ".join(completes_core(ia, ib, products_a,
                                                                                             products_b)),
           "relative": "", "relative_source": "", "relative_assembly": "", "relative_identity_a": "",
           "relative_identity_b": "", "locus_gap_genes": ""}
    gap = None
    if shared:
        rel = max(sorted(shared), key=lambda r: ca[r][1] + cb[r][1])  # ties go to the lowest accession
        gap = locus_distance(ca[rel][2], cb[rel][2])
        ida = sum(ca[rel][2].values()) / len(ca[rel][2])
        idb = sum(cb[rel][2].values()) / len(cb[rel][2])
        complete = any(w in ca[rel][0].lower() for w in COMPLETE_WORDS)
        row.update(relative=rel, relative_source=ca[rel][0], relative_assembly="complete" if complete else "draft",
                   relative_identity_a=round(ida, 1), relative_identity_b=round(idb, 1),
                   locus_gap_genes="" if gap is None else int(gap))
    if dup:
        verdict = "CONFLICT"
    elif gap is None:
        verdict = "NOT_READ"
    elif gap <= ADJACENT_GENES:
        verdict = "CONSISTENT"
    elif complete and min(row["relative_identity_a"], row["relative_identity_b"]) >= APART_MIN_IDENTITY:
        verdict = "APART_CLOSE"
    else:
        verdict = "APART_WEAK"
    row["layers_verdict"] = verdict
    return row


def scorecards_from_archive(zip_path, strain_id: str, bgcs: list[dict], pairs) -> list[dict]:
    """Scorecard rows for `pairs` (iterable of (bgc_id_a, bgc_id_b)) in the shape `position_index` reads.

    Each BGC must carry `source_gbk` (its region record's path in the archive). A pair whose record is missing is
    skipped, so the policy reports it as not read rather than as evidence either way."""
    from .companion_evidence import identity_text
    by_id = {b["bgc_id"]: b for b in bgcs}
    rows, seen = [], set()
    from .source_context import source_zipfile  # the captured copy during a run; the file itself otherwise
    with source_zipfile(zip_path) as zf:
        names = set(zf.namelist())
        cache = RegionCache(zf)
        for a, b in pairs:
            key = frozenset((a, b))
            if a == b or key in seen or a not in by_id or b not in by_id:
                continue
            seen.add(key)
            ga, gb = by_id[a].get("source_gbk") or "", by_id[b].get("source_gbk") or ""
            if ga not in names or gb not in names:
                continue
            row = score_pair(cache, ga, gb, by_id[a].get("products", []), by_id[b].get("products", []))
            row.update(strain=strain_id, pair=f"{a}+{b}", identity_a=identity_text(strain_id, by_id[a]),
                       identity_b=identity_text(strain_id, by_id[b]))
            rows.append(row)
    return rows
