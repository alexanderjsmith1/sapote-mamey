#!/usr/bin/env python3
"""
build_punchcard.py — deterministic literature punch-card, generated IMMEDIATELY
after Mamey (no Sapote judgment required), for one or more strains at once.

Why post-Mamey, not post-judgment: the KCB dereplication anchors and gene markers
are deterministic. Pulling them up-front for all leads, including low-ranked ones, lets the
background inform the whole judgment pass instead of being chased lead-by-lead at the
end. A web-enabled session (ChatGPT) answers the card; results return to Sapote.

Multi-strain: pass several packages; anchors shared across strains collapse to one
question (tagged with every strain/BGC that hit them), so a 3-strain card stays small.

Usage:
  python tools/build_punchcard.py \
      --packages pkgA/package pkgB/package pkgC/package \
      [--gbk-dirs gbkA gbkB gbkC]   # optional: enables the gene-marker scan
      [--out combined_punchcard.md]

Reads each package's manifest.json. With --gbk-dirs, also scans region GBKs for a
curated set of compound-naming marker genes (e.g. nikJ -> nikkomycin) that can name a
product the generic KCB anchor missed.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text
from collections import defaultdict


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# Anchors that are primary/ubiquitous metabolites or project-excluded — confirm class
# only, do not spend a literature slot. (NAPAA / e-poly-L-lysine is a standing exclusion.)
DEPRIORITIZE = {
    "ectoine": "osmolyte (primary-adjacent)",
    "hopene": "hopanoid membrane lipid (primary)",
    "geosmin": "ubiquitous terpene odorant (primary)",
    "isorenieratene": "carotenoid pigment (primary-adjacent)",
    "ε-poly-l-lysine": "NAPAA — PROJECT-EXCLUDED from comparative claims",
    "poly-l-lysine": "NAPAA — PROJECT-EXCLUDED from comparative claims",
    "melanin": "pigment (primary-adjacent)",
    "desferrioxamine": "ubiquitous siderophore (iron economy; keep as flag only)",
}

# Curated compound-naming markers: gene/domain token -> (compound/class, why it matters).
# Catches products the generic KCB anchor can miss (your nikJ -> nikkomycin case).
GENE_MARKERS = {
    "nikJ": ("nikkomycin-class peptidyl-nucleoside", "chitin-synthase inhibitor; antifungal incl. Candida"),
    "phzB": ("phenazine", "redox-active antibacterial"),
    "phzF": ("phenazine", "redox-active antibacterial"),
    "tra_KS": ("trans-AT PKS", "high-interest PKS architecture"),
    "AHBA_syn": ("ansamycin (mC7N starter)", "rifamycin/ansamycin family"),
    "StrR": ("aminoglycoside (StrR-regulated)", "streptomycin-type pathway regulator"),
    "salinomycin": ("polyether ionophore", "antibacterial ionophore"),
}


def _complete_identity(strain, row):
    """Fail closed rather than emitting a shortened BGC alias."""
    contig = row.get("contig") or row.get("node_id")
    region = row.get("region") or row.get("region_number")
    alias = row.get("bgc_id")
    if not all((strain, contig, region, alias)):
        raise ValueError("PUNCHCARD_IDENTITY_HOLD: strain, full node-or-contig, region, and BGC alias are required")
    return f"{strain} / {contig} / {region} / {alias}"


def collect(packages, gbk_dirs):
    anchors = defaultdict(list)     # (mibig, name) -> [(strain,bgc)]
    cryptic = defaultdict(list)     # product_class -> [(strain,bgc)]
    markers = defaultdict(list)     # (gene, compound, why) -> [(strain,bgc,locus_tag)]
    strains = []
    for i, pkg in enumerate(packages):
        man = _read_json(os.path.join(pkg, "manifest.json"))
        sid = man.get("strain_id", os.path.basename(pkg))
        strains.append(sid)
        node_of = {}
        for b in man["bgcs"]:
            mib = b.get("closest_mibig_accession")
            cp = b.get("closest_candidate_kcb_product")
            identity = _complete_identity(sid, b)
            if mib and mib not in ("-", "UNRESOLVED") and cp and cp != "UNRESOLVED":
                anchors[(mib, cp[:48])].append((sid, identity))
            else:
                cryptic[";".join(b.get("products") or [])].append((sid, identity))
            mm = re.search(r"NODE_(\d+)", b.get("contig") or "")
            node_of[b["bgc_id"]] = mm.group(1) if mm else None
        # optional gene-marker scan
        if gbk_dirs and i < len(gbk_dirs) and gbk_dirs[i]:
            for b in man["bgcs"]:
                nn = node_of.get(b["bgc_id"])
                if not nn:
                    continue
                for gp in glob.glob(os.path.join(gbk_dirs[i], "NODE_%s_*.gbk" % nn)):
                    txt = open(gp, encoding="utf-8", errors="replace").read()
                    for gene, (comp, why) in GENE_MARKERS.items():
                        # v9.7.115: bounded-token match, not bare substring — the old pattern flagged
                        # 'StrRX'/'StrReductase' as StrR. Letters/digits bound the token; '_' separates.
                        _hit = any(re.search(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(gene), vv.group(1))
                                   for vv in re.finditer(r'/(?:gene|sec_met_domain|NRPS_PKS)="?([^"]*)', txt))
                        if _hit:
                            lt = ""
                            mlt = re.search(r'/locus_tag="(ctg\d+_\d+)"[^/]*%s' % re.escape(gene), txt, re.S)
                            markers[(gene, comp, why)].append((sid, _complete_identity(sid, b), nn))
    return strains, anchors, cryptic, markers


def render(strains, anchors, cryptic, markers):
    L = []
    L.append("# Combined Literature Punch Card — %s" % " + ".join(strains))
    L.append("")
    L.append("**To the web session (e.g. ChatGPT):** you have web access. Answer each numbered "
             "block from the literature and **cite a source** (DOI / PMID / MIBiG or NCBI accession) "
             "with a one-line confidence. These are *dereplication signposts*, not confirmed identities. "
             "For each named compound, report only targets actually tested in the cited source; do not assume project targets. "
             "Fill the `A:` blanks; do not judge beyond sources.")
    L.append("")
    L.append("**Strains covered:** %s. Anchors hit by more than one strain are asked once and tagged with every hit." % ", ".join(strains))
    L.append("")

    # Section 1: named anchors
    L.append("## 1 · Named dereplication anchors (all leads, incl. low-ranked)")
    L.append("")
    keep = []
    depri = []
    for (mib, name), hits in anchors.items():
        low = name.lower()
        tag = next((v for k, v in DEPRIORITIZE.items() if k in low), None)
        (depri if tag else keep).append((mib, name, hits, tag))
    keep.sort(key=lambda x: -len(x[2]))
    n = 1
    for mib, name, hits, _ in keep:
        who = ", ".join("%s:%s" % (s, b) for s, b in hits)
        st = "+".join(sorted(set(s for s, _ in hits)))
        L.append("**1.%d · %s** — `%s` — hits: %s%s" % (n, name, mib, who, (" [%s]" % st if "+" in st else "")))
        L.append("- Q: Is `%s` a validated cluster for this product? What is the compound's class, "
                 "mechanism, and any target-specific activity actually reported?" % mib)
        L.append("- A: ____________________  (source: ____, confidence: ____)")
        L.append("")
        n += 1
    if depri:
        L.append("### De-prioritized anchors (confirm class only — primary/ubiquitous or project-excluded)")
        for mib, name, hits, tag in depri:
            who = ", ".join("%s:%s" % (s, b) for s, b in hits)
            L.append("- **%s** (`%s`) — %s — %s" % (name, mib, tag, who))
        L.append("")

    # Section 2: gene markers
    if markers:
        L.append("## 2 · Gene-marker hits (catch products the KCB anchor missed)")
        L.append("")
        n = 1
        for (gene, comp, why), hits in markers.items():
            who = ", ".join("%s:%s(ctg%s)" % (s, b, nn) for s, b, nn in hits)
            L.append("**2.%d · `%s` → %s** — %s — hits: %s" % (n, gene, comp, why, who))
            L.append("- Q: Confirm `%s` marks the %s pathway. What is the compound's activity "
                     "for a cited tested target? Closest characterized cluster?" % (gene, comp))
            L.append("- A: ____________________  (source: ____, confidence: ____)")
            L.append("")
            n += 1

    # Section 3: cryptic by class
    L.append("## 3 · Cryptic / unresolved — closest characterized cluster (by product class)")
    L.append("")
    n = 1
    for cls, hits in sorted(cryptic.items(), key=lambda x: -len(x[1])):
        if not cls:
            cls = "(no product class)"
        who = ", ".join("%s:%s" % (s, b) for s, b in hits[:10])
        more = "" if len(hits) <= 10 else " (+%d more)" % (len(hits) - 10)
        L.append("**3.%d · %s** — %d region(s): %s%s" % (n, cls, len(hits), who, more))
        L.append("- Q: For a *Streptomyces* %s cluster with no KCB hit, what are the most likely "
                 "characterized families to dereplicate against, and any with antifungal/antibacterial activity?" % cls)
        L.append("- A: ____________________  (source: ____, confidence: ____)")
        L.append("")
        n += 1

    L.append("## Return")
    L.append("Return with `A:` blanks filled + sources. Flag conflicts/absences. Returned literature remains owner-reviewed and does not promote a lead or establish BGC activity.")
    return "\n".join(L)


def _bucket(name):
    """Coarse antibacterial / antifungal / other split from anchor keywords."""
    low = name.lower()
    af = ["polyene", "nystatin", "amphotericin", "candicidin", "fengycin", "syringomycin",
          "nikkomycin", "rustmicin", "galbonolide", "cycloheximide", "pimaricin", "echinocandin",
          "pneumocandin", "natamycin", "filipin"]
    ab = ["phenazine", "thiopeptide", "lasso", "glycopeptide", "lipopeptide", "daptomycin",
          "friulimicin", "a54145", "anthracimycin", "difficidin", "aborycin", "lankacidin",
          "albomycin", "bombyxamycin", "streptophenazine", "cinnapeptin", "naphthyridinomycin"]
    if any(k in low for k in af):
        return "antifungal"
    if any(k in low for k in ab):
        return "antibacterial"
    return "other"


def render_directed(strains, anchors, cryptic, markers):
    """A more directed card: batched by intent, each question forces a primary-literature,
    target-resolved answer rather than a MIBiG-entry summary."""
    L = []
    L.append("# Directed Literature Punch Card — %s" % " + ".join(strains))
    L.append("")
    L.append("**To the web session:** answer in the batches below. For every numbered lead, **pull the "
             "PRIMARY reference (the original article), not just the MIBiG entry**, and report ONLY:")
    L.append("")
    L.append("- **(a)** each target actually tested  ·  **(b)** exact reported result and assay context  ·  "
             "**(c)** molecular target if source-supported  ·  **(d)** source scope and limitations")
    L.append("- If a target was **not tested** in the primary article, write `not tested` — do not infer "
             "from class. Cite the **primary DOI/PMID**. One line per lead.")
    L.append("")
    # bucket the named anchors
    buckets = {"antibacterial": [], "antifungal": [], "other": []}
    depri = []
    for (mib, name), hits in anchors.items():
        low = name.lower()
        if any(k in low for k in DEPRIORITIZE):
            depri.append((mib, name, hits))
        else:
            buckets[_bucket(name)].append((mib, name, hits))
    batch_titles = {"antibacterial": "Batch A — antibacterial-class literature questions",
                    "antifungal": "Batch B — antifungal-class literature questions",
                    "other": "Batch C — broad / unresolved literature questions"}
    n = 1
    for key in ["antibacterial", "antifungal", "other"]:
        rows = buckets[key]
        if not rows:
            continue
        L.append("## " + batch_titles[key])
        L.append("")
        for mib, name, hits in rows:
            who = ", ".join("%s:%s" % (s, b) for s, b in hits)
            L.append("**%d. %s** (`%s`) — %s" % (n, name, mib, who))
            L.append("- a:___ b:___ c:___ d:___  (primary source: ____)")
            L.append("")
            n += 1
    if markers:
        L.append("## Batch D — gene-marker identities (confirm the gene names the pathway)")
        L.append("")
        for (gene, comp, why), hits in markers.items():
            who = ", ".join("%s:%s" % (s, b) for s, b, _ in hits)
            L.append("**%d. `%s` → %s** — %s" % (n, gene, comp, who))
            L.append("- Confirm `%s` marks %s (y/n); closest characterized cluster; activity (a–e above): ____" % (gene, comp))
            L.append("")
            n += 1
    if depri:
        L.append("## Batch E — deprioritized (one-line class confirmation only, no MIC needed)")
        L.append("")
        for mib, name, hits in depri:
            L.append("- **%s** (`%s`): confirm it is primary/ubiquitous or non-antimicrobial (y/n) + class: ____" % (name, mib))
        L.append("")
    L.append("## Return")
    L.append("Return batches in order. `not tested` is a typed missingness state; no returned literature automatically changes a ranking, evidence state, or release status.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", nargs="+", required=True)
    ap.add_argument("--gbk-dirs", nargs="*", default=None)
    ap.add_argument("--out", default="combined_punchcard.md")
    ap.add_argument("--directed", action="store_true",
                    help="emit the directed, intent-batched, primary-literature card")
    a = ap.parse_args()
    strains, anchors, cryptic, markers = collect(a.packages, a.gbk_dirs)
    md = render_directed(strains, anchors, cryptic, markers) if a.directed else \
        render(strains, anchors, cryptic, markers)
    atomic_write_text(a.out, md)
    emit("wrote", a.out)
    emit("strains:", len(strains), "| named anchors:", len(anchors),
          "| gene markers:", len(markers), "| cryptic classes:", len(cryptic),
          "| mode:", "directed" if a.directed else "standard")


if __name__ == "__main__":
    main()
