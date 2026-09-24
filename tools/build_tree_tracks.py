#!/usr/bin/env python3
"""Adapt hash-bound Figure Factory BIOASSAY tracks for exact-tip R rendering.

Usage: python tools/build_tree_tracks.py --config config.json --out new-directory
No aggregation, taxonomy inference, identifier normalization, or missing-value imputation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.csv_safety import SafeDictWriter, csv_safe_cell

class TrackHold(ValueError):
    """Input cannot be admitted to a quantitative tree display."""

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def bound(root, spec):
    locator = Path(spec["path"])
    if locator.is_absolute():
        raise TrackHold("TRACK_LOCATOR_HOLD: use a relative path under input_root")
    path = (root / locator).resolve()
    if not path.is_relative_to(root):
        raise TrackHold("TRACK_LOCATOR_HOLD: input escapes input_root")
    if not path.is_file() or digest(path) != spec.get("sha256"):
        raise TrackHold("TRACK_HASH_HOLD: input missing or changed")
    return path

def read_table(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
            raise TrackHold("TRACK_SCHEMA_HOLD: duplicate columns")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise TrackHold("TRACK_SCHEMA_HOLD: ragged table")
    return rows

def write_table(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = SafeDictWriter(handle, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)

def prepare(config_path, output):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    if config.get("schema") != "sapote.tree-tracks.v1":
        raise TrackHold("TRACK_SCHEMA_HOLD: expected sapote.tree-tracks.v1")
    root = (config_path.parent / config["input_root"]).resolve()
    meta_path = bound(root, config["metadata"])
    metadata = read_table(meta_path)
    if not metadata or not {"tip", "strain", "label", "role"}.issubset(metadata[0]):
        raise TrackHold("TRACK_METADATA_HOLD: tip, strain, label, role required")
    tips, queries = set(), set()
    rows = []
    for item in metadata:
        tip, strain, label, role = (item[k] for k in ("tip", "strain", "label", "role"))
        if not tip or tip in tips or not label or role not in {"query", "reference", "outgroup"}:
            raise TrackHold("TRACK_METADATA_HOLD: unique exact tips, labels and explicit roles required")
        if any(csv_safe_cell(value) != value for value in (tip, strain, label)):
            raise TrackHold("TRACK_METADATA_HOLD: formula-leading identifiers or labels are not admissible")
        tips.add(tip)
        if role == "query":
            if not strain or strain in queries:
                raise TrackHold("TRACK_METADATA_HOLD: query strain must bind exactly one tip")
            queries.add(strain)
        rows.append(dict(tip=tip, label=label, role=role))
    if not queries:
        raise TrackHold("TRACK_METADATA_HOLD: no query strains")
    specs = config.get("tracks", [])
    if not specs:
        raise TrackHold("TRACK_SELECTION_HOLD: at least one admitted track required")
    series, sources, columns, labels = [], [], set(), set()
    for spec in specs:
        column, label, colour = (spec[k] for k in ("column", "label", "colour"))
        if (not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", column) or column in columns
                or column in {"tip", "label", "role"} or not label or label in labels
                or not re.fullmatch(r"#[0-9a-fA-F]{6}", colour)):
            raise TrackHold("TRACK_SERIES_HOLD: unique columns/labels and hex colours required")
        columns.add(column); labels.add(label)
        receipt_path = bound(root, spec["receipt"])
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("status") not in {"PASS_DATA_READY_R_NOT_REQUESTED", "PASS_FIGURE_FACTORY_RENDERED"}:
            raise TrackHold("TRACK_ADMISSION_HOLD: Figure Factory receipt not passed")
        artifacts = receipt.get("outputs", [])
        by_name = {a["logical_locator"]: a for a in artifacts}
        if len(by_name) != len(artifacts):
            raise TrackHold("TRACK_ADMISSION_HOLD: duplicate receipt outputs")
        def artifact(name):
            if name not in by_name:
                raise TrackHold("TRACK_ADMISSION_HOLD: missing selected-track artifact")
            record = by_name[name]
            return bound(receipt_path.parent, {"path": name, "sha256": record["sha256"]})
        track = artifact("bioassay_tree_track.tsv")
        caption = json.loads(artifact("bioassay_caption_methods.json").read_text())
        selection = caption.get("tree_track_selection") or {}
        required = {"selection_id", "target", "target_state", "timepoint_hours", "material_type",
                    "final_concentration_ug_ml", "aggregation", "strain_roster", "material_ids_by_strain"}
        if caption.get("tree_overlay_state") != "EMITTED_EXPLICIT_SELECTION" or not required.issubset(selection):
            raise TrackHold("TRACK_SELECTION_HOLD: explicit admitted selection required")
        values = {}
        for row in read_table(track):
            strain = row.get("strain")
            if not strain or strain in values or row.get("channel") != "BIOASSAY" or row.get("feature") != selection["selection_id"]:
                raise TrackHold("TRACK_JOIN_HOLD: duplicate strain or mismatched channel/selection")
            state, value = row.get("state"), row.get("value")
            if state == "OBSERVED":
                try:
                    if not math.isfinite(float(value)):
                        raise ValueError
                except (ValueError, TypeError):
                    raise TrackHold("TRACK_VALUE_HOLD: observed value must be finite") from None
            elif state == "NOT_MEASURED" and value == "":
                pass
            else:
                raise TrackHold("TRACK_VALUE_HOLD: only OBSERVED numeric or NOT_MEASURED blank accepted")
            values[strain] = value
        roster = selection["strain_roster"]
        if len(roster) != len(set(roster)) or set(roster) != set(values) or set(values) != queries:
            raise TrackHold("TRACK_JOIN_HOLD: exact query roster differs from admitted selection")
        for meta, row in zip(metadata, rows):
            row[column] = values[meta["strain"]] if meta["role"] == "query" else ""
        series.append(dict(column=column, label=label, colour=colour))
        sources.append(dict(column=column, receipt=spec["receipt"], selection=selection,
                            track_sha256=digest(track)))
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".tree-tracks-", dir=output.parent))
    try:
        write_table(stage / "tracks.tsv", ["tip", "label", "role", *[s["column"] for s in series]], rows)
        write_table(stage / "series.tsv", ["column", "label", "colour"], series)
        receipt = dict(schema="sapote.tree-tracks.v1", status="PASS_EXACT_ADMITTED_VALUES",
                       metadata=config["metadata"], sources=sources, config_sha256=digest(config_path),
                       missingness="NOT_MEASURED remains blank; recorded zero remains numeric zero",
                       ceiling="Strain-level assay context; no locus attribution or taxonomic inference",
                       outputs=[dict(path=p.name, sha256=digest(p), bytes=p.stat().st_size) for p in sorted(stage.iterdir())])
        (stage / "track_adapter_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage)
        raise
    return output

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        prepare(args.config, args.out)
    except (TrackHold, OSError, KeyError, TypeError, ValueError) as exc:
        sys.stderr.write(f"TREE_TRACK_REFUSED: {exc}\n")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
