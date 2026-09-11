"""gene_by_gene.py — per-gene table for top Mode B leads (v9.7.81).

Generates <strain>_gene_by_gene_top_leads.csv and .xlsx from the sealed Mamey
package. One row per CDS within each top-N BGC, columns:

  bgc_id, rank, locus_tag, contig, start, end, strand, length_bp, aa_length,
  product_qualifier, gene_function_inference, sec_met_domains,
  run_depth_mode, cctt_triggers, bldA_tta_codon, resistance_tier,
  boundary_flag, edge_core_overlap, rggmci_adjacency_context,
  source_gbk, source_line_locator

For fragmented assemblies: edge/core-overlap flags and RG-GMCI adjacency.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any
from .ziputil import regular_file_names
from .xlsx_determinism import canonicalize_xlsx
from .crosswalk import assembly_locator as _assembly_locator  # v9.7.409: per-row provenance anchor

# v9.7.409 (DEEP_AUDIT2_resource_dos #2): antiSMASH-derived /product and /translation qualifiers flow
# uncapped from parse -> gene-by-gene CSV -> Mode-B markdown -> widget JSON; bound every such display
# value with an explicit [truncated] marker. Env-overridable via MAMEY_QUALIFIER_MAX_CHARS.
_QUALIFIER_MAX_CHARS = 20_000


def _cap_qualifier(value: object, max_chars: int = _QUALIFIER_MAX_CHARS) -> str:
    """Bound an antiSMASH-derived qualifier for display/export (see note above)."""
    text = "" if value is None else str(value)
    try:
        cap = int(os.environ.get("MAMEY_QUALIFIER_MAX_CHARS", str(max_chars)))
    except (TypeError, ValueError):
        cap = max_chars
    if len(text) > cap:
        return text[:cap] + f" …[truncated {len(text) - cap} of {len(text)} chars]"
    return text
from .xlsx_determinism import save_workbook_safely as _save_wb_safely

# Optional openpyxl for XLSX output
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    _HAS_XLSX = True
except ImportError:
    _HAS_XLSX = False


# ---------------------------------------------------------------------------
# GBK CDS parser (minimal; no Biopython required)
# ---------------------------------------------------------------------------

def _parse_cds_from_gbk(gbk_text: str, gbk_name: str) -> list[dict]:
    """Parse CDS features from a GenBank flat-file string.

    Returns list of dicts with: locus_tag, start, end, strand, product,
    translation_length, sec_met_domains, tta_codons, source_line.
    """
    records: list[dict] = []
    lines = gbk_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Feature block start: "     CDS             <coords>"
        if re.match(r"\s{5}CDS\s+", line):
            cds_start_line = i + 1
            feat: dict[str, Any] = {
                "locus_tag": "",
                "start": None,
                "end": None,
                "strand": "+",
                "product": "",
                "translation_length": None,
                "sec_met_domains": [],
                "gene_kind": "",
                "tta_codons": 0,
                "source_line": f"{gbk_name}:{cds_start_line}",
            }
            # Parse coordinates from the CDS line
            coord_str = line.strip().replace("CDS", "").strip()
            # Handle multi-line coordinates (complement, join, etc.)
            j = i + 1
            while j < len(lines) and lines[j].startswith(" " * 21) and not lines[j].strip().startswith("/"):
                coord_str += lines[j].strip()
                j += 1
            if "complement" in coord_str:
                feat["strand"] = "-"
            nums = re.findall(r"\d+", coord_str)
            if len(nums) >= 2:
                feat["start"] = int(nums[0])
                feat["end"] = int(nums[-1])
            elif len(nums) == 1:
                feat["start"] = feat["end"] = int(nums[0])

            # Parse qualifiers
            k = j
            while k < len(lines):
                qline = lines[k]
                if re.match(r"\s{5}\w", qline) and not qline.strip().startswith("/"):
                    break  # next feature
                if qline.strip().startswith("/locus_tag="):
                    feat["locus_tag"] = qline.strip().split("=", 1)[1].strip('"')
                elif qline.strip().startswith("/product="):
                    feat["product"] = qline.strip().split("=", 1)[1].strip('"')
                elif qline.strip().startswith("/translation="):
                    # Count amino acids in translation
                    trans = qline.strip().split("=", 1)[1].strip('"')
                    m = k + 1
                    while m < len(lines) and lines[m].startswith(" " * 21):
                        trans += lines[m].strip().strip('"')
                        m += 1
                    feat["translation_length"] = len(re.sub(r"[^A-Za-z]", "", trans))
                elif qline.strip().startswith("/sec_met_domain="):
                    dom = qline.strip().split("=", 1)[1].strip('"')
                    feat["sec_met_domains"].append(dom.split(" ")[0])  # just the domain name
                elif qline.strip().startswith("/gene_kind="):
                    # v9.7.374 AUDIT: antiSMASH's own core/non-core call for this CDS
                    # ("biosynthetic" = rule-based core gene; "biosynthetic-additional" /
                    # "transport" / "regulatory" / "other" = not core). Parsed but previously
                    # discarded; _infer_role() below now uses it as an authoritative fallback
                    # so a true core gene the keyword heuristic doesn't recognize (RiPP-class
                    # core domains in particular -- see _infer_role) is never mislabeled as
                    # "biosynthetic context".
                    feat["gene_kind"] = qline.strip().split("=", 1)[1].strip('"')
                k += 1

            # TTA codon count (rough: count TTA in coding sequence lines isn't available
            # without the translation — estimate from product/domain context)
            # We mark TTA presence from the sec_met qualifiers if available; full codon
            # scanning requires the DNA sequence which is not reliably in the feature section.
            # Leave tta_codons=0; upstream per-BGC TTA data from the manifest is authoritative.

            if feat["start"] is not None and feat["end"] is not None:
                if feat["end"] > feat["start"]:
                    feat["length_bp"] = feat["end"] - feat["start"] + 1  # GenBank coords are 1-based inclusive
                else:
                    feat["length_bp"] = 0
                records.append(feat)
            i = k
        else:
            i += 1
    return records


# ---------------------------------------------------------------------------
# Role inference heuristic
# ---------------------------------------------------------------------------

_ROLE_PATTERNS = [
    (r"\bketosynthase\b|\bKS\b|\bcondensation\b|\bC domain\b|\badenylation\b|\bA domain\b|\bthiolation\b|\bT domain\b|"
     r"\bacyl.carrier\b|\benoylreductase\b|\bdehydratase\b|\bmethyltransferase\b|\bAT domain\b",
     "core biosynthetic"),
    (r"\bhalogenase\b|\bchlorinase\b|\bbrominase\b|\bflavin.dependent oxygenase\b", "halogenation"),
    (r"\bglycosyltransferase\b|\bglycoside hydrolase\b|\bsugar synthase\b", "glycosylation / sugar"),
    (r"\bthioesterase\b|\bTE domain\b|\brelease\b", "chain release / TE"),
    (r"\bresistance\b|\befflux\b|\bMFS\b|\bABC transporter\b|\bRND transporter\b", "self-resistance / export"),
    (r"\bregulator\b|\brepressor\b|\bactivator\b|\bLuxR\b|\bSARP\b|\bAraC\b|\bTetR\b|\bsigma\b", "regulation"),
    (r"\bprotease\b|\bpeptidase\b|\bsubtilisin\b|\bLanP\b", "maturation / proteolysis"),
    (r"\bphosphatase\b|\bkinase\b|\bisomerase\b|\bepimerase\b", "tailoring / modification"),
    (r"\bhypothetical\b|\bunknown\b|\bputative\b", "unknown"),
]


def _infer_role(product: str, domains: list[str], gene_kind: str = "") -> str:
    combined = (product + " " + " ".join(domains)).lower()
    for pattern, role in _ROLE_PATTERNS:
        if re.search(pattern, combined, re.I):
            return role
    # v9.7.374 AUDIT (audit: AS-XXX runtime deep audit): _ROLE_PATTERNS above is
    # PKS/NRPS-vocabulary-biased (ketosynthase, condensation, adenylation, acyl-carrier,
    # enoylreductase, dehydratase, AT domain, ...) with no RiPP-core patterns -- no match for
    # Asn_synthase or PF13471/Transglut_core3 (the lasso-peptide cyclase domain antiSMASH's own
    # detection rule requires), nor for YcaO/PqqD/Lant_dehydr/LANC_like (lanthipeptide/RiPP
    # maturation domains). Confirmed live: AS-XXX BGC001's proto_core CDS ctg101_14
    # (sec_met_domain=Asn_synthase) and ctg101_15 (sec_met_domain=PF13471), both antiSMASH
    # /gene_kind="biosynthetic" (rule-based core), matched no pattern above and silently fell to
    # "biosynthetic context" -- read by authored_verify.py's n_core_genes (feeds the §4 BLASTp
    # coverage gate denominator), bgc_guide.py, modeb_template_emitter.py's per-BGC core-gene
    # count, and domain_figures.py's core-vs-accessory figure. Defer to antiSMASH's own call
    # before defaulting to "context" so an unrecognized-by-keyword core gene is never
    # mislabeled as non-core.
    if gene_kind == "biosynthetic":
        return "core biosynthetic"
    return "biosynthetic context"


# ---------------------------------------------------------------------------
# Edge/core overlap flag
# ---------------------------------------------------------------------------

def write_gene_count_crosscheck(package_dir: str | Path,
                                input_zip: str | Path | None = None,
                                outdir: str | Path | None = None) -> dict:
    """Seal-time INDEPENDENT CDS recount → `gene_count_crosscheck.json` (v9.7.191, AS-XXX hardening).

    Walks each BGC's region GBK directly with `_parse_cds_from_gbk` — a different code path than the
    gene-by-gene CSV writer — and records, per BGC: gbk_cds_count (total CDS), gbk_edge_cds_count
    (CDS the clipped GBK could legitimately drop, i.e. edge/full-contig-boundary), and gbk_source.
    `guide_quality_gate` reads this to catch upstream omission it otherwise can't see (the count and
    the omission check would otherwise both derive from the same CSV). Shares the region-GBK source
    with the CSV writer so a benign antiSMASH-version difference can't masquerade as omission.

    Region GBKs live in the antiSMASH INPUT ZIP (they are not copied into the sealed package), so
    this runs at seal time with `input_zip` in hand. Falls back to a package glob for the rare case
    where region GBKs were staged into the package.

    Returns {"path", "per_bgc", "antismash_version"}. Best-effort: a BGC with no loadable GBK is
    skipped with a note; never raises on a single-BGC parse failure.
    """
    import zipfile
    pdir = Path(package_dir)
    out = Path(outdir) if outdir else pdir
    manifest = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
    as_version = (manifest.get("provenance", {}) or {}).get("antismash_version") \
        or manifest.get("antismash_version")
    if not as_version and input_zip and Path(input_zip).exists():
        try:
            from .parsers import extract_antismash_version as _eav
            as_version = _eav(input_zip)
        except Exception:
            as_version = None
    as_version = as_version or "unknown"

    # Build a basename -> GBK-text resolver from the input zip (primary) and package glob (fallback).
    zip_gbk: dict[str, str] = {}
    if input_zip and Path(input_zip).exists():
        try:
            with zipfile.ZipFile(input_zip) as zf:
                for n in regular_file_names(zf):
                    if n.lower().endswith(".gbk"):
                        zip_gbk[Path(n).name] = zf.read(n).decode("utf-8", "replace")
        except Exception:
            pass  # fall through to package glob

    def _gbk_text(src_name: str) -> str | None:
        if src_name in zip_gbk:
            return zip_gbk[src_name]
        cand = list(pdir.glob(f"**/{src_name}"))
        if cand:
            try:
                return cand[0].read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    per_bgc: dict[str, dict] = {}
    for bgc in manifest.get("bgcs", []):
        bid = bgc.get("bgc_id")
        boundary = (bgc.get("edge_status") or bgc.get("boundary")
                    or bgc.get("Boundary") or "")
        src = bgc.get("source_gbk") or bgc.get("Source_GBK") or ""
        if not (bid and src):
            continue
        src_name = Path(src).name
        text = _gbk_text(src_name)
        if text is None:
            per_bgc[bid] = {"gbk_cds_count": None, "gbk_edge_cds_count": None,
                            "gbk_source": src_name, "note": "region GBK not found"}
            continue
        try:
            cds = _parse_cds_from_gbk(text, src_name)
        except Exception as exc:
            per_bgc[bid] = {"gbk_cds_count": None, "gbk_edge_cds_count": None,
                            "gbk_source": src_name, "note": f"parse failed: {type(exc).__name__}"}
            continue
        # edge-droppable = CDS in a non-Interior region (Edge / Full-contig). An Interior region
        # can drop nothing legitimately, so its edge count is 0 (any shortfall there is real omission).
        if boundary == "Interior":
            edge_droppable = 0
        else:
            edge_droppable = len(cds)  # whole partial region is droppable relative to the full assembly
        per_bgc[bid] = {"gbk_cds_count": len(cds),
                        "gbk_edge_cds_count": edge_droppable,
                        "gbk_source": Path(src).name,
                        "boundary": boundary}
    payload = {"schema": "gene-count-crosscheck-1.0",
               "antismash_version": as_version,
               "per_bgc": per_bgc}
    out.mkdir(parents=True, exist_ok=True)
    path = out / "gene_count_crosscheck.json"
    # v9.7.374 fix: was a bare path.write_text() -- an interrupted write leaves a truncated/corrupt
    # gene_count_crosscheck.json. Matches the established tmp+replace pattern used throughout this
    # codebase (mamey/packaging.py::_atomic_write_text, mamey/master_workbook.py's _save_wb_safely(wb, tmp)+
    # os.replace) for exactly this failure mode.
    _tmp = path.with_name(path.name + ".tmp")
    _tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _tmp.replace(path)
    return {"path": str(path), "per_bgc": per_bgc, "antismash_version": as_version}


def _edge_overlap_flag(boundary: str, bgc_start: int | None, bgc_end: int | None,
                        cds_start: int | None, cds_end: int | None,
                        contig_length: int | None) -> str:
    """Return edge/core overlap descriptor for a CDS within a BGC."""
    if boundary == "Interior":
        return "core"
    if boundary == "Full-contig":
        return "full-contig (truncated both ends)"
    if boundary == "Edge":
        if cds_start is None or bgc_start is None:
            return "edge (position unknown)"
        # Within 5 kb of the contig edge = edge-proximal
        edge_5 = cds_start < 5000
        edge_3 = contig_length and cds_end and (contig_length - cds_end) < 5000
        if edge_5 or edge_3:
            return "edge-proximal (within 5 kb of contig end)"
        return "edge (interior of partial cluster)"
    return boundary or "unknown"


# ---------------------------------------------------------------------------
# Main table builder
# ---------------------------------------------------------------------------

def build_gene_by_gene_table(
    package_dir: str | Path,
    top_n: int = 10,
    strain_id: str | None = None,
    outdir: str | Path | None = None,
    scope: str = "top_leads",
) -> dict:
    """Build the gene-by-gene table from a sealed Mamey package.

    scope="top_leads" (default): top_n lead BGCs only → <sid>_gene_by_gene_top_leads.csv
    scope="all_bgcs": every BGC (drops included, untruncated) → <sid>_gene_by_gene_all_bgcs.csv

    Returns dict with keys: csv_path, xlsx_path (or None), row_count, bgcs_covered, scope.
    """
    pdir = Path(package_dir)

    # Load manifest
    manifest = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
    # AUDIT_374 fix: manifest.json records strain_id at the flat top-level key
    # ("strain_id"), never under a nested "strain" object -- no writer in cli.py emits a
    # "strain" key into manifest.json. The old lookup (manifest["strain"]["strain_id"]) is
    # always empty on a real package, so this function silently fell straight through to
    # pdir.parent.name -- correct only by the accident of packaging.py's <outdir>/<strain>/
    # package layout, and silently WRONG whenever this function is called (as a library, with
    # no explicit strain_id) on a copied/relocated/renamed package directory. Try the real flat
    # key first; keep the old nested lookup as a harmless legacy fallback.
    sid = (strain_id or manifest.get("strain_id")
           or manifest.get("strain", {}).get("strain_id") or pdir.parent.name)
    bgcs_by_id = {b["bgc_id"]: b for b in manifest.get("bgcs", [])}
    tta_per_bgc = (manifest.get("source_scans", {})
                           .get("blda_tta", {}).get("per_bgc", {}))
    res_per_bgc = (manifest.get("source_scans", {})
                            .get("resistance_tiers", {}).get("per_bgc", {}))
    cctt_per_bgc: dict[str, list[str]] = {}
    for bgc in manifest.get("bgcs", []):
        triggers = bgc.get("cctt_triggers") or []
        if isinstance(triggers, str):
            triggers = [t.strip() for t in triggers.split(";") if t.strip()]
        cctt_per_bgc[bgc["bgc_id"]] = triggers

    # Load triage board
    triage_candidates = sorted(pdir.glob("*_4_triage_board.csv"))
    if not triage_candidates:
        raise FileNotFoundError(f"Triage board not found in {pdir}")
    with open(triage_candidates[0], newline="", encoding="utf-8") as fh:
        triage_rows = list(csv.DictReader(fh))

    def _score(row: dict, col: str) -> float:
        try:
            return float(row.get(col) or 0)
        except (TypeError, ValueError):
            return 0.0

    # Rank by AB+AF, excluding standing-rule and primary-metab drops
    active = [r for r in triage_rows
              if not r.get("Standing_rule")
              and r.get("Primary_metab_flag") != "YES"]
    if scope == "all_bgcs":
        # v9.7.93: uniform all-BGC coverage — every BGC (standing-rule / primary-metab
        # drops included), ranked by AB+AF but NOT truncated. The point is complete
        # gene/domain visibility at the artifact level, matching gold's uniform full
        # Mode B; lead-board membership is deliberately not a filter here.
        selected = sorted(triage_rows,
                          key=lambda r: _score(r, "AB_auto") + _score(r, "AF_auto"),
                          reverse=True)
    else:
        selected = sorted(active,
                          key=lambda r: _score(r, "AB_auto") + _score(r, "AF_auto"),
                          reverse=True)[:top_n]

    # Load RGGMCI pairs
    rggmci_pairs: list[dict] = []
    rggmci_candidates = sorted(pdir.glob("*_4A_RGGMCI_ranked_pairs.csv"))
    if rggmci_candidates:
        with open(rggmci_candidates[0], newline="", encoding="utf-8") as fh:
            rggmci_pairs = list(csv.DictReader(fh))

    def _rggmci_adjacency(bgc_id: str) -> str:
        pairs = [r for r in rggmci_pairs
                 if bgc_id in (r.get("bgc_a", ""), r.get("bgc_b", ""))]
        if not pairs:
            return ""
        high = [r for r in pairs if "HIGH" in r.get("rggmci_confidence", "")]
        mod = [r for r in pairs if "MODERATE" in r.get("rggmci_confidence", "")]
        parts = []
        if high:
            partners = [r.get("bgc_b") if r.get("bgc_a") == bgc_id else r.get("bgc_a")
                        for r in high]
            parts.append(f"HIGH with {', '.join(str(p) for p in partners)}")
        if mod:
            partners = [r.get("bgc_b") if r.get("bgc_a") == bgc_id else r.get("bgc_a")
                        for r in mod]
            parts.append(f"MODERATE with {', '.join(str(p) for p in partners)}")
        return "; ".join(parts)

    # Find antiSMASH ZIP within the package seal
    # GBK files are present in the package dir directly (from the run extraction)
    gbk_map: dict[str, str] = {}  # region_key -> gbk text
    for gbk_path in pdir.glob("*.gbk"):
        try:
            gbk_map[gbk_path.stem] = gbk_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Also try reading from the sealed ZIP if GBK files aren't loose
    if not gbk_map:
        zip_candidates = sorted(pdir.parent.glob("*.zip"))
        for zp in zip_candidates:
            try:
                with zipfile.ZipFile(zp) as z:
                    for name in regular_file_names(z):
                        if name.endswith(".gbk") and "region" in name:
                            key = Path(name).stem
                            gbk_map[key] = z.read(name).decode("utf-8", errors="replace")
            except Exception:
                pass
            if gbk_map:
                break

    # v9.7.88 roadmap #1: the sealed normalized gene context is the PRIMARY source — it carries
    # real per-CDS rows written at run time, so the builder no longer depends on loose GBKs or the
    # original antiSMASH ZIP being present post-seal. GBK parsing remains a fallback for older
    # packages cut before v9.7.88 that lack the gene_context file.
    try:
        from .gene_context import load_gene_context as _load_gc
        # v9.7.374 fix: was keyed on the raw `strain_id` PARAMETER (default None), not `sid` --
        # the strain id this same function already resolves two lines above specifically so every
        # other lookup/output in this function (filenames, etc.) has a real value even when the
        # caller omits --strain-id and relies on the manifest fallback. Every call in this
        # module's own test suite (tests/test_gene_by_gene.py) omits strain_id, so the v9.7.88
        # PRIMARY source (the sealed gene_context.jsonl) was silently skipped in favor of the
        # weaker synthetic "<bgc>_NOLOCUS" fallback row on every one of those runs, even when a
        # real gene_context.jsonl was present on disk -- reproduced live: with strain_id=None the
        # emitted row read locus_tag=BGC001_NOLOCUS (no real gene resolution) instead of the real
        # ctg1_5/ketosynthase/aa_length=400 row `sid`-keyed loading correctly returns. Today's only
        # production caller (cli.py's two build_gene_by_gene_table() call sites) always passes
        # strain_id explicitly so this was latent, not live, in the gold pipeline -- but any future
        # caller relying on the manifest-derived fallback (exactly what this function's own `sid`
        # resolution exists to support) hit it silently.
        _gene_ctx = _load_gc(pdir, sid) if sid else {}
    except Exception as exc:
        # v9.7.371 fix: was a bare swallow. A genuine load failure of the v9.7.88 PRIMARY source
        # (malformed gene_context.jsonl, schema drift) silently routed a CURRENT package into the
        # weaker GBK-parsing fallback below, indistinguishable from a genuinely pre-v9.7.88 package.
        from . import degradation as _degradation
        _degradation.record("gene_by_gene.build_gene_by_gene_table.load_gene_context", exc,
                            strain_id=str(strain_id))
        _gene_ctx = {}

    # Build rows
    all_rows: list[dict] = []
    outdir_path = Path(outdir) if outdir else pdir
    outdir_path.mkdir(parents=True, exist_ok=True)

    for rank, triage_row in enumerate(selected, 1):
        bgc_id = triage_row.get("BGC_ID", "?")
        bgc = bgcs_by_id.get(bgc_id, {})
        contig = bgc.get("contig", triage_row.get("Contig", ""))
        boundary = bgc.get("edge_status", triage_row.get("Boundary", ""))
        bgc_start = bgc.get("start")
        bgc_end = bgc.get("end")
        contig_length = bgc.get("contig_length")
        region_num = bgc.get("region_number", "")
        # v9.7.409 (CLAUDE_409 provenance anchors): per-row strain/assembly_locator/region so every
        # gene row is traceable to its durable locus (was bgc_id + contig only).
        _gbg_region = (bgc.get("antismash_region") or triage_row.get("antiSMASH_Region")
                       or (f"region{int(region_num):03d}" if str(region_num).isdigit() else ""))
        _gbg_locator = _assembly_locator(bgc) if bgc else ""
        source_gbk_name = bgc.get("source_gbk", "")
        tta_info = tta_per_bgc.get(bgc_id, {})
        tta_tier = tta_info.get("bldA_tier", "")
        res_tier = res_per_bgc.get(bgc_id, {}).get("tier", "")
        cctt = "; ".join(cctt_per_bgc.get(bgc_id, []))
        # VGP-06 (.366): this is the per-RUN depth mode (Depth_floor), constant across a strain's genes —
        # renamed from the misleading `diagnostic_tier`, which read as a per-gene signal it never was.
        run_depth_mode = triage_row.get("Depth_floor", "")
        rggmci_ctx = _rggmci_adjacency(bgc_id)
        products = bgc.get("products", [])
        prods_str = "; ".join(products) if isinstance(products, list) else str(products)

        # v9.7.88: prefer the sealed normalized gene context (real CDS rows). Map its schema to
        # the row shape the rest of the builder expects. Only fall back to GBK parsing / the
        # NOLOCUS placeholder when the gene context has nothing for this BGC (older packages).
        gbk_key = ""   # defined for the source_gbk column regardless of which path is taken
        _gc_rows = _gene_ctx.get(bgc_id, [])
        if _gc_rows:
            cds_records = [{
                "locus_tag": r.get("locus_tag") or f"{bgc_id}_CDS{i+1}",
                "start": r.get("start"),
                "end": r.get("end"),
                "strand": "+" if (r.get("strand") in (1, "+", None)) else "-",
                "length_bp": r.get("length_bp"),
                "product": r.get("product", ""),
                "translation_length": r.get("aa_length"),
                "sec_met_domains": r.get("sec_met_domains", []),
                # v9.7.374 AUDIT (audit: AS-XXX runtime deep audit, follow-up to
                # gene_by_gene_ripp_core_gene_kind_ignored): gene_context.jsonl rows already
                # carry antiSMASH's own /gene_kind= call (verified: load_gene_context() returns
                # the raw cds dicts unmodified, "gene_kind" key intact) but this dict comprehension
                # -- the PRIMARY path every real run since v9.7.88 takes -- silently dropped it
                # before _infer_role() ever saw it, so the sibling patch's gene_kind fallback
                # (which only reached the _parse_cds_from_gbk() pre-v9.7.88 fallback path) never
                # fired on real production output. MUST be applied together with (after)
                # AUDIT_374_gene_by_gene_ripp_core_gene_kind_ignored.
                "gene_kind": r.get("gene_kind", ""),
                "tta_codons": r.get("tta_codons", 0),
                "source_line": "gene_context.jsonl (sealed normalized gene context)",
            } for i, r in enumerate(_gc_rows)]
        else:
            # Try to parse CDS from GBK (fallback for packages cut before v9.7.88)
            gbk_key = source_gbk_name.replace(".gbk", "") if source_gbk_name else ""
            gbk_text = gbk_map.get(gbk_key, "")
            if not gbk_text and contig:
                # Try matching by contig name
                node_id = bgc.get("node_id", contig.split(".")[0])
                for k, v in gbk_map.items():
                    if node_id in k or (contig and contig.split("_length")[0] in k):
                        gbk_text = v
                        gbk_key = k
                        break
            try:
                cds_records = _parse_cds_from_gbk(gbk_text, gbk_key) if gbk_text else []
            except Exception as exc:
                # v9.7.371 fix: was unguarded, unlike the identical _parse_cds_from_gbk call in
                # the sibling write_gene_count_crosscheck() (line ~218), which catches per-BGC and
                # continues. Here a malformed fallback-path GBK could abort the ENTIRE strain's
                # gene-by-gene table (every BGC, not just the one with the bad GBK).
                from . import degradation as _degradation
                _degradation.record("gene_by_gene.build_gene_by_gene_table.parse_cds_fallback", exc,
                                    bgc_id=str(bgc_id), gbk_key=str(gbk_key))
                cds_records = []

        if cds_records:
            # Filter to CDS within BGC coordinates
            bgc_cds = [c for c in cds_records
                       if bgc_start is None or bgc_end is None
                       or (c["start"] is not None and c["end"] is not None
                           and c["start"] <= bgc_end and c["end"] >= bgc_start)]
            if not bgc_cds:
                bgc_cds = cds_records  # fallback: use all if coordinate filter yields nothing
        else:
            # No GBK available: emit one synthetic summary row per BGC
            bgc_cds = [{
                "locus_tag": f"{bgc_id}_NOLOCUS",
                "start": bgc_start,
                "end": bgc_end,
                "strand": "+",
                "length_bp": (bgc_end - bgc_start) if bgc_start and bgc_end else None,
                "product": prods_str,
                "translation_length": None,
                "sec_met_domains": [],
                "tta_codons": 0,
                "source_line": f"GBK not available (antiSMASH ZIP not in package)",
            }]

        for cds in bgc_cds:
            domains = cds.get("sec_met_domains", [])
            role = _infer_role(cds.get("product", ""), domains, cds.get("gene_kind", ""))
            edge_flag = _edge_overlap_flag(
                boundary, bgc_start, bgc_end,
                cds.get("start"), cds.get("end"), contig_length,
            )
            all_rows.append({
                "strain":                sid,            # v9.7.409 provenance anchor
                "assembly_locator":      _gbg_locator,   # v9.7.409 provenance anchor
                "region":                _gbg_region,    # v9.7.409 provenance anchor
                "bgc_id":                bgc_id,
                "rank":                  rank,
                "locus_tag":             cds.get("locus_tag", ""),
                "contig":                contig,
                "bgc_start":             bgc_start,
                "bgc_end":               bgc_end,
                "cds_start":             cds.get("start"),
                "cds_end":               cds.get("end"),
                "strand":                cds.get("strand", "+"),
                "length_bp":             cds.get("length_bp"),
                "aa_length":             cds.get("translation_length"),
                "product_qualifier":     _cap_qualifier(cds.get("product", "")),
                "gene_function_inference": role,
                "sec_met_domains":       "; ".join(domains) if domains else "",
                "run_depth_mode":        run_depth_mode,
                "cctt_triggers":         cctt,
                "bldA_tta_tier":         tta_tier,
                "resistance_tier":       res_tier,
                "boundary_flag":         boundary,
                "edge_core_overlap":     edge_flag,
                "rggmci_adjacency":      rggmci_ctx,
                "source_gbk":            gbk_key or source_gbk_name,
                "source_line_locator":   cds.get("source_line", ""),
                "bgc_products":          _cap_qualifier(prods_str),
                "ab_score":              _score(triage_row, "AB_auto"),
                "af_score":              _score(triage_row, "AF_auto"),
            })

    # --- Write CSV ---
    _suffix = "all_bgcs" if scope == "all_bgcs" else "top_leads"
    csv_path = outdir_path / f"{sid}_gene_by_gene_{_suffix}.csv"
    # v9.7.374 fix: both branches wrote csv_path directly (bare open(...,'w') / write_text()) --
    # non-atomic. This exact file is what authored_verify.py's _bgc_context_from_package() reads
    # as the authoritative source for the per-BGC locus_home/known_locus_tags roster (the roster
    # the .373/.373b fabrication-detection and BLASTp-matrix gates depend on) -- an interrupted
    # write here leaves a truncated CSV that authored_verify's bare try/except around its own CSV
    # read (mamey/authored_verify.py) silently degrades to "no roster" for, reopening exactly the
    # class of gap those cuts just closed, via file-corruption instead of a missing key.
    if all_rows:
        fields = list(all_rows[0].keys())
        _tmp = csv_path.with_name(csv_path.name + ".tmp")
        with open(_tmp, "w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(all_rows)
        _tmp.replace(csv_path)
    else:
        _tmp = csv_path.with_name(csv_path.name + ".tmp")
        # v9.7.409: keep the anchor columns in the empty-table header too, so the provenance gate
        # sees a traceable (if rowless) per-BGC table rather than a bare bgc_id.
        _tmp.write_text("strain,assembly_locator,region,bgc_id,rank,locus_tag,contig,notes\n", encoding="utf-8")
        _tmp.replace(csv_path)

    # --- Write XLSX (if openpyxl available) ---
    xlsx_path: Path | None = None
    if _HAS_XLSX and all_rows:
        xlsx_path = outdir_path / f"{sid}_gene_by_gene_{_suffix}.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Gene-by-Gene All BGCs" if scope == "all_bgcs" else "Gene-by-Gene Top Leads"

        # Header styling
        header_fill = PatternFill("solid", fgColor="1F4E79")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        fields = list(all_rows[0].keys())
        for col_idx, field_name in enumerate(fields, 1):
            cell = ws.cell(row=1, column=col_idx, value=field_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        # BGC alternating row colours
        bgc_colors = ["DCE6F1", "FFFFFF"]  # alternating light blue / white
        current_bgc = None
        color_idx = 0
        for row_idx, row in enumerate(all_rows, 2):
            if row["bgc_id"] != current_bgc:
                current_bgc = row["bgc_id"]
                color_idx = (color_idx + 1) % 2
            fill = PatternFill("solid", fgColor=bgc_colors[color_idx])
            for col_idx, field_name in enumerate(fields, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=row.get(field_name))
                cell.fill = fill
                cell.font = Font(size=9)
                cell.alignment = Alignment(wrap_text=False)

        # Auto-fit column widths (approximate)
        for col_idx, field_name in enumerate(fields, 1):
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            max_len = max(len(field_name), *(len(str(r.get(field_name, "") or ""))
                                             for r in all_rows))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

        # Freeze header row
        ws.freeze_panes = "A2"
        # v9.7.374 fix: was a bare wb.save() -- non-atomic, same established fix pattern as the
        # CSV write above.
        _xlsx_tmp = xlsx_path.with_name(xlsx_path.name + ".tmp")
        _save_wb_safely(wb, str(_xlsx_tmp))
        canonicalize_xlsx(_xlsx_tmp)
        _xlsx_tmp.replace(xlsx_path)

    return {
        "csv_path": str(csv_path),
        "xlsx_path": str(xlsx_path) if xlsx_path else None,
        "row_count": len(all_rows),
        "bgcs_covered": len(selected),
        "scope": scope,
        "top_n": top_n,
        "has_gbk_data": bool(gbk_map),
    }
