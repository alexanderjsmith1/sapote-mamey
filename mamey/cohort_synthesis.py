"""cohort_synthesis.py — Gap 3: deterministic cross-strain synthesis writer.

THE GAP THIS FILLS
------------------
The cohort figures and sheets exist, but nothing turns them into the methods-paper "cross-strain
results" prose. This reads the VERIFIED cohort master and emits that synthesis deterministically:
cohort composition, convergent capacities, host-biased classes, the novelty gradient, the
cohort-unique differentiating leads, and genus signatures. Capacity-level throughout; every number
traces to a named sheet.

THE novelty_basis PARAMETER (the reason this module is careful)
--------------------------------------------------------------
"Reference-dark" has two legitimate definitions that differ by >2x on this cohort:
  - "fully_dark"          : no MIBiG anchor at all (the B1 `kcb_top` field is not a BGC####### accession)
                            -> 164/1131 (15%) on the 24-strain cohort; matches the
                               Cross_Strain_Findings "fully KCB-dark" column.
  - "dark_or_unresolved"  : also counts BGCs whose KCB hit is only a bare genome reference
                            (no MIBiG accession) -> 423/1131 (37%); the broader novelty signal.
Reporting 37% against a sheet that means 15% is a silent wrong-answer. So EVERY novelty number this
writer emits is tagged with its basis, and `novelty_basis` (default "fully_dark", matching the
canonical sheet) selects which definition the headline numbers use. The non-selected figure is
still reported, explicitly labeled, so the two are never conflated.

DETERMINISTIC. No scoring change. Legacy calls remain private; explicit public calls
independently admit package identities and project master rows before synthesis.
DEPENDENCY: a verified master (DAPR populated, Cross_Strain_Findings recomputed, denominator
invariant holding). On a stale master it refuses rather than emitting wrong prose.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
import re
from pathlib import Path
from collections import defaultdict, Counter
from openpyxl import load_workbook

_MIBIG_RE = re.compile(r"\bBGC\d{7}\b")  # a real MIBiG accession in KCB_Top_Hit

# host grouping from a free-text host field
# --- ubiquitous-class exclusion sets (Bunny Hop v9.7.119) -------------------
# These two sets intentionally DIFFER. Keep them named and commented so a future
# editor does not "unify" them and silently break genus signatures.
#
# _DIFF_UBIQ: classes excluded from cohort-unique DIFFERENTIATING-lead detection.
#   Broader — ectoine/melanin/terpene-precursor are too common across genera to
#   mark a strain as a *differentiator* even when only one strain carries them.
# _GENUS_UBIQ: classes excluded from GENUS-SIGNATURE display (§6). Smaller —
#   ectoine/melanin ARE retained as signatures because e.g. "all Pseudonocardia
#   make ectoine" is a real genus finding.
_DIFF_UBIQ = {"other", "saccharide", "fatty_acid", "terpene", "NI-siderophore",
              "NRP-metallophore", "ectoine", "melanin", "terpene-precursor",
              "RiPP", "NRPS", "PKS", "T1PKS", "NRPS-like", "PKS-like", "RiPP-like"}
_GENUS_UBIQ = {"other", "saccharide", "fatty_acid", "terpene", "RiPP", "NRPS",
               "PKS", "T1PKS", "NRPS-like", "PKS-like", "RiPP-like",
               "NI-siderophore", "NRP-metallophore"}


def meta_from_differentiating_csv(csv_path: str | Path) -> dict:
    """Build {strain: {"genus":..., "host":...}} from a differentiating-capacities CSV.

    Used to populate genus/host when the master registry's taxonomy columns are unpopulated. The CSV
    typically covers only the strains that carry a differentiating capacity (a subset of the cohort),
    so the resulting genus signatures / host gradient are over the covered subset — the writer states
    this coverage rather than implying the full cohort.
    """
    import csv as _csv
    meta = {}
    p = Path(csv_path)
    if not p.exists():
        return meta
    with open(p, newline="") as f:
        for row in _csv.DictReader(f):
            sid = (row.get("strain") or "").strip()
            if not sid:
                continue
            meta[sid] = {"genus": (row.get("genus") or "").strip(),
                         "host": (row.get("host") or "").strip()}
    return meta


def _host_group(h: str) -> str:
    h = (h or "").lower()
    if "bombus" in h: return "Bombus"
    if any(x in h for x in ("attine", "acromyrmex", "atta")): return "Attine"
    if "apis" in h: return "Apis"
    if "wasp" in h or "vespid" in h: return "Wasp"
    if "moss" in h or "bryo" in h: return "Moss"
    if "apidae" in h: return "Other Apidae"
    return "Other"


def _is_fully_dark(kcb_top: str) -> bool:
    """fully-dark = NO knownclusterblast hit at all (empty KCB_Top_Hit).

    On the verified master this reproduces 164/1131 (15%) and matches both the manifest
    `no kcb_top` count and the Cross_Strain_Findings 'fully KCB-dark' column.
    """
    s = str(kcb_top or "").strip()
    return s == "" or s.lower() == "none"


def _is_dark_or_unresolved(kcb_top: str) -> bool:
    """broader = no MIBiG accession in the hit (empty OR a bare genome-reference hit).

    On the verified master this reproduces 423/1131 (37%) — the 164 empty plus the 259
    bare-genome-reference hits that never resolved to a MIBiG cluster.
    """
    s = str(kcb_top or "").strip()
    if s == "" or s.lower() == "none":
        return True
    return not bool(_MIBIG_RE.search(s))


# COH-02: the registry/BGC columns are resolved against the REAL master_workbook schema
# (mamey/master_workbook.py::CANONICAL_V1_HEADERS), NOT capitalized display names. The previous
# version resolved by keys ("KCB_Top_Hit", "Products", "Genus", "Corrected_BGCs") that do NOT exist
# in a real master, then fell back to fixed POSITIONAL indices that landed on the wrong columns
# (KCB_Top_Hit->products, Products->a coordinate, Genus->ecology_source, Corrected_BGCs->top_ab_bgc)
# — emitting confident WRONG prose on a real master while a fixture with the same fake headers hid
# it. We now resolve by the real lowercase headers and RAISE on a missing required column rather
# than silently mis-reading a positional fallback.
_A2_REQUIRED = ("strain", "taxonomy", "ecology_source")
_B1_REQUIRED = ("strain", "products", "kcb_top")
_UNPOPULATED_TAX = ("", "not", "not verified", "none", "—", "unresolved", "unknown")


def _genus_from_taxonomy(tax) -> str:
    """Genus = first token of the taxonomy string. 'Streptomyces sp.' -> 'Streptomyces'.

    The shipped A2_Strain_Registry has no dedicated Genus column — it carries `taxonomy`
    (e.g. 'Streptomyces sp.'), so genus is derived from it. Returns '' for empty/placeholder
    taxonomy so the meta-override path can supply genus."""
    s = str(tax or "").strip()
    if s.lower() in _UNPOPULATED_TAX:
        return ""
    toks = s.split()
    if toks[0].lower() == "candidatus" and len(toks) > 1:
        return toks[1]
    return toks[0]


def _resolve_headers(ws, required, sheet_name: str) -> dict:
    """Return {header_name: col_index} for a worksheet's header row.

    Raises RuntimeError if any required column is absent. NO positional fallback — a real master
    always ships the CANONICAL_V1_HEADERS columns; a master lacking them is stale/foreign and must
    refuse rather than mis-read a coordinate as a compound name (COH-02)."""
    row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    header = [str(x) if x is not None else "" for x in row]
    idx = {name: i for i, name in enumerate(header) if name}
    missing = [c for c in required if c not in idx]
    if missing:
        raise RuntimeError(
            f"master sheet {sheet_name} is missing required column(s) {missing} "
            f"(present headers: {header}). This master does not match the shipped master_workbook "
            f"schema; refusing to emit cross-strain prose from a foreign/stale schema (COH-02)."
        )
    return idx


def load_master(master_path: str | Path, host_overrides: dict | None = None,
                meta_overrides: dict | None = None) -> dict:
    """Read the verified master into the structures the writer needs. Returns {} if stale.

    Columns are resolved against the shipped master_workbook schema (CANONICAL_V1_HEADERS):
    A2_Strain_Registry has `strain, taxonomy, ecology_source, habitat, …, n50, bgc_count, …`
    (genus is derived from `taxonomy`, host from `ecology_source`); B1_BGC_Master has
    `strain, …, products, boundary, arch, kcb_top, …`. A master missing a required column RAISES.

    host_overrides: legacy {strain: host} map (kept for back-compat).
    meta_overrides: {strain: {"genus": ..., "host": ...}} — used when the master registry's
    `taxonomy`/`ecology_source` columns are unpopulated (some cuts ship a structural registry
    without taxonomy). The differentiating-capacities CSV is the usual source; see
    meta_from_differentiating_csv()."""
    from .xlsx_determinism import guard_workbook_size as _guard_xlsx  # v9.7.410: shared-strings still inflate under read_only
    _guard_xlsx(master_path)
    wb = load_workbook(Path(master_path), read_only=True, data_only=True)
    sheets = set(wb.sheetnames)
    # F4 fix: the dedicated Cross_Strain_Class_Prevalence sheet is only added post-hoc by
    # tools/add_xstrain_sheets.py; a plain gold-run master never has it. But the equivalent
    # per-class strain counts live in B2_Product_Class_Matrix, which master_workbook.py writes
    # into EVERY base master. Accept either, and derive prevalence from B2 when the dedicated
    # sheet is absent (see below) so `mamey cohort` works on a bare gold master.
    required = {"A2_Strain_Registry", "B1_BGC_Master"}
    has_prevalence = ("Cross_Strain_Class_Prevalence" in sheets) or ("B2_Product_Class_Matrix" in sheets)
    if not (required <= sheets and has_prevalence):
        return {}
    meta_overrides = meta_overrides or {}

    # registry: strain -> genus/host/n50/bgc_count (resolved by real lowercase headers)
    reg = {}
    ws = wb["A2_Strain_Registry"]
    gi = _resolve_headers(ws, _A2_REQUIRED, "A2_Strain_Registry")
    si = gi["strain"]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or si >= len(r) or not r[si]:
            continue
        sid = r[si]
        ov = meta_overrides.get(sid, {})
        reg_genus = _genus_from_taxonomy(r[gi["taxonomy"]] if gi["taxonomy"] < len(r) else "")
        # a registry whose taxonomy is unpopulated ("", "not", …) yields no genus → prefer the override
        if not reg_genus:
            reg_genus = ov.get("genus", "")
        host = (host_overrides or {}).get(sid) or ov.get("host") \
            or (r[gi["ecology_source"]] if gi["ecology_source"] < len(r) else "") or ""
        reg[sid] = {
            "genus": reg_genus,
            "host": host,
            "host_group": _host_group(host),
            "n50": r[gi["n50"]] if "n50" in gi and gi["n50"] < len(r) else None,
            "corrected": r[gi["bgc_count"]] if "bgc_count" in gi and gi["bgc_count"] < len(r) else None,
        }
    N = len(reg)

    # prevalence — prefer the dedicated sheet; else derive it from B2_Product_Class_Matrix (F4 fix)
    prevalence = {}
    if "Cross_Strain_Class_Prevalence" in sheets:
        ws = wb["Cross_Strain_Class_Prevalence"]
        h = [str(x) for x in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
        pi = {k: h.index(k) for k in h}
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or not r[pi.get("product_class", 0)]:
                continue
            cls = str(r[pi["product_class"]])
            prevalence[cls] = {
                "n_strains": int(r[pi["n_strains"]]) if r[pi["n_strains"]] is not None else 0,
                "band": str(r[pi.get("band", -1)]) if "band" in pi else "",
                # AUDIT_374: was `r[pi.get("informative_for_comparison", -1)]` unguarded —
                # when that column is absent (a foreign/older-schema prevalence sheet), the -1
                # sentinel is not "missing", it is a valid Python index: it silently read whatever
                # value sits in the sheet's LAST column (e.g. a notes field) instead of refusing or
                # defaulting. Mirror the "band" field's own `if "X" in pi` guard immediately above;
                # default to non-informative (claim-safe: never let an absent column spuriously
                # promote a class into the host-bias/differentiator signal in §3).
                "informative": (str(r[pi["informative_for_comparison"]]).lower().startswith("yes")
                                if "informative_for_comparison" in pi else False),
            }
    else:
        # derive from the strain×class count matrix: n_strains = # strains with a nonzero count
        ws = wb["B2_Product_Class_Matrix"]
        h = [str(x) for x in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
        class_cols = [(i, c) for i, c in enumerate(h)
                      if c not in ("strain", "label_provenance", "counts_reliability")]
        counts = {c: 0 for _, c in class_cols}
        provenance_i = h.index("label_provenance") if "label_provenance" in h else None
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or not r[0]:
                continue
            if provenance_i is not None and str(r[provenance_i]).upper() != "GENE_BACKED":
                continue
            for i, c in class_cols:
                v = r[i] if i < len(r) else 0
                try:
                    if v is not None and float(v) > 0:
                        counts[c] += 1
                except (TypeError, ValueError):
                    continue
        for cls, ns in counts.items():
            if ns == 0:
                continue
            frac = ns / N if N else 0
            band = ("ubiquitous" if N and ns == N else "common" if frac >= 0.5
                    else "occasional" if frac >= 0.2 else "rare")
            prevalence[cls] = {"n_strains": ns, "band": band,
                               "informative": 1 <= ns < N}  # differentiates when not carried by all

    # B1: per-BGC for novelty, joined to host via registry (resolved by real lowercase headers)
    bgcs = []
    ws = wb["B1_BGC_Master"]
    bi = _resolve_headers(ws, _B1_REQUIRED, "B1_BGC_Master")
    b_strain, b_kcb, b_products = bi["strain"], bi["kcb_top"], bi["products"]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or b_strain >= len(r) or not r[b_strain]:
            continue
        sid = r[b_strain]
        kcb = r[b_kcb] if b_kcb < len(r) else ""
        products = r[b_products] if b_products < len(r) else ""
        bgcs.append({
            "strain": sid,
            "host_group": reg.get(sid, {}).get("host_group", "Other"),
            "genus": reg.get(sid, {}).get("genus", ""),
            "products": str(products or ""),
            "fully_dark": _is_fully_dark(kcb),
            "dark_or_unresolved": _is_dark_or_unresolved(kcb),
        })

    return {"registry": reg, "N": N, "prevalence": prevalence, "bgcs": bgcs}


def novelty_by_host(bgcs: list, basis: str) -> dict:
    """KCB-dark fraction per host group under the chosen basis. Returns {host: (pct, n)}."""
    assert basis in ("fully_dark", "dark_or_unresolved")
    by = defaultdict(list)
    for b in bgcs:
        by[b["host_group"]].append(b[basis])
    return {hg: (sum(v) / len(v) * 100, len(v)) for hg, v in by.items() if v}


def differentiating_capacities(prevalence: dict) -> list:
    """Classes carried by exactly one strain (cohort-unique), excluding backbone/ubiquitous."""
    return sorted(c for c, p in prevalence.items() if p["n_strains"] == 1 and c not in _DIFF_UBIQ)



# Public synthesis deliberately has a separate strict projection from the legacy reader.
PUBLIC_CLASS_VIEWS = ("RAW_ANTISMASH", "GENE_BACKED")
PUBLIC_SCOPE_VERSION = "sapote_public_master_scope_v1"


class PublicCohortScopeError(ValueError):
    """Content-free refusal: input paths, row values and held identities are never echoed."""


def _scope_refuse(code):
    raise PublicCohortScopeError(code)


def _scope_digest(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def recheck_public_scope(view):
    """Recheck all consumed byte bindings before publishing saved-result projections."""
    try:
        for path, digest in view["_bindings"].items():
            if path.is_symlink() or _scope_digest(path) != digest:
                _scope_refuse("PUBLIC_SCOPE_INPUT_CHANGED")
        for package, names in view["_package_files"].items():
            if _scope_package_files(package) != names:
                _scope_refuse("PUBLIC_SCOPE_INPUT_CHANGED")
    except PublicCohortScopeError:
        raise
    except Exception:
        _scope_refuse("PUBLIC_SCOPE_INPUT_CHANGED")


def _scope_package_files(package):
    from .packaging import _package_files_fail_closed
    return tuple(sorted(p.relative_to(package).as_posix()
                        for p in _package_files_fail_closed(package)))


def _scope_rows(wb, name, required, selected):
    """Project selected identities before reading any other scientific field."""
    if name not in wb.sheetnames:
        _scope_refuse("PUBLIC_MASTER_REQUIRED_SHEET_MISSING")
    ws = wb[name]
    head = next(ws.iter_rows(min_row=1, max_row=1), ())
    headers = [c.value for c in head]
    if any(headers.count(k) != 1 for k in required):
        _scope_refuse("PUBLIC_MASTER_HEADER_INVALID")
    idx = {k: headers.index(k) for k in required}
    rows = []
    for row in ws.iter_rows(min_row=2):
        cell = row[idx["strain"]] if idx["strain"] < len(row) else None
        sid = cell.value if cell is not None else None
        if sid not in selected:
            continue
        values = {}
        for name_, i in idx.items():
            c = row[i] if i < len(row) else None
            if c is not None and c.data_type == "f":
                _scope_refuse("PUBLIC_MASTER_FORMULA_UNSUPPORTED")
            values[name_] = c.value if c is not None else None
        rows.append(values)
    return rows


def _scope_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        _scope_refuse("PUBLIC_MASTER_VALUE_INVALID")
    return value


def _scope_count(value):
    import math
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _scope_refuse("PUBLIC_MASTER_COUNT_INVALID")
    if not math.isfinite(value) or value < 0 or int(value) != value:
        _scope_refuse("PUBLIC_MASTER_COUNT_INVALID")
    return int(value)


def _scope_gene_backing(manifest):
    """Adapt saved producer evidence to the existing selector; never execute scans."""
    from types import SimpleNamespace
    from .master_workbook import _gene_backed_carotenoid_bgcs
    bgcs = manifest["bgcs"]
    ids = {b["bgc_id"] for b in bgcs}
    scans = manifest.get("source_scans")
    if not isinstance(scans, dict):
        _scope_refuse("GENE_BACKED_EVIDENCE_UNAVAILABLE")
    da, pm = scans.get("domain_architecture"), scans.get("primary_metabolism")
    if (not isinstance(da, dict) or da.get("status") != "SOURCE_DERIVED_STRUCTURED_DOMAINS"
            or not isinstance(pm, dict) or pm.get("status") != "SOURCE_DERIVED"):
        _scope_refuse("GENE_BACKED_EVIDENCE_UNAVAILABLE")
    if any(not isinstance(x.get("per_bgc"), dict) or set(x["per_bgc"]) != ids for x in (da, pm)):
        _scope_refuse("GENE_BACKED_COVERAGE_CONFLICT")
    for rec in da["per_bgc"].values():
        if (not isinstance(rec, dict) or not isinstance(rec.get("domains"), list)
                or any(not isinstance(d, dict) or not isinstance(d.get("domain"), str)
                       for d in rec["domains"])):
            _scope_refuse("GENE_BACKED_EVIDENCE_UNAVAILABLE")
    if any(not isinstance(x, dict) or not isinstance(x.get("families"), list)
           for x in pm["per_bgc"].values()):
        _scope_refuse("GENE_BACKED_EVIDENCE_UNAVAILABLE")
    hits = pm.get("hits")
    if not isinstance(hits, dict) or not isinstance(hits.get("pigment"), list):
        _scope_refuse("GENE_BACKED_EVIDENCE_UNAVAILABLE")
    for hit in hits["pigment"]:
        if (not isinstance(hit, dict) or not isinstance(hit.get("product"), str)
                or not isinstance(hit.get("contig"), str)
                or isinstance(hit.get("start"), bool) or isinstance(hit.get("end"), bool)
                or not isinstance(hit.get("start"), int) or not isinstance(hit.get("end"), int)
                or hit["start"] > hit["end"]):
            _scope_refuse("GENE_BACKED_EVIDENCE_UNAVAILABLE")
        if not any(hit["contig"] == b["contig"] for b in bgcs):
            _scope_refuse("GENE_BACKED_COVERAGE_CONFLICT")
    run = SimpleNamespace(bgcs=[SimpleNamespace(**b) for b in bgcs],
                          source_scans=SimpleNamespace(**scans))
    return _gene_backed_carotenoid_bgcs(run)


def load_public_master(master_path, *, runs_dir, privacy_profile=None, strains=None, class_view=None):
    """Independently admit packages, then join only authorized saved master rows.

    Public calls never trust a caller-provided row filter or precomputed prevalence.
    Legacy private load_master remains unchanged. All errors are content-free codes.
    """
    import json
    from .release_policy import load_bound_profile, package_release_policy
    from .privacy_profile import load_public_export_policy
    from .master_workbook import CANONICAL_V1_HEADERS, _b2_product_class_counts
    from .class_architecture import with_family_labels
    from .validate import verify_checksums
    from .crosswalk import assembly_locator
    from .cohort_deliverable import _load_version_gate
    from .xlsx_determinism import guard_workbook_size
    if class_view not in PUBLIC_CLASS_VIEWS:
        _scope_refuse("PUBLIC_CLASS_VIEW_REQUIRED")
    if not master_path:
        _scope_refuse("PUBLIC_MASTER_PATH_REQUIRED")
    view = {"_bindings": {}, "_package_files": {}, "_blocked": set(), "_packages": {},
            "class_view": class_view, "registry": {}, "bgcs": [], "prevalence": {}}
    try:
        root = Path(runs_dir).resolve(strict=True)
        master = Path(master_path)
        if master.is_symlink() or not master.is_file():
            _scope_refuse("PUBLIC_MASTER_PATH_INVALID")
        view["_bindings"][master] = _scope_digest(master)
        profile, pdigest = load_bound_profile(privacy_profile) if privacy_profile else (None, "")
        policy = load_public_export_policy(privacy_profile)
        view["_policy"] = policy
        if privacy_profile:
            view["_bindings"][Path(privacy_profile)] = pdigest
        admitted, manifests, authority = {}, {}, {}
        for package in sorted(root.glob("*/package")):
            if package.is_symlink() or package.parent.is_symlink() or not package.is_dir():
                _scope_refuse("PUBLIC_PACKAGE_CONTAINMENT_INVALID")
            privacy = package_release_policy(package, package.parent.name, profile=profile, profile_sha256=pdigest)
            for meta in [package / "manifest.json", package / "manifest_short.json", *sorted(package.glob("*_1_intake.json"))]:
                if meta.exists():
                    if meta.is_symlink():
                        _scope_refuse("PUBLIC_PACKAGE_CONTAINMENT_INVALID")
                    view["_bindings"][meta] = _scope_digest(meta)
                    try:
                        obj = json.loads(meta.read_text(encoding="utf-8"))
                        identity = obj.get("strain_id") if isinstance(obj, dict) else None
                        if isinstance(identity, str) and privacy["effective_release"] != "PUBLIC":
                            view["_blocked"].add(identity)
                    except (ValueError, OSError):
                        if privacy["effective_release"] == "PUBLIC":
                            _scope_refuse("PUBLIC_PRIVACY_METADATA_UNREADABLE")
                        view["_blocked"].add(str(privacy["strain_id"]))
                        import warnings
                        warnings.warn("PRIVATE_PACKAGE_METADATA_UNREADABLE_EXCLUDED",
                                      RuntimeWarning, stacklevel=2)
            if package.parent.name != privacy["strain_id"]:
                view["_blocked"].add(package.parent.name)
            if privacy["effective_release"] != "PUBLIC":
                view["_blocked"].add(str(privacy["strain_id"]))
                continue
            sid = privacy["strain_id"]
            if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", sid):
                _scope_refuse("PUBLIC_IDENTITY_UNSAFE")
            if sid in admitted:
                _scope_refuse("PUBLIC_PACKAGE_IDENTITY_DUPLICATE")
            admitted[sid] = package
            authority[sid] = privacy["authority_sha256"]
        if strains is not None:
            if not strains or len(strains) != len(set(strains)) or any(s not in admitted for s in strains):
                _scope_refuse("PUBLIC_REQUESTED_IDENTITY_UNAVAILABLE")
            order = list(strains)
        else:
            order = sorted(admitted)
        if not order:
            _scope_refuse("PUBLIC_SCOPE_EMPTY")
        selected = set(order)
        view["_blocked"].update(set(admitted) - selected)
        view["_blocked"].difference_update(selected)
        for sid in order:
            package = admitted[sid]
            files = _scope_package_files(package)
            if verify_checksums(package):
                _scope_refuse("PUBLIC_PACKAGE_INTEGRITY_INVALID")
            view["_package_files"][package] = files
            for rel in files:
                path = package / rel
                view["_bindings"][path] = _scope_digest(path)
            man = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
            if not isinstance(man, dict) or man.get("strain_id") != sid or not isinstance(man.get("bgcs"), list):
                _scope_refuse("PUBLIC_PACKAGE_SCIENCE_INVALID")
            ids = []
            for bgc in man["bgcs"]:
                if not isinstance(bgc, dict):
                    _scope_refuse("PUBLIC_PACKAGE_SCIENCE_INVALID")
                if bgc.get("release") != "PUBLIC":
                    _scope_refuse("PUBLIC_PACKAGE_ROW_RELEASE_CONFLICT")
                if any(not isinstance(bgc.get(k), str) or not bgc[k] for k in ("bgc_id", "contig", "antismash_region")):
                    _scope_refuse("PUBLIC_BGC_IDENTITY_INVALID")
                if not isinstance(bgc.get("products"), list) or any(not isinstance(x, str) for x in bgc["products"]):
                    _scope_refuse("PUBLIC_PACKAGE_SCIENCE_INVALID")
                for k in ("start", "end"):
                    _scope_count(bgc.get(k))
                if bgc["start"] > bgc["end"]:
                    _scope_refuse("PUBLIC_PACKAGE_SCIENCE_INVALID")
                ids.append(bgc["bgc_id"])
            if len(ids) != len(set(ids)):
                _scope_refuse("PUBLIC_BGC_IDENTITY_DUPLICATE")
            manifests[sid] = man
            view["_packages"][sid] = package
        view["_manifests"] = manifests
        guard_workbook_size(master)
        wb = load_workbook(master, read_only=True, data_only=False)
        try:
            a2 = _scope_rows(wb, "A2_Strain_Registry", (*_A2_REQUIRED, "workflow_version", "bgc_count"), selected)
            a3 = _scope_rows(wb, "A3_Run_Manifest", ("strain", "version"), selected)
            b1 = _scope_rows(wb, "B1_BGC_Master", (*_B1_REQUIRED, "contig", "region", "BGC_ID", "assembly_locator", "engine_version"), selected)
            classes = tuple(c for c in CANONICAL_V1_HEADERS["B2_Product_Class_Matrix"]
                            if c not in ("strain", "label_provenance", "counts_reliability"))
            b2 = _scope_rows(wb, "B2_Product_Class_Matrix", ("strain", "label_provenance", *classes), selected)
        finally:
            wb.close()
        gate = _load_version_gate()
        if gate is None:
            _scope_refuse("PUBLIC_ENGINE_GATE_UNAVAILABLE")
        versions = {}
        for sid in order:
            man = manifests[sid]
            ar = [x for x in a2 if x["strain"] == sid]
            vr = [x for x in a3 if x["strain"] == sid]
            matrix = [x for x in b2 if x["strain"] == sid and x["label_provenance"] == class_view]
            if len(ar) != 1 or len(vr) != 1 or len(matrix) != 1:
                _scope_refuse("PUBLIC_MASTER_IDENTITY_CARDINALITY_INVALID")
            ar, vr, matrix = ar[0], vr[0], matrix[0]
            if (_scope_text(ar["taxonomy"]) != _scope_text(man.get("taxonomy"))
                    or _scope_text(ar["ecology_source"]) != _scope_text(man.get("source"))
                    or _scope_count(ar["bgc_count"]) != len(man["bgcs"])):
                _scope_refuse("PUBLIC_MASTER_REGISTRY_CONFLICT")
            stamps = [vr["version"], ar["workflow_version"], man.get("workflow_version")]
            rows = [x for x in b1 if x["strain"] == sid]
            expected = {b["bgc_id"]: b for b in man["bgcs"]}
            if len(rows) != len(expected) or len({x["BGC_ID"] for x in rows}) != len(rows):
                _scope_refuse("PUBLIC_MASTER_BGC_MEMBERSHIP_CONFLICT")
            backed = _scope_gene_backing(man) if class_view == "GENE_BACKED" else set()
            all_labels = []
            for row in rows:
                bgc = expected.get(row["BGC_ID"])
                if bgc is None:
                    _scope_refuse("PUBLIC_MASTER_BGC_MEMBERSHIP_CONFLICT")
                if (row["contig"] != (bgc.get("node_id") or bgc["contig"])
                        or row["region"] != bgc["antismash_region"]
                        or row["assembly_locator"] != assembly_locator(bgc)
                        or _scope_text(row["products"]) != "; ".join(bgc["products"])
                        or _scope_text(row["kcb_top"]) != _scope_text(bgc.get("kcb_top"))):
                    _scope_refuse("PUBLIC_MASTER_BGC_VALUE_CONFLICT")
                stamps.append(row["engine_version"])
                labels = with_family_labels(bgc["products"])
                raw_counts = _b2_product_class_counts(labels)
                all_labels.extend(labels)
                members = {c for c in classes if raw_counts.get(c, 0) > 0}
                if class_view == "GENE_BACKED":
                    members.discard("carotenoid")
                    if bgc["bgc_id"] in backed:
                        members.add("carotenoid")
                view["bgcs"].append({"strain": sid, "bgc_id": bgc["bgc_id"], "classes": sorted(members),
                    "host_group": _host_group(ar["ecology_source"]), "genus": _genus_from_taxonomy(ar["taxonomy"]),
                    "fully_dark": _is_fully_dark(row["kcb_top"]), "dark_or_unresolved": _is_dark_or_unresolved(row["kcb_top"])})
            counts = _b2_product_class_counts(all_labels)
            if class_view == "GENE_BACKED":
                counts["carotenoid"] = len(backed)
            if any(_scope_count(matrix[c]) != counts.get(c, 0) for c in classes):
                _scope_refuse("PUBLIC_MASTER_CLASS_VIEW_CONFLICT")
            parsed = [gate.parse_engine_version(_scope_text(v)) for v in stamps]
            if None in parsed or len(set(parsed)) != 1:
                _scope_refuse("PUBLIC_ENGINE_PROVENANCE_CONFLICT")
            versions[sid] = stamps[0]
            view["registry"][sid] = {"genus": _genus_from_taxonomy(ar["taxonomy"]), "host_group": _host_group(ar["ecology_source"]), "classes": {c for c in classes if counts.get(c, 0) > 0}}
        engine = gate.parse_engine_version(versions[order[0]])
        try:
            gate.assert_uniform_scoring_engine(versions, engine)
        except Exception:
            _scope_refuse("PUBLIC_ENGINE_MIXED_OR_MISSING")
        view["N"] = len(order)
        for c in classes:
            ns = sum(c in row["classes"] for row in view["registry"].values())
            if ns:
                frac = ns / view["N"]
                view["prevalence"][c] = {"n_strains": ns, "informative": 1 <= ns < view["N"],
                    "band": "ubiquitous" if ns == view["N"] else "common" if frac >= .5 else "occasional" if frac >= .2 else "rare"}
        if not view["bgcs"]:
            _scope_refuse("PUBLIC_SCOPE_NO_BGCS")
        view["strains"] = order
        view["receipt"] = {"schema_version": PUBLIC_SCOPE_VERSION, "class_view": class_view,
            "strains": order, "strain_denominator": len(order), "bgc_denominator": len(view["bgcs"]),
            "engine_version": engine, "master_sha256": view["_bindings"][master],
            "profile_sha256": pdigest, "authority_sha256": {sid: authority[sid] for sid in order},
            "package_inputs": {sid: {rel: view["_bindings"][admitted[sid] / rel]
                                     for rel in view["_package_files"][admitted[sid]]} for sid in order}}
        # Do not publish filenames within packages: those may themselves contain local/private labels.
        view["receipt"]["package_inputs"] = {sid: sorted(files.values()) for sid, files in view["receipt"]["package_inputs"].items()}
        recheck_public_scope(view)
        return view
    except PublicCohortScopeError:
        raise
    except Exception:
        _scope_refuse("PUBLIC_SCOPE_INPUT_INVALID")


def check_public_scope_text(view, text, *, relative_path="", digest=""):
    """Fail closed for held identities and configured content-only policy literals."""
    import hashlib
    # Exact identifier token boundaries avoid promoting a folder/prefix naming rule into authority.
    for identity in view["_blocked"]:
        if identity and re.search(r"(?<![A-Za-z0-9])" + re.escape(identity) + r"(?![A-Za-z0-9])", text):
            _scope_refuse("PUBLIC_SCOPE_HELD_IDENTIFIER_IN_CONTENT")
    policy = view["_policy"]
    actual = digest or hashlib.sha256(text.encode("utf-8")).hexdigest()
    for ident in policy.private_identifiers:
        if ident.literal not in text:
            continue
        allowed = any(a.identifier_id == ident.identifier_id and a.relative_path == relative_path
                      and a.sha256 == actual and a.purpose == "CONTENT_ONLY_EXCEPTION" and a.state == "ACTIVE"
                      for a in policy.allowlisted_occurrences)
        if not allowed:
            _scope_refuse("PUBLIC_SCOPE_PRIVATE_LITERAL_IN_CONTENT")


def render_public_synthesis(view, novelty_basis):
    """Render only an independently loaded view; all summaries are subset-derived."""
    if novelty_basis not in ("fully_dark", "dark_or_unresolved"):
        _scope_refuse("PUBLIC_NOVELTY_BASIS_INVALID")
    reg, bgcs, prev, n = view["registry"], view["bgcs"], view["prevalence"], view["N"]
    total = len(bgcs)
    alt = "dark_or_unresolved" if novelty_basis == "fully_dark" else "fully_dark"
    genera, hosts = Counter(x["genus"] or "Unresolved" for x in reg.values()), Counter(x["host_group"] for x in reg.values())
    lines = ["# Cross-Strain Biosynthetic Synthesis (public subset)", "",
             f"**Cohort:** {n} strains · {total} BGCs · {len(genera)} genera · {len(hosts)} host groups",
             f"**Class view:** `{view['class_view']}` · projection `{PUBLIC_SCOPE_VERSION}`",
             f"**Novelty basis:** `{novelty_basis}`; alternate `{alt}` is reported separately.",
             "**Source:** independently release-admitted package identities joined to selected master rows. Capacity-level; KCB = similarity, not identity.", "",
             "Class prevalence counts distinct admitted strains; class occurrence summaries count each admitted BGC once per selected class. No mixed-cohort aggregate or fit is reused.", "",
             "## 1. Cohort composition",
             f"{n} strains; genera: " + ", ".join(f"{g} ×{v}" for g, v in sorted(genera.items())) + ".",
             "Host groups: " + ", ".join(f"{h} ×{v}" for h, v in sorted(hosts.items())) + ".", "",
             "## 2. Capacity prevalence (selected class view)", "| Class | Strains | Band |", "|---|---:|---|"]
    for c, record in sorted(prev.items()):
        lines.append(f"| {c} | {record['n_strains']}/{n} | {record['band']} |")
    lines += ["", "## 3. Host-associated class occurrences"]
    host_class = defaultdict(Counter)
    for b in bgcs:
        for c in b["classes"]:
            if prev[c]["informative"]:
                host_class[c][b["host_group"]] += 1
    biased = []
    for c, counts in sorted(host_class.items()):
        denom = sum(counts.values())
        top, num = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0]
        if denom >= 4 and num / denom >= .55:
            biased.append((c, top, num, denom))
    lines += ([f"- {c}: {top}, {num}/{denom} BGCs ({num/denom:.0%})." for c, top, num, denom in biased]
              or ["No class exceeded the 55% display threshold at n≥4 BGCs in this subset."])
    lines += ["", f"## 4. Reference-dark fractions (basis: `{novelty_basis}`)",
              f"`{novelty_basis}`: {sum(b[novelty_basis] for b in bgcs)}/{total} ({sum(b[novelty_basis] for b in bgcs)/total:.1%}); "
              f"`{alt}`: {sum(b[alt] for b in bgcs)}/{total} ({sum(b[alt] for b in bgcs)/total:.1%}).",
              "", "| Host group | Dark % | n BGCs |", "|---|---:|---:|"]
    for host, (pct, count) in sorted(novelty_by_host(bgcs, novelty_basis).items()):
        lines.append(f"| {host} | {pct:.1f}% | {count} |")
    lines += ["", "## 5. Classes unique within this public subset"]
    unique = differentiating_capacities(prev)
    lines.append(f"{len(unique)} classes carried by exactly one admitted strain after the standing display exclusions.")
    for c in unique:
        carrier = next(sid for sid in view["strains"] if c in reg[sid]["classes"])
        lines.append(f"- {c} → {carrier} ({reg[carrier]['genus'] or 'Unresolved'}, {reg[carrier]['host_group']}).")
    lines += ["", "## 6. Genus class occurrences"]
    gc = defaultdict(Counter)
    for b in bgcs:
        for c in b["classes"]:
            if c not in _GENUS_UBIQ:
                gc[b["genus"] or "Unresolved"][c] += 1
    for genus_, counts in sorted(gc.items()):
        lines.append(f"- {genus_}: " + ", ".join(f"{c} ({v})" for c, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:4]) + ".")
    if not gc:
        lines.append("No selected class remained after the standing genus-display exclusions.")
    lines += ["", "Counts describe only the admitted public subset and selected saved-evidence label view; they do not establish product identity or biological activity."]
    text = "\n".join(lines) + "\n"
    check_public_scope_text(view, text, relative_path="CROSS_STRAIN_SYNTHESIS.md")
    return text


def write_synthesis(master_path: str | Path, novelty_basis: str = "fully_dark",
                    host_overrides: dict | None = None,
                    meta_overrides: dict | None = None, *, public_only=False,
                    runs_dir=None, privacy_profile=None, strains=None, class_view=None) -> str:
    """Emit the cross-strain synthesis markdown. Raises on a stale/unverified master."""
    if public_only:
        if host_overrides or meta_overrides:
            _scope_refuse("PUBLIC_METADATA_OVERRIDE_UNBOUND")
        view = load_public_master(master_path, runs_dir=runs_dir,
                                 privacy_profile=privacy_profile, strains=strains, class_view=class_view)
        text = render_public_synthesis(view, novelty_basis)
        recheck_public_scope(view)
        return text
    if novelty_basis not in ("fully_dark", "dark_or_unresolved"):
        raise ValueError(f"novelty_basis must be 'fully_dark' or 'dark_or_unresolved', got {novelty_basis!r}")
    M = load_master(master_path, host_overrides, meta_overrides)
    if not M:
        raise RuntimeError(f"master {master_path} is missing required sheets or is stale; refusing to write")
    reg, N, prev, bgcs = M["registry"], M["N"], M["prevalence"], M["bgcs"]
    total_bgc = len(bgcs)
    # v9.7.117 (Bug Hunt): a master whose required sheets are present but B1_BGC_Master is empty
    # (header-only scaffold) passes the load_master sheet check but would ZeroDivisionError on the
    # novelty-fraction math. Refuse cleanly, same contract as the stale-master refusal above.
    if total_bgc == 0:
        raise RuntimeError(f"master {master_path} has an empty B1_BGC_Master (0 BGCs); "
                           "refusing to write a synthesis with no cohort data")

    # novelty under BOTH bases, headline = chosen
    nov_chosen = novelty_by_host(bgcs, novelty_basis)
    other_basis = "dark_or_unresolved" if novelty_basis == "fully_dark" else "fully_dark"
    chosen_total = sum(b[novelty_basis] for b in bgcs)
    other_total = sum(b[other_basis] for b in bgcs)

    genera = Counter(v["genus"] for v in reg.values())
    hosts = Counter(v["host_group"] for v in reg.values())
    diff_caps = differentiating_capacities(prev)

    L = []
    L.append("# Cross-Strain Biosynthetic Synthesis (auto-generated)")
    L.append("")
    L.append(f"**Cohort:** {N} strains · {total_bgc} BGCs · {len(genera)} genera · {len(hosts)} host groups  ")
    L.append(f"**Novelty basis:** `{novelty_basis}` "
             f"({'no MIBiG anchor at all' if novelty_basis=='fully_dark' else 'no MIBiG accession incl. unresolved genome-ref hits'})  ")
    L.append("**Source:** verified cohort master · capacity-level (KCB = similarity, not identity) · "
             "bioactivity extract-level · PRIVATE (unpublished AS strains)")
    L.append("")
    L.append("All numbers trace to named master sheets. Every reference-dark number is tagged with its "
             "basis; the alternate definition is reported alongside so the two are never conflated.")
    L.append("")

    # 1. composition
    L.append("## 1. Cohort composition")
    L.append(f"{N} strains across {len(genera)} genera "
             f"({', '.join(f'{g} ×{n}' for g, n in genera.most_common(5))}…) and {len(hosts)} host "
             f"groups ({', '.join(f'{h} ×{n}' for h, n in hosts.most_common())}). "
             f"{total_bgc} BGCs detected. [A2_Strain_Registry, B1_BGC_Master]")
    L.append("")

    # 2. convergent iron
    sider = prev.get("NI-siderophore", {}).get("n_strains", 0)
    metal = prev.get("NRP-metallophore", {}).get("n_strains", 0)
    L.append("## 2. Convergent capacities (down-weighted as differentiators)")
    L.append(f"Iron acquisition is near-universal: NI-siderophore in {sider}/{N} strains, "
             f"NRP-metallophore in {metal}/{N}. Per the standing exclusion rule these are treated as "
             f"convergent cohort-ubiquitous capacities, not differentiating signals — the convergence "
             f"itself is the finding. [Cross_Strain_Class_Prevalence]")
    L.append("")

    # 3. host-biased
    L.append("## 3. Host-biased capacities")
    host_class = defaultdict(Counter)
    for b in bgcs:
        for c in re.split(r"[;,]", b["products"]):
            c = c.strip()
            if c and c in prev and prev[c]["informative"]:
                host_class[c][b["host_group"]] += 1
    biased = []
    for c, dist in host_class.items():
        tot = sum(dist.values())
        if tot < 4:
            continue
        top, n = dist.most_common(1)[0]
        # COH-05: no host allowlist. The old `and top in ("Bombus", "Attine")` made
        # Apis/Wasp/Moss/Other-Apidae host-specialization structurally unreportable. The
        # 55%-of-≥4-BGCs threshold already guards significance for ANY host group.
        if n / tot >= 0.55:
            biased.append((c, top, n, tot))
    if biased:
        for c, top, n, tot in sorted(biased, key=lambda x: -x[3])[:8]:
            L.append(f"- **{c}** — {n/tot:.0%} {top}-associated ({n}/{tot} BGCs)")
    else:
        L.append("- (No class exceeded the 55% host-bias threshold at n≥4.)")
    L.append("")

    # 4. novelty gradient (THE basis-tagged section)
    L.append(f"## 4. Novelty gradient by host (basis: `{novelty_basis}`)")
    L.append(f"Cohort reference-dark total: **{chosen_total}/{total_bgc} "
             f"({chosen_total/total_bgc*100:.0f}%)** under `{novelty_basis}`; "
             f"for comparison, `{other_basis}` gives {other_total}/{total_bgc} "
             f"({other_total/total_bgc*100:.0f}%). The two are different metrics — do not mix.")
    L.append("")
    L.append("| Host group | dark % | n BGCs |")
    L.append("|---|---|---|")
    for hg, (pct, n) in sorted(nov_chosen.items(), key=lambda x: x[1][0]):
        L.append(f"| {hg} | {pct:.1f}% | {n} |")
    L.append("")

    # 5. differentiating capacities
    L.append("## 5. Cohort-unique differentiating capacities")
    L.append(f"{len(diff_caps)} classes carried by exactly one strain — the discovery-frontier leads:")
    L.append("")
    for c in diff_caps:
        # token-split match (not bare substring) so "lanthipeptide" does not
        # false-match "class-i-lanthipeptide"; mirrors the split used in §3 and §6.
        carrier = next(
            (b["strain"] for b in bgcs
             if c in [t.strip() for t in re.split(r"[;,]", b["products"])]),
            "?")
        L.append(f"- **{c}** → {carrier} (*{reg.get(carrier, {}).get('genus','')}*, "
                 f"{reg.get(carrier, {}).get('host_group','')})")
    L.append("")

    # 6. genus signatures
    L.append("## 6. Genus signatures")
    genus_class = defaultdict(Counter)
    UBIQ = _GENUS_UBIQ
    _UNRESOLVED_GENUS = {"", "not", "not verified", "none", "—", "unresolved"}
    for b in bgcs:
        for c in re.split(r"[;,]", b["products"]):
            c = c.strip()
            if c and c not in UBIQ:
                genus_class[b["genus"]][c] += 1
    resolved = [g for g in sorted(genus_class) if str(g).strip().lower() not in _UNRESOLVED_GENUS]
    n_unresolved = sum(1 for g in genus_class if str(g).strip().lower() in _UNRESOLVED_GENUS)
    if resolved:
        for genus in resolved:
            top = [(c, n) for c, n in genus_class[genus].most_common(4)]
            if top:
                L.append(f"- **{genus}**: {', '.join(f'{c} ({n})' for c, n in top)}")
        if n_unresolved:
            L.append(f"- *(Strains without a genus assignment are omitted; genus signatures cover "
                     f"only the taxonomy-assigned subset. Provide genus for all {N} strains to "
                     f"complete this section.)*")
    else:
        L.append("*Genus is not populated for any strain in this master (registry taxonomy empty "
                 "and no override supplied); per-genus signatures require strain genus assignments.*")
    L.append("")
    L.append("---")
    L.append(f"*Auto-generated from the verified cohort master. novelty_basis=`{novelty_basis}`. "
             f"Capacity-level; KCB = similarity not identity; bioactivity extract-level.*")
    return "\n".join(L)


def load_from_capacity_csv(csv_path):
    """Load cohort data from a CCSM capacity-integration CSV (no master workbook required).

    Schema: strain, genus, host, host_group, total_bgcs_raw, deeply_carded, pct_carded,
    analytical_depth, n_xstrain_flags, [class_flag_cols...]. Returns a minimal M dict
    compatible with write_synthesis_from_capacity_csv. This is the no-workbook path.
    """
    import csv as _csv
    with open(Path(csv_path), encoding="utf-8", newline="") as _fh:
        rows = list(_csv.DictReader(_fh))
    if not rows:
        return {}
    if "strain" not in rows[0]:
        raise ValueError(
            f"capacity CSV {csv_path!r} is missing a required 'strain' column; "
            f"found columns: {list(rows[0].keys())}")
    meta_cols = {"strain", "genus", "host", "host_group", "total_bgcs_raw",
                 "deeply_carded", "pct_carded", "analytical_depth", "n_xstrain_flags"}
    class_cols = [k for k in rows[0].keys() if k not in meta_cols]
    reg = {}
    class_by_strain = {}
    for r in rows:
        sid = r["strain"]
        reg[sid] = {
            "genus": r.get("genus", ""),
            "host": r.get("host", ""),
            "host_group": r.get("host_group") or _host_group(r.get("host", "")),
        }
        class_by_strain[sid] = {c: int(r.get(c, 0) or 0) for c in class_cols}
    N = len(reg)
    prevalence = {}
    for c in class_cols:
        n = sum(class_by_strain[s].get(c, 0) for s in class_by_strain)
        prevalence[c] = {"n_strains": n, "informative": n > 0 and n < N}
    return {"registry": reg, "N": N, "prevalence": prevalence,
            "class_by_strain": class_by_strain, "class_cols": class_cols}


def write_synthesis_from_capacity_csv(csv_path):
    """Emit a cross-strain synthesis from the capacity integration CSV (no master required).

    Covers cohort composition, class landscape, cohort-unique capacities, genus signatures.
    Does NOT cover the novelty gradient (requires B1_BGC_Master) — states the absence explicitly.
    """
    M = load_from_capacity_csv(csv_path)
    if not M:
        raise RuntimeError(f"Could not load capacity CSV from {csv_path}")
    reg = M["registry"]; N = M["N"]; prev = M["prevalence"]
    class_by_strain = M["class_by_strain"]; class_cols = M["class_cols"]
    from collections import Counter as _Counter
    genera = _Counter(v["genus"] for v in reg.values())
    hosts = _Counter(v["host_group"] for v in reg.values())
    L = []
    L.append("# Cross-Strain Capacity Synthesis (from capacity CSV)")
    L.append("")
    L.append(f"**Cohort:** {N} strains \u00b7 {len(genera)} genera \u00b7 {len(hosts)} host groups  ")
    L.append("**Source:** CCSM capacity integration CSV \u00b7 class presence flags (not corrected BGC counts)  ")
    L.append("**Note:** Novelty gradient (KCB-dark %) requires the master workbook B1_BGC_Master sheet \u2014 absent here.  ")
    L.append("**PRIVATE** \u2014 unpublished AS strains \u00b7 capacity-level throughout")
    L.append("")
    L.append("## 1. Cohort composition")
    L.append(f"{N} strains \u00b7 {len(genera)} genera: "
             f"{', '.join(f'*{g}* \u00d7{n}' for g, n in genera.most_common(6))}\u2026  ")
    L.append(f"Host groups: {', '.join(f'{h} n={n}' for h, n in hosts.most_common())}")
    L.append("")
    L.append("## 2. Class landscape (strain-presence counts)")
    L.append("")
    # FIG-02: derive host-group columns from the data (preferred order first, then any others
    # sorted) so host groups outside the hardcoded list are no longer silently dropped.
    _pref = ["Bombus", "Attine", "Wasp", "Apis", "Other Apidae", "Moss"]
    _seen = {reg[s]["host_group"] for s in class_by_strain}
    hg_order = [h for h in _pref if h in _seen] + sorted(_seen - set(_pref))
    L.append("| Class | n/" + str(N) + " | " + " | ".join(hg_order) + " |")
    L.append("|" + "|".join(["---"] * (len(hg_order) + 2)) + "|")
    for c in sorted(class_cols, key=lambda x: -prev[x]["n_strains"]):
        n = prev[c]["n_strains"]
        if n == 0:
            continue
        by_hg = _Counter()
        for s, flags in class_by_strain.items():
            if flags.get(c, 0):
                by_hg[reg[s]["host_group"]] += 1
        cells = [str(by_hg.get(hg, 0)) if by_hg.get(hg, 0) else "\u00b7" for hg in hg_order]
        L.append(f"| {c} | {n}/{N} | {' | '.join(cells)} |")
    L.append("")
    L.append("## 3. Cohort-unique capacities (n=1 strains)")
    unique = [(c, p["n_strains"]) for c, p in prev.items() if p["n_strains"] == 1]
    if unique:
        for c, _ in sorted(unique):
            carrier = next((s for s, f in class_by_strain.items() if f.get(c, 0)), "?")
            g = reg.get(carrier, {}).get("genus", "?")
            hg = reg.get(carrier, {}).get("host_group", "?")
            L.append(f"- **{c}** \u2192 {carrier} (*{g}*, {hg})")
    else:
        L.append("- (No class present in exactly 1 strain.)")
    L.append("")
    L.append("## 4. Genus signatures")
    genus_class = defaultdict(list)
    for s, flags in class_by_strain.items():
        g = reg.get(s, {}).get("genus", "?")
        if g and g.strip().lower() not in ("", "?", "not", "none"):
            for c, v in flags.items():
                if v:
                    genus_class[g].append(c)
    for g in sorted(genus_class):
        classes = sorted(set(genus_class[g]))
        L.append(f"- **{g}** (n={genera.get(g,0)} strains): {', '.join(classes)}")
    L.append("")
    L.append("---")
    L.append("*Auto-generated from CCSM capacity integration CSV. Class flags derived from "
             "strain-specific BGC descriptions. Claim-safe throughout.*")
    return "\n".join(L)


def main(argv=None):
    """CLI: emit the cross-strain synthesis. Genus/host are sourced from --differentiating when the
    master registry lacks taxonomy."""
    import argparse
    ap = argparse.ArgumentParser(description="Deterministic cross-strain synthesis writer (Gap 3).")
    ap.add_argument("--master", default=None,
                    help="Verified cohort master workbook (xlsx). Required unless --capacity-csv.")
    ap.add_argument("--capacity-csv", default=None,
                    help="CCSM capacity integration CSV (no-workbook path). Use when the private "
                         "master is unavailable. Novelty gradient section will be absent.")
    ap.add_argument("--differentiating", default=None,
                    help="differentiating-capacities CSV (supplies genus/host when the master "
                         "registry taxonomy columns are unpopulated). Ignored with --capacity-csv.")
    ap.add_argument("--novelty-basis", default="fully_dark",
                    choices=["fully_dark", "dark_or_unresolved"],
                    help="KCB-dark definition for headline novelty numbers (default fully_dark = "
                         "canonical 164/1131 floor); the alternate basis is always reported alongside. "
                         "Ignored with --capacity-csv.")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.capacity_csv:
        md = write_synthesis_from_capacity_csv(a.capacity_csv)
    elif a.master:
        meta = meta_from_differentiating_csv(a.differentiating) if a.differentiating else None
        md = write_synthesis(a.master, novelty_basis=a.novelty_basis, meta_overrides=meta)
    else:
        import sys as _sys
        emit("error: one of --master or --capacity-csv is required", file=_sys.stderr)
        return 2
    _atomic_write_text(Path(a.out), md)
    emit(f"wrote cohort synthesis -> {a.out} ({len(md)} chars)")
    return 0


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated cohort-level deliverable (the cross-strain synthesis markdown) on disk."""
    import os
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))


if __name__ == "__main__":
    raise SystemExit(main())
