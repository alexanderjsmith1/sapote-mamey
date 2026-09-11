"""domain_level.py — native domain-level Mode B enrichment (v9.7.89).

WHAT THIS IS
------------
Post-seal enrichment that turns each top BGC's protein domains into a structured evidence
review: every domain mapped to a controlled biosynthetic role, per-BGC role-burden and
complexity metrics, and architecture/family-level safe/unsafe claim ceilings. This separates
**score priority** (AB/AF) from **architecture confidence** (domain burden) from **claim ceiling**
(what may safely be said) — the thing Mode B should do but couldn't from score + product label
alone.

ARCHITECTURE (mirrors Finding L / Option A)
-------------------------------------------
This is POST-SEAL. It never blocks the deterministic package seal. Two input paths:
  1. `--source-antismash <zip>`: full per-domain detail (name, description, evalue) via the
     existing extract_domain_features parser — the complete view.
  2. sealed package only: falls back to the v9.7.88 gene context (`gene_context.jsonl`), which
     carries domain NAMES per CDS but not descriptions/evalues — a LIMITED view, clearly marked.
On any failure it writes a domain-level failure receipt and leaves the core package valid.

CLAIM SAFETY
------------
Every role assignment is structural (what a domain IS). Every claim is architecture/family-level
capacity language — never product identity. Aligned with the standing rules.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_DATA = Path(__file__).parent / "data" / "domain_level"

# role categories that count as biosynthetic core (for complexity metrics)
_CORE_ROLES = {
    "NRPS A-domain / loading", "NRPS condensation", "Carrier protein / PP-binding",
    "ACP / acyl carrier", "PKS ketosynthase", "PKS acyltransferase/loading",
    "PKS reductive loop", "PKS cyclase/aromatase", "Lanthipeptide maturation",
    "Lasso/RiPP maturation", "Azole/crocagin/RiPP tailoring",
}
_TAILORING_ROLES = {
    "Sugar/glycosyl tailoring", "Redox tailoring", "Methylation/alkylation",
    "Amino/amide tailoring", "Release/editing hydrolase",
}
_TRANSPORT_ROLES = {"Transport/export/uptake", "Siderophore uptake/export"}
_REGULATORY_ROLES = {"Regulatory/sensor"}


def load_rules() -> tuple[dict, dict]:
    """Load the versioned taxonomy + claim-safety rule files. Raises if missing (caller catches)."""
    tax = json.loads((_DATA / "domain_role_taxonomy.v1.json").read_text(encoding="utf-8"))
    claim = json.loads((_DATA / "domain_claim_safety.v1.json").read_text(encoding="utf-8"))
    return tax, claim


def load_architecture_templates(*, strict: bool = False) -> dict:
    """Load the architecture-template rules (v9.7.90).

    strict=False (default): returns {} if the file is absent (caller tolerates).
    strict=True: raises FileNotFoundError if absent (caller requires the file).
    """
    p = _DATA / "domain_architecture_templates.v1.json"
    if not p.exists():
        if strict:
            raise FileNotFoundError(f"Architecture templates required but absent: {p}")
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def architecture_for_roles(roles_present: set[str], templates: dict) -> str:
    """Assign a canonical architecture archetype from the set of roles present in a BGC. Highest
    required-hit count above min wins; forbidden roles disqualify; else the fallback archetype.
    Architecture is structural, never a product-identity claim."""
    if not templates:
        return ""
    best, best_score = templates.get("fallback_archetype", "unclassified architecture"), 0
    for t in templates.get("templates", []):
        if set(t.get("forbidden_roles", [])) & roles_present:
            continue
        hits = len(set(t.get("required_roles", [])) & roles_present)
        if hits >= t.get("min_required_hits", 1) and hits > best_score:
            best, best_score = t["archetype"], hits
    return best


def role_for_domain(domain_name: str, taxonomy: dict) -> str:
    """Map a domain name to its role category by case-insensitive substring; first match wins.
    Strips a trailing ' (e=...)' evalue annotation the upstream table sometimes appends, and
    routes bare TIGR##### numbers (opaque to substring matching) to the unknown/accessory fallback
    unless an explicit TIGR map entry exists."""
    if not domain_name:
        return taxonomy["fallback_other"]["role"]
    # strip a trailing evalue annotation like "Beta-lactamase (e=2.10E-52)"
    dn_clean = re.sub(r"\s*\(e=[^)]*\)\s*$", "", domain_name).strip()
    dn = dn_clean.lower()
    for cat in taxonomy["categories"]:
        for pat in cat["patterns"]:
            if pat.lower() in dn:
                return cat["role"]
    # bare TIGR numbers carry no substring signal — opaque identifiers
    if re.match(r"^tigr\d+$", dn):
        return taxonomy["fallback_unknown_repeat"]["role"]
    fb = taxonomy["fallback_unknown_repeat"]
    for pat in fb["patterns"]:
        if pat.lower() in dn:
            return fb["role"]
    return taxonomy["fallback_other"]["role"]


def _claim_for_roles(roles_present: set[str], claim_rules: dict) -> dict:
    """Pick the claim-safety verdict for a BGC from the set of roles present in it."""
    core_count = len(roles_present & _CORE_ROLES)
    floor = None
    for rule in claim_rules["rules"]:
        if rule.get("is_default_floor"):
            floor = rule
        need_all = rule.get("trigger_roles_all")
        need_any = rule.get("trigger_roles_any")
        min_core = rule.get("require_min_core", 0)
        if need_all and not set(need_all).issubset(roles_present):
            continue
        if need_any and not (set(need_any) & roles_present):
            continue
        if min_core and core_count < min_core:
            continue
        if rule.get("is_default_floor"):
            continue  # floor only used if nothing else matched
        return {"safe": rule["safe_claim"], "unsafe": rule["unsafe_claim"],
                "ceiling": rule["ceiling"], "rule_id": rule["id"]}
    if floor:
        return {"safe": floor["safe_claim"], "unsafe": floor["unsafe_claim"],
                "ceiling": floor["ceiling"], "rule_id": floor["id"]}
    return {"safe": "domain evidence present", "unsafe": "product identity without validation",
            "ceiling": claim_rules["_meta"]["default_ceiling"], "rule_id": "default"}


def build_domain_rows(bgcs: list[dict], domains_by_bgc: dict[str, list[dict]],
                      taxonomy: dict) -> list[dict]:
    """One row per domain, mapped to a role. domains_by_bgc: {bgc_id: [ {locus_tag, start, end,
    strand, domain_name, domain_description, evalue}, ... ]}."""
    rows: list[dict] = []
    for rank, b in enumerate(bgcs, 1):
        bid = b.get("bgc_id")
        for d in domains_by_bgc.get(bid, []):
            rows.append({
                "Strain": b.get("strain", ""), "Rank": rank, "BGC_ID": bid,
                "Assembly_Locator": b.get("assembly_locator", ""),
                "locus_tag": d.get("locus_tag", ""),
                "cds_start": d.get("start", ""), "cds_end": d.get("end", ""),
                "strand": d.get("strand", ""),
                "domain_name": d.get("domain_name", ""),
                "domain_description": d.get("domain_description", ""),
                "evalue": d.get("evalue", ""),
                "domain_role_category": role_for_domain(d.get("domain_name", ""), taxonomy),
                "BGC_products": b.get("products", ""),
                "KCB_top": b.get("kcb_top", ""),
                "AB_score": b.get("ab_score", ""), "AF_score": b.get("af_score", ""),
            })
    return rows


def build_complexity_metrics(bgcs: list[dict], domain_rows: list[dict]) -> list[dict]:
    """Per-BGC complexity: total/unique domains, CDS count, role-burden breakdown, and (v9.7.90)
    a canonical architecture archetype from the domain-role set."""
    by_bgc: dict[str, list[dict]] = defaultdict(list)
    for r in domain_rows:
        by_bgc[r["BGC_ID"]].append(r)
    templates = load_architecture_templates()
    out: list[dict] = []
    for rank, b in enumerate(bgcs, 1):
        bid = b.get("bgc_id")
        drows = by_bgc.get(bid, [])
        roles = Counter(r["domain_role_category"] for r in drows)
        archetype = architecture_for_roles(set(roles), templates)
        out.append({
            "Strain": b.get("strain", ""), "Rank": rank, "BGC_ID": bid,
            "Assembly_Locator": b.get("assembly_locator", ""),
            "Products": b.get("products", ""),
            "Domain_total": len(drows),
            "Unique_domain_names": len({r["domain_name"] for r in drows}),
            "Domain_CDS_count": len({r["locus_tag"] for r in drows if r["locus_tag"]}),
            "Biosynthetic_core_domain_count": sum(roles[r] for r in roles if r in _CORE_ROLES),
            "Tailoring_domain_count": sum(roles[r] for r in roles if r in _TAILORING_ROLES),
            "Transport_domain_count": sum(roles[r] for r in roles if r in _TRANSPORT_ROLES),
            "Regulatory_domain_count": sum(roles[r] for r in roles if r in _REGULATORY_ROLES),
            "Architecture_archetype": archetype,
        })
    return out


def build_claim_rows(bgcs: list[dict], domain_rows: list[dict], claim_rules: dict) -> list[dict]:
    by_bgc: dict[str, set] = defaultdict(set)
    for r in domain_rows:
        by_bgc[r["BGC_ID"]].add(r["domain_role_category"])
    out: list[dict] = []
    for rank, b in enumerate(bgcs, 1):
        bid = b.get("bgc_id")
        verdict = _claim_for_roles(by_bgc.get(bid, set()), claim_rules)
        out.append({
            "Strain": b.get("strain", ""), "Rank": rank, "BGC_ID": bid,
            "Assembly_Locator": b.get("assembly_locator", ""),
            "Safe_domain_claims": verdict["safe"],
            "Unsafe_domain_claims": verdict["unsafe"],
            "Domain_claim_ceiling": verdict["ceiling"],
        })
    return out


def build_role_counts_by_bgc(domain_rows: list[dict]) -> list[dict]:
    by: dict[tuple, Counter] = defaultdict(Counter)
    meta: dict[tuple, dict] = {}
    for r in domain_rows:
        key = (r["Strain"], r["BGC_ID"])
        by[key][r["domain_role_category"]] += 1
        meta[key] = {"Assembly_Locator": r["Assembly_Locator"]}
    out: list[dict] = []
    for (strain, bid), counts in by.items():
        for role, n in sorted(counts.items()):
            out.append({"Strain": strain, "BGC_ID": bid,
                        "Assembly_Locator": meta[(strain, bid)]["Assembly_Locator"],
                        "domain_role_category": role, "count": n})
    return out



def classify_architecture(roles_present: set[str], templates: dict) -> tuple[str, str]:
    """Match a BGC's role set to an architecture archetype; first template that satisfies
    required (>= min_required_hits) and has no forbidden role wins. Returns (archetype, note)."""
    for t in templates["templates"]:
        req = set(t.get("required_roles", []))
        forb = set(t.get("forbidden_roles", []))
        hits = len(req & roles_present)
        if hits >= t.get("min_required_hits", len(req)) and not (forb & roles_present):
            return t["archetype"], t.get("note", "")
    return templates["fallback_archetype"], "no template matched"


def build_architecture_rows(bgcs: list[dict], domain_rows: list[dict], templates: dict) -> list[dict]:
    """Ordered domain-architecture string per BGC + the matched archetype (request c1: replaces the
    workbook-only string with a template classification)."""
    by_bgc: dict[str, list[dict]] = defaultdict(list)
    roles_by_bgc: dict[str, set] = defaultdict(set)
    for r in domain_rows:
        by_bgc[r["BGC_ID"]].append(r)
        roles_by_bgc[r["BGC_ID"]].add(r["domain_role_category"])
    out: list[dict] = []
    for rank, b in enumerate(bgcs, 1):
        bid = b.get("bgc_id")
        drows = sorted(by_bgc.get(bid, []), key=lambda r: int(r.get("cds_start") or 0))
        arch_string = " - ".join(d.get("domain_name", "") for d in drows)
        archetype, note = classify_architecture(roles_by_bgc.get(bid, set()), templates)
        out.append({
            "Strain": b.get("strain", ""), "Rank": rank, "BGC_ID": bid,
            "Assembly_Locator": b.get("assembly_locator", ""),
            "Products": b.get("products", ""),
            "architecture_archetype": archetype, "archetype_note": note,
            "n_domains": len(drows),
            "domain_architecture_string": arch_string[:2000],
        })
    return out


def build_module_summary(bgcs: list[dict], modules_by_bgc: dict[str, list[dict]]) -> list[dict]:
    """aSModule summary per BGC (request c2): count, module types, ordered domains, monomer pairings.
    modules_by_bgc: {bgc_id: [ {module_type, domains:[...], monomer, ...}, ... ]}."""
    out: list[dict] = []
    for rank, b in enumerate(bgcs, 1):
        bid = b.get("bgc_id")
        mods = modules_by_bgc.get(bid, [])
        mtypes = sorted({m.get("module_type", "") for m in mods if m.get("module_type")})
        mdomains = " | ".join(";".join(m.get("domains", [])) for m in mods if m.get("domains"))
        pairings = " | ".join(f"{m.get('monomer','?')}" for m in mods if m.get("monomer"))
        out.append({
            "Strain": b.get("strain", ""), "Rank": rank, "BGC_ID": bid,
            "Assembly_Locator": b.get("assembly_locator", ""),
            "Products": b.get("products", ""),
            "aSModule_count": len(mods),
            "module_types": "; ".join(mtypes),
            "module_domains": mdomains[:2000],
            "monomer_pairings": pairings[:1000] or "not_computed",
        })
    return out


def modules_from_source_zip(zip_path, bgcs: list[dict]) -> dict[str, list[dict]]:
    """Extract antiSMASH aSModule features from the source zip, keyed to BGC by contig + coordinate
    overlap. Returns {bgc_id: [module_dict, ...]}.

    NOTE (Patch G supersedes substrate): A-domain substrate resolution lives in
    mamey/nrps_predictions.py (JSON Stachelhaus). This function restores the module COUNT/type per BGC.
    v9.7.197 (F completion): the feature contig carries the antiSMASH region suffix
    (`NODE_6_..._84.228413`) while the BGC contig is the bare `NODE_6_..._84`, so raw matching found
    nothing and aSModule_count stayed 0. Strip the suffix and match bare contig + coordinate window."""
    from .parsers import extract_domain_features
    import re as _re
    feats = extract_domain_features(zip_path)

    def _bare(c) -> str:
        return _re.sub(r"\.\d+$", "", str(c or ""))

    by_contig: dict[str, list[dict]] = defaultdict(list)
    for b in bgcs:
        by_contig[_bare(b.get("contig", ""))].append(b)
    out: dict[str, list[dict]] = defaultdict(list)
    for f in feats:
        if getattr(f, "feature_type", "") != "aSModule":
            continue
        contig = _bare(getattr(f, "contig", "") or "")
        fs, fe = getattr(f, "start", None), getattr(f, "end", None)
        q = getattr(f, "qualifiers", {}) or {}
        for b in by_contig.get(contig, []):
            bs, be = b.get("start"), b.get("end")
            if bs is None or be is None or fs is None or fe is None:
                out[b["bgc_id"]].append({"module_type": "", "domains": [], "monomer": ""})
                continue
            if not (fe < int(bs) or fs > int(be)):
                out[b["bgc_id"]].append({
                    "module_type": (q.get("type", [""]) or [""])[0] if isinstance(q.get("type"), list) else "",
                    "domains": [str(x) for x in q.get("domains", [])] if q.get("domains") else [],
                    "monomer": "",  # substrate resolution is G's job (nrps_predictions.py)
                })
    return out


# --- domain extraction from the antiSMASH source zip (full detail path) ----------------------

def domains_from_source_zip(zip_path: str | Path, bgcs: list[dict]) -> dict[str, list[dict]]:
    """Extract per-domain rows from the antiSMASH zip and assign to BGCs by contig + overlap.
    Returns {bgc_id: [domain_row, ...]} with full name/description/evalue."""
    from .parsers import extract_domain_features
    feats = extract_domain_features(zip_path)
    # group BGCs by contig for overlap assignment
    by_contig: dict[str, list[dict]] = defaultdict(list)
    for b in bgcs:
        by_contig[b.get("contig", "")].append(b)
    out: dict[str, list[dict]] = defaultdict(list)
    for f in feats:
        contig = getattr(f, "contig", "") or ""
        fs, fe = getattr(f, "start", None), getattr(f, "end", None)
        for b in by_contig.get(contig, []):
            bs, be = b.get("start"), b.get("end")
            if bs is None or be is None or fs is None or fe is None:
                continue
            if not (fe < bs or fs > be):
                desc = (getattr(f, "qualifiers", {}) or {}).get("description", [""])
                desc = desc[0] if isinstance(desc, list) and desc else (desc if isinstance(desc, str) else "")
                out[b["bgc_id"]].append({
                    "locus_tag": getattr(f, "locus_tag", "") or "",
                    "start": fs, "end": fe, "strand": getattr(f, "strand", ""),
                    "domain_name": getattr(f, "domain", "") or "",
                    "domain_description": desc,
                    "evalue": getattr(f, "evalue", "") or "",
                })
    return out


def domains_from_gene_context(package_dir: str | Path, strain_id: str,
                              bgcs: list[dict]) -> dict[str, list[dict]]:
    """LIMITED fallback: domain NAMES from the sealed v9.7.88 gene context (no descriptions/evalues)."""
    from .gene_context import load_gene_context
    gc = load_gene_context(package_dir, strain_id)
    out: dict[str, list[dict]] = defaultdict(list)
    for b in bgcs:
        bid = b.get("bgc_id")
        for cds in gc.get(bid, []):
            for dom in cds.get("sec_met_domains", []):
                out[bid].append({
                    "locus_tag": cds.get("locus_tag", "") or "",
                    "start": cds.get("start", ""), "end": cds.get("end", ""),
                    "strand": cds.get("strand", ""),
                    "domain_name": dom, "domain_description": "", "evalue": "",
                })
    return out


def _top_bgcs_from_package(pkg: Path, top_n: int) -> tuple[str, list[dict]]:
    """Read the strain id + top-N BGCs (by AB+AF) from a sealed package's manifest + triage board."""
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    strain_id = manifest.get("strain_id") or pkg.parent.name
    bgcs_by_id = {b["bgc_id"]: b for b in manifest.get("bgcs", [])}
    triage = sorted(pkg.glob("*_4_triage_board.csv"))
    ranked_ids: list[tuple[str, float, float]] = []
    if triage:
        with open(triage[0], newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                # AUDIT_379: mirror scoring.is_lead_excluded()'s 3-flag lead-exclusion gate.
                # The triage CSV has no Mobile_element_flag column (cli.py triage_headers), but the
                # manifest bgcs (bgcs_by_id, loaded above) carry mobile_element_flag (models.py:369,
                # v9.7.374). Without this third check a BGC the engine demoted PURELY for mobile/IS-
                # element dominance (no standing-rule, no primary-metabolism flag) still enters the
                # domain-level top-N and receives a full figure/table set as if it were a ranked lead.
                if (r.get("Standing_rule") or r.get("Primary_metab_flag") == "YES"
                        or bgcs_by_id.get(r.get("BGC_ID", ""), {}).get("mobile_element_flag")):
                    continue
                def _f(c):
                    try: return float(r.get(c) or 0)
                    except (TypeError, ValueError): return 0.0
                ranked_ids.append((r.get("BGC_ID", ""), _f("AB_auto"), _f("AF_auto")))
    ranked_ids.sort(key=lambda t: t[1] + t[2], reverse=True)
    out: list[dict] = []
    for bid, ab, af in ranked_ids[:top_n]:
        b = bgcs_by_id.get(bid, {})
        out.append({
            "bgc_id": bid, "strain": strain_id, "contig": b.get("contig", ""),
            "start": b.get("start"), "end": b.get("end"),
            "assembly_locator": f"{b.get('contig','')} region{int(b.get('region_number') or 0):03d}",
            "products": "; ".join(b.get("products", []) or []),
            "kcb_top": b.get("kcb_top", ""), "ab_score": ab, "af_score": af,
        })
    return strain_id, out


def _write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def run_domain_level(package_dir: str | Path, source_antismash: str | Path | None = None,
                     top_n: int = 10, outdir: str | Path | None = None) -> dict[str, Any]:
    """Post-seal domain-level enrichment. Never raises — on failure writes a receipt and returns
    a status dict, leaving the core package valid. Returns the receipt dict."""
    pkg = Path(package_dir)
    out = Path(outdir) if outdir else pkg / "domain_level"
    out.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {"command": "domain-level", "package": ".",
                               "source_antismash": Path(source_antismash).name if source_antismash else None,
                               "top_n": top_n, "files": [], "warnings": [],
                               "core_package_valid": True}

    def _fail(card_name: str, reason: str, mode: str) -> dict:
        receipt.update({"status": "SKIPPED", "reason": reason, "mode": mode})
        (out / card_name).write_text(
            f"# Domain-level enrichment skipped\n\n{reason}\n\n"
            f"Core package remains valid. Retry: "
            f"`python -m mamey domain-level --package <pkg>"
            f"{' --source-antismash <zip>' if 'NO_GBK' in card_name else ''}`\n",
            encoding="utf-8")
        (out / "domain_level_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt

    try:
        taxonomy, claim_rules = load_rules()
    except Exception as e:
        return _fail("DOMAIN_LEVEL_CLAIM_SAFETY_RULES_MISSING.md",
                     f"taxonomy/claim-safety rule files missing or invalid: {e}", "none")

    if not (pkg / "manifest.json").exists():
        return _fail("DOMAIN_LEVEL_LIMITED_PACKAGE_ONLY.md",
                     "manifest.json not found in package directory", "none")

    strain_id, bgcs = _top_bgcs_from_package(pkg, top_n)
    if not bgcs:
        return _fail("DOMAIN_LEVEL_LIMITED_PACKAGE_ONLY.md", "no eligible top BGCs in triage board", "none")

    # choose the input path: full source zip if given, else the sealed gene context (limited)
    mode = "full_source"
    domains_by_bgc: dict[str, list[dict]] = {}
    if source_antismash and Path(source_antismash).exists():
        try:
            domains_by_bgc = domains_from_source_zip(source_antismash, bgcs)
        except Exception as e:
            receipt["warnings"].append(f"source-zip parse failed ({e}); falling back to gene context")
            domains_by_bgc = {}
    if not domains_by_bgc:
        domains_by_bgc = domains_from_gene_context(pkg, strain_id, bgcs)
        mode = "limited_gene_context"
        if not any(domains_by_bgc.values()):
            return _fail("DOMAIN_LEVEL_SKIPPED_NO_GBK.md",
                         "no domain context available (no source zip and no sealed gene context). "
                         "Re-run with --source-antismash <zip>.", "none")
        receipt["warnings"].append(
            "LIMITED mode: domain names only (no descriptions/evalues) from the sealed gene "
            "context. Pass --source-antismash <zip> for full per-domain detail.")
        (out / "MODE_B_LIMITED_DOMAIN_CONTEXT.md").write_text(
            "# Domain-level: LIMITED context\n\nBuilt from the sealed gene context (domain names "
            "only). For full descriptions/evalues, re-run with --source-antismash <zip>.\n",
            encoding="utf-8")

    receipt["mode"] = mode
    # PC-9 (v9.7.253 audit): stamp input-path fidelity onto every row so a standalone reader of
    # domain_rows_long.csv knows whether it got the FULL (source-zip: name+description+evalue) or
    # LIMITED (sealed gene-context: names only) view. Previously the mode lived only in the receipt
    # and the OPEN_ME_FIRST narrative, so a CSV read on its own lost that context.
    view_fidelity = "FULL" if mode == "full_source" else "LIMITED"
    # build all tables
    domain_rows = build_domain_rows(bgcs, domains_by_bgc, taxonomy)
    for _row in domain_rows:
        _row["view_fidelity"] = view_fidelity
    complexity = build_complexity_metrics(bgcs, domain_rows)
    claims = build_claim_rows(bgcs, domain_rows, claim_rules)
    role_counts = build_role_counts_by_bgc(domain_rows)

    _write_csv(out / "domain_rows_long.csv", domain_rows,
               ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "locus_tag", "cds_start",
                "cds_end", "strand", "domain_name", "domain_description", "evalue",
                "domain_role_category", "BGC_products", "KCB_top", "AB_score", "AF_score",
                "view_fidelity"])
    _write_csv(out / "domain_complexity_metrics_by_bgc.csv", complexity,
               ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Products", "Domain_total",
                "Unique_domain_names", "Domain_CDS_count", "Biosynthetic_core_domain_count",
                "Tailoring_domain_count", "Transport_domain_count", "Regulatory_domain_count",
                "Architecture_archetype"])
    _write_csv(out / "domain_safe_unsafe_claims.csv", claims,
               ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Safe_domain_claims",
                "Unsafe_domain_claims", "Domain_claim_ceiling"])
    _write_csv(out / "domain_role_counts_by_bgc.csv", role_counts,
               ["Strain", "BGC_ID", "Assembly_Locator", "domain_role_category", "count"])

    # Base outputs are recorded before optional extensions append their own files.  Do not
    # overwrite this list after the optional blocks: that silently erased the architecture
    # and aSModule filenames from the receipt even though both files existed on disk.
    receipt["files"] = ["domain_rows_long.csv", "domain_complexity_metrics_by_bgc.csv",
                        "domain_safe_unsafe_claims.csv", "domain_role_counts_by_bgc.csv"]

    # v9.7.90 (request c1/c2): architecture-template classification + aSModule summary
    try:
        templates = load_architecture_templates(strict=True)
        arch_rows = build_architecture_rows(bgcs, domain_rows, templates)
        _write_csv(out / "ordered_domain_architectures_by_bgc.csv", arch_rows,
                   ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Products",
                    "architecture_archetype", "archetype_note", "n_domains",
                    "domain_architecture_string"])
        receipt["files"].append("ordered_domain_architectures_by_bgc.csv")
        receipt["architecture_templates_version"] = templates["_meta"].get("schema_version", "1.0")
    except Exception as _arch_e:
        receipt["warnings"].append(f"architecture templates unavailable: {_arch_e}")
    try:
        mods_by_bgc = {}
        if source_antismash and Path(source_antismash).exists():
            mods_by_bgc = modules_from_source_zip(source_antismash, bgcs)
        module_rows = build_module_summary(bgcs, mods_by_bgc)
        _write_csv(out / "antismash_module_summary_by_bgc.csv", module_rows,
                   ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Products",
                    "aSModule_count", "module_types", "module_domains", "monomer_pairings"])
        receipt["files"].append("antismash_module_summary_by_bgc.csv")
    except Exception as _mod_e:
        receipt["warnings"].append(f"module summary unavailable: {_mod_e}")

    receipt["n_domain_rows"] = len(domain_rows)
    receipt["n_bgcs"] = len(bgcs)
    receipt["taxonomy_version"] = taxonomy["_meta"]["schema_version"]
    receipt["claim_safety_version"] = claim_rules["_meta"]["schema_version"]
    receipt["status"] = "OK"

    # OPEN_ME_FIRST front-facing report
    (out / "OPEN_ME_FIRST_Domain_Level_ModeB.md").write_text(
        f"# Domain-level Mode B — {strain_id}\n\n"
        f"Mode: **{mode}** · {len(domain_rows)} domain rows across {len(bgcs)} top BGCs.\n\n"
        "Separates score priority (AB/AF) from architecture confidence (domain burden) from "
        "claim ceiling (what may safely be said). All claims are architecture/family-level "
        "capacity statements — never product identity.\n\n"
        "Files: `domain_rows_long.csv` (per-domain evidence), "
        "`domain_complexity_metrics_by_bgc.csv` (role-burden per BGC), "
        "`domain_safe_unsafe_claims.csv` (claim ceilings), "
        "`domain_role_counts_by_bgc.csv` (role tallies).\n",
        encoding="utf-8")
    (out / "domain_level_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt
