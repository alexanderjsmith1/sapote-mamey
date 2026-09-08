#!/usr/bin/env python3
"""find_asset.py — locate a big/shared local asset BEFORE downloading or re-deriving it.

Reads OFFICIAL_DATA/ASSET_REGISTRY.tsv (the canonical map). Recurring problem this fixes: chats
re-download data that is already on disk (e.g. a chat tried to fetch ~2 GB of Pfam-A HMM that lives
in BigSCAPE/), and — the 2026-08-17 escalation — recommend re-RUNNING compute (BiG-SCAPE) whose
results are already registered. Check here first; end heavy-compute recipes with
tools/register_compute_output.py so the next result is findable here by construction.

v9.7.370: ships IN THE BUNDLE (wishlist #36), portable via the same root contract as the engine
(SAPOTE_WORKSPACE_ROOT → SAPOTE_ROOT → mamey.workspace_root; no personal-path literal — the
portability guard forbids it outside its one sanctioned home).

USAGE
  python3 tools/find_asset.py <query>        # find by asset_id or keyword (pfam, blastp, gtdb, genome…)
  python3 tools/find_asset.py --list         # list every registered asset
  python3 tools/find_asset.py --check "<shell command>"
                                             # is this download/compute redundant? exit 3 + local path if so
Exit: 0 found / listed; 2 not found; 3 redundant-download/compute detected (for --check).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os
import sys
import pathlib


def _root() -> pathlib.Path:
    for env in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        v = os.environ.get(env)
        if v:
            return pathlib.Path(v)
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from mamey.workspace_root import workspace_root as _wr
        return pathlib.Path(_wr())
    except Exception:
        raise SystemExit(
            "find_asset: no workspace root configured. Set SAPOTE_WORKSPACE_ROOT (or "
            "SAPOTE_ROOT), or run from a bundle where the mamey package is importable.")


ROOT = _root()
REG = ROOT / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv"


def rows():
    if not REG.is_file():
        sys.stderr.write(f"[find_asset] registry missing: {REG}\n"); return []
    out = []
    for ln in REG.read_text().splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("asset_id\t"):
            continue
        f = ln.split("\t")
        if len(f) >= 6:
            out.append(dict(asset_id=f[0], kind=f[1], path=f[2], size=f[3],
                            guards=[g for g in f[4].split("|") if g], note=f[5]))
    return out


def _show(r):
    p = ROOT / r["path"]
    exists = "" if ("<" in r["path"] or p.exists()) else "  [NOT ON DISK]"
    emit(f"{r['asset_id']}  ({r['kind']}, {r['size']}){exists}\n  path: {p}\n  {r['note']}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        emit(__doc__); return 0
    if argv[0] == "--list":
        for r in rows():
            _show(r)
        return 0
    if argv[0] == "--check":
        cmd = " ".join(argv[1:]).lower()
        is_dl = any(t in cmd for t in ("wget", "curl", "aria2", "pip download", "pip install",
                    "datasets download", "ncbi-genome-download", "hmmfetch", "git lfs", "git-lfs",
                    "gtdbtk", "rsync"))
        # 2026-08-17 (the review lane, the Developer or User-flagged incident): also catch REDUNDANT COMPUTE — a chat
        # recommended re-running BiG-SCAPE while 5.3G of results sat registered on disk. Run-style
        # invocations of tools whose RESULTS are registered get the same treatment as downloads.
        # Tokens are run-signatures (tool + flag), so `ls BigSCAPE/` etc. never engages.
        is_dl = is_dl or any(t in cmd for t in ("bigscape -", "bigscape cluster", "bigscape.py",
                    "run_bigscape", "gtotree -", "antismash -", "antismash.py", "clinker -"))
        hits = [r for r in rows() if any(g.lower() in cmd for g in r["guards"])]
        if is_dl and hits:
            sys.stderr.write("[find_asset] REDUNDANT DOWNLOAD/COMPUTE — this asset is already local:\n")
            for r in hits:
                sys.stderr.write(f"  {r['asset_id']} -> {ROOT / r['path']}  ({r['size']})\n    {r['note']}\n")
            return 3
        return 0
    # keyword / id search
    q = argv[0].lower()
    hits = [r for r in rows() if q in r["asset_id"].lower()
            or any(q in g.lower() for g in r["guards"]) or q in r["note"].lower()]
    if not hits:
        emit(f"no asset matches '{argv[0]}'. Try --list."); return 2
    for r in hits:
        _show(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
