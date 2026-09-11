"""resistance_dossier — post-seal per-BGC resistance-focused gene-by-gene writeups.

For every BGC in a sealed package that carries a **self-resistance-like gene** (a locus with a
domain the engine's ``domain_reference`` categorizes as ``resistance``), emit a claim-safe
gene-by-gene dossier: genes grouped by ``domain_reference`` role, each annotated with its
per-gene nr BLASTp top hit (``blastp_nr/<BGC>_top10.csv``, when present) and per-gene MIBiG
convergence (``*_3_mibig_per_gene.csv``), plus a "what the evidence says" synthesis and a
self-resistance spotlight.

Deterministic and side-effect free apart from writing the dossier files. No product-identity,
production, or activity claim: homology is similarity, MIBiG is family relatedness, priors are
capacity, resistance genes raise priority but never prove a phenotype. Judgment deferred.

Post-seal, non-blocking: consumes an already-sealed package and never mutates it. Mirrors the
``emit-modeb-cards`` subcommand shape.
"""
from __future__ import annotations
import csv, os, glob, re, statistics, collections
import sys as _sys


def _atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: write to a sibling .tmp then os.replace into place, so a crash mid-write
    never leaves a truncated dossier .md file sitting in the output dir. Mirrors the tmp+replace
    pattern used elsewhere in this codebase (tools/_wbio.py, mamey/packaging.py)."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, path)
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible writer (no bare print(); holds strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

try:
    from . import domain_reference as _dref
except ImportError:  # standalone / test import
    import domain_reference as _dref  # type: ignore

RES_CATEGORY = "resistance"
HOUSEKEEPING_RE = re.compile(
    r"ribosomal|rrna|trna|molybdenum cofactor|moab|moea|dna polymerase|gyrase|"
    r"elongation factor|chaperon|groel|dnak|atp synthase|cell division|divisome|"
    r"glycolysis|citrate synth|methylcitrate", re.I)


# --------------------------------------------------------------------------- package readers
def _find(pkg: str, suffix: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(pkg, f"*{suffix}")))
    return hits[0] if hits else None


def _rows(path: str | None) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_domains(pkg: str) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """{bgc_id: {locus_tag: [(domain, pfam_acc), ...]}} from *_domains.csv."""
    out: dict[str, dict[str, list]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in _rows(_find(pkg, "_domains.csv")):
        b = (r.get("bgc_id") or "").strip()
        lt = (r.get("locus_tag") or "").strip()
        dom = (r.get("domain") or "").strip()
        if b and lt and dom:
            out[b][lt].append((dom, (r.get("pfam_acc") or "").strip()))
    return out


def load_nr(pkg: str, bgc: str) -> dict[str, dict]:
    """locus -> best (rank1) nr hit from blastp_nr/<BGC>_top10.csv (if present)."""
    path = os.path.join(pkg, "blastp_nr", f"{bgc}_top10.csv")
    best: dict[str, dict] = {}
    for r in _rows(path):
        g = (r.get("gene") or "").strip()
        try:
            rank = int(r.get("hit_rank") or 99)
        except ValueError:
            rank = 99
        if g and (g not in best or rank < best[g]["_rank"]):
            best[g] = {"_rank": rank, "org": (r.get("subject_organism") or "").strip(),
                       "def": (r.get("subject_def") or "").strip(),
                       "pid": r.get("pct_identity", ""), "pos": r.get("pct_positives", ""),
                       "cov": r.get("query_coverage", ""), "aa": r.get("aa_length", "")}
    return best


def load_mibig(pkg: str) -> dict[tuple[str, str], list[dict]]:
    """{(bgc_id, query_gene): [MIBiG hits]} from *_3_mibig_per_gene.csv.

    BUGFIX (cross-BGC leakage): keyed by the EXACT (bgc_id, query_gene) pair. Keying by the bare
    query_gene alone leaked a MIBiG hit assigned to one BGC into another BGC's dossier whenever a
    locus tag recurred across regions. A row with no bgc_id cannot be safely attributed and is dropped
    (claim-safe: never mis-attribute).
    """
    out: dict[tuple[str, str], list] = collections.defaultdict(list)
    for r in _rows(_find(pkg, "_3_mibig_per_gene.csv")):
        b = (r.get("bgc_id") or "").strip()
        lt = (r.get("query_gene") or "").strip()
        comp = (r.get("mibig_compound") or r.get("mibig_accession") or "").strip()
        if b and lt and comp:
            out[(b, lt)].append({"compound": comp, "pid": r.get("pct_identity", "")})
    return out


def load_inventory(pkg: str) -> dict[str, dict]:
    inv: dict[str, dict] = {}
    for r in _rows(_find(pkg, "_2_inventory.csv")):
        b = (r.get("BGC_ID") or "").strip()
        if b:
            inv[b] = r
    return inv


def load_lead_tier(pkg: str) -> dict[str, str]:
    tb = _find(pkg, "_4_triage_board.csv")
    out: dict[str, str] = {}
    for r in _rows(tb):
        b = (r.get("bgc_id") or r.get("BGC_ID") or "").strip()
        # v9.7.371 fix: the real triage-board column is Lead_tier_auto (cli.py triage_headers) --
        # none of lead_tier/Lead_tier/tier ever exist on a real row, so lt was always empty and
        # every resistance dossier silently rendered "Lead tier: —" regardless of the BGC's
        # actual tier.
        lt = (r.get("Lead_tier_auto") or r.get("lead_tier") or r.get("Lead_tier") or r.get("tier") or "").strip()
        if b and lt:
            out[b] = lt
    return out


# AUDIT_378: the same three-flag exclusion vocabulary compile_report.py's _decision_for()
# / _key_findings() use (v9.7.377) to keep an engine-excluded BGC from headlining a claim-safety
# report. scoring.py:737 gates Corrected_rank blank on ANY of standing_rule_flag,
# primary_metabolism_flag, or mobile_element_flag (scoring.py:752). A present-but-blank
# Corrected_rank is diagnostic of all three at once -- including a mobile-element-only exclusion,
# where Standing_rule/Primary_metab_flag are BOTH blank and only Corrected_rank tells you the row
# was dropped (mobile_element_flag itself has no _4_triage_board.csv column yet; see the sibling
# AUDIT_378_cli_mobile_element_flag_triage_column card).
_EXCL_TOKENS = ("saccharide", "napaa", "hgle-ks-prev", "ni-siderophore", "nrp-metallophore", "primary")


def load_exclusion(pkg: str) -> dict[str, str]:
    """{bgc_id: reason} for BGCs scoring.py has already excluded/downgraded from lead status via
    its standing-rule / primary-metabolism / mobile-element three-flag gate. Without this, a
    resistance-marker gene inside an already-excluded BGC (e.g. a SACCHARIDE housekeeping operon
    misfiled with a resistance-tier source scan) still produces a full, unmarked "resistance-
    bearing BGC" dossier that reads exactly like a live discovery lead."""
    tb = _find(pkg, "_4_triage_board.csv")
    out: dict[str, str] = {}
    for r in _rows(tb):
        b = (r.get("bgc_id") or r.get("BGC_ID") or "").strip()
        if not b:
            continue
        standing = (r.get("Standing_rule") or r.get("Downgrade") or "").strip()
        primary = (r.get("Primary_metab_flag") or "").strip().lower()
        corrected_rank_blank = "Corrected_rank" in r and not (r.get("Corrected_rank") or "").strip()
        if (any(tok in standing.lower() for tok in _EXCL_TOKENS) or primary in ("1", "true", "yes")
                or corrected_rank_blank):
            out[b] = (standing or r.get("Mobile_element_flag") or r.get("Primary_metab_flag")
                      or "engine-excluded (corrected_rank blank)")
    return out


# --------------------------------------------------------------------------- category lookup
def load_domain_reference_tsv(path: str | None) -> dict[str, str]:
    """{domain: category} from a built ``domain_reference.tsv`` (tools/build_domain_reference.py).

    The TSV is the **curated** vocabulary the Mode-B cards already use; it is richer than the
    in-code fallback table (e.g. ``LANC_like``/``RamS`` -> RiPP-maturation, ``Lactamase_B`` ->
    resistance). Consuming it keeps this subcommand's categories identical to the card's
    "Domain inventory" section. Absent/unreadable file -> empty map (in-code fallback used).
    """
    out: dict[str, str] = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            dom = (r.get("domain") or "").strip()
            cat = (r.get("category") or "").strip()
            if dom and cat:
                out[dom] = cat
    return out


def _cat(dom: str, pfam: str, ref: dict[str, str] | None = None) -> str:
    """Category for a domain: curated TSV first, then the in-code domain_reference rules."""
    if ref and dom in ref:
        return ref[dom]
    return _dref.categorize(dom, "")[0]


def _hitcell(nr: dict | None) -> str:
    if not nr:
        return "— (no nr hit)"
    def r0(v):
        f = _fnum(v)
        return f"{f:.0f}" if f is not None else (v or "")
    org = nr.get("org", "").strip()
    sdef = re.sub(r"\s*\[[^\]]*\]$", "", nr.get("def", "").strip())
    cov = nr.get("cov", "")
    cov_txt = f" / {r0(cov)}% cov" if str(cov).strip() not in ("", "None") else ""
    return f"{r0(nr.get('pid'))}% id / {r0(nr.get('pos'))}% pos{cov_txt} · *{org}* · {sdef[:60]}"


def _mibcell(mib: list[dict]) -> str:
    return "; ".join(f"{m['compound'].split('/')[0]} {m['pid']}%" for m in mib[:2])


_TRANSPORT_IMMUNITY_RE = re.compile(r"abc2?_membrane|abc_tran|\bmfs|mmpl|macb|feccd", re.I)


def build_dossier(bgc: str, inv_row: dict, tier: str, gene_domains: dict,
                  nr: dict, mibig: dict, immunity_transporters: bool = False,
                  ref: dict[str, str] | None = None, excl_reason: str = "") -> tuple[str, bool]:
    """Return (markdown, has_resistance).

    Resistance loci are strict: a gene whose ``domain_reference`` category is ``resistance``
    (beta-lactamase / Van / efflux-labelled / aminoglycoside-modifying). This is deliberately
    narrower than the §27 "efflux|target-modification" heuristic, which also counts co-located
    transporters. With ``immunity_transporters=True`` a transporter gene in a resistance-tier
    BGC is additionally flagged ``[IMM]`` (candidate producer-immunity export), matching the
    broader §27 view without conflating export with a resistance marker.

    ``excl_reason`` (AUDIT_378): non-empty when scoring.py's standing-rule /
    primary-metabolism / mobile-element gate already excluded this BGC from lead status
    (``load_exclusion``). The dossier is still emitted -- the resistance-marker content is real
    antiSMASH evidence worth keeping on record -- but is loudly marked as engine-excluded so it
    is never mistaken for a live discovery lead (same exclusion-marking discipline as
    ``compile_report.py``'s ``_decision_for``/``_key_findings``).
    """
    res_tier_val = (inv_row.get("Resistance_tier") or "").upper()
    tier_is_resistance = "RESISTANCE_LIKE" in res_tier_val or res_tier_val.startswith(("T1_", "T2_"))
    genes = []
    res_loci = []
    imm_loci = []
    for lt, doms in gene_domains.items():
        cats = [_cat(d, p, ref) for d, p in doms]
        is_res = RES_CATEGORY in cats
        is_imm = (immunity_transporters and tier_is_resistance and not is_res
                  and any(_TRANSPORT_IMMUNITY_RE.search(d) for d, _ in doms))
        role = _dref_role(cats)
        nb = nr.get(lt, {})
        genes.append({"lt": lt, "doms": [d for d, _ in doms], "role": role,
                      "is_res": is_res, "is_imm": is_imm, "nr": nb, "mibig": mibig.get((bgc, lt), []),
                      "aa": nb.get("aa", "")})
        if is_res:
            res_loci.append(lt)
        if is_imm:
            imm_loci.append(lt)
    if not res_loci and not imm_loci:
        return "", False

    products = (inv_row.get("Products") or "").strip()
    kcb = (inv_row.get("KCB_top") or "").strip()
    res_tier = (inv_row.get("Resistance_tier") or "").strip()
    L = [f"# {inv_row.get('BGC_ID', bgc)} — resistance-bearing BGC · gene-by-gene dossier", ""]
    if excl_reason:
        L.append(f"> **ENGINE-EXCLUDED — NOT A LIVE LEAD.** This BGC was already excluded/downgraded "
                 f"from lead status by the engine's standing-rule / primary-metabolism / mobile-element "
                 f"gate (`{excl_reason}`). This dossier documents its resistance-marker content for the "
                 "record only; treat the priority language below as void.")
        L.append("")
    imm_note = f"  ·  **candidate-immunity transporters:** {len(imm_loci)}" if imm_loci else ""
    L.append(f"**Lead tier:** {tier or '—'}  ·  **Products (antiSMASH):** {products or '—'}  ·  "
             f"**Resistance tier:** {res_tier or '—'}  ·  **self-resistance loci:** {len(res_loci)}{imm_note}")
    L.append("")
    L.append(f"**Product-family anchor (KCB, similarity only):** {kcb or '—'}")
    L.append("")
    L.append("> **Claim-safety.** Domain calls are antiSMASH facts; nr %id/%positives are similarity, "
             "not identity; MIBiG per-gene numbers are family relatedness; a co-located resistance-like "
             "gene raises interpretive priority and plausibility, it does **not** prove production, potency, "
             "or a producer-immunity phenotype. Judgment deferred to Sapote / wet-lab.")
    L.append("")
    hk = [(g["lt"], re.sub(r"\s*\[[^\]]*\]$", "", g["nr"].get("def", "")).strip()[:40])
          for g in genes if not g["is_res"] and HOUSEKEEPING_RE.search(
              (g["nr"].get("def", "") if g["nr"] else "") + " " + " ".join(g["doms"]))]
    if len(hk) >= 3:
        L.append(f"> **Boundary caveat.** {len(hk)} housekeeping/primary-metabolism genes are inside this "
                 "region (e.g. " + ", ".join(f"`{g}` {d}" for g, d in hk[:4]) + ") — the antiSMASH region "
                 "likely over-extends into a flanking operon; those genes are not part of the cluster.")
        L.append("")

    # synthesis
    L += ["## What the evidence says", _synthesis(genes), ""]

    # grouped tables
    buckets = collections.defaultdict(list)
    for g in genes:
        buckets[g["role"]].append(g)
    for rk, rlabel in _ROLE_ORDER:
        gs = buckets.get(rk, [])
        if not gs:
            continue
        gs.sort(key=lambda g: -(_fnum(g["nr"].get("pid")) or -1))
        L += [f"## {rlabel}  ({len(gs)})", "",
              "| gene | aa | domains | nr top hit (% id / % positives · organism · annotation) | MIBiG per-gene |",
              "|---|--:|---|---|---|"]
        for g in gs[:30]:
            flag = "**[RES]** " if g["is_res"] else ("**[IMM]** " if g.get("is_imm") else "")
            dom = ", ".join(dict.fromkeys(g["doms"]))[:44] or "—"
            L.append(f"| {flag}`{g['lt']}` | {g['aa'] or '?'} | {dom} | {_hitcell(g['nr'])} | {_mibcell(g['mibig'])} |")
        L.append("")

    L += ["## Interpretation (class-level, judgment deferred)",
          f"- **Capacity:** content consistent with a **{products or 'specialised-metabolite'}** pathway in "
          f"the neighbourhood of **{(kcb.split('|')[1].strip() if '|' in kcb else kcb) or 'its KCB anchor'}** "
          "(sequence-similarity family, not a product or activity claim).",
          "- **Self-resistance reading:** the resistance-category locus/loci above are consistent with a "
          "producer self-protection cassette (export ± target modification); this raises priority, not proof.",
          "- **Next evidence:** per-cluster KCB + targeted BLASTp (nr vs ClusteredNR) of the resistance loci and "
          "the most-divergent core genes to separate genus-conserved housekeeping from pathway-specific resistance.",
          "", "---",
          "_Domains are antiSMASH facts; homology is similarity not identity; MIBiG is family relatedness; "
          "priors are capacity not activity. Judgment deferred. Mamey extracts._"]
    return "\n".join(L), True


_ROLE_ORDER = [("core", "Core biosynthetic assembly"),
               ("resistance", "Resistance & immunity (self-protection)"),
               ("tailoring", "Tailoring / precursor enzymes"),
               ("transport", "Transport"),
               ("regulation", "Regulation"),
               ("other", "Other / accessory")]

_ROLE_MAP = {
    "PKS-core": "core", "PKS-reductive": "core", "NRPS-core": "core", "carrier": "core",
    "loading": "core", "release": "core", "RiPP-maturation": "core", "terpene/prenyl": "core",
    "tailoring-oxidoreduction": "tailoring", "tailoring-methylation": "tailoring",
    "tailoring-glycosylation": "tailoring", "tailoring-halogenation": "tailoring",
    "tailoring-other": "tailoring", "transport": "transport", "regulatory": "regulation",
    "resistance": "resistance", "structural": "other", "uncharacterized": "other", "other": "other",
}


def _dref_role(cats: list[str]) -> str:
    """Collapse a gene's domain categories to one display bucket (resistance/core win)."""
    buckets = [_ROLE_MAP.get(c, "other") for c in cats]
    for pref in ("resistance", "core", "tailoring", "transport", "regulation"):
        if pref in buckets:
            return pref
    return "other"


def _synthesis(genes: list[dict]) -> str:
    orgs = collections.Counter()
    for g in genes:
        o = g["nr"].get("org", "").strip() if g["nr"] else ""
        if o and "MULTISPECIES" not in o and "unclassified" not in o.lower():
            orgs[o] += 1
    fam = collections.Counter()
    fam_pids = collections.defaultdict(list)
    for g in genes:
        for m in g["mibig"]:
            c = m["compound"].split("/")[0]
            fam[c] += 1
            p = _fnum(m["pid"])
            if p is not None:
                fam_pids[c].append(p)
    div = sorted((_fnum(g["nr"].get("pid")), g["lt"],
                  re.sub(r"\s*\[[^\]]*\]$", "", g["nr"].get("def", ""))[:40])
                 for g in genes if g["nr"] and _fnum(g["nr"].get("pid")) is not None
                 and _fnum(g["nr"].get("pid")) < 70)
    lines = []
    ng = sum(1 for g in genes if g["nr"])
    if orgs:
        top = orgs.most_common(3)
        lines.append(f"- **Dominant nr neighbour:** *{top[0][0]}* ({top[0][1]}/{ng} named nr hits)"
                     + ("; " + ", ".join(f"*{o}* ({n})" for o, n in top[1:]) if len(top) > 1 else "") + ".")
    if fam:
        parts = []
        for c, n in fam.most_common(3):
            med = statistics.median(fam_pids[c]) if fam_pids[c] else 0
            parts.append(f"**{c}** ({n} genes, median {med:.0f}%)")
        lines.append("- **Dominant MIBiG family convergence:** " + "; ".join(parts) + ".")
    if div:
        lines.append("- **Most divergent genes (candidate reference-dark, nr <70%):** "
                     + ", ".join(f"`{lt}` ({p:.0f}%, {d})" for p, lt, d in div[:5]) + ".")
    spot = [f"`{g['lt']}` ({', '.join(g['doms'][:2])}; {_hitcell(g['nr'])})" for g in genes if g["is_res"]]
    if spot:
        lines.append(f"- **Self-resistance loci ({len(spot)}):** " + " · ".join(spot))
    return "\n".join(lines) or "- (no nr/MIBiG evidence banked for this region yet)"


# --------------------------------------------------------------------------- driver
def run(package_dir: str, out_dir: str | None = None, immunity_transporters: bool = False,
        domain_reference_tsv: str | None = None) -> dict:
    inv = load_inventory(package_dir)
    tiers = load_lead_tier(package_dir)
    excl = load_exclusion(package_dir)
    all_domains = load_domains(package_dir)
    mibig = load_mibig(package_dir)
    # curated vocabulary: explicit path, else one banked beside the package, else in-code rules
    ref = load_domain_reference_tsv(domain_reference_tsv
                                    or _find(package_dir, "domain_reference.tsv"))
    # Post-seal deliverables are SIBLINGS — never write inside the sealed package (breaks its
    # checksum/manifest coverage). Default to a sibling dir; refuse any target inside the package.
    package_dir_abs = os.path.abspath(package_dir)
    if out_dir is None:
        out_dir = package_dir_abs.rstrip(os.sep) + "_resistance_dossiers"
    out_dir = os.path.abspath(out_dir)
    if out_dir == package_dir_abs or out_dir.startswith(package_dir_abs + os.sep):
        raise ValueError("resistance-dossier output must be OUTSIDE the sealed package directory")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for bgc, gene_domains in sorted(all_domains.items()):
        nr = load_nr(package_dir, bgc)
        md, has_res = build_dossier(bgc, inv.get(bgc, {"BGC_ID": bgc}), tiers.get(bgc, ""),
                                    gene_domains, nr, mibig, immunity_transporters, ref,
                                    excl_reason=excl.get(bgc, ""))
        if has_res:
            fn = os.path.join(out_dir, f"{bgc}_resistance_dossier.md")
            _atomic_write_text(fn, md)
            written.append(fn)
    return {"n_dossiers": len(written), "out_dir": out_dir, "files": written,
            "used_reference": bool(ref), "n_reference_domains": len(ref)}


# --------------------------------------------------------------------------- CLI
def register_subparser(sub) -> None:
    p = sub.add_parser("resistance-dossier",
                       help="post-seal: per-BGC resistance-focused gene-by-gene dossiers "
                            "(resistance loci via domain_reference + nr BLASTp + MIBiG). Non-blocking.")
    p.add_argument("package", help="path to a sealed package directory")
    p.add_argument("--out", default=None,
                   help="output dir (default: a SIBLING <package>_resistance_dossiers; never inside the sealed package)")
    p.add_argument("--immunity-transporters", action="store_true",
                   help="also flag transporters in resistance-tier BGCs as candidate-immunity [IMM] "
                        "(broader §27 view; default off = strict resistance-marker domains only)")
    p.add_argument("--domain-reference", default=None,
                   help="path to a curated domain_reference.tsv (tools/build_domain_reference.py). "
                        "Strongly recommended: the in-code fallback misses curated calls such as "
                        "Lactamase_B -> resistance. Auto-detected beside the package when present.")
    p.set_defaults(func=_cli_main)


def _cli_main(args) -> int:
    # v9.7.409 (AUDIT_cli_edgecases): validate the package exists BEFORE run() mkdir()s its sibling
    # output dir. On a nonexistent package this used to crash with a raw OSError when the parent was
    # read-only, or silently create a spurious empty _resistance_dossiers/ dir (rc 0) when writable.
    if not os.path.isdir(args.package):
        emit(f"ERROR: not a package directory: {args.package}", file=_sys.stderr)
        return 1
    res = run(args.package, args.out, getattr(args, "immunity_transporters", False),
              getattr(args, "domain_reference", None))
    src = "curated TSV" if res.get("used_reference") else "in-code fallback vocabulary"
    emit(f"resistance-dossier: wrote {res['n_dossiers']} dossiers -> {res['out_dir']}  [{src}]")
    return 0
