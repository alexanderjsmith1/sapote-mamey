"""Validated saved-coordinate replay shared by optional embedding displays.

This module never fits an embedding or changes saved coordinate values.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "sapote.embedding-replay.v1"
METHODS = {"trimap": "TriMap", "tsne": "t-SNE"}


class ReplayRefusal(ValueError):
    """A replay cannot preserve the declared data and membership contract."""


def read_snapshot(path: Path, *, expected_sha256: str | None = None) -> tuple[bytes, dict]:
    """Bind the exact bytes returned for parsing, with no path reopen."""
    raw = path.read_bytes()
    actual = {"path": str(path.resolve()), "bytes": len(raw),
              "sha256": hashlib.sha256(raw).hexdigest()}
    if expected_sha256 is not None and actual["sha256"] != expected_sha256:
        raise ReplayRefusal(f"consumed input hash mismatch: {path}")
    return raw, actual


def binding(path: Path) -> dict:
    """Bind bytes in place without copying scientific inputs."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def checked_input(root: Path, spec: dict, label: str) -> tuple[Path, dict]:
    """Resolve a declared input relative to the manifest and check its hash."""
    if not isinstance(spec, dict) or set(spec) != {"path", "sha256"}:
        raise ReplayRefusal(f"{label} requires exactly path and sha256")
    raw, expected = spec["path"], spec["sha256"]
    if not isinstance(raw, str) or not raw or not isinstance(expected, str):
        raise ReplayRefusal(f"{label} path and sha256 must be strings")
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ReplayRefusal(f"{label} sha256 must be lowercase hexadecimal")
    path = (root / raw).resolve()
    actual = binding(path)
    if actual["sha256"] != expected:
        raise ReplayRefusal(f"{label} hash mismatch: {path}")
    return path, actual


def rows_by_id(path: Path, id_column: str, required: list[str], *,
               expected_sha256: str | None = None) -> dict[str, dict]:
    """Read a TSV while rejecting duplicate identities and malformed rows."""
    result = {}
    raw, _ = read_snapshot(path, expected_sha256=expected_sha256)
    with io.StringIO(raw.decode("utf-8-sig"), newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ReplayRefusal(f"missing or duplicate TSV headers: {path}")
        if any(name not in reader.fieldnames for name in required):
            raise ReplayRefusal(f"required TSV columns missing: {path}: {required}")
        for number, row in enumerate(reader, 2):
            identity = row.get(id_column)
            if None in row or any(value is None for value in row.values()):
                raise ReplayRefusal(f"malformed TSV row {number}: {path}")
            if not identity or identity != identity.strip() or identity in result:
                raise ReplayRefusal(f"blank, padded or duplicate id at row {number}: {path}")
            result[identity] = row
    if not result:
        raise ReplayRefusal(f"empty table: {path}")
    return result


def prepare_replay(manifest: Path) -> dict:
    """Validate all inputs and selections before creating an output directory."""
    manifest = Path(manifest).resolve()
    manifest_raw, manifest_binding = read_snapshot(manifest)
    spec = json.loads(manifest_raw.decode("utf-8"))
    required = {"schema", "method", "generation", "coordinates", "metadata",
                "exclusions", "columns", "expected_points", "palette", "group_order"}
    if not isinstance(spec, dict) or set(spec) != required:
        raise ReplayRefusal(f"manifest requires exactly {sorted(required)}")
    if spec["schema"] != SCHEMA or spec["method"] not in METHODS:
        raise ReplayRefusal("unsupported schema or method; use trimap or tsne")
    if not isinstance(spec["generation"], str) or not spec["generation"].strip():
        raise ReplayRefusal("generation must identify the original run")
    expected = spec["expected_points"]
    if type(expected) is not int or expected < 1:
        raise ReplayRefusal("expected_points must be a positive integer")
    columns = spec["columns"]
    if not isinstance(columns, dict) or set(columns) != {"id", "x", "y", "group"}:
        raise ReplayRefusal("columns requires exactly id, x, y and group")
    if any(not isinstance(value, str) or not value for value in columns.values()):
        raise ReplayRefusal("column names must be nonempty strings")
    if len(set(columns.values())) != 4:
        raise ReplayRefusal("id, x, y and group column names must be distinct")
    paths, inputs = {}, {"manifest": manifest_binding}
    for name in ["coordinates", "metadata", "exclusions"]:
        paths[name], inputs[name] = checked_input(manifest.parent, spec[name], name)
    coordinates = rows_by_id(paths["coordinates"], columns["id"],
                             [columns[k] for k in ["id", "x", "y"]],
                             expected_sha256=inputs["coordinates"]["sha256"])
    metadata = rows_by_id(paths["metadata"], columns["id"],
                          [columns[k] for k in ["id", "group"]],
                          expected_sha256=inputs["metadata"]["sha256"])
    if set(coordinates) != set(metadata):
        raise ReplayRefusal("coordinate and metadata id rosters differ")
    exclusions_raw, _ = read_snapshot(paths["exclusions"], expected_sha256=inputs["exclusions"]["sha256"])
    excluded_list = exclusions_raw.decode("utf-8").splitlines()
    if any(not item or item != item.strip() for item in excluded_list):
        raise ReplayRefusal("exclusions must contain one exact id per line; use an empty file for none")
    excluded = set(excluded_list)
    if len(excluded) != len(excluded_list) or excluded - coordinates.keys():
        raise ReplayRefusal("exclusions contain duplicate or unknown ids")
    points = []
    for identity, row in coordinates.items():
        try:
            x, y = float(row[columns["x"]]), float(row[columns["y"]])
        except ValueError:
            raise ReplayRefusal(f"nonnumeric coordinates: {identity}") from None
        if not math.isfinite(x) or not math.isfinite(y):
            raise ReplayRefusal(f"nonfinite coordinates: {identity}")
        group = metadata[identity][columns["group"]]
        if not group or group != group.strip():
            raise ReplayRefusal(f"blank or padded display group: {identity}")
        points.append({"id": identity, "x": x, "y": y, "group": group,
                       "drawn": identity not in excluded,
                       "reason": "EXPLICIT_EXCLUSION" if identity in excluded else ""})
    drawn = [point for point in points if point["drawn"]]
    palette = spec["palette"]
    if not isinstance(palette, dict) or set(palette) != {point["group"] for point in points}:
        raise ReplayRefusal("palette must bind every metadata group exactly")
    order = spec["group_order"]
    if (not isinstance(order, list) or any(not isinstance(group, str) for group in order)
            or len(set(order)) != len(order) or set(order) != set(palette)):
        raise ReplayRefusal("group_order must list each metadata group once, background first")
    for colour in palette.values():
        if (not isinstance(colour, str) or len(colour) != 7 or colour[0] != "#"
                or any(c not in "0123456789abcdefABCDEF" for c in colour[1:])):
            raise ReplayRefusal("palette colours must be #RRGGBB values")
    if len(drawn) != expected:
        raise ReplayRefusal(f"drawn point count {len(drawn)} differs from expected_points {expected}")
    return {"spec": spec, "inputs": inputs, "points": points,
            "counts": {"input_rows": len(points), "drawn_rows": len(drawn),
                       "excluded_rows": len(excluded),
                       "drawn_by_group": dict(sorted(Counter(p["group"] for p in drawn).items()))},
            "membership_sha256": hashlib.sha256(
                json.dumps(sorted(p["id"] for p in drawn), separators=(",", ":")).encode()).hexdigest()}


def unchanged(inputs: dict) -> None:
    """Refuse a final receipt after input or producer drift."""
    for name, previous in inputs.items():
        try:
            current = binding(Path(previous["path"]))
        except OSError as error:
            raise ReplayRefusal(f"{name} disappeared during replay") from error
        if current != previous:
            raise ReplayRefusal(f"{name} changed during replay")


def draw_points(plan: dict, output: Path) -> list[Path]:
    """Draw saved values with plain embedding axes and explicit group counts."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mamey.figure_policy import assert_no_banned_figure_text
    from mamey.figure_theme import apply_theme

    method = METHODS[plan["spec"]["method"]]
    apply_theme(plt, profile="manuscript")
    drawn = [point for point in plan["points"] if point["drawn"]]
    groups = [group for group in plan["spec"]["group_order"] if any(p["group"] == group for p in drawn)]
    assert_no_banned_figure_text([method + " 1", method + " 2", *groups])
    figure, axis = plt.subplots(figsize=(7.2, 5.0))
    try:
        # Group values are displayed exactly; no cohort or biological role is inferred.
        for group in groups:
            selected = [point for point in drawn if point["group"] == group]
            axis.scatter([point["x"] for point in selected], [point["y"] for point in selected],
                         s=10, color=plan["spec"]["palette"][group], linewidths=0,
                         label=f"{group} ({len(selected):,} points)", rasterized=True)
        axis.set_xlabel(method + " 1")
        axis.set_ylabel(method + " 2")
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1))
        outputs = [output / ("embedding." + suffix) for suffix in ["pdf", "svg", "png"]]
        for path in outputs:
            figure.savefig(path, dpi=300, bbox_inches="tight")
        return outputs
    finally:
        plt.close(figure)


def run_replay(manifest: Path, output: Path, *, draw=None) -> dict:
    """Write a ledger and receipt for a validated saved-coordinate display."""
    from mamey.csv_safety import SafeDictWriter
    from mamey import csv_safety, figure_policy, figure_theme

    plan = prepare_replay(manifest)
    producers = {name: binding(Path(module.__file__)) for name, module in
                 [("helper", sys.modules[__name__]), ("csv_safety", csv_safety),
                  ("figure_policy", figure_policy), ("figure_theme", figure_theme)]}
    unchanged(plan["inputs"])
    output = Path(output)
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ReplayRefusal("output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = (draw or draw_points)(plan, output)
    with (output / "POINTS.tsv").open("w", newline="") as stream:
        writer = SafeDictWriter(stream, fieldnames=list(plan["points"][0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(plan["points"])
    artifacts = [*artifacts, output / "POINTS.tsv"]
    unchanged(plan["inputs"])
    unchanged(producers)
    receipt = {"schema": SCHEMA, "state": "SAVED_COORDINATE_REPLAY",
               "mode": "replot", "method": plan["spec"]["method"],
               "generation": plan["spec"]["generation"], "counts": plan["counts"],
               "group_order": plan["spec"]["group_order"], "palette": plan["spec"]["palette"],
               "membership_sha256": plan["membership_sha256"],
               "inputs": plan["inputs"], "producers": producers,
               "outputs": [binding(path) for path in artifacts],
               "environment": {"python": platform.python_version(), "platform": platform.platform(),
                               "matplotlib": getattr(sys.modules.get("matplotlib"), "__version__", None),
                               "numpy": getattr(sys.modules.get("numpy"), "__version__", None)},
               "renderer": "matplotlib" if draw is None else "supplied_callable",
               "scope": "Saved coordinate display only; point counts are rows, not represented proteins. No refit, identity threshold, biological interpretation or publication acceptance.",
               "holds": ["Historical fitting environment, parameters and stochastic stability are not validated by replotting.",
                         "Input hashes and explicit exclusions bind the selected display; scientific selection remains owner supplied."]}
    # Receipt is last: failed/different inputs leave artwork as unaccepted intermediates.
    (output / "REPLAY_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
