#!/usr/bin/env python3
"""Plan or render a declared catalog of phylogenetic display variants.

The catalog operates on completed, validated placement runs. It does not select
reference sequences, infer a tree, or promote a display subset into a new
analysis. Each rendered variant retains its upstream placement and selection
receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


SCHEMA = "sapote.tree-catalog.v1"
VIEWS = {"publication", "publication-detailed", "publication-noloc", "internal"}
PANELS = {"type_only", "type_plus_selected_non_type"}
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _path(value, base: Path, must_exist=True) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=must_exist)


def load_catalog(path):
    source = Path(path).resolve(strict=True)
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not isinstance(data.get("trees"), list):
        raise ValueError("TREE_CATALOG_SCHEMA")
    defaults = data.get("defaults") or {}
    default_views = defaults.get("views", ["publication", "publication-noloc"])
    default_ratios = defaults.get("reference_ratios", [1, 2, 3])
    jobs = []
    seen = set()
    for tree in data["trees"]:
        required = {"id", "run_dir", "group", "cohort_scope", "taxonomic_scope",
                    "reference_panel", "host_table", "ref_source_db"}
        if not isinstance(tree, dict) or not required <= set(tree):
            raise ValueError("TREE_CATALOG_ENTRY_SCHEMA")
        tree_id = tree["id"]
        if not isinstance(tree_id, str) or not SAFE.fullmatch(tree_id):
            raise ValueError("TREE_CATALOG_ID")
        panel = tree["reference_panel"]
        if panel not in PANELS:
            raise ValueError("TREE_CATALOG_REFERENCE_PANEL")
        views = tree.get("views", default_views)
        ratios = tree.get("reference_ratios", default_ratios)
        if not views or any(view not in VIEWS for view in views):
            raise ValueError("TREE_CATALOG_VIEW")
        if not ratios or any(type(ratio) is not int or ratio not in (1, 2, 3, 4) for ratio in ratios):
            raise ValueError("TREE_CATALOG_RATIO")
        spotlight = tree.get("spotlight_queries", [])
        if spotlight and (not isinstance(spotlight, list) or
                          any(not re.fullmatch(r"(?:AS|SID)-\d+", item) for item in spotlight)):
            raise ValueError("TREE_CATALOG_SPOTLIGHT")
        common = {
            "tree_id": tree_id,
            "run_dir": str(_path(tree["run_dir"], source.parent)),
            "group": tree["group"],
            "cohort_scope": tree["cohort_scope"],
            "taxonomic_scope": tree["taxonomic_scope"],
            "reference_panel": panel,
            "host_table": str(_path(tree["host_table"], source.parent)),
            "ref_source_db": str(_path(tree["ref_source_db"], source.parent)),
            "required_reference_table": str(_path(tree["required_reference_table"], source.parent)) if tree.get("required_reference_table") else "",
            "genus_roster": str(_path(tree["genus_roster"], source.parent)) if tree.get("genus_roster") else "",
            "aux_tables": [str(_path(item, source.parent)) for item in tree.get("aux_tables", [])],
            "spotlight_queries": spotlight,
            "figure_width": tree.get("figure_width", defaults.get("figure_width", 0)),
            "label_room": tree.get("label_room", defaults.get("label_room", 0)),
        }
        for ratio in ratios:
            for view in views:
                suffix = {"publication": "concise", "publication-detailed": "detailed",
                          "publication-noloc": "nogeo", "internal": "internal"}[view]
                job_id = f"{tree_id}_r{ratio}_{suffix}"
                if job_id in seen:
                    raise ValueError("TREE_CATALOG_DUPLICATE_JOB")
                seen.add(job_id)
                jobs.append(dict(common, job_id=job_id, reference_ratio=ratio, view=view))
    return source, data, jobs


def write_plan(catalog_path, destination):
    source, _data, jobs = load_catalog(catalog_path)
    payload = {
        "schema": "sapote.tree-catalog-plan.v1",
        "catalog": str(source),
        "catalog_sha256": _digest(source),
        "job_count": len(jobs),
        "jobs": jobs,
    }
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def render(catalog_path, outdir, python=sys.executable, rscript="Rscript"):
    source, _data, jobs = load_catalog(catalog_path)
    if any(job["spotlight_queries"] for job in jobs):
        raise ValueError("SPOTLIGHT_REQUIRES_DECLARED_QUERY_SUBSET_RUN")
    root = Path(outdir).resolve()
    if root.exists():
        raise ValueError("OUTPUT_EXISTS")
    root.mkdir(parents=True)
    tool = Path(__file__).with_name("placement_display.py")
    results = []
    for job in jobs:
        destination = root / job["job_id"]
        command = [python, str(tool), job["run_dir"], "--name", job["job_id"],
                   "--group", job["group"], "--host-table", job["host_table"],
                   "--ref-source-db", job["ref_source_db"], "--neighbors-per-query",
                   str(job["reference_ratio"]), "--label-style", job["view"],
                   "--rscript", rscript, "--out", str(destination)]
        if job["genus_roster"]:
            command += ["--genus-roster", job["genus_roster"]]
        if job["required_reference_table"]:
            command += ["--required-reference-table", job["required_reference_table"]]
        for path in job["aux_tables"]:
            command += ["--aux-table", path]
        if job["figure_width"]:
            command += ["--figure-width", str(job["figure_width"])]
        if job["label_room"]:
            command += ["--label-room", str(job["label_room"])]
        result = subprocess.run(command, text=True, capture_output=True)
        results.append({"job_id": job["job_id"], "command": command,
                        "returncode": result.returncode,
                        "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            break
    receipt = {
        "schema": "sapote.tree-catalog-render.v1",
        "catalog": str(source),
        "catalog_sha256": _digest(source),
        "planned_jobs": len(jobs),
        "completed_jobs": sum(item["returncode"] == 0 for item in results),
        "results": results,
    }
    (root / "TREE_CATALOG_RENDER_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if len(results) == len(jobs) and all(not item["returncode"] for item in results) else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="validate a catalog and write its expanded job plan")
    plan.add_argument("catalog")
    plan.add_argument("--out", required=True)
    run = sub.add_parser("render", help="render every declared variant from completed placement runs")
    run.add_argument("catalog")
    run.add_argument("--outdir", required=True)
    run.add_argument("--python", default=sys.executable)
    run.add_argument("--rscript", default="Rscript")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            payload = write_plan(args.catalog, args.out)
            sys.stdout.write(json.dumps({"jobs": payload["job_count"], "plan": args.out}) + "\n")
            return 0
        return render(args.catalog, args.outdir, args.python, args.rscript)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"TREE_CATALOG_REFUSED: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
