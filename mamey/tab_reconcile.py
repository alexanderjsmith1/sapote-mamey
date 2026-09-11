"""antiSMASH tab reconciliation for one BGC/region.

Deterministic Mode B evidence layer: reads antiSMASH ZIP/directory internals plus
an optional Mamey sealed package/crosswalk, then emits a tab evidence ledger and an
antiSMASH-vs-Mamey comparison table.  This is deliberately a raw-evidence report:
it never promotes comparator/product names to compound identities.
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

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import html
import json
import re
import shutil
import tempfile
import zipfile
from .ziputil import safe_extract_all
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

LEDGER_FIELDS = [
    "tab", "direct_evidence", "raw_result", "mamey_extraction",
    "interpretation", "missed_or_underused", "follow_up", "source"
]
COMPARISON_FIELDS = ["layer", "status", "impact", "recommended_fix", "source"]


def _q(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return "; ".join(_q(x) for x in v if _q(x))
    if isinstance(v, dict):
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    return str(v)


def _safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_") or "region"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV as row-dicts. Returns `[]` for a genuinely absent file (the normal, silent
    case — most crosswalk/evidence inputs are optional). A file that EXISTS but fails to parse
    (corrupt bytes, a decode error, ...) is a different situation — that is a real data-loss
    event for this module's Mode-B evidence-ledger role, not "no data," and must not look
    identical to a legitimately absent input. Reproduced directly: before this fix, a missing
    file, a genuinely-empty-but-valid file, AND a file with invalid UTF-8 bytes all returned the
    same silent `[]` — indistinguishable to every caller."""
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as exc:  # pragma: no cover - defensive
        import warnings
        warnings.warn(
            f"tab_reconcile.py: could not read {path} ({exc}); treating as empty for this "
            "reconciliation pass, but the file exists and this is a parse failure, not a "
            "genuinely absent input.",
            RuntimeWarning,
            stacklevel=2,
        )
        return []


def _looks_like_zip(path: Path) -> bool:
    return path.is_file() and zipfile.is_zipfile(path)


def _materialize_input(path: Path) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """Return a directory for an antiSMASH zip or directory."""
    if path.is_dir():
        return path, None
    if not _looks_like_zip(path):
        raise SystemExit(f"Input does not look like antiSMASH ZIP or directory: {path}")
    tmp = tempfile.TemporaryDirectory(prefix="mamey_tab_reconcile_")
    root = Path(tmp.name)
    with zipfile.ZipFile(path) as zf:
        safe_extract_all(zf, root)
    # If the zip contains a single top-level folder with antiSMASH files, use it.
    children = [p for p in root.iterdir() if not p.name.startswith("__MACOSX")]
    # v9.7.379: generic antiSMASH-at-root check (was a hardcoded cohort filename "AS-XXX.json").
    # Descend into a single wrapper directory unless antiSMASH result JSON sits directly at root.
    if len(children) == 1 and children[0].is_dir() and not any(root.glob("*.json")):
        return children[0], tmp
    return root, tmp


def _materialize_package(path: Path | None) -> tuple[Path | None, tempfile.TemporaryDirectory | None]:
    if path is None:
        return None, None
    if path.is_dir():
        # Accept either the complete package root or the inner package dir.
        if (path / "package").is_dir():
            return path / "package", None
        return path, None
    if _looks_like_zip(path):
        tmp = tempfile.TemporaryDirectory(prefix="mamey_pkg_tab_reconcile_")
        root = Path(tmp.name)
        with zipfile.ZipFile(path) as zf:
            safe_extract_all(zf, root)
        if (root / "package").is_dir():
            return root / "package", tmp
        # fallback to first package-like directory
        for p in root.rglob("manifest.json"):
            return p.parent, tmp
        return root, tmp
    raise SystemExit(f"Package is not a directory or ZIP: {path}")


def _load_package_rows(pkg: Path | None) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    if not pkg:
        return out
    for p in pkg.rglob("*.csv"):
        name = p.name
        if name.endswith("_2b_bgc_crosswalk.csv"):
            out["crosswalk"] = _read_csv_rows(p)
            out["crosswalk_file"] = [{"path": str(p)}]
        elif name.endswith("_4_triage_board.csv"):
            out["triage"] = _read_csv_rows(p)
            out["triage_file"] = [{"path": str(p)}]
        elif name.endswith("gene_by_gene_all_bgcs.csv"):
            out["genes"] = _read_csv_rows(p)
            out["genes_file"] = [{"path": str(p)}]
        elif name.endswith("_7_cell_provenance.csv"):
            out["provenance"] = _read_csv_rows(p)
            out["provenance_file"] = [{"path": str(p)}]
        elif name.endswith("_HMM_adjudication_by_bgc.csv"):
            out["hmm_bgc"] = _read_csv_rows(p)
            out["hmm_bgc_file"] = [{"path": str(p)}]
    return out


def _find_bgc_package_context(rows: dict[str, list[dict[str, str]]], bgc: str | None) -> dict[str, str]:
    if not bgc:
        return {}
    for table in ("crosswalk", "triage"):
        for r in rows.get(table, []):
            rid = r.get("bgc_id") or r.get("BGC_ID") or ""
            if rid == bgc:
                return {k: v for k, v in r.items() if v is not None}
    return {}


def _node_core(node: str | None) -> str | None:
    if not node:
        return None
    # Mamey node_id may strip the decimal coverage suffix; antiSMASH record id keeps it.
    return re.sub(r"\.\d+(?=($|\s|\.region))", "", node)


def _region_index(rec: dict[str, Any], wanted_region) -> int:
    """antiSMASH `areas` are ordered: areas[0] IS region001. There is no region_number key on an area,
    so the 1-based region label is the index. Returns 0 when no region was requested (single-region
    contigs are unaffected — which is exactly why the BGC028 reference fixture never caught this)."""
    areas = rec.get("areas") or []
    if not wanted_region or not areas:
        return 0
    m = re.search(r"(\d+)", str(wanted_region))
    if not m:
        return 0
    idx = int(m.group(1)) - 1
    return idx if 0 <= idx < len(areas) else 0


def _choose_record(data: dict[str, Any], *, bgc: str | None, node: str | None, region: str | None,
                   ctx: dict[str, str]) -> tuple[dict[str, Any], int]:
    wanted_node = node or ctx.get("contig") or ctx.get("Contig") or ctx.get("node_id") or ctx.get("Node_ID")
    wanted_source = ctx.get("source_gbk") or ctx.get("Source_GBK") or ""
    wanted_region = region or ctx.get("antismash_region") or ctx.get("antiSMASH_Region") or ctx.get("region_number")
    wanted_core = _node_core(wanted_node)
    records = data.get("records") or []
    candidates = []
    for idx, rec in enumerate(records):
        rid = rec.get("id", "")
        score = 0
        if wanted_node and wanted_node in rid:
            score += 10
        if wanted_core and wanted_core in _node_core(rid):
            score += 8
        if wanted_source and rid in wanted_source:
            score += 10
        if score:
            candidates.append((score, idx, rec))
    if not candidates:
        # Last resort: BGC number cannot map to antiSMASH without a package; try node substring.
        if wanted_node:
            for idx, rec in enumerate(records):
                if wanted_node.lower() in rec.get("id", "").lower():
                    candidates.append((1, idx, rec))
    if not candidates:
        raise SystemExit("Could not resolve requested BGC/node/region to an antiSMASH record. Provide --package or --node.")
    candidates.sort(reverse=True, key=lambda x: x[0])
    rec = candidates[0][2]
    # v9.7.244: `wanted_region` was computed here and never read. The caller then took areas[0] —
    # the FIRST region on the contig — no matter which region was requested. On AS-XXX NODE_2
    # (3 regions) asking for BGC018 (region003, lanthipeptide, 438609-463791) reported region001
    # (233558-275304, NRPS-like). Resolve the area index here and hand it back.
    return rec, candidates[0][1], _region_index(rec, wanted_region)


def _load_antismash_json(root: Path) -> dict[str, Any]:
    jsons = [p for p in root.glob("*.json") if not p.name.startswith(".")]
    if not jsons:
        jsons = list(root.rglob("*.json"))
    # Prefer non-manifest antiSMASH JSON with records.
    for p in jsons:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("records"), list):
                data["_source_json"] = str(p)
                return data
        except Exception:
            continue
    raise SystemExit(f"Could not find antiSMASH JSON with records under {root}")


def _feature_in_span(f: dict[str, Any], start: int, end: int) -> bool:
    """antiSMASH JSON locations look like `[635:3869](+)` or `join{[a:b](+),[c:d](+)}`. A CDS belongs
    to a region when its own span overlaps the region's. v9.7.244: used to scope the gene overview to
    the requested region instead of reporting the whole contig's CDS count."""
    nums = [int(n) for n in re.findall(r"\d+", str(f.get("location", "")))]
    if len(nums) < 2:
        return False
    lo, hi = min(nums), max(nums)
    return lo < end and hi > start


def _feature_qual(f: dict[str, Any], key: str) -> str:
    v = (f.get("qualifiers") or {}).get(key)
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return _q(v)


def _cds_features(rec: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in rec.get("features", []) if f.get("type") == "CDS"]


def _domain_features(rec: dict[str, Any], db: str | None = None) -> list[dict[str, Any]]:
    feats = []
    for f in rec.get("features", []):
        if "domain" in f.get("type", "").lower():
            if db is None or db.lower() in _feature_qual(f, "database").lower() or db.lower() in f.get("type", "").lower():
                feats.append(f)
    return feats


def _count_domains_from_features(rec: dict[str, Any]) -> Counter:
    c = Counter()
    for f in _domain_features(rec):
        label = _feature_qual(f, "label") or _feature_qual(f, "aSDomain") or _feature_qual(f, "description") or f.get("type", "domain")
        c[label] += 1
    return c


def _clusterblast_txt(root: Path, folder: str, rec_id: str, area_idx: int = 0) -> Path | None:
    # antiSMASH txt names use NODE..._c{N}.txt, where N is the 1-based region/cluster number on
    # that contig (region001 -> _c1.txt, region002 -> _c2.txt, ...) — confirmed 1:1 against real
    # multi-region antiSMASH output (AS-XXX NODE_1's 5 regions <-> _c1..._c5.txt, gene coordinates
    # inside each numbered file fall inside that region's own area span). `area_idx` is the 0-based
    # area index already resolved by `_region_index`/`_choose_record` for this request; the caller
    # must pass it so this hits the SAME region already selected for the Gene overview tab.
    prefix = f"{rec_id}_c{area_idx + 1}.txt"
    candidates = list((root / folder).glob(prefix)) if (root / folder).is_dir() else []
    if not candidates:
        # Legacy/degenerate layouts only: a single un-numbered txt per contig. Do not fall back to
        # "any *_c*.txt containing this node" — on a multi-region contig that silently substitutes
        # a DIFFERENT region's ClusterBlast/KnownClusterBlast/SubClusterBlast evidence (previously
        # always resolved to _c1.txt regardless of which region was requested).
        core = rec_id.split(".")[0]
        candidates = [
            p for p in (root / folder).glob("*.txt")
            if core in p.name and not re.search(r"_c\d+\.txt$", p.name)
        ] if (root / folder).is_dir() else []
    return candidates[0] if candidates else None


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:250]
    return ""


def _summarize_clusterblast_txt(path: Path | None) -> tuple[int, str]:
    if not path or not path.exists():
        return 0, "TAB_ABSENT"
    txt = path.read_text(encoding="utf-8", errors="ignore")
    # Count obvious ranked subject blocks; fallback to non-empty length.
    n = len(re.findall(r"^\s*\d+\.\s+", txt, flags=re.M))
    # antiSMASH TXT always contains a header.  Treat an empty "Significant hits:"
    # section as an explicit zero-hit tab, not as one generic text hit.
    m_sig = re.search(r"Significant hits:[ \t]*(.*?)(?:\n\s*Details:|\Z)", txt, flags=re.S | re.I)
    if m_sig is not None:
        sig = m_sig.group(1).strip()
        if not sig:
            return 0, "NO_HITS"
    if n == 0 and re.search(r"no significant|no hits|No hits", txt):
        return 0, "NO_HITS"
    # KnownClusterBlast files in antiSMASH v8 have tables; pull top BGC and product if available.
    acc = re.search(r"(BGC\d+\.\d+)", txt)
    top = acc.group(1) if acc else _first_nonempty_line(txt)
    if n == 0 and txt.strip():
        n = 1
    return n, top


def _cluster_compare_summary(rec: dict[str, Any]) -> tuple[int, str]:
    cc = rec.get("modules", {}).get("antismash.modules.cluster_compare", {})
    db = ((cc.get("db_results") or {}).get("MIBiG") or {})
    by_region = db.get("by_region") or {}
    hits = []
    def walk(x):
        if isinstance(x, dict):
            # common antiSMASH fields in hit objects
            if any(k in x for k in ("accession", "label", "name", "description")):
                hits.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(by_region)
    # Deduplicate accessions/descriptions.
    labels=[]
    for h in hits:
        lab = h.get("accession") or h.get("label") or h.get("name") or h.get("description")
        if lab and lab not in labels:
            labels.append(str(lab))
    return len(labels), "; ".join(labels[:5]) or ("NO_HITS" if by_region == {} else "PRESENT_UNPARSED")


def _clusterblast_json_summary(rec: dict[str, Any], key: str, area_idx: int = 0) -> tuple[int, str]:
    # antiSMASH's clusterblast JSON block is `results: [<region001 result>, <region002 result>, ...]`
    # — index-aligned to the record's `areas` list in the SAME order (confirmed live on a real
    # 3-region contig: results[0]/[1]/[2] hit-label to region001/002/003's own KnownClusterBlast TXT
    # tabs 1:1). `walk_hits(results[:3])` used to walk the first up-to-3 entries regardless of which
    # region was requested, so on a multi-region contig it silently mixed in — or returned outright —
    # a DIFFERENT region's named comparator as if it were the requested region's. This is the same
    # region-agnostic-indexing defect `_clusterblast_txt`/`_region_index` already fix for the TXT
    # tabs; `area_idx` (already resolved by `_choose_record`/`_region_index` for this request) is
    # threaded through here so the JSON fallback (used whenever the TXT tab is NO_HITS/TAB_ABSENT,
    # see `raw_by_tab` in `build_tab_reconciliation`) reads the SAME region already selected
    # everywhere else in the ledger, instead of an arbitrary prefix of the whole contig's results.
    cb = rec.get("modules", {}).get("antismash.modules.clusterblast", {})
    block = cb.get(key) or {}
    results = block.get("results") or []
    if not results:
        return 0, "NO_HITS" if key == "subcluster" else "NO_RESULTS"
    region_result = results[area_idx] if 0 <= area_idx < len(results) else results[0]
    labels=[]
    def walk_hits(x):
        if isinstance(x, dict):
            if "description" in x or "accession" in x or "name" in x:
                val = x.get("description") or x.get("accession") or x.get("name")
                if val and str(val) not in labels:
                    labels.append(str(val))
            for v in x.values(): walk_hits(v)
        elif isinstance(x, list):
            for v in x: walk_hits(v)
    walk_hits([region_result])
    return (1 if labels else 0), "; ".join(labels[:3]) or "NO_HITS"


def _nrps_pks_summary(rec: dict[str, Any]) -> tuple[int, str, dict[str, int]]:
    mod = rec.get("modules", {}).get("antismash.modules.nrps_pks", {})
    preds = mod.get("domain_predictions") or {}
    consensus = mod.get("consensus") or {}
    dom_counts = Counter()
    for key in preds:
        for tok in ["PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "PKS_ER", "ACP", "PKS_PP", "Thioesterase", "Docking"]:
            if tok in key:
                dom_counts[tok] += 1
                break
    at_counts = Counter(consensus.values())
    raw = ", ".join(f"{k}={v}" for k,v in dom_counts.most_common())
    if at_counts:
        raw += "; AT consensus: " + ", ".join(f"{k}={v}" for k,v in at_counts.items())
    return len(preds), raw or "NO_NRPS_PKS_DOMAINS", dict(dom_counts)


def _active_site_summary(rec: dict[str, Any]) -> tuple[int, str]:
    mod = rec.get("modules", {}).get("antismash.modules.active_site_finder", {})
    pairs = mod.get("pairings") or []
    return len(pairs), f"{len(pairs)} active-site pairings" if pairs else "NO_ACTIVE_SITE_HITS"


def _tfbs_summary(rec: dict[str, Any]) -> tuple[int, str]:
    mod = rec.get("modules", {}).get("antismash.modules.tfbs_finder", {})
    hits_by_region = mod.get("hits_by_region") or {}
    hits=[]
    for rs in hits_by_region.values():
        hits.extend(rs or [])
    if not hits:
        return 0, "NO_TFBS_HITS"
    names = [f"{h.get('name','?')}({h.get('confidence','?')})" for h in hits[:6]]
    return len(hits), "; ".join(names)


def _tta_summary(rec: dict[str, Any]) -> tuple[int, str]:
    mod = rec.get("modules", {}).get("antismash.modules.tta", {})
    codons = mod.get("TTA codons") or []
    return len(codons), f"{len(codons)} TTA codons" if codons else "NO_TTA_CODONS"


def _tigrfam_summary(rec: dict[str, Any]) -> tuple[int, str]:
    mod = rec.get("modules", {}).get("antismash.detection.tigrfam", {})
    hits = mod.get("hits") or []
    if not hits:
        return 0, "NO_HITS"
    labels = []
    for h in hits[:10]:
        labels.append(h.get("label") or h.get("domain") or h.get("description") or "hit")
    return len(hits), "; ".join(labels)


def _pfam_summary(rec: dict[str, Any]) -> tuple[int, str, Counter]:
    hits = rec.get("modules", {}).get("antismash.detection.cluster_hmmer", {}).get("hits") or []
    if not hits:
        return 0, "NO_HITS", Counter()
    counts = Counter(h.get("domain") or h.get("label") or h.get("description") or "domain" for h in hits)
    top = "; ".join(f"{k}={v}" for k,v in counts.most_common(12))
    return len(hits), top, counts


def _tailoring_summary(rec: dict[str, Any]) -> tuple[int, str]:
    terms = ["p450", "P450", "Glycos", "glycos", "Methyl", "methyl", "halogen", "Halogen", "Polysacc", "transf"]
    rows=[]
    for f in _domain_features(rec):
        qual = f.get("qualifiers") or {}
        text = " ".join(_q(qual.get(k)) for k in ("label", "description", "locus_tag", "domain_id"))
        if any(t in text for t in terms):
            rows.append(text)
    # Add rule domains, which capture p450 and Polysacc_synt_2 used by detection.
    rr = rec.get("modules", {}).get("antismash.detection.hmm_detection", {}).get("rule_results", {})
    for proto in rr.get("cds_by_protocluster", []) or []:
        if len(proto) > 1:
            for cds in proto[1]:
                for dom in cds.get("domains", []) or []:
                    name = str(dom[0]) if dom else ""
                    if any(t.lower() in name.lower() for t in terms):
                        rows.append(f"{cds.get('cds_name')}:{name}")
    counts=Counter(rows)
    return sum(counts.values()), "; ".join(f"{k} x{v}" for k,v in counts.most_common(10)) or "NO_TAILORING_DOMAINS_CAPTURED"


def _gene_overview_summary(rec: dict[str, Any], area_idx: int = 0) -> tuple[int, str]:
    """v9.7.244: takes the resolved area index. Previously hardcoded areas[0], so every BGC that was
    not the first region on its contig got another region's span, products and CDS count."""
    products = []
    areas = rec.get("areas") or []
    if areas:
        area = areas[area_idx] if 0 <= area_idx < len(areas) else areas[0]
        products = area.get("products") or []
        start, end = area.get("start"), area.get("end")
    else:
        area, start, end = None, "", ""
    # CDS scoped to the region, not the whole contig. The old code reported the contig's CDS count
    # (NODE_2: 535) as if it were the BGC's.
    cds = _cds_features(rec)
    if area and isinstance(start, int) and isinstance(end, int):
        cds = [f for f in cds if _feature_in_span(f, start, end)]
    core = []
    for f in cds:
        q = f.get("qualifiers") or {}
        if "biosynthetic" in _q(q.get("gene_kind")).lower() or q.get("sec_met_domain"):
            loc = _q(q.get("locus_tag"))
            if loc: core.append(loc)
    return len(cds), f"record={rec.get('id')}; span={start}-{end}; products={'; '.join(products)}; CDS={len(cds)}; secmet/core-like={', '.join(core[:12])}"


def _mamey_status_for_layer(layer: str, triage: dict[str, str], rows: dict[str, list[dict[str, str]]], bgc: str | None) -> tuple[str, str]:
    # Returns extraction summary and comparison status.
    if layer == "Gene overview":
        if rows.get("genes") and bgc:
            n = sum(1 for r in rows["genes"] if (r.get("BGC_ID") or r.get("bgc_id") or r.get("BGC") or "") == bgc)
            return (f"Mamey gene table rows={n}", "captured" if n else "missed")
        return ("No gene table supplied", "missed")
    if layer == "KnownClusterBlast":
        val = triage.get("KCB_top") or triage.get("KCB_clusterblast") or ""
        return (val or "blank", "captured" if val else "missed")
    if layer == "ClusterBlast":
        val = triage.get("ClusterBlast_organism") or ""
        return (val or "blank", "captured" if val else "missed")
    if layer == "SubClusterBlast":
        val = triage.get("SubCluster_hits") or ""
        return (val or "blank", "captured" if val == "NO_HITS" or val else "underused")
    if layer == "MIBiG comparison":
        val = triage.get("MIBiG_ranked_n") or ""
        return (f"MIBiG_ranked_n={val}" if val else "blank", "captured" if val else "missed")
    if layer == "Pfam domains":
        # HMM writeback means offline HMM domain summary exists, not full antiSMASH PFAM tab.
        hrow = None
        if bgc:
            for r in rows.get("hmm_bgc", []):
                if r.get("bgc_id") == bgc:
                    hrow = r; break
        if hrow:
            return (f"HMM writeback domain_hits={hrow.get('domain_hits')}; genes={hrow.get('genes_with_hmm_hits')}", "underused")
        return ("No HMM writeback supplied", "missed")
    if layer in {"TIGRFAM domains", "TFBS Finder", "NRPS/PKS predictions", "Active-site finder", "TTA/bldA"}:
        return ("Not surfaced as first-class Mamey fields", "missed")
    if layer == "Tailoring":
        return ("Partially present through gene/domain table; no tab-level ledger", "underused")
    return ("", "missed")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=_SafeDictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: _q(row.get(k, "")) for k in fields})


def _write_html(path: Path, title: str, rows: list[dict[str, Any]], fields: list[str]) -> None:
    parts=["<html><head><meta charset='utf-8'><style>body{font-family:Arial,sans-serif;margin:24px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #ddd;padding:6px;vertical-align:top}th{background:#f2f2f2}</style></head><body>"]
    parts.append(f"<h1>{html.escape(title)}</h1><table><thead><tr>")
    for f in fields: parts.append(f"<th>{html.escape(f)}</th>")
    parts.append("</tr></thead><tbody>")
    for r in rows:
        parts.append("<tr>")
        for f in fields: parts.append(f"<td>{html.escape(_q(r.get(f,'')))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></body></html>")
    path.write_text("".join(parts), encoding="utf-8")


def build_tab_reconciliation(antismash: str | Path, outdir: str | Path, *, bgc: str | None = None,
                             node: str | None = None, region: str | None = None,
                             package: str | Path | None = None) -> dict[str, Any]:
    antismash = Path(antismash)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    root, tmp = _materialize_input(antismash)
    pkg_root, pkg_tmp = _materialize_package(Path(package) if package else None)
    try:
        pkg_rows = _load_package_rows(pkg_root)
        ctx = _find_bgc_package_context(pkg_rows, bgc)
        data = _load_antismash_json(root)
        rec, rec_idx, area_idx = _choose_record(data, bgc=bgc, node=node, region=region, ctx=ctx)
        rec_id = rec.get("id", "")
        triage = {}
        if bgc:
            for r in pkg_rows.get("triage", []):
                if (r.get("BGC_ID") or r.get("bgc_id")) == bgc:
                    triage = r; break

        source_gbk = ctx.get("source_gbk") or f"{rec_id}.region{area_idx + 1:03d}.gbk"
        cb_txt = _clusterblast_txt(root, "clusterblast", rec_id, area_idx)
        kcb_txt = _clusterblast_txt(root, "knownclusterblast", rec_id, area_idx)
        scb_txt = _clusterblast_txt(root, "subclusterblast", rec_id, area_idx)

        gene_n, gene_raw = _gene_overview_summary(rec, area_idx)
        tail_n, tail_raw = _tailoring_summary(rec)
        mibig_n, mibig_raw = _cluster_compare_summary(rec)
        cb_n, cb_raw_json = _clusterblast_json_summary(rec, "general", area_idx)
        cb_txt_n, cb_txt_raw = _summarize_clusterblast_txt(cb_txt)
        kcb_n, kcb_raw_json = _clusterblast_json_summary(rec, "knowncluster", area_idx)
        kcb_txt_n, kcb_txt_raw = _summarize_clusterblast_txt(kcb_txt)
        scb_n, scb_raw_json = _clusterblast_json_summary(rec, "subcluster", area_idx)
        scb_txt_n, scb_txt_raw = _summarize_clusterblast_txt(scb_txt)
        if scb_txt_raw == "NO_HITS":
            # The TXT tab is the rendered antiSMASH SubClusterBlast result; if its
            # Significant hits block is empty, treat query-protein scaffolding present in
            # JSON as zero significant hits.
            scb_n, scb_raw_json = 0, "NO_HITS"
        tfbs_n, tfbs_raw = _tfbs_summary(rec)
        pfam_n, pfam_raw, pfam_counts = _pfam_summary(rec)
        tigr_n, tigr_raw = _tigrfam_summary(rec)
        nrps_n, nrps_raw, nrps_counts = _nrps_pks_summary(rec)
        active_n, active_raw = _active_site_summary(rec)
        tta_n, tta_raw = _tta_summary(rec)

        raw_by_tab = {
            "Gene overview": (gene_n, gene_raw, source_gbk),
            "Tailoring": (tail_n, tail_raw, data.get("_source_json", "AS JSON")),
            "MIBiG comparison": (mibig_n, mibig_raw, "AS JSON: antismash.modules.cluster_compare"),
            "ClusterBlast": (max(cb_n, cb_txt_n), cb_txt_raw if cb_txt_raw not in {"TAB_ABSENT", "NO_HITS"} else cb_raw_json, str(cb_txt) if cb_txt else "AS JSON: clusterblast.general"),
            "KnownClusterBlast": (max(kcb_n, kcb_txt_n), kcb_txt_raw if kcb_txt_raw not in {"TAB_ABSENT", "NO_HITS"} else kcb_raw_json, str(kcb_txt) if kcb_txt else "AS JSON: clusterblast.knowncluster"),
            "SubClusterBlast": (max(scb_n, scb_txt_n), "NO_HITS" if max(scb_n, scb_txt_n) == 0 else (scb_txt_raw if scb_txt_raw != "TAB_ABSENT" else scb_raw_json), str(scb_txt) if scb_txt else "AS JSON: clusterblast.subcluster"),
            "TFBS Finder": (tfbs_n, tfbs_raw, "AS JSON: antismash.modules.tfbs_finder"),
            "Pfam domains": (pfam_n, pfam_raw, "AS JSON: antismash.detection.cluster_hmmer"),
            "TIGRFAM domains": (tigr_n, tigr_raw, "AS JSON: antismash.detection.tigrfam"),
            "NRPS/PKS predictions": (nrps_n, nrps_raw, "AS JSON: antismash.modules.nrps_pks"),
            "Active-site finder": (active_n, active_raw, "AS JSON: antismash.modules.active_site_finder"),
            "TTA/bldA": (tta_n, tta_raw, "AS JSON: antismash.modules.tta"),
        }

        interpretations = {
            "Gene overview": "Primary raw location/product/gene-order evidence; use as the card anchor.",
            "Tailoring": "Tailoring-like domains are enzyme-presence evidence only; product effects remain inferred.",
            "MIBiG comparison": "Comparator-family context; never product identity.",
            "ClusterBlast": "Genomic-neighbourhood similarity outside the curated known-cluster anchor.",
            "KnownClusterBlast": "Strong named comparator layer when high, but still similarity not identity.",
            "SubClusterBlast": "Zero hits are negative evidence for confidently captured sub-operons such as sugar/tailoring cassettes.",
            "TFBS Finder": "Weak/cross-species motifs are demoted; do not build a regulation model from them alone.",
            "Pfam domains": "Architecture and enzyme-family support; reconcile with gene table/HMM writeback.",
            "TIGRFAM domains": "Curated family support when present; zero hits block TIGRFAM-support claims.",
            "NRPS/PKS predictions": "Module/AT/KR/ordering predictions are structure-grammar evidence, not compound identity.",
            "Active-site finder": "Catalytic motif presence supports domain activity but does not prove expression/product.",
            "TTA/bldA": "TTA codon evidence can inform regulation only when present and biologically relevant.",
        }
        followups = {
            "Gene overview": "Use node/region in §1 and locus-map notes.",
            "Tailoring": "Confirm missing/off-contig sugar and glycosyltransferase genes by scaffolding or BLASTp.",
            "MIBiG comparison": "Use as context below KCB priority; report if KCB and cluster_compare disagree.",
            "ClusterBlast": "Check whether neighbour organisms/gene order support a genus-conserved locus.",
            "KnownClusterBlast": "Use kcb-frontpage or raw KCB table to report gene coverage/similarity.",
            "SubClusterBlast": "Report NO_HITS explicitly when relevant to missing submodule claims.",
            "TFBS Finder": "Only mention as weak/demoted unless strong same-genus motifs appear.",
            "Pfam domains": "Use domain counts in §4/§5 and HMM provenance.",
            "TIGRFAM domains": "Avoid TIGRFAM claims when NO_HITS.",
            "NRPS/PKS predictions": "Carry AT consensus and active/inactive KR calls into §5 when structure-relevant.",
            "Active-site finder": "Use to qualify catalytic-domain confidence.",
            "TTA/bldA": "If present, put regulatory implication in §7; if absent, do not infer bldA control.",
        }

        ledger=[]
        comparison=[]
        for tab, (n, raw, src) in raw_by_tab.items():
            mextract, status = _mamey_status_for_layer(tab, triage, pkg_rows, bgc)
            missed = status
            if tab in {"Tailoring", "Pfam domains"} and status == "captured":
                missed = "underused"
            ledger.append({
                "tab": tab,
                "direct_evidence": "positive" if n else "no positive evidence",
                "raw_result": raw,
                "mamey_extraction": mextract,
                "interpretation": interpretations[tab],
                "missed_or_underused": missed,
                "follow_up": followups[tab],
                "source": src,
            })
            impact = "Card can cite deterministic Mamey field" if status == "captured" else ("Available raw evidence should be surfaced in Mode B" if n else "Negative evidence should be explicit")
            fix = "None" if status == "captured" else f"Surface {tab} in tab-reconcile ledger / package provenance"
            comparison.append({"layer": tab, "status": status, "impact": impact, "recommended_fix": fix, "source": src})

        # v9.7.233: only prepend the BGC id segment when --bgc was actually supplied. The old
        # `{bgc or _safe_name(rec_id)}_{_safe_name(rec_id)}` collapsed to `<node>_<node>` on the
        # --node/--region path (no --bgc), duplicating the node id in every output filename.
        prefix = f"{bgc}_{_safe_name(rec_id)}" if bgc else _safe_name(rec_id)
        ledger_csv = outdir / f"{prefix}_ANTISMASH_TAB_EVIDENCE_LEDGER.csv"
        comp_csv = outdir / f"{prefix}_ANTISMASH_VS_MAMEY_COMPARISON.csv"
        _write_csv(ledger_csv, ledger, LEDGER_FIELDS)
        _write_csv(comp_csv, comparison, COMPARISON_FIELDS)
        _write_html(outdir / f"{prefix}_EVIDENCE_LEDGER.html", f"antiSMASH tab evidence ledger — {bgc or rec_id}", ledger, LEDGER_FIELDS)
        # JSON summary for automated gates.
        summary = {
            "bgc": bgc,
            "record_id": rec_id,
            "region": region or ctx.get("antismash_region") or "region001",
            "node": node or ctx.get("node_id") or ctx.get("Node_ID") or rec_id,
            "source_json": data.get("_source_json"),
            "ledger_csv": str(ledger_csv),
            "comparison_csv": str(comp_csv),
            "tabs": {row["tab"]: {"direct_evidence": row["direct_evidence"], "status": row["missed_or_underused"]} for row in ledger},
        }
        (outdir / f"{prefix}_tab_reconcile_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        # Markdown report.
        md=[f"# antiSMASH tab reconciliation — {bgc or rec_id}", "", f"Record: `{rec_id}`", "", "## Evidence ledger", ""]
        for row in ledger:
            md.append(f"### {row['tab']}")
            md.append(f"- Direct evidence: **{row['direct_evidence']}**")
            md.append(f"- Raw result: {row['raw_result']}")
            md.append(f"- Mamey extraction: {row['mamey_extraction']}")
            md.append(f"- Status: **{row['missed_or_underused']}**")
            md.append(f"- Interpretation: {row['interpretation']}")
            md.append("")
        (outdir / f"{prefix}_TAB_RECONCILIATION_REPORT.md").write_text("\n".join(md), encoding="utf-8")
        return summary
    finally:
        if tmp: tmp.cleanup()
        if pkg_tmp: pkg_tmp.cleanup()


def tab_reconcile_command(args) -> int:
    summary = build_tab_reconciliation(
        args.antismash, args.out, bgc=args.bgc, node=args.node, region=args.region, package=args.package
    )
    emit(f"tab-reconcile complete: {summary['bgc'] or summary['record_id']}", f"  ledger     : {summary['ledger_csv']}", f"  comparison : {summary['comparison_csv']}", sep="\n")
    return 0
