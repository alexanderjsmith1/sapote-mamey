"""raw_antismash_triage.py — guided pre-extraction genome triage (new, v9.7.233).

NAMING NOTE (v9.7.233 merge): an independent parallel session built a DIFFERENT, also
genuinely valuable "mamey explore" — mamey/genome_explore.py, operating on a SEALED
package (scan_divergence/scan_co_capture/exploration_board, nr-preferred conservation,
"is this claim internally consistent" correctness checks). Both modules were built the
same day under the same "genome exploration mode" brief and originally collided on the
same file name and CLI verb. This module is renamed to raw_antismash_triage.py / CLI
verb `mamey triage-raw` to resolve that collision. The two tools are complementary, not
redundant: this one runs BEFORE extraction, directly on a raw antiSMASH ZIP/dir, to
prioritize which regions are worth a person's first five minutes (named KCB leads +
rare/watchlist motifs + scanner gate evidence + split-candidate warnings). The official
`mamey explore` runs AFTER extraction, on a sealed package, to check whether an
authored/authoring claim of novelty or divergence is actually correct against nr-level
evidence. Neither replaces the other.

Chains the Layer 0/2/3 "read what's already there, cheaply, first" analysis modules into
one pass over a single strain's antiSMASH output, in the exact order
`Sapote_Mamey_ROADMAP.md` documents under "The order operations SHOULD run":

    1. KCB front page   (mamey.kcb_frontpage.read_frontpage)  — named leads, tiered
    2. Scanner evidence  (this module, new)                    — gate/support domain census
    3. Rare-motif scan  (mamey.rare_motif.rare_motif_scan)     — the actual unknowns
    4. Split candidates (mamey.split_detector.detect)          — fragmented-assembly warning
    5. bgc_walk on the resulting priority regions               — ordered domain architecture

As of v9.7.232 these four modules exist, are individually tested, and are individually
documented — but per the roadmap's own "Known gaps / not built" section, none of them is
wired into the standard run or reachable as a single command; each needs its own separate
invocation, and `bgc_walk` additionally needs its own HMM-database resolution wired by
hand. This module and the `mamey explore` CLI verb are exactly that missing wiring: an
analyst-facing "look at this strain" mode built from what already exists. It adds no new
inference logic beyond one thing (see below) and fires no new capability calls.

Accretion-justified: none of the four chained modules import each other or share a
run-order concept today; this is a distinct orchestration/prioritization concern (which
regions are worth a human's next five minutes) from extraction, scanning, or judgment.

Claim-safety note on step 2 (scanner evidence): this module deliberately does NOT
auto-fire a verdict for any of the 29 scanner-registry rules. Each rule's `rule` field is
free text (count thresholds, mutual-exclusion clauses, negative traps) — correctly
auto-interpreting all 29 is exactly the automation the roadmap itself says is "designed
but not automated," and getting even one wrong would misrepresent a capacity call. What
IS mechanically safe, and is exactly what this module reports: which of a scanner's
`gate` domains are observed vs. missing in a region (`gate` is always a literal domain
list in the registry — presence/absence is a fact, not an interpretation), the observed
`support`-domain hit count, and the scanner's own `rule` + `trap` text verbatim — evidence
for a human or an authoring LLM to apply the final judgment, the same evidence-first
posture the rest of the Mode B pipeline already uses (BLASTp REFINE/OVERTURN, HMM
adjudication AMBIGUOUS/INSUFFICIENT: surface, never auto-decide).
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

import glob
import json
import re
import os
import zipfile
from pathlib import Path
from typing import Any

from Bio import SeqIO

from .ziputil import safe_extract_all
from . import kcb_frontpage as _kcb_frontpage
from . import rare_motif as _rare_motif
from . import split_detector as _split_detector
from . import wheelhouse as _wheelhouse


# ---------------------------------------------------------------------------
# Input staging (an antiSMASH ZIP -> an on-disk strain_dir the four modules expect)
# ---------------------------------------------------------------------------

def _safe_extract_zip(z: zipfile.ZipFile, dest: Path) -> None:
    """Back-compat shim; canonical guard now lives in mamey.ziputil (v9.7.367)."""
    safe_extract_all(z, dest)


def stage_strain_dir(input_zip: str | Path, dest: str | Path) -> Path:
    """Extract a raw antiSMASH output ZIP to `dest` and return the directory that
    actually contains the region GBKs (which may be nested one level inside the zip)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_zip) as z:
        _safe_extract_zip(z, dest)
    macosx = dest / "__MACOSX"
    if macosx.exists():
        import shutil
        shutil.rmtree(macosx, ignore_errors=True)
    region_gbks = list(dest.glob("**/*region*.gbk"))
    if not region_gbks:
        raise ValueError(
            f"{input_zip} doesn't look like an antiSMASH output ZIP — no *region*.gbk "
            f"found after extraction. See COMPANION_FILES.md."
        )
    return region_gbks[0].parent


# ---------------------------------------------------------------------------
# Step 2 (new) — scanner evidence census: gate/support domain presence per region
# ---------------------------------------------------------------------------

def _resolve_scanner_registry(bundle_root: Path | None = None) -> dict | None:
    """Locate and load the highest-version scanner registry in the Wheelhouse, mirroring
    the version-selection convention `mamey wheelhouse list` already uses (sorted glob,
    take the last = highest version). Returns None if no registry is present."""
    if bundle_root is None:
        bundle_root = Path(__file__).resolve().parent.parent
    wh = Path(bundle_root) / "Wheelhouse"
    candidates = list((wh / "scanners").glob("scanner_registry_v*.json"))
    if not candidates:
        return None
    # pick the highest version by NUMERIC (major, minor) key — lexicographic sorted()[-1] mis-orders
    # v0.10 < v0.5 once the minor reaches double digits. Registries are dotted (v0.2..v0.5 today).
    def _reg_ver(path):
        mm = re.search(r"v(\d+)\.(\d+)", path.name)
        return (int(mm.group(1)), int(mm.group(2))) if mm else (-1, -1)
    latest = max(candidates, key=_reg_ver)
    with open(latest, encoding="utf-8") as fh:
        registry = json.load(fh)
    registry["_source_path"] = str(latest)
    return registry


def _region_domain_tokens(gbk_path: str) -> tuple[set[str], str | None]:
    """All sec_met_domain tokens observed anywhere in one region GBK, plus its antiSMASH
    product label. Domain tokens are truncated at the first space (matching the convention
    every other module in this file already uses, e.g. rare_motif._region_domains)."""
    domains: set[str] = set()
    product = None
    for rec in SeqIO.parse(gbk_path, "genbank"):
        for feat in rec.features:
            if feat.type == "region":
                product = ";".join(feat.qualifiers.get("product", []))
            if feat.type == "CDS":
                for d in feat.qualifiers.get("sec_met_domain", []):
                    domains.add(str(d).split(" ")[0])
    return domains, product


def scanner_evidence(strain_dir: str | Path, bundle_root: Path | None = None) -> dict:
    """Per-region, per-scanner evidence census against the Wheelhouse scanner registry.

    Returns {"registry_version", "registry_path", "regions": {region_id: [{scanner_id,
    name, cls, gate_present, gate_missing, gate_complete, support_hits, rule, trap}]}}.
    A scanner entry is only listed for a region when at least one of its gate/support
    domains is observed there (keeps the census readable — 29 scanners x every region
    with mostly-empty rows would bury the signal).

    `gate_complete=True` means every literal domain in the scanner's `gate` list was
    observed in that region — a mechanical fact. It is NOT the same as "scanner fires":
    several scanners' `rule` text requires additional conditions (a count threshold, a
    co-occurrence window, a mutual-exclusion check) this function does not evaluate. See
    the module docstring for why that line is drawn here.
    """
    registry = _resolve_scanner_registry(bundle_root)
    if registry is None:
        return {"registry_version": None, "registry_path": None, "regions": {},
                "note": "no scanner registry found under Wheelhouse/scanners/"}

    scanners = registry.get("scanners", [])
    out_regions: dict[str, list[dict]] = {}
    for gbk in sorted(glob.glob(f"{strain_dir}/**/*region*.gbk", recursive=True)):
        if "MACOSX" in gbk:
            continue
        rid = Path(gbk).name.replace(".gbk", "")
        doms, _product = _region_domain_tokens(gbk)
        if not doms:
            continue
        rows = []
        for sc in scanners:
            gate = set(sc.get("gate", []) or [])
            support = set(sc.get("support", []) or [])
            gate_present = sorted(gate & doms)
            gate_missing = sorted(gate - doms)
            support_hits = sorted(support & doms)
            if not gate_present and not support_hits:
                continue  # nothing about this scanner is even partially observed here
            rows.append({
                "scanner_id": sc.get("id"),
                "name": sc.get("name"),
                "cls": sc.get("cls"),
                "gate_present": gate_present,
                "gate_missing": gate_missing,
                "gate_complete": bool(gate) and not gate_missing,
                "support_hits": support_hits,
                "n_support_hits": len(support_hits),
                "rule": sc.get("rule"),
                "trap": sc.get("trap"),
                "test_status": sc.get("test_status"),
            })
        if rows:
            rows.sort(key=lambda r: (not r["gate_complete"], -r["n_support_hits"]))
            out_regions[rid] = rows
    return {
        "registry_version": registry.get("registry_version"),
        "registry_path": registry.get("_source_path"),
        "n_scanners": len(scanners),
        "regions": out_regions,
    }


# ---------------------------------------------------------------------------
# Priority ranking — combine the (independent) signals into one explore order
# ---------------------------------------------------------------------------

def _kcb_anchor_to_region_id(strain_dir: str | Path) -> dict[str, str]:
    """Map antiSMASH's KnownClusterBlast front-page anchor keys (e.g. "r7c1", read from
    `regions.js`'s `resultsData`/`read_frontpage`) to the same `NODE_..._regionNNN` region
    id the other three modules (rare_motif, split_detector, scanner_evidence) key on from
    GBK filenames.

    Without this, `kcb_frontpage`'s "r{n}c{n}" anchors and the GBK-filename-based region
    ids are two DIFFERENT id spaces for the same underlying regions, and naively bucketing
    by both side by side (as an early version of rank_priority_regions did) silently never
    merges a region's KCB lead with its rare-motif/scanner signal — verified against a real
    AS-XXX run, where this produced a 5-region priority list carrying rare-motif/scanner
    evidence but showing zero KCB hits, even though 36 real KCB hits existed in the same
    strain.

    The mapping is derived directly from `regions.js`'s own `recordData`: record i's
    `seq_id` is the contig name (== the GBK filename prefix), and each of its `regions[j]`
    carries `idx` (the antiSMASH region number, 1-based) and `anchor` (== "r{i+1}c{j+1}",
    the same key `read_frontpage` returns). Region ids are zero-padded to 3 digits to match
    the real GBK naming (`...region001.gbk`), the same convention `kcb_frontpage`'s own
    docstring assumes.
    """
    js_files = [f for f in glob.glob(f"{strain_dir}/**/regions.js", recursive=True)
                if "MACOSX" not in f]
    if not js_files:
        return {}
    import re as _re
    txt = open(js_files[0], encoding="utf-8", errors="ignore").read()
    m = _re.search(r"var\s+recordData\s*=\s*(\[.*?\]);\s*var\s+all_regions", txt, _re.DOTALL)
    if not m:
        return {}
    try:
        record_data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    anchor_map: dict[str, str] = {}
    for rec in record_data:
        seq_id = rec.get("seq_id")
        if not seq_id:
            continue
        for reg in rec.get("regions", []):
            anchor = reg.get("anchor")
            idx = reg.get("idx")
            if anchor and idx:
                anchor_map[anchor] = f"{seq_id}.region{int(idx):03d}"
    return anchor_map


_KCB_TIER_RANK = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "LARGE_GENERIC": 3,
                   "COINCIDENTAL": 4, "LOW": 5}


def rank_priority_regions(frontpage_hits: list[dict], rare_ranked: list[dict],
                           scanner_ev: dict, split_candidates: list[dict]) -> list[dict]:
    """Combine the four independent evidence sources into one explore-first ordering.

    This is a PRIORITIZATION heuristic, not a capability or novelty score — it decides
    what a person should look at first, nothing more. Each contributing signal is kept
    visible in the output (`why`) rather than collapsed into an opaque number, so the
    ranking can be checked against its own inputs.
    """
    by_region: dict[str, dict] = {}

    def _bucket(rid: str) -> dict:
        return by_region.setdefault(rid, {
            "region": rid, "kcb": None, "rare_motifs": [], "important_motifs": [],
            "scanner_gate_complete": [], "split_candidate": False, "why": [],
        })

    for h in frontpage_hits:
        rid = h.get("region")
        if not rid:
            continue
        b = _bucket(rid)
        b["kcb"] = {"compound": h.get("compound"), "tier": h.get("tier"),
                     "similarity": h.get("similarity"), "n_genes": h.get("n_genes")}
        if h.get("tier") == "STRONG":
            b["why"].append(f"KCB STRONG lead: {h.get('compound')}")
        elif h.get("tier") == "LOW" or not h.get("tier"):
            b["why"].append("no strong named lead (KCB corroboration low/absent) — a candidate unknown")

    for r in rare_ranked:
        rid = r.get("region", "").split(":")[-1] if ":" in r.get("region", "") else r.get("region")
        if not rid:
            continue
        b = _bucket(rid)
        b["rare_motifs"] = r.get("rare_motifs", [])
        b["important_motifs"] = r.get("important_motifs", [])
        if r.get("important_motifs"):
            b["why"].append(f"high-value motif watchlist hit: {', '.join(r['important_motifs'])}")
        if r.get("rare_motifs"):
            b["why"].append(f"{len(r['rare_motifs'])} genome-rare domain(s)")

    for rid, rows in (scanner_ev.get("regions") or {}).items():
        b = _bucket(rid)
        fired = [row["scanner_id"] for row in rows if row["gate_complete"]]
        b["scanner_gate_complete"] = fired
        if fired:
            b["why"].append(f"scanner gate domains complete: {', '.join(fired)} (verify rule/trap before claiming)")

    for c in split_candidates:
        for rid, role in ((c.get("body"), "body"), (c.get("fragment"), "fragment")):
            if not rid:
                continue
            b = _bucket(rid)
            b["split_candidate"] = True
            b["why"].append(
                f"contig-end split candidate ({role}, confidence={c.get('confidence')}, "
                f"paralog_id={c.get('best_paralog_id')}%) — likely fragmented, "
                f"boundary claims need care"
            )

    def _score(b: dict) -> tuple:
        kcb_rank = _KCB_TIER_RANK.get((b["kcb"] or {}).get("tier"), 6)
        important = len(b["important_motifs"])
        rare = len(b["rare_motifs"])
        gates = len(b["scanner_gate_complete"])
        # Priority: important-motif hits and complete scanner gates first (concrete,
        # checkable capability signal), then STRONG KCB leads, then rare-motif count.
        return (-(important * 3 + gates * 2), kcb_rank, -rare)

    ranked = sorted(by_region.values(), key=_score)
    return ranked


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

def explore_strain(strain_dir: str | Path, *, bundle_root: Path | None = None,
                    top_n: int = 5, run_bgc_walk: bool = True) -> dict:
    """Run the full Layer 0/2/3 exploration pass over one strain's antiSMASH output dir
    and return a structured, JSON-serializable report. Every step is best-effort and
    independently failure-isolated (matches the project's established `render-all-figures`
    convention: one module's absence/failure never blocks the others)."""
    report: dict[str, Any] = {"strain_dir": str(strain_dir), "steps": {}}

    # Step 1 — KCB front page
    try:
        frontpage_hits = _kcb_frontpage.read_frontpage(str(strain_dir))
        anchor_map = _kcb_anchor_to_region_id(strain_dir)
        _unmapped = 0
        for h in frontpage_hits:
            anchor = h.get("region")
            if anchor in anchor_map:
                h["region"] = anchor_map[anchor]
            else:
                _unmapped += 1  # keep the raw anchor as a fallback rather than dropping the hit
        report["steps"]["kcb_frontpage"] = {"status": "RAN", "n_hits": len(frontpage_hits),
                                             "n_unmapped_anchors": _unmapped}
    except Exception as e:
        frontpage_hits = []
        report["steps"]["kcb_frontpage"] = {"status": "ERRORED", "error": f"{type(e).__name__}: {e}"}

    # Step 2 — scanner evidence (new)
    try:
        scanner_ev = scanner_evidence(strain_dir, bundle_root=bundle_root)
        n_regions_with_evidence = len(scanner_ev.get("regions") or {})
        report["steps"]["scanner_evidence"] = {
            "status": "RAN" if scanner_ev.get("registry_version") else "SKIPPED",
            "registry_version": scanner_ev.get("registry_version"),
            "n_scanners": scanner_ev.get("n_scanners"),
            "n_regions_with_evidence": n_regions_with_evidence,
            "skipped_reason": scanner_ev.get("note"),
        }
    except Exception as e:
        scanner_ev = {"regions": {}}
        report["steps"]["scanner_evidence"] = {"status": "ERRORED", "error": f"{type(e).__name__}: {e}"}

    # Step 3 — rare-motif scan
    try:
        rare_ranked, domain_counts = _rare_motif.rare_motif_scan([str(strain_dir)])
        report["steps"]["rare_motif"] = {"status": "RAN", "n_flagged_regions": len(rare_ranked)}
    except Exception as e:
        rare_ranked, domain_counts = [], {}
        report["steps"]["rare_motif"] = {"status": "ERRORED", "error": f"{type(e).__name__}: {e}"}

    # Step 4 — contig-end split candidates
    # NOTE: split_detector.detect() returns a LIST of {body, fragment, score, confidence, ...}
    # candidate pairs (a region-pair hypothesis: `body` = the larger piece, `fragment` = the
    # likely continuation on another contig) — not a dict keyed by a single region id. Both
    # `body` and `fragment` region ids are surfaced as split candidates below.
    try:
        split_pairs = _split_detector.detect(str(strain_dir))
        split_candidates = split_pairs
        report["steps"]["split_detector"] = {"status": "RAN", "n_candidates": len(split_candidates)}
    except Exception as e:
        split_candidates = []
        report["steps"]["split_detector"] = {"status": "ERRORED", "error": f"{type(e).__name__}: {e}"}

    # Rank
    priority = rank_priority_regions(frontpage_hits, rare_ranked, scanner_ev, split_candidates)
    report["priority_regions"] = priority[:max(top_n, 0)] if top_n else priority
    report["frontpage_hits"] = frontpage_hits
    report["rare_motif_ranked"] = rare_ranked
    report["split_candidates"] = split_candidates
    report["scanner_evidence"] = scanner_ev

    # Step 5 — bgc_walk on the top-N priority regions (needs pyhmmer + an HMM db; best-effort)
    walks: dict[str, Any] = {}
    if run_bgc_walk and report["priority_regions"]:
        try:
            from . import bgc_walk as _bgc_walk
            hmm_info = _wheelhouse.resolve_hmm_database(bundle_root)
            for b in report["priority_regions"]:
                rid = b["region"]
                gbk_matches = glob.glob(f"{strain_dir}/**/{rid}.gbk", recursive=True)
                if not gbk_matches:
                    continue
                genes, hits = _bgc_walk.bgc_walk(gbk_matches[0], hmm_info["path"])
                rare_domains = set()
                for r in rare_ranked:
                    if r.get("region", "").endswith(rid):
                        rare_domains |= set(r.get("rare_motifs", []))
                walks[rid] = _bgc_walk.render_walk(genes, hits, rare_domains=rare_domains)
            report["steps"]["bgc_walk"] = {"status": "RAN" if walks else "SKIPPED",
                                            "n_regions_walked": len(walks),
                                            "hmm_db": hmm_info.get("path"),
                                            "hmm_tier": hmm_info.get("tier")}
        except Exception as e:
            report["steps"]["bgc_walk"] = {"status": "SKIPPED",
                                            "skipped_reason": f"{type(e).__name__}: {e} "
                                                               "(needs pyhmmer + an HMM database; "
                                                               "install_sapote_addons.sh)"}
    else:
        report["steps"]["bgc_walk"] = {"status": "SKIPPED",
                                        "skipped_reason": "run_bgc_walk=False or no priority regions"}
    report["bgc_walks"] = walks

    return report


def render_explore_report_md(report: dict, strain_name: str = "") -> str:
    """Render the explore_strain() report as a compact, human-readable markdown page —
    the "30-second answer a postdoc gets" the roadmap describes for the KCB front page,
    extended to all four Layer 0/2/3 signals."""
    lines = [f"# Genome exploration — {strain_name or report.get('strain_dir', '')}", ""]
    lines.append("Steps run: " + ", ".join(
        f"{k}={v.get('status')}" for k, v in report["steps"].items()))
    lines.append("")
    lines.append("## Priority regions (explore-first order)")
    if not report["priority_regions"]:
        lines.append("_No regions carried enough KCB/rare-motif/scanner/split signal to prioritize._")
    for b in report["priority_regions"]:
        lines.append(f"\n### {b['region']}")
        if b["kcb"]:
            k = b["kcb"]
            lines.append(f"- KCB: **{k['tier']}** — {k['compound']} "
                          f"({k['similarity']}% sim, {k['n_genes']} genes) — a lead, not a verdict.")
        if b["scanner_gate_complete"]:
            lines.append(f"- Scanner gate domains complete: {', '.join(b['scanner_gate_complete'])} "
                          f"— check `rule`/`trap` in the scanner_evidence detail before claiming capacity.")
        if b["important_motifs"]:
            lines.append(f"- High-value motif watchlist: {', '.join(b['important_motifs'])}")
        if b["rare_motifs"]:
            lines.append(f"- Rare (genome-wide) domains: {', '.join(b['rare_motifs'])}")
        if b["split_candidate"]:
            lines.append("- ⚠ Contig-end split candidate — treat as a fragmented-assembly lead, not a sealed boundary.")
        walk = report.get("bgc_walks", {}).get(b["region"])
        if walk:
            lines.append("\n```\n" + walk + "\n```")
        for w in b["why"]:
            lines.append(f"  - _{w}_")
    return "\n".join(lines)


def explore_command(args) -> int:
    """CLI entry point for `mamey explore`."""
    strain_dir = args.strain_dir
    tmp_dir = None
    if getattr(args, "input_zip", None):
        # v9.7.409 (AUDIT_cli_edgecases): guard the ZIP before stage_strain_dir opens it. A missing
        # path used to crash with a raw FileNotFoundError and a non-zip file with a raw
        # zipfile.BadZipFile; `inspect` refuses these cleanly and triage-raw did not. Mirror it.
        if not Path(args.input_zip).is_file():
            emit(f"ERROR: triage-raw input zip not found: {args.input_zip}",
                  file=__import__("sys").stderr)
            return 1
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="mamey_explore_")
        try:
            strain_dir = str(stage_strain_dir(args.input_zip, tmp_dir))
        except zipfile.BadZipFile:
            emit(f"ERROR: triage-raw input is not a valid zip: {args.input_zip}",
                  file=__import__("sys").stderr)
            return 1
    if not strain_dir:
        emit("mamey explore: supply --strain-dir <extracted antiSMASH dir> "
              "or --input-zip <antiSMASH.zip>", file=__import__("sys").stderr)
        return 1

    report = explore_strain(strain_dir, top_n=getattr(args, "top_n", 5),
                             run_bgc_walk=not getattr(args, "no_walk", False))
    md = render_explore_report_md(report, strain_name=getattr(args, "strain", "") or "")

    out = getattr(args, "out", None)
    if out:
        Path(out).write_text(md, encoding="utf-8")
        if getattr(args, "json", False):
            Path(str(out).rsplit(".", 1)[0] + ".json").write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8")
        emit(f"wrote {out}")
    else:
        emit(md)
    if getattr(args, "json", False) and not out:
        emit("\n---\n", json.dumps(report, indent=2, default=str), sep="\n")
    return 0
