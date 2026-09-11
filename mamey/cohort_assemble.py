"""cohort_assemble.py — assemble many sealed packages into ONE cohort table
(strain_summary + bgc_inventory + class_by_strain) without the O(N^2) per-run
master-workbook rewrite (ADD-01 substrate / Figure Factory feed).

Why: the persistent `--master` workbook is rewritten on every strain run
(accumulate-then-rewrite), which is O(N^2) across a growing cohort and couples
figure prep to the engine. The cohort figures only need a tidy substrate: one row
per strain, one row per BGC, and a class-by-strain matrix. This module reads
already-sealed packages (glob a dir) once and emits that substrate directly.

It follows `tools/export_figure_ready.py` conventions: tidy (one observation per
row), snake_case headers, no formulas. But it reads the sealed CSV/JSON package
files (`*_1_intake.json`, `*_2_inventory.csv`) rather than the workbook, so it has
no openpyxl dependency for the CSV path (xlsx emission is optional).

Claim-safety: pure re-projection of sealed capacity-level outputs. No scoring, no
tier movement, no bioactivity/structure claims. Carries each BGC's existing
`safe_claim` string verbatim.

Usage (library):
    from mamey.cohort_assemble import assemble_cohort, write_cohort_csv
    cohort = assemble_cohort("path/to/runs_dir")
    write_cohort_csv(cohort, "COHORT_MASTER.csv")
    # optional xlsx (needs openpyxl):
    write_cohort_xlsx(cohort, "COHORT_MASTER.xlsx")
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
csv.field_size_limit(min(__import__("sys").maxsize, 2**31 - 1))  # v9.7.409 H12: engine-written CSV fields may exceed 128 KB
import glob
import json
import os
from collections import Counter, defaultdict
from typing import Any
from .xlsx_determinism import save_workbook_safely as _save_wb_safely

# ---- strain_summary columns (one row per strain) ----
STRAIN_SUMMARY_COLUMNS = [
    "strain",
    "taxonomy",
    "genus",
    "source",
    "release",
    "engine_version",
    "genome_bp",
    "contigs",
    "n50",
    "gc_pct",
    "bgc_count",
]

# ---- bgc_inventory columns (one row per BGC) ----
BGC_INVENTORY_COLUMNS = [
    "strain",
    "BGC_ID",
    "contig",
    "region",
    "boundary",
    "length_kb",
    "products",
    "n_classes",
    "arch",
    "kcb_top",
    "kcb_score",
    "safe_claim",
]


def _num(x: Any):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def _genus_of(tax: Any) -> str:
    """Genus = first whitespace-delimited token of the taxonomy string."""
    return (str(tax).split()[0] if tax else "") or ""


def find_packages(runs_dir: str) -> list[str]:
    """Return sorted package dirs (each holding a `*_1_intake.json`) under runs_dir.

    A package dir is identified by containing exactly one intake json. Handles both
    `<runs>/<strain>/package/` (audit_runs) and flat layouts.
    """
    patterns = [
        os.path.join(runs_dir, "*", "package", "*_1_intake.json"),
        os.path.join(runs_dir, "*", "*_1_intake.json"),
        os.path.join(runs_dir, "*_1_intake.json"),
    ]
    seen: set[str] = set()
    dirs: list[str] = []
    for pat in patterns:
        for p in glob.glob(pat):
            d = os.path.realpath(os.path.dirname(p))
            if d not in seen:
                seen.add(d)
                dirs.append(os.path.dirname(p))
    return sorted(dirs)


def _package_prefix(pkg_dir: str) -> str:
    """Strain prefix used on the numbered files in this package (e.g. 'AS-XXX')."""
    hits = glob.glob(os.path.join(pkg_dir, "*_1_intake.json"))
    if not hits:
        return ""
    return os.path.basename(hits[0]).replace("_1_intake.json", "")


def _engine_version(pkg_dir: str) -> str:
    mpath = os.path.join(pkg_dir, "manifest.json")
    if os.path.isfile(mpath):
        try:
            with open(mpath, encoding="utf-8") as fh:
                m = json.load(fh)
            return str(m.get("workflow_version") or m.get("engine_version") or "").strip()
        except (OSError, ValueError, json.JSONDecodeError):
            return ""
    return ""


def read_package(pkg_dir: str) -> dict | None:
    """Read one sealed package into {strain_summary, bgc_rows, class_counts}.

    Returns None if the package has no intake json.
    """
    prefix = _package_prefix(pkg_dir)
    if not prefix:
        return None
    intake_path = os.path.join(pkg_dir, f"{prefix}_1_intake.json")
    inv_path = os.path.join(pkg_dir, f"{prefix}_2_inventory.csv")
    try:
        with open(intake_path, encoding="utf-8") as fh:
            intake = json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        return None

    strain = str(intake.get("strain_id") or intake.get("display_name") or prefix).strip()
    asm = intake.get("assembly") or {}
    engine = _engine_version(pkg_dir)

    strain_summary = {
        "strain": strain,
        "taxonomy": intake.get("taxonomy") or "",
        "genus": _genus_of(intake.get("taxonomy")),
        "source": intake.get("source") or "",
        "release": intake.get("release") or "",
        "engine_version": engine,
        "genome_bp": asm.get("genome_bp"),
        "contigs": asm.get("contigs"),
        "n50": asm.get("n50"),
        "gc_pct": asm.get("gc_pct"),
        "bgc_count": intake.get("bgc_count"),
    }

    bgc_rows: list[dict] = []
    class_counts: Counter = Counter()
    if os.path.isfile(inv_path):
        try:
            with open(inv_path, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    products = (r.get("Products") or "").strip()
                    classes = [c.strip() for c in products.split(";") if c.strip()]
                    for c in classes:
                        class_counts[c] += 1
                    bgc_rows.append(
                        {
                            "strain": strain,
                            "BGC_ID": (r.get("BGC_ID") or "").strip(),
                            "contig": (r.get("Contig") or "").strip(),
                            "region": (r.get("Region") or r.get("antiSMASH_Region") or "").strip(),
                            "boundary": (r.get("Boundary") or "").strip(),
                            "length_kb": _num(r.get("Length_kb")),
                            "products": products,
                            "n_classes": len(classes),
                            "arch": (r.get("Arch") or "").strip(),
                            "kcb_top": (r.get("KCB_top") or "").strip(),
                            "kcb_score": _num(r.get("KCB_score")),
                            "safe_claim": (r.get("safe_claim") or "").strip(),
                        }
                    )
        except OSError:
            pass

    return {
        "strain_summary": strain_summary,
        "bgc_rows": bgc_rows,
        "class_counts": dict(class_counts),
    }


def assemble_cohort(runs_dir: str) -> dict:
    """Assemble a runs-dir of sealed packages into one cohort structure.

    Returns:
      {
        "strain_summary": [ {..}, .. ],       # one row per strain
        "bgc_inventory": [ {..}, .. ],        # one row per BGC
        "class_by_strain": {                  # {strain: {class: count}}
            "AS-XXX": {"NRPS": 3, ...}, ...
        },
        "classes": [ sorted unique class names ],
        "meta": {n_strains, n_bgcs, engine_versions, mixed_engine},
      }
    """
    pkg_dirs = find_packages(runs_dir)
    strain_summary: list[dict] = []
    bgc_inventory: list[dict] = []
    class_by_strain: dict[str, dict[str, int]] = {}
    all_classes: set[str] = set()
    engine_versions: set[str] = set()

    for pkg_dir in pkg_dirs:
        pkg = read_package(pkg_dir)
        if pkg is None:
            continue
        ss = pkg["strain_summary"]
        strain_summary.append(ss)
        if ss["engine_version"]:
            engine_versions.add(ss["engine_version"])
        bgc_inventory.extend(pkg["bgc_rows"])
        # AUDIT_374: MERGE (not overwrite) per-package class counts into the strain's
        # entry. Two package dirs for the same strain key under one runs_dir (a re-run left in
        # place -- the project's own strain-folder-freshen convention explicitly retires old runs
        # to older_data/ rather than always deleting them, so this coexistence is expected) used
        # to silently DROP the earlier package's class counts entirely: this dict assignment
        # replaced rather than accumulated, so class_by_strain (the wide matrix CSV / cohort
        # heatmap feed) under-reported classes that bgc_inventory (unioned, not overwritten) still
        # listed correctly for the very same strain -- an internal inconsistency between two
        # tables of the same cohort output.
        strain_classes = class_by_strain.setdefault(ss["strain"], {})
        for _cls, _n in pkg["class_counts"].items():
            strain_classes[_cls] = strain_classes.get(_cls, 0) + _n
        all_classes.update(pkg["class_counts"].keys())

    strain_summary.sort(key=lambda r: str(r["strain"]))
    bgc_inventory.sort(key=lambda r: (str(r["strain"]), str(r["BGC_ID"])))

    return {
        "strain_summary": strain_summary,
        "bgc_inventory": bgc_inventory,
        "class_by_strain": class_by_strain,
        "classes": sorted(all_classes),
        "meta": {
            "n_strains": len(strain_summary),
            "n_bgcs": len(bgc_inventory),
            "engine_versions": sorted(engine_versions),
            "mixed_engine": len(engine_versions) > 1,
        },
    }


def _class_matrix_rows(cohort: dict) -> tuple[list[str], list[dict]]:
    """Build the class_by_strain wide matrix: header + one row per strain."""
    classes = cohort["classes"]
    header = ["strain"] + classes
    rows = []
    for ss in cohort["strain_summary"]:
        strain = ss["strain"]
        counts = cohort["class_by_strain"].get(strain, {})
        row = {"strain": strain}
        for c in classes:
            row[c] = counts.get(c, 0)
        rows.append(row)
    return header, rows


def write_cohort_csv(cohort: dict, out_path: str) -> dict:
    """Write the primary COHORT_MASTER.csv (bgc_inventory) + two sibling CSVs.

    Sibling files are written next to out_path:
      - <base>_strain_summary.csv
      - <base>_class_by_strain.csv
    Returns {main, strain_summary, class_by_strain} of written paths.
    """
    out_path = os.path.abspath(out_path)
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    base, _ext = os.path.splitext(out_path)

    # AUDIT_374: atomic writes (tmp-sibling + os.replace) for all three CSVs — this is the
    # ADD-01 / Figure Factory substrate; a process killed mid-write previously left a truncated
    # COHORT_MASTER.csv (or a sibling) on disk with no error surfaced, matching the atomic-write
    # gap already fixed this session elsewhere (packaging.py::_atomic_write_text,
    # workbook.py's _save_wb_safely(wb, tmp)+os.replace pattern).
    def _atomic_write_csv(path, fieldnames, rows):
        tmp = str(path) + ".tmp"
        try:
            with open(tmp, "w", newline="", encoding="utf-8") as fh:
                w = _SafeDictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    w.writerow(r)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        os.replace(tmp, path)

    # main = bgc_inventory (the widest, per-BGC substrate)
    _atomic_write_csv(out_path, BGC_INVENTORY_COLUMNS, cohort["bgc_inventory"])

    ss_path = f"{base}_strain_summary.csv"
    _atomic_write_csv(ss_path, STRAIN_SUMMARY_COLUMNS, cohort["strain_summary"])

    cm_path = f"{base}_class_by_strain.csv"
    header, rows = _class_matrix_rows(cohort)
    _atomic_write_csv(cm_path, header, rows)

    return {"main": out_path, "strain_summary": ss_path, "class_by_strain": cm_path}


def write_cohort_xlsx(cohort: dict, out_path: str) -> str:
    """Write a 3-sheet COHORT_MASTER.xlsx (strain_summary / bgc_inventory /
    class_by_strain). Requires openpyxl; raises ImportError if unavailable."""
    try:
        import openpyxl  # noqa: F401
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError("write_cohort_xlsx requires openpyxl") from exc

    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "strain_summary"
    ws1.append(STRAIN_SUMMARY_COLUMNS)
    for r in cohort["strain_summary"]:
        ws1.append([r.get(c) for c in STRAIN_SUMMARY_COLUMNS])

    ws2 = wb.create_sheet("bgc_inventory")
    ws2.append(BGC_INVENTORY_COLUMNS)
    for r in cohort["bgc_inventory"]:
        ws2.append([r.get(c) for c in BGC_INVENTORY_COLUMNS])

    ws3 = wb.create_sheet("class_by_strain")
    header, rows = _class_matrix_rows(cohort)
    ws3.append(header)
    for r in rows:
        ws3.append([r.get(c) for c in header])

    # AUDIT_374: atomic xlsx write, matching the established tmp-sibling + os.replace
    # pattern used for every other workbook writer in this codebase (workbook.py, master_workbook.py).
    _tmp = out_path + ".tmp"
    _save_wb_safely(wb, _tmp)
    os.replace(_tmp, out_path)
    return out_path


def run(runs_dir: str, out_path: str = "COHORT_MASTER.csv", xlsx: bool = False) -> dict:
    """Convenience entry: assemble + write CSVs (+ optional xlsx). Returns meta."""
    cohort = assemble_cohort(runs_dir)
    paths = write_cohort_csv(cohort, out_path)
    if xlsx:
        base, _ = os.path.splitext(os.path.abspath(out_path))
        paths["xlsx"] = write_cohort_xlsx(cohort, base + ".xlsx")
    meta = dict(cohort["meta"])
    meta["paths"] = paths
    return meta
