#!/usr/bin/env python3
"""gen_marker_catalog.py — generate the marker/cassette catalog FROM the regex backend (W9).

THE TRAP THIS CLOSES
--------------------
The bundle ships human-readable marker/cassette catalogs that *look* authoritative, but
the actual scanning is the regex dicts in mamey/source_scans.py. The doc and the code can
disagree, and a reader (or the LLM) reasons over the pretty catalog instead of what the
scanner truly matches. This tool makes the catalog a *generated artifact* of the regex
dicts, and `--check` fails the build if the committed catalog has drifted from the code.

It introspects mamey.source_scans for module-level dicts of the shape {family: [patterns]}
(the *_PATTERNS / *_MOTIFS / *_VETOES tables), so new tables are picked up automatically.

    python3 tools/gen_marker_catalog.py                 # write docs/MARKER_CATALOG.generated.{md,json}
    python3 tools/gen_marker_catalog.py --check         # exit 1 if the committed catalog is stale
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import hashlib
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# make the bundle root importable when run as `python3 tools/gen_marker_catalog.py`
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _wbio import atomic_write_text  # noqa: E402
MD_OUT = ROOT / "docs" / "MARKER_CATALOG.generated.md"
JSON_OUT = ROOT / "docs" / "MARKER_CATALOG.generated.json"

# tables to skip: not {family: [patterns]} pattern tables
_SKIP = {"DOMAIN_CLASS_PATTERNS"} if False else set()


def _is_pattern_table(name: str, val) -> bool:
    if not name.isupper():
        return False
    if not (name.endswith("_PATTERNS") or name.endswith("_MOTIFS") or name.endswith("_VETOES")):
        return False
    if not isinstance(val, dict) or not val:
        return False
    # values should be lists/tuples of strings (the regex/term lists)
    return all(isinstance(v, (list, tuple)) for v in val.values())


def collect() -> dict:
    import mamey.source_scans as ss
    tables = {}
    for name in sorted(dir(ss)):
        val = getattr(ss, name)
        if _is_pattern_table(name, val):
            fams = {fam: [str(p) for p in pats] for fam, pats in val.items()}
            tables[name] = fams
    payload = {"source": "mamey/source_scans.py", "tables": tables}
    payload["sha256"] = hashlib.sha256(
        json.dumps(tables, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_md(payload: dict) -> str:
    lines = ["# Marker / Cassette Catalog (generated)", "",
             f"**Generated from** `{payload['source']}` — do not edit by hand.",
             f"**Content hash:** `{payload['sha256'][:16]}…`", "",
             "Regenerate with `python3 tools/gen_marker_catalog.py`. The build checks this "
             "file against the live regex tables (`--check`), so the catalog cannot drift "
             "from the scanner.", ""]
    for table, fams in payload["tables"].items():
        n_pat = sum(len(v) for v in fams.values())
        lines.append(f"\n## {table}  ·  {len(fams)} families / {n_pat} patterns\n")
        for fam, pats in fams.items():
            shown = ", ".join(f"`{p}`" for p in pats[:8])
            more = f"  … (+{len(pats) - 8} more)" if len(pats) > 8 else ""
            lines.append(f"- **{fam}** ({len(pats)}): {shown}{more}")
    return "\n".join(lines) + "\n"


def write(payload: dict) -> None:
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    # v9.7.374: was a bare Path.write_text() -- a process killed mid-write left a truncated
    # MARKER_CATALOG.generated.{json,md} on disk (the exact "corrupts the artifact into an
    # unreadable/truncated file" hazard tools/_wbio.py exists to close for every other generator
    # in this family). atomic_write_text is the same tmp+os.replace() helper already used
    # elsewhere in this codebase for exactly this write pattern.
    atomic_write_text(JSON_OUT, json.dumps(payload, indent=2, sort_keys=True))
    atomic_write_text(MD_OUT, render_md(payload))


def main() -> int:
    payload = collect()
    if "--check" in sys.argv:
        if not JSON_OUT.exists():
            emit("MARKER CATALOG missing — run gen_marker_catalog.py")
            return 1
        committed = json.loads(JSON_OUT.read_text(encoding="utf-8"))
        if committed.get("sha256") != payload["sha256"]:
            emit("MARKER CATALOG DRIFT — docs/MARKER_CATALOG.generated.json is stale vs "
                  "mamey/source_scans.py. Regenerate with gen_marker_catalog.py.")
            return 1
        emit(f"marker catalog OK — in sync with source_scans.py ({len(payload['tables'])} tables)")
        return 0
    write(payload)
    n = sum(len(f) for f in payload["tables"].values())
    emit(f"wrote catalog: {len(payload['tables'])} tables, {n} families "
          f"(hash {payload['sha256'][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
