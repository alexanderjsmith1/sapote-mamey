"""package_map.py — PACKAGE_MAP.json generator (Cut A candidate).

Reads the declarative package_map_spec.json (SSOT: artifact -> purpose ->
section), walks a real sealed package, resolves each spec artifact to a concrete
present/absent state, and writes PACKAGE_MAP.json — the semantic layer the flat
`manifest.json["files"]` checksum inventory lacks.

Purpose: close the "files are there but not found/read" failure. For each Mode B
section, PACKAGE_MAP.json states the required_reads and optional_reads that
actually exist in THIS package, so the author (and the read-gate) know what to
open before writing §N — instead of authoring §4 off a summary while the
gene tables sit unread in the package.

Resolution handles four artifact-name shapes seen in real packages:
  1. "{strain}_gene_context.jsonl"        -> prefix substitution, top-level file
  2. "locus_maps/{bgc}_locus_map.svg"     -> subdir + per-BGC glob
  3. "manifest.json#source_scans"         -> a key INSIDE a json, not a file
  4. "deep_data.json" / "checksums..."    -> plain top-level file

Availability semantics (validated against a real v9.7.158 gold package):
  always | gold | conditional | external | deliverable
The resolver marks present/absent by what's on disk; it never invents. A
gold-only artifact absent from a smoke package is reported present=false with
availability=gold, so the read-gate can distinguish "missing but expected here"
from "missing because this mode doesn't emit it" and never false-alarm.

Version-aware (spec v0.5+): each 'always' artifact carries always_since_engine.
When an always-artifact is absent AND the package's engine version predates it,
the section verdict is LEGACY_ABSENT (package too old to comply) rather than GAP
(a modern run that failed to emit an artifact it should have). This lets the
read-gate tell an old package apart from a broken run.

Pure stdlib, never raises on a malformed package (fail-soft, honest-blank).
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

import json
import glob
import os
import re
from pathlib import Path
from typing import Any


SPEC_VERSION_EXPECTED_PREFIX = "0."  # accept 0.x drafts; a real cut pins this


def default_spec_path() -> Path:
    """The bundled SSOT: mamey/data/mode_b/package_map_spec.json (next to this module's data)."""
    return Path(__file__).resolve().parent / "data" / "mode_b" / "package_map_spec.json"


def _load_spec(spec_path: str | Path | None) -> dict:
    p = Path(spec_path) if spec_path else default_spec_path()
    return json.loads(p.read_text(encoding="utf-8"))


def _load_json_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Load a JSON object with one strict, non-raising missingness contract.

    The empty error string means the path is absent. Any present-but-unreadable, malformed, or
    non-object JSON returns a typed diagnostic so every consumer makes the same distinction.
    """
    try:
        if not path.exists():
            return None, ""
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, f"JSON root is {type(data).__name__}, not object"
    return data, ""


def _parse_engine_version(pkg: Path) -> tuple[int, ...] | None:
    """Read the package's engine version from manifest.json['workflow_version']
    (e.g. 'Mamey v1.9.x' -> (1,9,x)). Returns None if unreadable."""
    man = pkg / "manifest.json"
    data, _error = _load_json_object(man)
    if data is None:
        return None
    wv = data.get("workflow_version", "")
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(wv))
    return tuple(int(x) for x in m.groups()) if m else None


def _version_tuple(s: str) -> tuple[int, ...] | None:
    """'1.9.3' -> (1,9,3); 'post-1.9.3' / 'unknown' -> None (undetermined)."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", str(s).strip())
    return tuple(int(x) for x in m.groups()) if m else None


def _predates(pkg_ver: tuple[int, ...] | None, since: str) -> bool:
    """True iff the package engine version is OLDER than an artifact's always_since_engine.
    Conservative: if either side is unknown/undetermined, returns False (treat as a real
    gap rather than silently excusing it) — EXCEPT 'post-1.9.3', where a package at/below
    1.9.3 is genuinely too old to carry the artifact."""
    if pkg_ver is None:
        return False
    sv = _version_tuple(since)
    if sv is not None:
        return pkg_ver < sv
    # honest placeholder handling: 'post-1.9.3' means "added after 1.9.3"
    if str(since).strip() == "post-1.9.3":
        return pkg_ver <= (1, 9, 3)
    return False


def _strain_id_from_package(pkg: Path) -> str:
    """Best-effort strain id: prefer manifest, else *_1_intake.json stem, else dir name."""
    man = pkg / "manifest.json"
    data, _error = _load_json_object(man)
    if data and data.get("strain_id"):
        return str(data["strain_id"])
    for p in pkg.glob("*_1_intake.json"):
        return p.name[: -len("_1_intake.json")]
    return pkg.name


def _json_has_key(path: Path, key: str) -> tuple[bool, Any]:
    """For 'file.json#key' artifacts: is `key` present and non-empty in the json?"""
    data, error = _load_json_object(path)
    if data is None:
        return False, {"read_error": error} if error else None
    if key in data:
        val = data[key]
        # non-empty test: [], {}, "", None all count as present-but-empty
        empty = val in (None, "", [], {})
        return True, {"present_key": True, "empty": empty}
    return False, None


def _resolve_artifact(name: str, pkg: Path, strain: str) -> dict:
    """Resolve one spec artifact name to a concrete on-disk state.

    Returns {present: bool, resolved_path: str|None, note: str}.
    """
    # shape 3: manifest.json#field  (data inside a json, not a standalone file)
    if "#" in name:
        fname, key = name.split("#", 1)
        fpath = pkg / fname.replace("{strain}", strain).replace("{strain_id}", strain)
        ok, meta = _json_has_key(fpath, key)
        if ok:
            empty = meta.get("empty", False)
            return {
                "present": True, "resolved_path": f"{fpath.name}#{key}",
                "empty": empty,
                "note": f"json key '{key}' present" + (" but empty" if empty else ""),
            }
        if meta and meta.get("read_error"):
            return {"present": False, "resolved_path": None,
                    "note": f"json evidence unreadable in {fname}: {meta['read_error']}"}
        return {"present": False, "resolved_path": None, "note": f"json key '{key}' absent in {fname}"}

    subbed = name.replace("{strain}", strain).replace("{strain_id}", strain)

    # shape 2: subdir + per-BGC pattern (has {bgc} or a known subdir)
    if "{bgc}" in subbed or "/" in subbed:
        # turn {bgc} into a glob wildcard; keep the subdir
        pat = subbed.replace("{bgc}", "*")
        hits = sorted(glob.glob(str(pkg / pat)))
        if hits:
            rels = [os.path.relpath(h, pkg) for h in hits]
            return {
                "present": True,
                "resolved_path": rels[0] + (f"  (+{len(rels)-1} more)" if len(rels) > 1 else ""),
                "count": len(rels), "note": f"{len(rels)} file(s) match {pat}",
            }
        return {"present": False, "resolved_path": None, "note": f"no files match {pat}"}

    # shape 1 & 4: a concrete top-level file (possibly strain-prefixed)
    fpath = pkg / subbed
    try:
        if fpath.exists():
            return {"present": True, "resolved_path": subbed, "note": "file present"}
    except OSError as exc:
        return {
            "present": False,
            "resolved_path": None,
            "note": f"file existence unreadable: {type(exc).__name__}: {exc}",
        }
    # last resort: basename match anywhere (handles minor path drift)
    base = os.path.basename(subbed)
    for root, _, files in os.walk(pkg):
        if base in files:
            rel = os.path.relpath(os.path.join(root, base), pkg)
            return {"present": True, "resolved_path": rel, "note": f"found by basename at {rel}"}
    return {"present": False, "resolved_path": None, "note": "file absent"}


def _package_mode(pkg: Path) -> str:
    """Read the run mode; distinguish absent metadata from unreadable metadata."""
    man = pkg / "manifest.json"
    data, error = _load_json_object(man)
    if error:
        return "unreadable"
    return str((data or {}).get("mode", "")).lower()


def build_package_map(pkg_dir: str | Path, spec_path: str | Path | None = None) -> dict:
    """Build the PACKAGE_MAP structure for one sealed package. Never raises."""
    pkg = Path(pkg_dir)
    spec = _load_spec(spec_path)
    strain = _strain_id_from_package(pkg)
    pkg_engine = _parse_engine_version(pkg)
    pkg_mode = _package_mode(pkg)

    sections_spec = spec["sections"]
    artifacts_out: dict[str, dict] = {}
    for name, meta in spec["artifacts"].items():
        state = _resolve_artifact(name, pkg, strain)
        # v9.7.374 fix: derive consumed_by_sections from the sections' own required_reads/
        # optional_reads (the field this same function already treats as authoritative for the
        # read-gate below) instead of trusting the hand-maintained artifact-side duplicate, which
        # had drifted out of sync with it in 27 cases (audit: AUDIT_374). This makes the two
        # views structurally unable to disagree, instead of merely re-syncing them once.
        derived_consumed_by = sorted(
            int(sec_id) for sec_id, sec in sections_spec.items()
            if name in (sec.get("required_reads") or []) or name in (sec.get("optional_reads") or [])
        )
        artifacts_out[name] = {
            "layer": meta.get("layer"),
            "availability": meta.get("availability"),
            "granularity": meta.get("granularity"),
            "purpose": meta.get("purpose"),
            "consumed_by_sections": derived_consumed_by,
            "present": state["present"],
            "resolved_path": state["resolved_path"],
            "resolution_note": state["note"],
        }
        if "empty" in state:
            artifacts_out[name]["present_but_empty"] = state["empty"]
        if "count" in state:
            artifacts_out[name]["file_count"] = state["count"]

    # per-section: which required/optional reads are actually present here
    sections_out: dict[str, dict] = {}
    for num, sec in spec["sections"].items():
        req = sec.get("required_reads", [])
        opt = sec.get("optional_reads", [])
        req_present = [r for r in req if artifacts_out.get(r, {}).get("present")]
        req_missing = [r for r in req if not artifacts_out.get(r, {}).get("present")]
        opt_present = [r for r in opt if artifacts_out.get(r, {}).get("present")]
        # a required 'always' read that's absent is either a real GAP or, if the package
        # predates the artifact's always_since_engine, an honest LEGACY_ABSENT (too old to comply).
        hard_missing = []
        legacy_absent = []
        for r in req_missing:
            meta = spec["artifacts"].get(r, {})
            if meta.get("availability") not in ("always",):
                continue  # mode-gated absence is fine
            since = meta.get("always_since_engine")
            if since and _predates(pkg_engine, since):
                legacy_absent.append(r)
            else:
                hard_missing.append(r)
        sections_out[num] = {
            "title": sec.get("title"),
            "required": sec.get("required"),
            "required_reads_present": req_present,
            "required_reads_missing": req_missing,
            "required_reads_hard_missing": hard_missing,   # absent, expected-always, engine new enough => real gap
            "required_reads_legacy_absent": legacy_absent,  # absent because package predates the artifact
            "optional_reads_present": opt_present,
            "read_completeness": (
                "COMPLETE" if not req_missing else
                "MODE_GATED" if not hard_missing and not legacy_absent else
                "LEGACY_ABSENT" if not hard_missing else
                "GAP"
            ),
            "note": sec.get("note", ""),
        }

    present_n = sum(1 for a in artifacts_out.values() if a["present"])
    return {
        "package_map_version": "1.2",
        "generated_from_spec": spec["_meta"].get("spec_version"),
        "strain_id": strain,
        "package_engine_version": ".".join(map(str, pkg_engine)) if pkg_engine else "unknown",
        "package_mode": pkg_mode or "unknown",
        # v9.7.160 read-gate teeth: a smoke package is a fast parse-gate, NOT analyzable.
        # The triage board is empty (no ranked leads), so §4+ Mode B authoring and any
        # cross-strain comparison must NOT be attempted from it — re-run gold first.
        "analyzable": pkg_mode in {"gold", "standard"},
        "analyzable_note": (
            "SMOKE package — NOT ANALYZABLE: empty triage board, no DAPR/lead-boards/priority-figures, "
            "partial locus maps. Do not author Mode B or compare strains; re-run --mode gold."
            if pkg_mode == "smoke" else
            "Package metadata unreadable — NOT ANALYZABLE: repair manifest.json before authoring or comparison."
            if pkg_mode == "unreadable" else
            "Unknown package mode — NOT ANALYZABLE: supply a valid manifest.json mode before authoring or comparison."
            if pkg_mode not in {"gold", "standard"} else
            "Gold/standard package — analyzable."
        ),
        # The map lives inside the package; an absolute build-host path is not
        # portable and makes identical runs byte-different.
        "package_dir": ".",
        "summary": {
            "artifacts_total": len(artifacts_out),
            "artifacts_present": present_n,
            "artifacts_absent": len(artifacts_out) - present_n,
            "sections_complete": sum(1 for s in sections_out.values() if s["read_completeness"] == "COMPLETE"),
            "sections_mode_gated": sum(1 for s in sections_out.values() if s["read_completeness"] == "MODE_GATED"),
            "sections_legacy_absent": sum(1 for s in sections_out.values() if s["read_completeness"] == "LEGACY_ABSENT"),
            "sections_with_gap": sum(1 for s in sections_out.values() if s["read_completeness"] == "GAP"),
        },
        "artifacts": artifacts_out,
        "sections": sections_out,
    }


def write_package_map(pkg_dir: str | Path, spec_path: str | Path | None = None,
                      out_path: str | Path | None = None) -> Path:
    """Build and write PACKAGE_MAP.json into the package (or out_path). Returns the path."""
    pkg = Path(pkg_dir)
    data = build_package_map(pkg, spec_path)
    out = Path(out_path) if out_path else (pkg / "PACKAGE_MAP.json")
    # v9.7.371 fix: was a plain write_text(). cli.py (SEAL-04) calls this just before
    # _phase_package_seal specifically so PACKAGE_MAP.json is inside the sealed ZIP and its
    # checksum set -- an interrupted write here leaves a truncated/corrupt file that the
    # immediately-following checksum step would then seal as "valid" (a checksum only captures
    # whatever partial bytes exist). Same tmp-sibling+replace pattern as packaging.py.
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(out)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Generate PACKAGE_MAP.json from a sealed package + spec.")
    ap.add_argument("--package", required=True)
    ap.add_argument("--spec", default=None,
                    help="Path to package_map_spec.json; defaults to the bundled "
                         "mamey/data/mode_b/package_map_spec.json.")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    p = write_package_map(a.package, a.spec, a.out)
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    s = d["summary"]
    emit(f"PACKAGE_MAP written: {p}", f"  strain: {d['strain_id']}  spec: {d['generated_from_spec']}", f"  artifacts present/absent: {s['artifacts_present']}/{s['artifacts_absent']}", sep="\n")
    emit(f"  sections complete/mode-gated/gap: "
          f"{s['sections_complete']}/{s['sections_mode_gated']}/{s['sections_with_gap']}")
