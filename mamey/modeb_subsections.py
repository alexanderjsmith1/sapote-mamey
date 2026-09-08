"""modeb_subsections.py — gate-safe #### subsections for the §1–§48 Mode B card (.344).

Each function renders a `#### <title>` block (NO `§N` marker, so the modeb_structure_gate — which
keys on §N section headings — is unaffected; same mechanism as the §4 interpretive stubs). They are
sourced entirely from the sealed package + the in-bundle literature KB, and they carry the claim
ceiling inline. Reader-layer; non-scoring.

Subsections (the Developer or User directive 2026-07-31):
  - catalytic_domain_census   §4 — catalytic/biosynthetic domains present across the BGC (HMM)
  - blastp_channel_evidence   §4 — per-channel BLASTp (nr/cluster_nr/swissprot/ebi): identity + positives
  - gene_clusterblast         §4 — gene-based ClusterBlast (per-gene MIBiG references)
  - good_guess                §2 — the Good-Guess interpretive prior, folded into the card
  - genus_literature          §5 — genus chemistry/ecology from mamey/data/literature/<Genus>.md

CLAIM CEILING (inline in every block): comparators are SIMILARITY, not identity; BLASTp identity and
positives are shown separately and never conflated; domains/HMMs are antiSMASH annotations (facts)
whose PRODUCT is not thereby known; genus literature is class-level context, not a per-strain claim.
"""
from __future__ import annotations
import csv
import glob
import json
import os

from .modeb_domain_phylogeny import domain_phylogeny  # P360-002 (§41 interim)
from .source_scans import cctt_trigger_corroborated  # AUDIT_374: honor the CCTT class-compat
                                                       # guard here too — see _corroborated_cctt_raw()
from collections import Counter, defaultdict
from pathlib import Path

# antiSMASH/Pfam domain_name tokens that indicate CATALYTIC / biosynthetic machinery (not exhaustive;
# used only to flag the catalytic subset in the census — everything is still listed).
_CATALYTIC = {
    "ketoacyl-synt": "PKS ketosynthase (KS)", "PKS_KS": "PKS ketosynthase (KS)",
    "Acyl_transf_1": "PKS acyltransferase (AT)", "PKS_AT": "PKS acyltransferase (AT)",
    "PKS_KR": "PKS ketoreductase (KR)", "PKS_DH": "PKS dehydratase (DH)", "PKS_ER": "PKS enoylreductase (ER)",
    "PKS_PP": "PKS/PP carrier", "PP-binding": "carrier protein (ACP/PCP)", "PCP": "peptidyl carrier (PCP)",
    "AMP-binding": "NRPS adenylation (A)", "Condensation": "NRPS condensation (C)",
    "Heterocyclization": "NRPS heterocyclization (Cy)", "Thioesterase": "thioesterase (TE)",
    "Epimerization": "NRPS epimerization (E)", "p450": "cytochrome P450 (oxidation)",
    "Trp_halogenase": "halogenase", "Methyltransf": "methyltransferase", "Glycos_transf": "glycosyltransferase",
    "Glyco_transf": "glycosyltransferase", "Aminotran": "aminotransferase", "LANC_like": "lanthipeptide cyclase",
    "DUF4135": "lanthipeptide dehydratase (class II)", "YcaO": "YcaO cyclodehydratase (azol(in)e)",
    "PF00109": "PKS ketosynthase (KS)", "Ketoacyl-synt": "PKS ketosynthase (KS)",
}


def _find(pkg: Path, suffix: str):
    hits = sorted(glob.glob(str(Path(pkg) / f"*{suffix}")))
    return hits[0] if hits else None


def _rows_for_bgc(path, bgc_id, key="bgc_id"):
    if not path or not os.path.exists(path):
        return []
    try:
        return [r for r in csv.DictReader(open(path, encoding="utf-8")) if (r.get(key) or "").strip() == bgc_id]
    except (OSError, csv.Error):
        return []


def _clean(s):
    return (s or "").replace("|", "·").strip()


def _corroborated_cctt_raw(row: dict) -> list:
    """Raw CCTT_triggers tokens from a triage-board row, excluding any class-defining trigger the
    engine's own guard (`cctt_trigger_corroborated`) flags as fired on a class-incompatible locus
    (e.g. T43-PHO_phosphonate on an ectoine/saccharide-labeled BGC). scoring.py already excludes an
    uncorroborated trigger from AB/AF/tier credit (see `_uncorr` in triage_bgcs()/render_rationale());
    this file's literature/keyword subsections (family_literature, biosynthetic_features,
    literature_citations) read the same CCTT_triggers cell independently and, before this fix, treated
    every listed trigger as class-corroborated — surfacing the wrong family's literature/PubMed
    keywords/citations on a Mode-B card for a BGC whose own product classes don't support that trigger.
    Evidence-preserving upstream (the cell itself is untouched); this only filters what these reader-
    layer subsections build FROM the cell."""
    import re as _re
    raw = [t.strip() for t in _re.split(r"[;,]", row.get("CCTT_triggers", "") or "")
           if t.strip() and t.strip() != "—"]
    products = [p.strip() for p in _re.split(r"[;,]", row.get("Products", "") or "") if p.strip()]
    return [t for t in raw if cctt_trigger_corroborated(t, products)]


def catalytic_domain_census(pkg, bgc_id) -> str:
    rows = _rows_for_bgc(_find(pkg, "_3_antismash_hmm.csv"), bgc_id)
    if not rows:
        return ""
    dom = Counter(_clean(r.get("domain_name")) for r in rows if r.get("domain_name"))
    diag = {_clean(r.get("domain_name")) for r in rows
            if str(r.get("tier1_diagnostic", "")).strip().lower() in ("1", "true", "yes")}
    catalytic = [(d, n) for d, n in dom.most_common() if any(k.lower() in d.lower() for k in _CATALYTIC)]
    L = ["#### Catalytic domain census (across the BGC)",
         "<!-- gate-safe subsection; antiSMASH/Pfam HMM domains — facts. Domains show CAPACITY/mechanism, "
         "not the product. -->",
         f"{len(dom)} distinct HMM/Pfam domains over {len(rows)} hits; "
         f"{len(catalytic)} catalytic/biosynthetic families. Diagnostic (tier-1): "
         f"{', '.join(sorted(diag)) if diag else '—'}.", "",
         "| catalytic domain | n | role |", "|---|--:|---|"]
    for d, n in catalytic[:16]:
        role = next((v for k, v in _CATALYTIC.items() if k.lower() in d.lower()), "biosynthetic")
        L.append(f"| `{d}` | {n} | {role}{' · **diagnostic**' if d in diag else ''} |")
    if not catalytic:
        L.append("| — | — | no canonical PKS/NRPS/RiPP catalytic domains detected (read from full census) |")
    return "\n".join(L)


_CHANNEL_STORES = [(("blastp_nr",), "nr"),
                   (("blastp_clustered_nr", "blastp_cluster_nr"), "clustered-nr"),
                   (("blastp_swissprot",), "Swiss-Prot"), (("blastp_ebi",), "EBI")]


def blastp_channel_evidence(pkg, bgc_id) -> str:
    pkg = Path(pkg)
    have = []
    for stores, label in _CHANNEL_STORES:
        f = next((pkg / store / f"{bgc_id}_top10.csv" for store in stores
                  if (pkg / store / f"{bgc_id}_top10.csv").exists()), None)
        if f is not None:
            try:
                rows = list(csv.DictReader(f.open(encoding="utf-8")))
            except (OSError, csv.Error):
                continue
            if rows:
                have.append((label, rows))
    if not have:
        return ""
    L = ["#### BLASTp evidence — by channel (identity & positives)",
         "<!-- gate-safe subsection; channels UNMIXED. %identity ≠ %positives(similarity); both shown, "
         "never conflated. BLASTp is similarity, not a product-identity claim. -->",
         "| channel | genes | best %id | best %pos | nearest subject (rank-1 exemplar) |",
         "|---|--:|--:|--:|---|"]
    for label, rows in have:
        r1 = [r for r in rows if str(r.get("hit_rank", "")).strip() == "1"]
        genes = len({r.get("gene") for r in r1}) or len({r.get("gene") for r in rows})
        def _f(r, k):
            try:
                return float(r.get(k) or 0)
            except ValueError:
                return 0.0
        best = max(r1 or rows, key=lambda r: _f(r, "pct_identity"))
        L.append(f"| {label} | {genes} | {_f(best,'pct_identity'):.0f}% | {_f(best,'pct_positives'):.0f}% | "
                 f"{_clean(best.get('subject_def'))[:44]} [{_clean(best.get('subject_organism'))[:20]}] |")
    L.append("")
    L.append("*Per-gene top-10 hits with both metrics are in the package channel stores "
             "(`blastp_nr/`, `blastp_clustered_nr/`, `blastp_swissprot/`). Identity = exact matches; "
             "positives = conservative-substitution similarity.*")
    return "\n".join(L)


def gene_clusterblast(pkg, bgc_id) -> str:
    rows = _rows_for_bgc(_find(pkg, "_4A2_ClusterBlast_per_gene.csv"), bgc_id)
    if not rows:
        return ""
    by_ref = defaultdict(list)
    for r in rows:
        ref = _clean(r.get("reference"))
        if ref:
            by_ref[ref].append(r)
    def _pid(r):
        try:
            return float(r.get("pct_identity") or 0)
        except ValueError:
            return 0.0
    ranked = sorted(by_ref.items(), key=lambda kv: (-len(kv[1]), -max(_pid(x) for x in kv[1])))
    L = ["#### Gene-based ClusterBlast (per-gene MIBiG reference channel)",
         "<!-- gate-safe subsection; per-GENE reference hits (distinct from region-level KCB). "
         "Similarity anchors for the class, not identity. -->",
         f"{len(rows)} per-gene hits across {len(by_ref)} reference cluster(s). Top references by "
         "genes shared:", "",
         "| reference (MIBiG/cluster) | genes | median %id | source |", "|---|--:|--:|---|"]
    for ref, rs in ranked[:6]:
        pids = sorted(_pid(x) for x in rs)
        med = pids[len(pids) // 2] if pids else 0
        L.append(f"| {ref[:40]} | {len({x.get('query_gene') for x in rs})} | {med:.0f}% | "
                 f"{_clean(rs[0].get('reference_source'))[:16]} |")
    return "\n".join(L)


def good_guess(pkg, bgc_id, guesses_csv: str | None = None) -> str:
    """Fold the Good-Guess interpretive prior for this BGC into the card. Reads a GOOD_GUESSES.csv
    (in the package or a sibling deliverable dir) if present."""
    path = guesses_csv
    if not path:
        for cand in (_find(pkg, "GOOD_GUESSES.csv"),
                     *glob.glob(str(Path(pkg).parent / "**" / "GOOD_GUESSES.csv"), recursive=True)):
            if cand and os.path.exists(cand):
                path = cand
                break
    rows = _rows_for_bgc(path, bgc_id) if path else []
    # v9.7.371 fix: GOOD_GUESSES.csv is a COHORT-WIDE, multi-strain aggregate (good_guesses.py
    # build_guesses() scans every package under an --out root into one shared CSV with an
    # explicit strain column) -- BGC IDs are numbered per-strain, so two different strains
    # routinely share the same bgc_id (e.g. both AS-XXX and AS-XXX can have a BGC003). The
    # parent-directory glob fallback above is exactly the path that discovers this cohort-level
    # file, but the lookup here never checked the strain column -- rendering AS-XXX's card could
    # silently display AS-XXX's Good-Guess flavour/read/confidence/evidence text as its own,
    # attributing one organism's interpretive content to another (the exact cross-strain
    # misattribution class this project's claim-safety conventions exist to prevent).
    strain = _strain_id_of(pkg)
    if strain:
        rows = [r for r in rows if not (r.get("strain") or "").strip()
                or (r.get("strain") or "").strip().upper() == strain.strip().upper()]
    if not rows:
        return ""
    g = rows[0]
    L = ["#### Good Guess — single best claim-safe read *(interpretive prior)*",
         "<!-- gate-safe subsection; the engine's Good-Guess synthesis, folded into the card as a prior "
         "for the author to adjudicate — not a conclusion. -->",
         f"**Flavour:** {_clean(g.get('flavours')) or '—'}  ·  **confidence:** {_clean(g.get('confidence')) or '—'}",
         f"**Read:** {_clean(g.get('read')) or '—'}",
         f"**Evidence basis:** {_clean(g.get('evidence_basis')) or '—'}",
         f"**Resolving experiment:** {_clean(g.get('resolving_experiment')) or '—'}"]
    return "\n".join(L)


# manifest taxonomy is often a generic placeholder; the resolved genus lives in the authoritative
# strain table, mirrored into the bundle as data/strain_genus.csv (portable). Prefer the manifest
# only when it names a real genus.
_GENERIC_TAX = {"actinomycete", "actinobacterium", "unclassified", "bacterium", "streptomycetales",
                "", "sp.", "actinomycetota"}


def _strain_id_of(pkg) -> str:
    for f in Path(pkg).glob("*_4_triage_board.csv"):
        return f.name.split("_4_triage_board.csv")[0]
    man = Path(pkg) / "manifest.json"
    if man.exists():
        try:
            return json.loads(man.read_text(encoding="utf-8")).get("strain_id", "") or ""
        except (OSError, json.JSONDecodeError):
            pass
    return ""


def _genus_from_crosswalk(strain: str) -> str:
    if not strain:
        return ""
    xw = Path(__file__).parent / "data" / "strain_genus.csv"
    if not xw.exists():
        return ""
    try:
        for r in csv.DictReader(xw.open(encoding="utf-8")):
            if (r.get("strain") or "").strip() == strain:
                return (r.get("genus") or "").strip()
    except (OSError, csv.Error):
        return ""
    return ""


def _genus_of(pkg) -> str:
    man = Path(pkg) / "manifest.json"
    if man.exists():
        try:
            tax = json.loads(man.read_text(encoding="utf-8")).get("taxonomy", "") or ""
            tok = tax.strip().split()
            if tok and tok[0].lower() not in _GENERIC_TAX:
                return tok[0]
        except (OSError, json.JSONDecodeError):
            pass
    # fall back to the authoritative strain->genus crosswalk
    return _genus_from_crosswalk(_strain_id_of(pkg))


def genus_literature(pkg, lit_dir: str | None = None) -> str:
    genus = _genus_of(pkg)
    if not genus:
        return ""
    # in-bundle literature KB (portable): mamey/data/literature/<Genus>.md
    search = [lit_dir] if lit_dir else []
    search += [str(Path(__file__).parent / "data" / "literature")]
    md = None
    for d in search:
        if d and os.path.exists(os.path.join(d, f"{genus}.md")):
            md = os.path.join(d, f"{genus}.md")
            break
    if not md:
        return ""
    try:
        body = open(md, encoding="utf-8").read()
    except OSError:
        return ""
    # pull the compound bullets (lines starting with '- **') as the compact context
    bullets = [ln for ln in body.splitlines() if ln.strip().startswith("- **")][:8]
    L = [f"#### Genus literature context — *{genus}*",
         "<!-- gate-safe subsection; class-level genus chemistry/ecology from the in-bundle literature "
         "KB. Similarity/capacity anchor for authoring, NOT a per-strain identity or product claim. -->",
         f"Characterised chemistry associated with *{genus}* / close relatives (capacity anchors):"]
    L += bullets if bullets else ["- (see the genus knowledge file for details)"]
    L.append(f"\n*Source: `mamey/data/literature/{genus}.md`. Use as a class anchor; if a core is "
             "reference-dark, read domain grammar, not this list.*")
    return "\n".join(L)


# family-level KB: map a BGC's own warheads / product-class tokens to family knowledge files in
# mamey/data/literature/_families/<family>.md (v9.7.345). This is the consumption side of the
# keyword-mining -> PubMed -> KB loop: a card cites the EXACT family literature, not just the genus.
_FAMILY_ALIASES = {
    "thioamide": "thioamide", "thioamitides": "thioamide", "thioamide-nrp": "thioamide",
    "polyene": "polyene", "polyene-macrolide": "polyene",
    "hsaf_tetramate": "hsaf", "hsaf": "hsaf", "pks-tetramate": "hsaf",
    "spirotetronate_tetronate": "spirotetronate", "tetronate_spirotetronate": "spirotetronate",
    "enediyne": "enediyne", "phosphonate": "phosphonate", "glycopeptide": "glycopeptide",
    "lanthipeptide": "lanthipeptide", "lassopeptide": "lassopeptide",
}


def family_literature(pkg, bgc_id, lit_dir: str | None = None) -> str:
    """Family-level KB for THIS BGC, keyed on its CCTT warheads + product classes. Renders only the
    families whose `_families/<family>.md` file exists in the bundle. Class-level capacity anchors."""
    import re as _re
    tri = _rows_for_bgc(_find(pkg, "_4_triage_board.csv"), bgc_id, key="BGC_ID")
    row = tri[0] if tri else {}
    toks = set()
    for t in _corroborated_cctt_raw(row):
        toks.add(_re.sub(r"^T\d+-[A-Z]+_", "", t).lower())
    for p in _re.split(r"[;,]", row.get("Products", "") or ""):
        toks.add(p.strip().lower())
    fam_files = {}
    base = Path(lit_dir) if lit_dir else Path(__file__).parent / "data" / "literature" / "_families"
    for tok in toks:
        fam = _FAMILY_ALIASES.get(tok)
        if fam and fam not in fam_files:
            fp = base / f"{fam}.md"
            if fp.exists():
                fam_files[fam] = fp
    if not fam_files:
        return ""
    L = ["#### Family literature context — this BGC's warhead classes",
         "<!-- gate-safe subsection; family-level chemistry keyed on THIS BGC's CCTT warheads / class "
         "tokens, from the in-bundle KB. Capacity/similarity anchor, NOT a product claim. -->"]
    for fam, fp in fam_files.items():
        try:
            body = open(fp, encoding="utf-8").read()
        except OSError:
            continue
        bullets = [ln for ln in body.splitlines() if ln.strip().startswith("- **")][:5]
        L.append(f"**{fam}** — capacity anchors:")
        L += bullets if bullets else [f"- (see `_families/{fam}.md`)"]
        L.append(f"*Source: `mamey/data/literature/_families/{fam}.md`.*")
    return "\n".join(L)


import re as _re

# housekeeping product classes — shown but flagged, never offered as a lead search keyword
_HOUSEKEEPING_CLASSES = {"terpene", "ectoine", "betalactone", "naggn", "hserlactone", "other",
                         "saccharide", "napaa", "ripp-like", "fatty_acid", "arylpolyene",
                         "carotenoid", "hopene", "melanin", "terpene-precursor"}


def biosynthetic_features(pkg, bgc_id) -> str:
    """Concrete, searchable biosynthetic features for this BGC — product classes, rare-class CCTT
    warheads, tier-1 diagnostic HMM domains, and per-gene MIBiG convergence families — with a
    ready-to-search PubMed keyword line. This is the per-card source from which cohort-wide keyword
    mining is derived. Class-level; similarity not identity; a warhead/domain is CAPACITY, not a
    made product."""
    tri = _rows_for_bgc(_find(pkg, "_4_triage_board.csv"), bgc_id, key="BGC_ID")
    row = tri[0] if tri else {}
    products = [p.strip() for p in _re.split(r"[;,]", row.get("Products", "") or "") if p.strip()]
    cctt = [_re.sub(r"^T\d+-[A-Z]+_", "", t) for t in _corroborated_cctt_raw(row)]
    hmm = _rows_for_bgc(_find(pkg, "_3_antismash_hmm.csv"), bgc_id)
    diag = sorted({_clean(r.get("domain_name")) for r in hmm
                   if str(r.get("tier1_diagnostic", "")).strip().lower() in ("1", "true", "yes")})
    conv = _rows_for_bgc(_find(pkg, "_3_mibig_convergence.csv"), bgc_id)
    fams = []
    seen = set()
    for r in conv:
        tier = (r.get("convergence_tier", "") or "")
        conc = (r.get("class_concordance", "") or "").upper()
        comp = (r.get("mibig_compound", "") or "").strip()
        if comp and ("H" in tier or "CONCORDANT" in conc):
            base = _re.split(r"[/,]", comp)[0].strip()
            if base and len(base) > 2 and base.lower() not in seen:
                seen.add(base.lower()); fams.append(base)
    if not (products or cctt or diag or fams):
        return ""
    lead_products = [p for p in products if p.lower() not in _HOUSEKEEPING_CLASSES]
    # keyword line: warheads + families + non-housekeeping classes, de-duplicated
    kws = []
    for k in cctt + fams[:5] + lead_products[:4]:
        if k and k.lower() not in {x.lower() for x in kws}:
            kws.append(k)
    L = ["#### Concrete biosynthetic features & search keywords",
         "<!-- gate-safe subsection; observed features (antiSMASH class / CCTT warhead / diagnostic "
         "HMM / per-gene MIBiG convergence). Features = CAPACITY, not a product. Convergence families "
         "are SIMILARITY anchors for the class. -->",
         f"- **Product class(es):** {', '.join(products) or '—'}"
         + (f"  ·  *(housekeeping-flagged: {', '.join(p for p in products if p.lower() in _HOUSEKEEPING_CLASSES)})*"
            if any(p.lower() in _HOUSEKEEPING_CLASSES for p in products) else ""),
         f"- **Rare-class warheads (CCTT):** {', '.join(cctt) or 'none'}",
         f"- **Tier-1 diagnostic HMM domains:** {', '.join(diag[:10]) or 'none'}",
         f"- **Per-gene MIBiG convergence families (similarity anchors):** {', '.join(fams[:8]) or 'reference-dark / none above floor'}",
         "",
         f"**PubMed keywords for this BGC:** {'; '.join(f'`{k}`' for k in kws[:10]) or '`(reference-dark — read domain grammar)`'}"]
    return "\n".join(L)


def _fmt_authors(authors: str) -> str:
    """First three authors + 'et al.' — a compact but real author list for the citation."""
    if not authors:
        return "[authors n/a]"
    names = [a.strip() for a in authors.split(",") if a.strip()]
    if len(names) <= 3:
        return ", ".join(names)
    return ", ".join(names[:3]) + ", et al."


def _citation(r: dict) -> str:
    title = _re.sub(r"([a-z]{2})([A-Z][a-z])", r"\1 \2", (r.get("title", "") or "").strip().rstrip("."))
    bits = [f"**{title}.**", f"{_fmt_authors(r.get('authors', ''))}.", f"{r.get('year', 'n.d.')}."]
    bits.append(f"PMID {r['pmid']}" + (f"; doi:{r['doi']}" if r.get("doi") else "") + ".")
    return " ".join(bits)


def _description(r: dict) -> str:
    ab = (r.get("abstract", "") or "").strip()
    if not ab:
        return "*(no abstract in export; title-level context — full record by PMID in `_corpus/`).*"
    ab = _re.sub(r"^(Background|Introduction|Abstract|Objective[s]?)\s*:?\s*", "", ab)
    sents = _re.split(r"(?<=[.!?])\s+", ab)
    snip = " ".join(sents[:2])
    return (snip[:480].rsplit(" ", 1)[0] + " …") if len(snip) > 480 else snip


def literature_citations(pkg, bgc_id, max_cites: int = 10) -> str:
    """Up to `max_cites` (≤10) full PubMed citations matched to THIS BGC's warhead classes + genus,
    drawn from the in-bundle corpus (`data/literature/_corpus/`). Each = full citation + a short
    description. CLAIM CEILING: class/genus-KEYWORD-matched literature CONTEXT — NOT evidence this
    BGC makes these compounds; similarity/keyword match only; judgment deferred. Degrades to empty
    if the corpus is purged (public tier)."""
    try:
        from . import literature_lookup as _ll
    except Exception:  # noqa: BLE001
        return ""
    corpus = _ll.load_corpus()
    if not corpus:
        return ""
    tri = _rows_for_bgc(_find(pkg, "_4_triage_board.csv"), bgc_id, key="BGC_ID")
    row = tri[0] if tri else {}
    toks = set()
    for t in _corroborated_cctt_raw(row):
        toks.add(_re.sub(r"^T\d+-[A-Z]+_", "", t).lower())
    for p in _re.split(r"[;,]", row.get("Products", "") or ""):
        p = p.strip().lower()
        if p and p not in _HOUSEKEEPING_CLASSES:
            toks.add(p)
    toks |= {_FAMILY_ALIASES[t] for t in list(toks) if t in _FAMILY_ALIASES}
    # broad backbone classes match thousands of papers and drown out the specific warhead — drop them
    # so a thioamide/HSAF/lasso BGC gets thioamide/HSAF/lasso citations, not generic NRPS/PKS ones.
    _BROAD = {"nrps", "nrps-like", "pks", "pks-like", "t1pks", "t2pks", "t3pks", "transat-pks",
              "hr-t2pks", "ripp", "ripp-like", "hybrid", "other", "nrp-metallophore", "ni-siderophore"}
    terms = {t for t in toks if len(t) >= 4 and t not in _BROAD}
    genus = _genus_of(pkg).lower()
    if not terms and not genus:
        return ""
    scored = []
    for r in corpus.values():
        blob = (r.get("title", "") + " " + r.get("abstract", "") + " " + " ".join(r.get("queries", []))).lower()
        matched = [t for t in terms if t in blob]
        if not matched:
            continue
        gbonus = 1 if (genus and genus in blob) else 0
        yr = int(r["year"]) if str(r.get("year", "")).isdigit() else 0
        scored.append((len(matched) + gbonus, yr, r, matched))
    if not scored:
        return ""
    scored.sort(key=lambda x: (-x[0], -x[1]))
    L = [f"#### Literature citations — top {min(max_cites, len(scored))} refs matched to this BGC's classes",
         "<!-- gate-safe subsection; class/genus-keyword-matched PubMed CONTEXT from the in-bundle "
         "corpus. NOT evidence this BGC makes these compounds — similarity/keyword match only; "
         "full abstracts by PMID in data/literature/_corpus/. Judgment deferred. -->"]
    for _score, _yr, r, matched in scored[:max(1, min(max_cites, 10))]:
        L.append(f"- {_citation(r)} *(matched: {', '.join(sorted(set(matched)))})* — {_description(r)}")
    return "\n".join(L)


def render_for_section(pkg, bgc_id, num: int, guesses_csv: str | None = None) -> str:
    """Return the concatenated gate-safe subsections that belong in section `num` (empty if none)."""
    blocks = []
    if num == 2:
        blocks = [good_guess(pkg, bgc_id, guesses_csv)]
    elif num == 4:
        blocks = [biosynthetic_features(pkg, bgc_id), catalytic_domain_census(pkg, bgc_id),
                  blastp_channel_evidence(pkg, bgc_id), gene_clusterblast(pkg, bgc_id),
                  domain_phylogeny(pkg, bgc_id)]
    elif num == 5:
        blocks = [family_literature(pkg, bgc_id), genus_literature(pkg),
                  literature_citations(pkg, bgc_id)]
    out = [b for b in blocks if b]
    return ("\n\n" + "\n\n".join(out)) if out else ""
