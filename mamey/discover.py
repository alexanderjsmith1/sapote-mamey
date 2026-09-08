#!/usr/bin/env python3
"""mamey discover — orient inside a Mamey workspace and report what's here + what to do next.

A read-only companion to `doctor` (env), `inspect` (one input), and `explain` (one package).
Run it anywhere: point it at a single sealed package, a runs/ tree, or a whole deliverables
workspace, and it enumerates every Mamey artifact it finds, each package's completeness, the
figure/Mode-B/BLASTp coverage, any patch/cut staging folders, and a ranked list of the next
subcommands that would move the work forward. Judgment deferred: it reports state, it does not run.

Usage:
    python mamey_run.py discover [ROOT] [--json] [--emit-md PATH] [--depth N]
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
import os, json, argparse
from pathlib import Path

from .manifest_schema import read_manifest_field  # canonical trap-field reader (no raw ms.get on trap fields)
from .workspace_source_discovery import ScanLimits, build_source_catalog, write_catalog

# ---- a package is any dir carrying a Mamey manifest -----------------------
PKG_MARKERS = ("manifest_short.json", "manifest.json")

def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

def _find_packages(root: Path, max_depth: int):
    """Yield package directories under root (a dir with a manifest is a package)."""
    root = root.resolve()
    base_depth = len(root.parts)
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        if len(d.parts) - base_depth > max_depth:
            dirnames[:] = []
            continue
        # skip noise
        dirnames[:] = [x for x in dirnames if x not in
                       (".git", "__pycache__", "node_modules", "_vendor", ".DS_Store")]
        if any((d / m).is_file() for m in PKG_MARKERS) and d not in seen:
            seen.add(d)
            yield d
            dirnames[:] = []  # don't descend into a package's own subdirs

def _capabilities(pkg: Path) -> dict:
    """File-presence flags for post-seal layers (what's been produced for this strain)."""
    names = {p.name for p in pkg.iterdir()} if pkg.is_dir() else set()
    def any_suffix(suf):  # e.g. a numbered per-strain output
        return any(n.endswith(suf) for n in names)
    has_worklist = any_suffix("_5b_manual_blastp_worklist.csv")
    return {
        "figures":   ("gold_figures" in names) or any_suffix("_8a_fig_landscape.png"),
        "mode_b":    any_suffix("modeb_verdicts.csv") or ("modeb_verdicts.csv" in names),
        "blastp":    ("bgc_blastp_panel" in names),
        "blastp_worklist_only": has_worklist and ("bgc_blastp_panel" not in names),
        "report":    any_suffix("_compiled_report.md"),
        "cohort_src":("cohort_source" in names),
    }

def _counts(pkg: Path) -> dict:
    """Depth counts for the coverage grid (0 when a layer is absent). Answers 'how many
    Mode-B cards / BLASTp panels / figures', not just present/absent."""
    if not pkg.is_dir():
        return {"figures": 0, "mode_b": 0, "blastp": 0}
    names = list(pkg.iterdir())
    gf = pkg / "gold_figures"
    if gf.is_dir():
        figures = sum(1 for p in gf.iterdir() if p.suffix.lower() == ".png")
    else:
        figures = sum(1 for p in names if p.name.endswith(".png") and "_8" in p.name and "_fig" in p.name)
    mb = next((p for p in names if p.name.endswith("modeb_verdicts.csv")), None)
    mode_b = 0
    if mb:
        try:  # data rows (verdicts) = lines minus the header
            mode_b = max(0, sum(1 for _ in mb.open(encoding="utf-8", errors="ignore")) - 1)
        except OSError:
            mode_b = 0
    bp = pkg / "bgc_blastp_panel"
    blastp = sum(1 for _ in bp.iterdir()) if bp.is_dir() else 0
    return {"figures": figures, "mode_b": mode_b, "blastp": blastp}

def _scan_package(pkg: Path) -> dict:
    ms = _load(next((pkg / m for m in PKG_MARKERS if (pkg / m).is_file()), pkg / "manifest_short.json"))
    gate = _load(pkg / "gate_validation.json")
    rec  = _load(pkg / "gold_mode_receipt.json")
    caps = _capabilities(pkg)
    return {
        "path": str(pkg),
        "strain": ms.get("strain_id", pkg.parent.name if pkg.name == "package" else pkg.name),
        "engine": ms.get("mamey_version", "?"),
        "release": ms.get("release", "?"),
        "status": ms.get("status") or gate.get("status", "?"),
        "gate": gate.get("status", "?"),
        "tier": read_manifest_field("assembly_tier", manifest=ms, manifest_short=ms, default="?"),
        "mode": rec.get("mode", "?"),
        "raw_bgcs": read_manifest_field("raw_bgcs", manifest=ms, manifest_short=ms, default=None),
        "corrected_bgcs": read_manifest_field("corrected_bgcs", manifest=ms, manifest_short=ms, default=None),
        "caps": caps,
        "counts": _counts(pkg),
    }

# ---- workspace-level context (patches, figure decks, master workbooks) ----
def _workspace_context(root: Path, max_depth: int) -> dict:
    root = root.resolve(); base = len(root.parts)
    cut_dirs, patch_files, masters, fig_decks = [], [], [], []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        if len(d.parts) - base > max_depth:
            dirnames[:] = []; continue
        dirnames[:] = [x for x in dirnames if x not in
                       (".git", "__pycache__", "node_modules", ".DS_Store")]
        low = d.name.lower()
        if ("patches and diffs" in low) or low == "red" or "candidate_cut" in low:
            cut_dirs.append(str(d))
        for f in filenames:
            fl = f.lower()
            if fl.endswith((".patch", ".diff")): patch_files.append(str(d / f))
            elif "master" in fl and fl.endswith(".xlsx"): masters.append(str(d / f))
            elif fl.startswith(("cohort", "cross_strain", "collection")) and fl.endswith((".png", ".pdf")):
                fig_decks.append(str(d / f))
    return {"cut_dirs": sorted(set(cut_dirs)), "patch_count": len(patch_files),
            "master_workbooks": sorted(set(masters)), "figure_deck_count": len(fig_decks)}

# ---- turn state into ranked next-actions ----------------------------------
def _suggest(pkgs: list[dict], ctx: dict) -> list[str]:
    s = []
    n = len(pkgs)
    incomplete = [p for p in pkgs if p["gate"] not in ("PASS", "PASS_WITH_ISSUES", "MAMEY_COMPLETE", "?")]
    no_fig  = [p for p in pkgs if not p["caps"]["figures"]]
    no_mb   = [p for p in pkgs if not p["caps"]["mode_b"]]
    bp_wait = [p for p in pkgs if p["caps"]["blastp_worklist_only"]]
    if incomplete:
        s.append(f"validate — {len(incomplete)} package(s) not at a passing gate: "
                 + ", ".join(p['strain'] for p in incomplete[:6]))
    if bp_wait:
        s.append(f"ingest-blastp — {len(bp_wait)} package(s) have a BLASTp worklist but no ingested panel: "
                 + ", ".join(p['strain'] for p in bp_wait[:6]))
    if no_fig:
        s.append(f"render-all-figures — {len(no_fig)} package(s) have no figure set")
    if no_mb:
        s.append(f"mode-b — {len(no_mb)} package(s) have no Mode-B verdicts")
    if n >= 2 and ctx["figure_deck_count"] == 0:
        s.append(f"cohort-figures / cohort — {n} packages present but no cohort figure deck found")
    if ctx["cut_dirs"]:
        s.append(f"note — {len(ctx['cut_dirs'])} patch/cut staging folder(s) and {ctx['patch_count']} "
                 f".patch/.diff file(s) present (pending cut work)")
    stale = [p for p in pkgs if p.get("stale")]
    if stale:
        s.append(f"re-run (engine drift) — {len(stale)} package(s) on an older engine than the "
                 f"newest run present: " + ", ".join(f"{p['strain']}({p['engine']})" for p in stale[:8]))
    if not s:
        if n == 0:
            s.append("no packages found — point `discover` at a directory containing sealed "
                     "Mamey packages (a run output dir, or a workspace holding them)")
        else:
            s.append("all scanned packages look complete — consider compile-report / cohort synthesis")
    return s

def _vtuple(v):
    """Parse an engine version like '1.9.111' into a comparable int tuple, else None."""
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (ValueError, AttributeError):
        return None

def run(
    root: Path,
    max_depth: int,
    current: str | None = None,
    *,
    source_collection_registry: Path | None = None,
    expected_source_collection_registry_sha256: str | None = None,
    source_root_id: str | None = None,
    source_scan_limits: ScanLimits | None = None,
) -> dict:
    pkgs = [_scan_package(p) for p in _find_packages(root, max_depth)]
    pkgs.sort(key=lambda p: p["strain"])
    # engine reference = explicit --current, else the newest engine seen among packages.
    vts = [t for t in (_vtuple(p["engine"]) for p in pkgs) if t]
    ref = _vtuple(current) if current else (max(vts) if vts else None)
    for p in pkgs:
        t = _vtuple(p["engine"])
        p["stale"] = bool(ref and t and t < ref)
    ctx = _workspace_context(root, max_depth)
    report = {"root": str(root.resolve()),
              "engine_ref": (".".join(map(str, ref)) if ref else None),
              "packages": pkgs, "context": ctx, "next_actions": _suggest(pkgs, ctx)}
    if source_collection_registry is not None:
        if not expected_source_collection_registry_sha256 or not source_root_id:
            raise ValueError(
                "workspace evidence discovery requires the expected registry SHA-256 and source root ID"
            )
        report["source_catalog"] = build_source_catalog(
            root=root,
            root_id=source_root_id,
            collection_registry_path=source_collection_registry,
            expected_collection_registry_sha256=expected_source_collection_registry_sha256,
            limits=source_scan_limits or ScanLimits(max_depth=max_depth),
        )
    return report

def _render(rep: dict) -> str:
    L = [f"# Mamey discovery — {rep['root']}", ""]
    pk = rep["packages"]
    L.append(f"## Packages found: {len(pk)}")
    if pk:
        L.append("")
        L.append("| Strain | Engine | Release | Gate | Tier | BGCs (raw/corr) | Figs | ModeB | BLASTp | Report |")
        L.append("|---|---|---|---|---|---|--:|--:|--:|:--:|")
        def y(b): return "✓" if b else "·"
        def num(n): return str(n) if n else "·"
        for p in pk:
            c = p["caps"]; n = p.get("counts", {})
            bp = num(n.get("blastp", 0)) if not c["blastp_worklist_only"] else "⧗"
            eng = f"{p['engine']} ⚠" if p.get("stale") else p["engine"]
            L.append(f"| {p['strain']} | {eng} | {p['release']} | {p['gate']} | {p['tier']} | "
                     f"{p['raw_bgcs']}/{p['corrected_bgcs']} | {num(n.get('figures',0))} | "
                     f"{num(n.get('mode_b',0))} | {bp} | {y(c['report'])} |")
    ctx = rep["context"]
    nstale = sum(1 for p in pk if p.get("stale"))
    ref_line = (f"- engine reference: {rep['engine_ref']}"
                + (f"  ({nstale} older → ⚠ re-run candidates)" if nstale else "  (all current)")
                ) if rep.get("engine_ref") else "- engine reference: (unknown)"
    L += ["", "## Workspace context", ref_line,
          f"- patch/cut staging folders: {len(ctx['cut_dirs'])} ({ctx['patch_count']} .patch/.diff files)",
          f"- master workbooks: {len(ctx['master_workbooks'])}",
          f"- cohort/cross-strain figure files: {ctx['figure_deck_count']}"]
    source_catalog = rep.get("source_catalog")
    if source_catalog is not None:
        registered = sum(
            1 for row in source_catalog["collections"]
            if row["classification_state"] == "REGISTERED_SIGNATURE"
        )
        unclassified = len(source_catalog["collections"]) - registered
        L += ["", "## Workspace evidence collections",
              f"- source catalog status: {source_catalog['status']}",
              f"- registered collections: {registered}",
              f"- unclassified material requiring review: {unclassified}",
              "- discovery is not source admission; report consumers require explicit decisions"]
    L += ["", "## What you can do from here"]
    L += [f"- **{a}**" for a in rep["next_actions"]]
    return "\n".join(L)

def discover_command(args):
    registry = getattr(args, "source_collection_registry", None)
    rep = run(
        Path(args.root),
        args.depth,
        current=getattr(args, "current", None),
        source_collection_registry=Path(registry) if registry else None,
        expected_source_collection_registry_sha256=getattr(
            args, "expected_source_collection_registry_sha256", None
        ),
        source_root_id=getattr(args, "source_root_id", None),
        source_scan_limits=ScanLimits(
            max_depth=getattr(args, "source_depth", args.depth),
            max_files=getattr(args, "source_max_files", 100_000),
            max_apparent_bytes=getattr(args, "source_max_apparent_bytes", 20_000_000_000),
            max_seconds=getattr(args, "source_max_seconds", 60.0),
        ) if registry else None,
    )
    if getattr(args, "stale", False):  # filter the displayed table to re-run candidates
        rep = dict(rep, packages=[p for p in rep["packages"] if p.get("stale")])
    if getattr(args, "json", False):
        emit(json.dumps(rep, indent=2))
    else:
        emit(_render(rep))
    if getattr(args, "emit_md", None):
        Path(args.emit_md).write_text(_render(rep))
        emit(f"\n[wrote {args.emit_md}]")
    catalog_json = getattr(args, "emit_source_catalog_json", None)
    catalog_tsv = getattr(args, "emit_source_catalog_tsv", None)
    if bool(catalog_json) != bool(catalog_tsv):
        raise ValueError("both source-catalog output paths are required together")
    if catalog_json and "source_catalog" in rep:
        receipt = write_catalog(rep["source_catalog"], Path(catalog_json), Path(catalog_tsv))
        emit(f"\n[wrote source catalog: {receipt['collection_count']} collections, {receipt['status']}]")
    return 0

def _build_parser():
    p = argparse.ArgumentParser(prog="mamey discover",
        description="Orient in a Mamey workspace: list packages, coverage, and next actions.")
    p.add_argument("root", nargs="?", default=".", help="workspace / runs / package dir (default: .)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--emit-md", metavar="PATH", help="also write the report to a markdown file")
    p.add_argument("--depth", type=int, default=6, help="max recursion depth (default 6)")
    p.add_argument("--stale", action="store_true",
                   help="show only packages on an older engine than the newest run (re-run candidates)")
    p.add_argument("--current", metavar="VER",
                   help="engine version to treat as current (default: newest seen among packages)")
    p.add_argument("--source-collection-registry", metavar="PATH",
                   help="also run governed workspace evidence discovery with this registry")
    p.add_argument("--expected-source-collection-registry-sha256", metavar="SHA256",
                   help="required exact registry hash for workspace evidence discovery")
    p.add_argument("--source-root-id", metavar="ID",
                   help="logical source root ID; absolute paths are not written to the catalog")
    p.add_argument("--emit-source-catalog-json", metavar="PATH")
    p.add_argument("--emit-source-catalog-tsv", metavar="PATH")
    p.add_argument("--source-depth", type=int, default=6)
    p.add_argument("--source-max-files", type=int, default=100_000)
    p.add_argument("--source-max-apparent-bytes", type=int, default=20_000_000_000)
    p.add_argument("--source-max-seconds", type=float, default=60.0)
    return p

if __name__ == "__main__":
    raise SystemExit(discover_command(_build_parser().parse_args()))
