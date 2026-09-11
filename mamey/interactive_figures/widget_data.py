#!/usr/bin/env python3
"""Build the AS widget-data aggregate FROM sealed Mamey packages.

Codex's interactive figures + `publication_bridge` consume a single JSON
aggregate (``{"meta": {...}, "strains": {STRAIN: {...}}}``). This module
reconstructs that aggregate deterministically from this engine's own sealed
package outputs, so the widgets and the publication bridge run on Mamey output
rather than on a one-off export.

Claim-safety: every value here is a class-level *structural* count taken from
the deterministic extraction layer — BGC boundary status, product-class
membership, physical-CDS counts, machinery-role gene lengths. Nothing here is a
metabolite-identity, production, activity, novelty, or host-causality claim.
Host context is copied verbatim from an accession-bearing crosswalk and is left
UNRESOLVED when the crosswalk gives no support; no host is inferred from a
strain identifier or a broad ecology label.

Sourcing (per sealed package ``runs/<STRAIN>/package/``):
  - bgcRows / classes      -> ``*_2_inventory.csv`` (one physical BGC per row;
                              Products split on ';' + deduped within a BGC;
                              Boundary -> Edge/Full-contig(->full)/Interior).
  - cdsRows / uniquePhysicalGenes / machineryGenes / machinery
                           -> ``*_cds_table.csv`` (physical CDS deduped on
                              contig+locus_tag+start+end; machinery role from the
                              antiSMASH ``gene_functions`` text via the declared
                              precedence). Falls back to
                              ``*_gene_by_gene_all_bgcs.csv``.
  - hostContext            -> measured_activity_table.csv (strain,host,genus) +
                              strain_genus.csv + the explicit attine-ant list.
  - governance             -> GOVERNED, except AS-XXX=EXCLUSION_ONLY,
                              AS-XXX=AUDIT_ONLY_QUARANTINED.
"""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit
import os
from ..workspace_root import workspace_root

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Constants derived from the Codex README ("Calculation definitions" /
# "Cohort governance" / "Host-linked cohort definitions").
# ---------------------------------------------------------------------------

MACHINERY_PRECEDENCE = [
    "Biosynthetic additional",
    "Biosynthetic core",
    "Resistance",
    "Transport",
    "Regulatory",
]

# antiSMASH gene_functions text -> machinery role, applied in precedence order.
# The gene_functions cell concatenates multiple annotations with spaces, so we
# test for substrings rather than splitting.
_ROLE_TESTS: list[tuple[str, Any]] = [
    ("Biosynthetic additional", re.compile(r"biosynthetic-additional")),
    ("Biosynthetic core", re.compile(r"biosynthetic \(")),
    ("Resistance", re.compile(r"resistance")),
    ("Transport", re.compile(r"transport")),
    ("Regulatory", re.compile(r"regulatory")),
]

_BOUNDARY_MAP = {"Edge": "edge", "Full-contig": "full", "Interior": "interior"}

# Attine-ant comparison cohort (Figure Factory scripts). Cohort-specific membership is
# not shipped in the code tier; loaded from OFFICIAL_DATA/attine_ant_cohort.json when
# present, else an empty set (no strain is flagged attine in a data-free code tier).
from ..exclusions import official_data_json as _official_data_json
ATTINE_ANT_STRAINS = set(_official_data_json("attine_ant_cohort.json", {}).get("strains", []))

# Governance status per strain, SOURCED from the exclusions SSOT so the excluded
# strain set is single-sourced (see OFFICIAL_DATA/EXCLUSIONS.md). The distinct
# labels are preserved: hard_excluded -> EXCLUSION_ONLY (AS-XXX), raw_assembly_void
# -> AUDIT_ONLY_QUARANTINED (AS-XXX raw). Behaviour matches the prior hardcoded map.
try:  # normal package import
    from ..exclusions import hard_excluded as _hard_excluded
    from ..exclusions import raw_assembly_void as _raw_assembly_void
except ImportError:  # standalone `python widget_data.py`
    import os as _os
    import sys as _wd_sys
    _wd_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    from mamey.exclusions import hard_excluded as _hard_excluded  # type: ignore
    from mamey.exclusions import raw_assembly_void as _raw_assembly_void  # type: ignore

GOVERNANCE_OVERRIDES = {
    **{s: "EXCLUSION_ONLY" for s in _hard_excluded()},
    **{s: "AUDIT_ONLY_QUARANTINED" for s in _raw_assembly_void()},
}

# Default crosswalk locations (absolute; overridable via build_widget_data args).
DEFAULT_MEASURED_ACTIVITY = Path(
    str(workspace_root()) + "/strain_data/cohort_master/"
    "measured_activity_table.csv"
)
DEFAULT_STRAIN_GENUS = (
    Path(__file__).resolve().parents[1] / "data" / "strain_genus.csv"
)

_HOST_LABELS = {
    "BEE": "Bee-associated",
    "WASP": "Wasp-associated",
    "ATTINE_ANT": "Attine ant-associated",
    "UNRESOLVED": "Host context unresolved",
}


# ---------------------------------------------------------------------------
# Small IO helpers
# ---------------------------------------------------------------------------

def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write via a tmp-sibling + os.replace so a killed process cannot leave a
    truncated aggregate that every interactive-figures consumer reads as fewer
    strains/classes than the run actually produced (mirrors
    mamey/packaging.py::_atomic_write_text)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _first(glob_dir: Path, *patterns: str) -> Path | None:
    for pattern in patterns:
        hits = sorted(glob_dir.glob(pattern))
        if hits:
            return hits[0]
    return None


def _package_dir(runs_dir: Path, strain: str) -> Path | None:
    """Resolve the sealed 'package' directory for a strain under runs_dir."""
    cand = runs_dir / strain / "package"
    if cand.is_dir():
        return cand
    # Tolerate a run dir that IS the package dir, or a flat layout.
    cand2 = runs_dir / strain
    if cand2.is_dir() and _first(cand2, "*_2_inventory.csv"):
        return cand2
    return None


# ---------------------------------------------------------------------------
# Per-field extractors
# ---------------------------------------------------------------------------

def machinery_role(gene_functions: str) -> str | None:
    """Return the machinery role for an antiSMASH gene_functions string.

    Precedence: Biosynthetic additional > Biosynthetic core > Resistance >
    Transport > Regulatory. Returns None for non-machinery genes.
    """
    if not gene_functions:
        return None
    for role, pattern in _ROLE_TESTS:
        if pattern.search(gene_functions):
            return role
    return None


def classes_from_inventory(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    """Per product-class boundary tallies from inventory rows.

    One inventory row == one physical strain-BGC record. Products split on ';'
    and deduped within the BGC; hybrid BGCs contribute once to every class, so
    class denominators are nonexclusive.
    """
    classes: dict[str, dict[str, int]] = {}
    for row in rows:
        boundary = _BOUNDARY_MAP.get((row.get("Boundary") or "").strip())
        seen = {
            p.strip()
            for p in (row.get("Products") or "").split(";")
            if p.strip()
        }
        for cls in seen:
            bucket = classes.setdefault(
                cls, {"total": 0, "edge": 0, "full": 0, "interior": 0}
            )
            bucket["total"] += 1
            if boundary:
                bucket[boundary] += 1
    return classes


def _gene_table(pkg: Path, strain: str) -> tuple[list[dict[str, str]], str]:
    """Return (deduped physical-CDS rows, gene_functions_field_name).

    Prefers ``*_cds_table.csv``; falls back to ``*_gene_by_gene_all_bgcs.csv``.
    Dedup key = (contig, locus_tag, start, end). The returned dicts always carry
    'length_aa' (int-parseable str) and 'gene_functions'.
    """
    cds = _first(pkg, f"{strain}_cds_table.csv", "*_cds_table.csv")
    if cds is not None:
        raw = _read_csv(cds)
        deduped: dict[tuple, dict[str, str]] = {}
        for r in raw:
            key = (r.get("contig"), r.get("locus_tag"), r.get("start"), r.get("end"))
            deduped.setdefault(key, r)
        return list(deduped.values()), "gene_functions"

    gg = _first(pkg, f"{strain}_gene_by_gene_all_bgcs.csv", "*_gene_by_gene_all_bgcs.csv")
    if gg is not None:
        raw = _read_csv(gg)
        deduped: dict[tuple, dict[str, str]] = {}
        for r in raw:
            key = (r.get("contig"), r.get("locus_tag"), r.get("cds_start"), r.get("cds_end"))
            # Normalize the columns we rely on.
            r = {
                **r,
                "length_aa": r.get("aa_length", ""),
                "gene_functions": r.get("gene_function_inference", ""),
            }
            deduped.setdefault(key, r)
        return list(deduped.values()), "gene_functions"

    return [], "gene_functions"


def _length_aa(row: dict[str, str]) -> int | None:
    val = (row.get("length_aa") or "").strip()
    if not val:
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Host crosswalk
# ---------------------------------------------------------------------------

def load_host_crosswalk(
    measured_activity: Path = DEFAULT_MEASURED_ACTIVITY,
    strain_genus: Path = DEFAULT_STRAIN_GENUS,
) -> dict[str, dict[str, str]]:
    """Return {strain: {host, genus}} from the accession-bearing crosswalk."""
    table: dict[str, dict[str, str]] = {}
    if measured_activity.is_file():
        for r in _read_csv(measured_activity):
            sid = (r.get("strain") or "").strip()
            if sid:
                table[sid] = {
                    "host": (r.get("host") or "").strip(),
                    "genus": (r.get("genus") or "").strip(),
                }
    if strain_genus.is_file():
        for r in _read_csv(strain_genus):
            sid = (r.get("strain") or "").strip()
            if not sid:
                continue
            entry = table.setdefault(sid, {"host": "", "genus": ""})
            if not entry.get("genus"):
                entry["genus"] = (r.get("genus") or "").strip()
    return table


def host_context(strain: str, crosswalk: dict[str, dict[str, str]]) -> dict[str, str]:
    """Map a strain to a claim-safe hostContext block.

    ATTINE_ANT membership follows the explicit nine-strain cohort. Bee/wasp
    membership is read from the crosswalk host field. Anything without support
    stays UNRESOLVED; no host is inferred from an identifier or ecology label.
    """
    if strain in ATTINE_ANT_STRAINS:
        group = "ATTINE_ANT"
        return {
            "group": group,
            "label": _HOST_LABELS[group],
            "hostSpecies": "",
            "location": "",
            "source": "Figure Factory attine cohort (explicit nine-strain list)",
        }
    entry = crosswalk.get(strain)
    host = (entry or {}).get("host", "").strip()
    if host:
        group = "WASP" if "wasp" in host.lower() else "BEE"
        return {
            "group": group,
            "label": _HOST_LABELS[group],
            "hostSpecies": host,
            "location": "",  # not present in this crosswalk
            "source": "strain_data/cohort_master/measured_activity_table.csv",
        }
    group = "UNRESOLVED"
    return {
        "group": group,
        "label": _HOST_LABELS[group],
        "hostSpecies": "",
        "location": "",
        "source": "",
    }


# ---------------------------------------------------------------------------
# Per-strain + aggregate builders
# ---------------------------------------------------------------------------

def _engine_version(pkg: Path, strain: str) -> str:
    ms = _first(pkg, f"{strain}_manifest_short.json", "manifest_short.json")
    if ms is not None:
        try:
            return json.loads(ms.read_text(encoding="utf-8")).get("mamey_version", "") or ""
        except Exception:
            return ""
    return ""


def _package_name(runs_dir: Path, pkg: Path, strain: str, engine_ver: str) -> str:
    zip_hit = _first(runs_dir / strain, "*.zip") or _first(pkg, "*.zip")
    if zip_hit is not None:
        return zip_hit.name
    suffix = f"_engine{engine_ver}" if engine_ver else ""
    return f"{strain}_SapoteMamey{suffix}_Complete_Package"


def build_strain_record(
    runs_dir: Path,
    strain: str,
    crosswalk: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    pkg = _package_dir(runs_dir, strain)
    if pkg is None:
        return None

    inv_path = _first(pkg, f"{strain}_2_inventory.csv", "*_2_inventory.csv")
    triage_path = _first(pkg, f"{strain}_4_triage_board.csv", "*_4_triage_board.csv")
    inv_rows = _read_csv(inv_path) if inv_path else []

    # bgcRows: physical BGC records (inventory); note triage board matches it.
    bgc_rows = len(inv_rows)
    if not bgc_rows and triage_path:
        bgc_rows = len(_read_csv(triage_path))

    classes = classes_from_inventory(inv_rows)

    gene_rows, gf_field = _gene_table(pkg, strain)
    cds_rows = len(gene_rows)
    unique_physical = cds_rows  # rows are already deduped physical CDS
    machinery: dict[str, list[int]] = {}
    for r in gene_rows:
        role = machinery_role(r.get(gf_field, ""))
        if role is None:
            continue
        aa = _length_aa(r)
        if aa is None:
            continue
        machinery.setdefault(role, []).append(aa)
    machinery_genes = sum(len(v) for v in machinery.values())

    governance = GOVERNANCE_OVERRIDES.get(strain, "GOVERNED")
    engine_ver = _engine_version(pkg, strain)

    return {
        "governance": governance,
        "package": _package_name(runs_dir, pkg, strain, engine_ver),
        "bgcRows": bgc_rows,
        "cdsRows": cds_rows,
        "uniquePhysicalGenes": unique_physical,
        "machineryGenes": machinery_genes,
        "classes": classes,
        "machinery": machinery,
        "hostContext": host_context(strain, crosswalk),
        "_engineVersion": engine_ver,  # internal; stripped before emit
    }


def _discover_strains(runs_dir: Path) -> list[str]:
    out = []
    for child in sorted(runs_dir.iterdir()):
        if child.is_dir() and _package_dir(runs_dir, child.name) is not None:
            out.append(child.name)
    return out


def _build_cohorts(records: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Reconstruct the six host cohorts from the strains actually present."""
    def group(sid: str) -> str:
        return records[sid]["hostContext"]["group"]

    def gov(sid: str) -> bool:
        return records[sid]["governance"] == "GOVERNED"

    bee = sorted(s for s in records if group(s) == "BEE")
    wasp = sorted(s for s in records if group(s) == "WASP")
    attine = sorted(s for s in records if group(s) == "ATTINE_ANT")
    unresolved = sorted(s for s in records if group(s) == "UNRESOLVED")

    bee_gov = [s for s in bee if gov(s)]
    quarantine_note = "Includes a quarantined (AUDIT_ONLY_QUARANTINED) record."
    bee_has_quarantine = any(not gov(s) for s in bee)
    beewasp = sorted(bee + wasp)
    beewasp_gov = [s for s in beewasp if gov(s)]

    cohorts: dict[str, dict[str, Any]] = {}
    if bee_gov:
        cohorts["BEE_GOVERNED"] = {
            "label": "Bee cohort — governed", "strains": bee_gov, "warning": "",
        }
    if bee:
        cohorts["BEE_FULL"] = {
            "label": "Bee cohort — full", "strains": bee,
            "warning": quarantine_note if bee_has_quarantine else "",
        }
    if attine:
        cohorts["ATTINE_ANT"] = {
            "label": "Attine-ant cohort", "strains": attine, "warning": "",
        }
    if beewasp_gov:
        cohorts["BEE_WASP_GOVERNED"] = {
            "label": "Bee + wasp cohort — governed", "strains": beewasp_gov,
            "warning": "",
        }
    if beewasp:
        cohorts["BEE_WASP_FULL"] = {
            "label": "Bee + wasp cohort — full", "strains": beewasp,
            "warning": quarantine_note if any(not gov(s) for s in beewasp) else "",
        }
    unresolved_gov = [s for s in unresolved if gov(s)]
    if unresolved_gov:
        cohorts["UNRESOLVED_GOVERNED"] = {
            "label": "Unresolved-host cohort — governed",
            "strains": unresolved_gov, "warning": "",
        }
    return cohorts


def build_widget_data(
    runs_dir: str | Path,
    strains: Iterable[str] | None = None,
    measured_activity: str | Path = DEFAULT_MEASURED_ACTIVITY,
    strain_genus: str | Path = DEFAULT_STRAIN_GENUS,
) -> dict[str, Any]:
    """Build the {meta, strains} widget-data aggregate from sealed packages."""
    runs_dir = Path(runs_dir)
    crosswalk = load_host_crosswalk(Path(measured_activity), Path(strain_genus))

    if strains is None:
        strain_ids = _discover_strains(runs_dir)
    else:
        strain_ids = list(strains)

    records: dict[str, dict[str, Any]] = {}
    engine_versions: set[str] = set()
    for sid in strain_ids:
        rec = build_strain_record(runs_dir, sid, crosswalk)
        if rec is None:
            continue
        ev = rec.pop("_engineVersion", "")
        if ev:
            engine_versions.add(ev)
        records[sid] = rec

    governed = [s for s, r in records.items() if r["governance"] == "GOVERNED"]
    engine_str = ", ".join(sorted(engine_versions)) if engine_versions else "unknown"

    meta = {
        "sourceRelease": f"Sapote-Mamey sealed packages / engine {engine_str}",
        "generated": _today(),
        "axisDefaultAa": 2000,
        "governance": {
            s: r["governance"]
            for s, r in records.items()
            if r["governance"] != "GOVERNED"
        },
        "machineryAssignmentPrecedence": MACHINERY_PRECEDENCE,
        "cohortSources": {
            "beeHostMetadata": "strain_data/cohort_master/measured_activity_table.csv",
            "attineAssignment": (
                "Figure Factory attine cohort: "
                + ", ".join(sorted(ATTINE_ANT_STRAINS))
            ),
        },
        "cohorts": _build_cohorts(records),
        "strainCount": len(records),
        "governedStrainCount": len(governed),
        "bgcRowsAll": sum(r["bgcRows"] for r in records.values()),
        "bgcRowsGoverned": sum(records[s]["bgcRows"] for s in governed),
        "uniquePhysicalGenesAll": sum(r["uniquePhysicalGenes"] for r in records.values()),
        "uniquePhysicalGenesGoverned": sum(
            records[s]["uniquePhysicalGenes"] for s in governed
        ),
    }
    return {"meta": meta, "strains": records}


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Structural validation (the aggregate; widget_view_schema.json describes the
# separate view-spec contract, not this aggregate).
# ---------------------------------------------------------------------------

_STRAIN_REQUIRED = [
    "governance", "package", "bgcRows", "cdsRows", "uniquePhysicalGenes",
    "machineryGenes", "classes", "machinery", "hostContext",
]
_META_REQUIRED = [
    "sourceRelease", "machineryAssignmentPrecedence", "cohorts",
    "strainCount", "governedStrainCount",
]


def validate_widget_data(data: dict[str, Any]) -> list[str]:
    """Return a list of structural problems (empty == valid)."""
    problems: list[str] = []
    if not isinstance(data.get("meta"), dict):
        problems.append("meta is missing or not an object")
    else:
        for key in _META_REQUIRED:
            if key not in data["meta"]:
                problems.append(f"meta.{key} missing")
    strains = data.get("strains")
    if not isinstance(strains, dict):
        problems.append("strains is missing or not an object")
        return problems
    for sid, rec in strains.items():
        for key in _STRAIN_REQUIRED:
            if key not in rec:
                problems.append(f"strains.{sid}.{key} missing")
        hc = rec.get("hostContext", {})
        if isinstance(hc, dict) and "group" not in hc:
            problems.append(f"strains.{sid}.hostContext.group missing")
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit_figures(data_path: Path, out_dir: Path, scope: str) -> dict[str, Any]:
    """Invoke the vendored publication_bridge on an emitted aggregate.

    Returns a small status dict. Never raises on a missing render dependency.
    """
    from . import publication_bridge as pb

    if not getattr(pb, "_HAVE_REPORTLAB", False):
        return {"status": "SKIPPED", "reason": "reportlab/render deps not installed"}
    ns = argparse.Namespace(
        data=data_path,
        output=out_dir,
        figure="all",
        scope=scope,
        min_memberships=10,
        axis_ceiling=2000,
    )
    try:
        rc = pb.build(ns)
        return {"status": "PASS" if rc == 0 else "FAIL", "output": str(out_dir)}
    except Exception as exc:  # pragma: no cover - depends on optional deps
        return {"status": "ERROR", "reason": str(exc)}


def run(
    runs_dir: str | Path,
    out: str | Path,
    strains: Iterable[str] | None = None,
    emit_figures: bool = False,
    figures_out: str | Path | None = None,
    scope: str = "GOVERNED",
) -> dict[str, Any]:
    data = build_widget_data(runs_dir, strains)
    problems = validate_widget_data(data)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(out_path, json.dumps(data, indent=1) + "\n", encoding="utf-8")

    result = {
        "out": str(out_path),
        "strainCount": data["meta"]["strainCount"],
        "governedStrainCount": data["meta"]["governedStrainCount"],
        "validation": "PASS" if not problems else "FAIL",
        "problems": problems,
    }
    if emit_figures:
        fig_dir = Path(figures_out) if figures_out else out_path.parent / "figures_publication"
        result["figures"] = _emit_figures(out_path, fig_dir, scope)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Emit the AS widget-data aggregate from sealed Mamey packages."
    )
    p.add_argument("--runs-dir", required=True,
                   help="Directory containing <STRAIN>/package/ sealed outputs.")
    p.add_argument("--out", default="AS_All_Strains_Widget_Data.json",
                   help="Output JSON path (default: AS_All_Strains_Widget_Data.json).")
    p.add_argument("--strains", nargs="*", default=None,
                   help="Explicit strain list (default: discover all under --runs-dir).")
    p.add_argument("--emit-figures", action="store_true",
                   help="Also render publication figures via the vendored "
                        "publication_bridge (needs reportlab; skipped if absent).")
    p.add_argument("--figures-out", default=None,
                   help="Output directory for --emit-figures (default: <out>/figures_publication).")
    p.add_argument("--scope", default="GOVERNED",
                   help="publication_bridge scope for --emit-figures (default: GOVERNED).")
    args = p.parse_args(argv)

    result = run(
        runs_dir=args.runs_dir,
        out=args.out,
        strains=args.strains,
        emit_figures=args.emit_figures,
        figures_out=args.figures_out,
        scope=args.scope,
    )
    emit(json.dumps(result, indent=2))
    return 0 if result["validation"] == "PASS" else 1


def interactive_figures_command(args: argparse.Namespace) -> int:
    """mamey CLI entry point for the `interactive-figures` subcommand."""
    result = run(
        runs_dir=args.runs_dir,
        out=args.out,
        strains=getattr(args, "strains", None),
        emit_figures=getattr(args, "emit_figures", False),
        figures_out=getattr(args, "figures_out", None),
        scope=getattr(args, "scope", "GOVERNED"),
    )
    emit(json.dumps(result, indent=2))
    return 0 if result["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
