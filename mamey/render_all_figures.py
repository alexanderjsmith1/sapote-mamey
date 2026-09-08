"""render_all_figures.py — post-seal aggregate over every applicable figure module.

The motivating gap:
    `--chatgpt-safe` (the manifest-recommended profile for LLM sessions)
    hard-sets `--brief none` and `--locus-maps off` to keep the capped
    run fast. The brief figures (`_8a..._8m_fig_*.png` via render_brief +
    figures_extra) and locus maps are deliberately suppressed. A typical
    ChatGPT session run thus produces only the 3 figures_smoke PNGs.
    The user complaint "the figures are basically nonexistent" comes from
    not knowing there's a post-seal way to populate the full suite.

This command runs every figure module that operates on an already-sealed
package, in one shot, non-blocking per module. The user runs it AFTER the
capped --chatgpt-safe run completes — wall-clock budget is no longer the
constraint, and the slow modules (locus maps, mamey-native, domain-level)
can run freely.

Public API:
    mamey render-all-figures --package <pkg> [--include <set,set,...>]
                              [--exclude <set,set,...>] [--workbook <wb.xlsx>]
                              [--top-n N] [--continue-on-error] [--dry-run]

Sets that run by default (all data-only and non-blocking):
    brief          — `_8a..._8m_fig_*.png` via render_brief + figures_extra
    smoke          — bgc_ranking, class_composition, assembly_tier
    locus-maps     — per-BGC SVG locus maps (from gene_by_gene CSV, W5 path)
    figure-suite   — top_antibacterial_leads, top_antifungal_leads (the
                     `render-figures` default set)
    domain-level   — domain complexity metrics figures

Sets that require extra inputs (run only if inputs available):
    cohort-class   — needs --workbook <cohort.xlsx>
    mamey-native   — needs --workbook <Mamey_Master.xlsx>

Returns a structured summary: per-set status (RAN/SKIPPED/ERRORED), figure
counts, output paths.

W9-N14 / Gap 3 (v9.7.150e+).
"""
from __future__ import annotations
import warnings as _warnings

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import json
import sys
import shutil
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import traceback
from pathlib import Path
from typing import Any


# Ordered to put the cheap+universal sets first; expensive/optional later
DEFAULT_SETS = ["smoke", "brief", "locus-maps", "figure-suite", "domain-level"]
OPTIONAL_SETS = ["cohort-class", "mamey-native"]  # need --workbook
ALL_SETS = DEFAULT_SETS + OPTIONAL_SETS


def _relativize_paths(obj: Any, root: "str | Path") -> Any:
    """Return a deep copy of ``obj`` with every absolute path under ``root``
    rewritten package-relative.

    The render-all summary is a SHIPPED package artifact, so its on-disk JSON must
    never embed the operator's absolute ``<home>/<user>/...`` layout (DEEP_AUDIT3 F1:
    the ``package``/``out``/``figures_dir``/``manifest`` fields all serialized a
    ``.resolve()``-d absolute path). Only strings equal to, prefixed by, or embedding
    the package root are touched; every other value passes through unchanged, so the
    summary is otherwise byte-for-byte identical.
    """
    import os
    root_str = str(root)
    prefix = root_str + os.sep
    if isinstance(obj, dict):
        return {k: _relativize_paths(v, root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_relativize_paths(v, root) for v in obj]
    if isinstance(obj, Path):
        obj = str(obj)
    if isinstance(obj, str):
        if obj == root_str:
            return "."
        if obj.startswith(prefix):
            return obj[len(prefix):]
        # Embedded occurrence (e.g. inside an error/traceback string): strip the
        # operator prefix so no absolute <home>/<user>/ path ships, keep the tail.
        if prefix in obj:
            return obj.replace(prefix, "")
        if root_str in obj:
            return obj.replace(root_str, ".")
        return obj
    return obj


def render_all(package_dir: str | Path,
               *,
               include: list[str] | None = None,
               exclude: list[str] | None = None,
               workbook: str | Path | None = None,
               top_n: int = 10,
               continue_on_error: bool = True,
               dry_run: bool = False) -> dict[str, Any]:
    """Run every requested figure set against a sealed package.

    Each set is non-blocking by default — a failure in one does not affect
    the others. Returns a summary dict with per-set status, figure count,
    output path, and (on failure) the exception trail.

    `include` defaults to DEFAULT_SETS. Pass `include=ALL_SETS` to also run
    the workbook-requiring sets. `exclude` removes from the run.
    `continue_on_error=False` switches to fail-fast on the first error
    (useful for CI / manual debugging; default is non-blocking).
    """
    pkg = Path(package_dir).resolve()
    if not (pkg / "manifest.json").exists():
        return {
            "package": str(pkg),
            "ok": False,
            "error": f"manifest.json not found in {pkg}",
            "sets": {},
        }

    requested = list(include) if include is not None else list(DEFAULT_SETS)
    if exclude:
        requested = [s for s in requested if s not in set(exclude)]

    summary: dict[str, Any] = {
        "package": str(pkg),
        "requested": requested,
        "dry_run": dry_run,
        "sets": {},
        "ok": True,
        # `ok` is the aggregate render-execution gate only.  It must become
        # false when any requested set errors, even when continue_on_error
        # allows later independent sets to keep running.
        "independent_gates": {
            "render_execution": "PENDING",
            "publication_approval": "NOT_ASSESSED",
            "biological_validation": "NOT_ASSESSED",
            "release_approval": "NOT_ASSESSED",
        },
    }

    if dry_run:
        for s in requested:
            summary["sets"][s] = {"status": "DRY_RUN"}
        summary["independent_gates"]["render_execution"] = "DRY_RUN"
        summary["completion_state"] = "DRY_RUN"
        return summary

    dispatchers = {
        "smoke":        _run_smoke,
        "brief":        _run_brief,
        "locus-maps":   _run_locus_maps,
        "figure-suite": _run_figure_suite,
        "domain-level": _run_domain_level,
        "cohort-class": lambda p, **kw: _run_cohort_class(p, workbook=workbook, **kw),
        "mamey-native": lambda p, **kw: _run_mamey_native(p, workbook=workbook, **kw),
    }

    for set_name in requested:
        if set_name not in dispatchers:
            summary["sets"][set_name] = {
                "status": "UNKNOWN_SET",
                "error": f"unknown set name: {set_name}",
            }
            summary["ok"] = False
            continue
        try:
            res = dispatchers[set_name](pkg, top_n=top_n)
            summary["sets"][set_name] = res
            if res.get("status") == "ERRORED":
                summary["ok"] = False
                if not continue_on_error:
                    break
        except Exception as e:
            tb = traceback.format_exc()
            summary["sets"][set_name] = {
                "status": "ERRORED",
                "error": f"{type(e).__name__}: {e}",
                "traceback": tb,
            }
            summary["ok"] = False
            if not continue_on_error:
                break

    statuses = [result.get("status") for result in summary["sets"].values()]
    if any(status in {"ERRORED", "UNKNOWN_SET"} for status in statuses):
        completion_state = "FAIL"
    elif any(status == "SKIPPED" for status in statuses):
        completion_state = "PASS_WITH_SKIPS"
    else:
        completion_state = "PASS"
    summary["completion_state"] = completion_state
    summary["independent_gates"]["render_execution"] = completion_state

    return summary


# ---------------------------------------------------------------------------
# Per-set runners
# ---------------------------------------------------------------------------

def _run_smoke(pkg: Path, **_kw) -> dict[str, Any]:
    from . import figures_smoke
    res = figures_smoke.generate(pkg)
    return {
        "status": "RAN" if res.get("figures") else "SKIPPED",
        "figures": res.get("figures", 0),
        "out": res.get("out"),
        "skipped_reason": res.get("skipped_reason"),
    }


def _run_brief(pkg: Path, **_kw) -> dict[str, Any]:
    """Render the `_8a..._8m_fig_*.png` suite via render_brief, the same way
    `mamey run` would absent --brief none / --chatgpt-safe."""
    try:
        from .render_brief import render_brief
    except ImportError as e:
        return {"status": "SKIPPED",
                "skipped_reason": f"render_brief unavailable: {e}"}
    try:
        r = render_brief(str(pkg), tier="standard")
        files = r.get("files", []) if isinstance(r, dict) else []
        figs = [f for f in files
                if (f.endswith(".png") or f.endswith(".svg"))]
        return {
            "status": "RAN" if figs else "SKIPPED",
            "figures": len(figs),
            "out": str(pkg),
            "files": figs,
        }
    except Exception as e:
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}


def _run_locus_maps(pkg: Path, top_n: int = 10, **_kw) -> dict[str, Any]:
    """Run the W5 post-seal locus-map renderer (no GBK zip needed; reads
    from the sealed gene_by_gene CSV)."""
    try:
        from .locus_map import render_for_compile_report
    except ImportError as e:
        return {"status": "SKIPPED",
                "skipped_reason": f"locus_map unavailable: {e}"}
    try:
        res = render_for_compile_report(pkg, top_n=top_n)
        if isinstance(res, dict):
            # v9.7.156: render_for_compile_report returns {"rendered": [bgc_ids]} (a list),
            # not a count. The prior `or len(res.get("files", []))` short-circuited on the
            # truthy list and passed the list itself through as `n`, so the runner returned
            # {"figures": <list>} and the summary JSON on disk carried a list. Normalize at
            # the source; the downstream CLI guard stays as defence-in-depth.
            rendered = res.get("rendered", 0)
            if isinstance(rendered, list):
                n = len(rendered)
            elif isinstance(rendered, int):
                n = rendered
            else:
                n = len(res.get("files", []) or [])
        else:
            n = 0
        return {
            "status": "RAN" if n else "SKIPPED",
            "figures": n,
            "out": str(pkg / "locus_maps"),
        }
    except Exception as e:
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}


def _run_figure_suite(pkg: Path, top_n: int = 10, **_kw) -> dict[str, Any]:
    """Run the `render-figures --figure-set standard` lead-board renderer
    via the same code path the existing CLI command uses."""
    try:
        from .chatgpt_commands import render_figures_command
    except ImportError as e:
        return {"status": "SKIPPED",
                "skipped_reason": f"render_figures unavailable: {e}"}

    # Build a synthetic args namespace for the existing command
    class _Args:
        package = str(pkg)
        outdir = str(pkg / "figures_rendered")
        top_n = 10
        style = "chatgpt-node-first"
        figure_set = "standard"
        workbook = None
    _Args.top_n = top_n
    try:
        rc = render_figures_command(_Args())
        out = Path(_Args.outdir)
        figs = list(out.rglob("*.png")) + list(out.rglob("*.svg"))
        return {
            "status": "RAN" if rc == 0 and figs else "SKIPPED",
            "figures": len(figs),
            "out": str(out),
            "exit_code": rc,
        }
    except Exception as e:
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}


def _resolve_source_zip(pkg: Path, explicit: str | None = None) -> str | None:
    """Find the antiSMASH source ZIP so automated domain-level can populate module
    detail (aSModule_count). Order: explicit arg > manifest `input_zip` > same
    basename beside the package tree. Returns None if nothing resolvable (the
    module summary then honestly reports 0, as it does for a sealed package)."""
    import json
    if explicit and Path(explicit).exists():
        return str(explicit)
    man = pkg / "manifest.json"
    if man.exists():
        try:
            iz = json.loads(man.read_text(encoding="utf-8")).get("input_zip")
        except Exception:
            iz = None
        if iz:
            if Path(iz).exists():
                return str(iz)
            cand = pkg.parent / Path(iz).name  # ZIP moved but kept its name
            if cand.exists():
                return str(cand)
    return None


def _run_domain_level(pkg: Path, top_n: int = 10, **_kw) -> dict[str, Any]:
    """Run the domain-level figure set. Requires `domain_level/` data (run
    by the domain-level pipeline if absent — non-blocking)."""
    try:
        from .domain_figures import render_domain_figures
    except ImportError as e:
        return {"status": "SKIPPED",
                "skipped_reason": f"domain_figures unavailable: {e}"}
    dl_dir = pkg / "domain_level"
    if not (dl_dir / "domain_complexity_metrics_by_bgc.csv").exists():
        # Try to compute it
        try:
            from .domain_level import run_domain_level
            run_domain_level(pkg, source_antismash=_resolve_source_zip(pkg, _kw.get("source_antismash")), top_n=top_n)
        except Exception:
            pass
    if not (dl_dir / "domain_complexity_metrics_by_bgc.csv").exists():
        return {"status": "SKIPPED",
                "skipped_reason": "no domain_level CSV data on disk"}
    try:
        out = dl_dir / "figures"
        res = render_domain_figures(dl_dir, outdir=out)
        if isinstance(res, dict):
            figs_list = res.get("figures", []) or []
            n = len(figs_list)
        else:
            n = 0
        return {
            "status": "RAN" if n else "SKIPPED",
            "figures": n,
            "out": str(out),
        }
    except Exception as e:
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}


def _run_cohort_class(pkg: Path, workbook: str | Path | None = None,
                       **_kw) -> dict[str, Any]:
    if not workbook:
        return {"status": "SKIPPED",
                "skipped_reason": "--workbook not supplied"}
    try:
        from .cohort_class_heatmap import render_cohort_class_heatmap
    except ImportError as e:
        return {"status": "SKIPPED",
                "skipped_reason": f"cohort_class_heatmap unavailable: {e}"}
    out = pkg / "cohort_figures"
    out.mkdir(parents=True, exist_ok=True)
    try:
        res = render_cohort_class_heatmap(
            workbook,
            out / "cohort_class_capacity_heatmap.png",
            out / "cohort_class_capacity_heatmap_data.csv",
            claim_prefix="PRIVATE",
            label_provenance=_kw.get("label_provenance", "RAW_ANTISMASH"),
        )
        # The renderer's public status is uppercase ``OK``.  The old exact
        # comparison accepted lowercase ``ok`` only, so a successfully written
        # PNG/CSV was misreported as SKIPPED by the aggregate command.
        renderer_status = str(res.get("status", "")).upper() if isinstance(res, dict) else ""
        ran = renderer_status in {"OK", "RAN"}
        result = {
            "status": "RAN" if ran else "SKIPPED",
            "figures": 1 if isinstance(res, dict)
                       and res.get("n_strains", 0) > 0 else 0,
            "out": str(out),
            "detail": res,
        }
        # render_cohort_class_heatmap never raises; on SKIPPED it reports its own real reason
        # under the key "reason" (e.g. "no B2 data", "matplotlib: <err>"). Thread that through
        # as skipped_reason so the --all summary prints the actual cause instead of falling
        # back to the generic "likely matplotlib/addon missing or no data" line.
        if not ran and isinstance(res, dict) and res.get("reason"):
            result["skipped_reason"] = f"cohort-class heatmap: {res['reason']}"
        return result
    except Exception as e:
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}


def _run_mamey_native(pkg: Path, workbook: str | Path | None = None,
                       **_kw) -> dict[str, Any]:
    if not workbook:
        return {"status": "SKIPPED",
                "skipped_reason": "--workbook not supplied"}
    try:
        from .mamey_native_figures import render_mamey_native_figure_set
    except ImportError as e:
        return {"status": "SKIPPED",
                "skipped_reason": f"mamey_native_figures unavailable: {e}"}
    out = pkg / "mamey_native_figures"
    try:
        res = render_mamey_native_figure_set(workbook, out)
        return {
            "status": "RAN" if isinstance(res, dict)
                      and res.get("figure_count", 0) > 0 else "SKIPPED",
            "figures": (res.get("figure_count", 0)
                        if isinstance(res, dict) else 0),
            "out": str(out),
        }
    except ValueError as e:
        # mamey-native figures are cohort/master-workbook figures (Strain_Registry,
        # DAPR_Antibacterial/Antifungal, RG-GMCI_All_Strains). A single-strain package's
        # own per-strain workbook never carries those sheets — that's the normal, expected
        # shape for a strain that hasn't been merged into a cohort master workbook yet, not
        # a broken run. Distinguish that from a genuine failure so it reports SKIPPED
        # (with the sheet names named) instead of ERRORED.
        msg = str(e)
        if "missing required sheets" in msg:
            return {"status": "SKIPPED",
                    "skipped_reason": f"no cohort/master-workbook data present yet — {msg} "
                                       "(expected for a single-strain package; merge into a "
                                       "master workbook first, or ignore for a strain-only run)"}
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}
    except Exception as e:
        return {"status": "ERRORED",
                "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def figure_stack_preflight() -> tuple[bool, str]:
    """Loud, actionable check for the figure rendering stack. Returns (present, message).
    A missing matplotlib is the single most common reason 'the figures don't produce' — this
    turns a silent SKIP into one clear line naming the fix."""
    try:
        import matplotlib  # noqa: F401
        return True, "Figure stack present \u2713 (matplotlib available)"
    except Exception:
        return False, ("Figure stack MISSING \u2014 matplotlib not installed. Most figure sets will "
                       "render 0 figures. Install the sapote-addons stack "
                       "(bash install_sapote_addons.sh) or `pip install matplotlib`, then re-run.")


def gather_figures(package_dir: str | Path, summary: dict) -> dict:
    """Collect every produced figure (PNG + SVG) from the scattered per-set output dirs into ONE
    `<pkg>/figures/` directory with a manifest CSV. Solves the '40 figures across 6 directories,
    nobody can find them' problem. Source dirs are read from the summary's per-set `out` fields
    plus the known package subdirs. Files keep a source-dir prefix so names stay unique/traceable.
    Non-destructive: copies, does not move. Returns {gathered, figures_dir, manifest, by_source}."""
    pkg = Path(package_dir).resolve()
    gathered_dir = pkg / "figures"
    gathered_dir.mkdir(exist_ok=True)
    # candidate source dirs: the package root + every subdir any set wrote to + known scatter dirs
    src_dirs = {pkg}
    for res in (summary.get("sets") or {}).values():
        out = res.get("out")
        if out:
            src_dirs.add(Path(out))
    for known in ("smoke_figures", "gold_figures", "figures_rendered", "domain_level/figures",
                  "locus_maps", "domain_level"):
        src_dirs.add(pkg / known)

    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    rows = []
    seen = set()
    for d in sorted(src_dirs, key=str):
        if not d.exists() or d.resolve() == gathered_dir.resolve():
            continue
        for f in sorted(d.glob("*.png")) + sorted(d.glob("*.svg")):
            if f.resolve() in seen:
                continue
            seen.add(f.resolve())
            rel = f.relative_to(pkg) if pkg in f.parents else Path(f.name)
            src_label = str(rel.parent) if str(rel.parent) not in (".", "") else "(root)"
            # prefix scattered files with their source dir so the flat dir keeps provenance
            dest_name = f.name if src_label == "(root)" else f"{src_label.replace('/', '_')}__{f.name}"
            dest = gathered_dir / dest_name
            try:
                shutil.copy2(f, dest)
                source_locator = str(rel)
                rows.append({"figure": dest_name, "source_dir": src_label,
                             "source_locator": source_locator,
                             "bytes": f.stat().st_size, "type": f.suffix.lstrip("."),
                             "sha256": _file_sha256(dest), "state": "CURRENT_GATHER"})
            except Exception:
                continue

    # Never silently blend files from an older gather with the current run.
    # Preserve them non-destructively, but enumerate them as untracked/stale so
    # a second LLM or human handoff cannot mistake them for current outputs.
    current_names = {row["figure"] for row in rows}
    stale = sorted(
        path for path in gathered_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".svg"}
        and path.name not in current_names
    )
    for path in stale:
        rows.append({
            "figure": path.name, "source_dir": "UNKNOWN_PRIOR_GATHER",
            "source_locator": "", "bytes": path.stat().st_size,
            "type": path.suffix.lstrip("."), "sha256": _file_sha256(path),
            "state": "UNTRACKED_OR_STALE",
        })

    manifest = gathered_dir / "FIGURE_INDEX.csv"
    try:
        with open(manifest, "w", newline="") as fh:
            w = _SafeDictWriter(
                fh,
                fieldnames=["figure", "source_dir", "source_locator", "bytes", "type", "sha256", "state"],
            )
            w.writeheader()
            for r in sorted(rows, key=lambda r: (r["source_dir"], r["figure"])):
                w.writerow(r)
    except Exception:
        pass
    by_source: dict[str, int] = {}
    for r in rows:
        if r["state"] != "CURRENT_GATHER":
            continue
        by_source[r["source_dir"]] = by_source.get(r["source_dir"], 0) + 1
    return {"gathered": len(current_names), "figures_dir": str(gathered_dir),
            "manifest": str(manifest), "by_source": by_source,
            "untracked_or_stale": len(stale),
            "untracked_or_stale_files": [path.name for path in stale]}


def render_all_figures_command(args) -> int:
    """CLI entry: `mamey render-all-figures --package <pkg> [options]`."""
    include = None
    if getattr(args, "include", None):
        include = [s.strip() for s in args.include.split(",") if s.strip()]
    elif getattr(args, "all_sets", False):
        include = list(ALL_SETS)
    exclude = None
    if getattr(args, "exclude", None):
        exclude = [s.strip() for s in args.exclude.split(",") if s.strip()]

    # loud preflight: one clear line about whether figures can render at all
    _present, _msg = figure_stack_preflight()
    emit(f"  {_msg}")

    summary = render_all(
        args.package,
        include=include,
        exclude=exclude,
        workbook=getattr(args, "workbook", None),
        top_n=getattr(args, "top_n", 10),
        continue_on_error=not getattr(args, "fail_fast", False),
        dry_run=getattr(args, "dry_run", False),
    )

    emit(f"render-all-figures: {summary['package']}")
    if not summary.get("ok"):
        emit(f"  ERROR: {summary.get('error','run aborted')}", file=sys.stderr)
        if "error" in summary and "manifest.json" in str(summary.get("error", "")):
            return 1
    total = 0
    for set_name, res in summary["sets"].items():
        st = res.get("status", "?")
        n = res.get("figures", 0)
        # PATCH-002: some set runners (e.g. locus-maps via render_for_compile_report)
        # can return `figures` as a LIST of paths rather than an int count. Coerce
        # before the `{n:3d}` format and the `total +=` accumulator, both of which
        # assume an int (a list crashes str.__format__ and halts the --all run).
        if isinstance(n, list):
            n = len(n)
        total += n if isinstance(n, int) else 0
        out = res.get("out", "")
        if st == "RAN":
            emit(f"  {set_name:14s} RAN     {n:3d} fig(s) → {out}")
        elif st == "SKIPPED":
            reason = res.get("skipped_reason") or ""
            if not reason.strip():
                reason = ("no figures produced \u2014 likely matplotlib/addon missing or no data for this set; "
                          "see the figure-stack line above")
            emit(f"  {set_name:14s} SKIPPED  ({reason})")
        elif st == "ERRORED":
            emit(f"  {set_name:14s} ERRORED  {res.get('error','')}",
                  file=sys.stderr)
        elif st == "DRY_RUN":
            emit(f"  {set_name:14s} (would run)")
        elif st == "UNKNOWN_SET":
            emit(f"  {set_name:14s} UNKNOWN  ({res.get('error','')})",
                  file=sys.stderr)
        else:
            emit(f"  {set_name:14s} {st}")

    if not summary.get("dry_run"):
        emit(f"\n  total figures: {total}")
        # Gather every produced PNG/SVG into one <pkg>/figures/ dir with a manifest, so the
        # scatter across 6 dirs stops being the reason figures can't be found.
        try:
            g = gather_figures(summary["package"], summary)
            emit(f"  gathered {g['gathered']} figure(s) → {g['figures_dir']}")
            if g["gathered"] != total:
                emit(f"    (note: sets self-reported {total}; on-disk gathered count "
                      f"{g['gathered']} is authoritative)")
            emit(f"    manifest: {g['manifest']}")
            if g.get("untracked_or_stale"):
                emit(f"    WARNING: {g['untracked_or_stale']} untracked/stale figure(s) remain "
                      "and are explicitly marked in the manifest", file=sys.stderr)
            if g["by_source"]:
                bits = ", ".join(f"{k}:{v}" for k, v in sorted(g["by_source"].items()))
                emit(f"    by source: {bits}")
            summary["gathered"] = g
        except Exception as exc:  # gathering must never break the run
            emit(f"  (figure gather skipped: {exc})", file=sys.stderr)
        # Write the summary JSON so downstream tools (compile-report) can find it.
        # CLAUDE_409: this JSON ships inside the package, so relativize every path
        # under the package root before serializing — the on-disk artifact must never
        # embed the operator's absolute <home>/<user>/... layout (DEEP_AUDIT3 F1). The
        # in-memory `summary` is left untouched, so console output is unchanged.
        try:
            pkg_root = Path(summary["package"])
            shipped = _relativize_paths(summary, pkg_root)
            # v9.7.414 (BC2): the shipped receipt could not identify its own subject. Relativizing
            # is correct and must stay (CLAUDE_409 / DEEP_AUDIT3 F1 — never embed the operator's
            # absolute layout), and `"package": "."` matches the house anchor convention used by
            # manifest.json and PACKAGE_MAP.json. What was missing is the OTHER half of that
            # convention: those two carry `strain_id` beside the "." anchor, and this file carried
            # no identifier at all. Supply it from the package's own manifest (authoritative), so
            # the anchor keeps its meaning and the receipt still names what it describes.
            try:
                _mf = json.loads((pkg_root / "manifest.json").read_text(encoding="utf-8"))
                for _k in ("strain_id", "package_engine_version", "workflow_version"):
                    if _mf.get(_k) is not None:
                        shipped.setdefault(_k, _mf[_k])
            except Exception:
                shipped.setdefault("strain_id", "UNKNOWN_MANIFEST_UNREADABLE")
            out = pkg_root / "render_all_figures_summary.json"
            out.write_text(json.dumps(shipped, indent=2, default=str),
                            encoding="utf-8")
        except Exception as _swallowed_exc:
            _warnings.warn(f"render_all_figures.py: non-blocking step skipped ({type(_swallowed_exc).__name__}: {_swallowed_exc})", RuntimeWarning, stacklevel=2)  # v9.7.409: was a silent swallow

    return 0 if summary.get("ok") else 1
