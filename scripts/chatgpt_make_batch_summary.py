#!/usr/bin/env python3
"""Build a lightweight CSV/Markdown summary from Mamey run packages."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path


def _resolve_engine_version() -> str:
    """Engine version, derived (never hardcoded) — falls back gracefully when run standalone."""
    try:
        from mamey import __version__ as v
        return v
    except Exception:
        pass
    try:
        import re as _re
        root = Path(__file__).resolve().parent.parent
        m = _re.search(r'__version__\s*=\s*"([^"]+)"', (root / "mamey" / "__init__.py").read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    except Exception:
        pass
    return "unknown"


_ENGINE_VERSION = _resolve_engine_version()


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_package(pkg: Path) -> dict:
    manifest = load_json(pkg / "manifest.json") or {}
    intake_files = list(pkg.glob("*_1_intake.json"))
    triage_files = list(pkg.glob("*_4_triage_board.csv"))
    gate = load_json(pkg / "gate_validation.json") or {}
    strain = manifest.get("strain_id") or (intake_files[0].name.split("_1_intake.json")[0] if intake_files else pkg.parent.name)
    bgcs = manifest.get("bgcs", []) or []
    corrected = manifest.get("assembly", {}).get("corrected_bgc_count", "")
    top = ""
    if triage_files:
        with triage_files[0].open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            if rows:
                top = rows[0].get("BGC") or rows[0].get("bgc_id") or rows[0].get("BGC_ID") or ""
    return {
        "strain": strain,
        "raw_bgcs": len(bgcs),
        "corrected_bgcs": corrected,
        "validation_status": gate.get("status", "unknown"),
        "top_triage_bgc": top,
        "package": str(pkg),
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: chatgpt_make_batch_summary.py OUT_PREFIX PACKAGE_DIR [PACKAGE_DIR ...]", file=sys.stderr)
        return 2
    out_prefix = Path(argv[0])
    packages = [Path(x) for x in argv[1:]]
    rows = [summarize_package(p) for p in packages]
    csv_path = out_prefix.with_suffix(".csv")
    md_path = out_prefix.with_suffix(".md")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["strain"])
        w.writeheader(); w.writerows(rows)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Mamey v{_ENGINE_VERSION} Batch Summary\n\n")
        f.write("| Strain | Raw BGCs | Corrected BGCs | Validation | Top triage BGC |\n")
        f.write("|---|---:|---:|---|---|\n")
        for r in rows:
            f.write(f"| {r['strain']} | {r['raw_bgcs']} | {r['corrected_bgcs']} | {r['validation_status']} | {r['top_triage_bgc']} |\n")
    print(csv_path)
    print(md_path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
