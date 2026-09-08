"""Provisional, source-bound Figure Factory repair tranche.

These static candidates consume only the hash-verified owner-kept projection.
They are engineering previews and are deliberately refused by the publication
bridge until an owner replaces ``PROVISIONAL_BINDING`` with a bound rule.
"""
from __future__ import annotations

import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from mamey.figure_save import save_figure


BINDING_STATE = "PROVISIONAL_BINDING"
IMPLEMENTED_IDS_7 = ("Q008_BW01", "Q013_F14", "Q015_G01", "Q019_SCI01C_F10R")
HELD_IDS_7 = ("Q017_SCI01A",)


class Tranche7Refusal(RuntimeError):
    """Typed failure for invalid or unready tranche-7 input."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _validate_inputs(root: Path) -> dict[str, Any]:
    receipt_path = root / "FIGURE_INPUT_RECEIPT.json"
    if not receipt_path.is_file():
        raise Tranche7Refusal("TRANCHE7_INPUT_RECEIPT_MISSING")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    bound = {row["path"]: row for row in receipt.get("outputs") or []}
    for name in (
        "a8_boundary_inventory.csv", "a8_architecture_features.csv",
        "a8_manifest_scan_counts.csv", "a8_resistance_routing.csv",
        "A8_PROVISIONAL_READINESS.tsv",
    ):
        path = root / name
        row = bound.get(name)
        if not path.is_file() or not row or row.get("sha256") != _sha(path):
            raise Tranche7Refusal(f"TRANCHE7_INPUT_BINDING_FAILED: {name}")
    readiness = {row["figure_id"]: row for row in _rows(root / "A8_PROVISIONAL_READINESS.tsv")}
    for figure_id in IMPLEMENTED_IDS_7:
        if (readiness.get(figure_id) or {}).get("status") != "PROVISIONAL_READY":
            holds = (readiness.get(figure_id) or {}).get("holds") or "READINESS_ROW_MISSING"
            raise Tranche7Refusal(f"TRANCHE7_NOT_READY: {figure_id}: {holds}")
    return receipt


def _layout_qa(fig: Any) -> dict[str, Any]:
    """Reusable final-size plot-bounds and adjacent-tick collision check."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    failures: list[str] = []
    for axis_index, axis in enumerate(fig.axes):
        labels = [label for label in (*axis.get_xticklabels(), *axis.get_yticklabels()) if label.get_visible() and label.get_text()]
        boxes = [label.get_window_extent(renderer) for label in labels]
        for box in boxes:
            # A small antialiasing tolerance is permitted; larger excursions
            # indicate text that will be clipped at the declared canvas size.
            if box.x0 < bounds.x0 - 4 or box.y0 < bounds.y0 - 4 or box.x1 > bounds.x1 + 4 or box.y1 > bounds.y1 + 4:
                failures.append(
                    f"AXIS_{axis_index}_LABEL_OUT_OF_BOUNDS"
                    f"[{box.x0:.1f},{box.y0:.1f},{box.x1:.1f},{box.y1:.1f}]"
                )
        xboxes = [label.get_window_extent(renderer) for label in axis.get_xticklabels() if label.get_visible() and label.get_text()]
        if any(left.overlaps(right) for left, right in zip(xboxes, xboxes[1:])):
            failures.append(f"AXIS_{axis_index}_X_TICK_COLLISION")
    return {"status": "PASS" if not failures else "FAIL", "failures": sorted(set(failures))}


def _finish(fig: Any) -> dict[str, Any]:
    fig.tight_layout(rect=(0.12, 0.18, 0.96, 0.92))
    qa = _layout_qa(fig)
    if qa["status"] != "PASS":
        raise Tranche7Refusal("TRANCHE7_LAYOUT_QA_FAILED: " + ";".join(qa["failures"]))
    return qa


def _q008(rows: list[dict[str, str]]):
    import matplotlib.pyplot as plt
    counts = Counter((row.get("boundary") or "MISSING") for row in rows)
    plotted = [{"boundary": key, "bgc_rows": value} for key, value in sorted(counts.items()) if value]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors = ("#0072B2", "#D55E00", "#009E73", "#6A51A3")
    left = 0
    for index, row in enumerate(plotted):
        ax.barh([0], [row["bgc_rows"]], left=left, label=row["boundary"], color=colors[index % len(colors)])
        left += row["bgc_rows"]
    ax.set_yticks([0], ["Governed cohort"])
    ax.set_xlabel("Admitted BGC rows")
    ax.set_ylabel("Boundary inventory", labelpad=16)
    ax.set_title("BGC boundary inventory — provisional governed-cohort binding")
    ax.legend(frameon=False, ncol=max(1, min(4, len(plotted))))
    return fig, plotted, _finish(fig)


def _feature_matrix(rows: list[dict[str, str]]):
    import numpy as np
    dimensions: list[tuple[str, str]] = []
    for field in ("arch", "arch_capacity", "class_conf"):
        dimensions.extend((field, value) for value in sorted({row.get(field) or "MISSING" for row in rows}))
    products = sorted({token.strip() for row in rows for token in (row.get("products") or "").split(";") if token.strip()})
    dimensions.extend(("product", token) for token in products)
    matrix = []
    for row in rows:
        product_set = {token.strip() for token in (row.get("products") or "").split(";") if token.strip()}
        matrix.append([1.0 if ((field == "product" and value in product_set) or (field != "product" and (row.get(field) or "MISSING") == value)) else 0.0 for field, value in dimensions])
    return np.asarray(matrix, dtype=float), dimensions


def _q013(rows: list[dict[str, str]]):
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import MaxNLocator
    matrix, dimensions = _feature_matrix(rows)
    if len(rows) < 2 or matrix.shape[1] < 2:
        raise Tranche7Refusal("TRANCHE7_F14_INSUFFICIENT_MATRIX")
    centered = matrix - matrix.mean(axis=0)
    u, singular, _ = np.linalg.svd(centered, full_matrices=False)
    coords = u[:, :2] * singular[:2]
    if coords.shape[1] == 1:
        coords = np.column_stack((coords[:, 0], np.zeros(len(rows))))
    clusters: list[Any] = []
    assignments = []
    for vector in matrix:
        assigned = None
        for index, centroid in enumerate(clusters):
            denom = float(np.linalg.norm(vector) * np.linalg.norm(centroid))
            cosine = float(vector @ centroid / denom) if denom else 0.0
            if cosine >= 0.85:
                assigned = index
                clusters[index] = (centroid + vector) / 2.0
                break
        if assigned is None:
            assigned = len(clusters)
            clusters.append(vector.copy())
        assignments.append(assigned)
    frequency = Counter(assignments)
    top = [key for key, _ in frequency.most_common(8)]
    labels = [f"Architecture {top.index(value)+1}" if value in top else "Other" for value in assignments]
    other_members = ";".join(
        row["complete_identity"] for row, label in zip(rows, labels) if label == "Other"
    )
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    for label in sorted(set(labels)):
        ids = [i for i, value in enumerate(labels) if value == label]
        ax.scatter(coords[ids, 0], coords[ids, 1], label=label, s=30, alpha=0.85)
    ax.set_xlabel("Principal component 1")
    ax.set_ylabel("Principal component 2", labelpad=12)
    ax.margins(x=0.18, y=0.18)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune="both"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, prune="both"))
    ax.set_title("BGC architecture ordination — provisional fixed feature vector")
    ax.legend(frameon=False, fontsize=7)
    total = float((singular ** 2).sum()) or 1.0
    variance = [float(value ** 2 / total) for value in singular[:2]]
    plotted = [{**row, "pc1": float(coords[i, 0]), "pc2": float(coords[i, 1]), "architecture_cluster": labels[i],
                "feature_dimensions": ";".join(f"{a}={b}" for a, b in dimensions),
                "other_cluster_members": other_members,
                "explained_variance_pc1": variance[0], "explained_variance_pc2": variance[1] if len(variance) > 1 else 0.0}
               for i, row in enumerate(rows)]
    return fig, plotted, _finish(fig)


def _q015(rows: list[dict[str, str]], boundary_rows: list[dict[str, str]]):
    import matplotlib.pyplot as plt
    rows = [row for row in rows if row.get("scan") == "cctt"]
    tokens = sorted({row["token"] for row in rows})
    strains = sorted({row["strain"] for row in rows})
    lookup = {(row["strain"], row["token"]): int(row.get("hit_count") or 0) for row in rows}
    denominator = Counter(row["strain"] for row in boundary_rows)
    shown = sorted(tokens, key=lambda token: (-sum(lookup.get((strain, token), 0) for strain in strains), token))[:12]
    plotted = [{"strain": strain, "trigger": token, "hit_count": lookup.get((strain, token), 0),
                "admitted_bgc_rows": denominator[strain],
                "source_field": "manifest.json.source_scans.cctt.hits", "rarity_rule": "UNBOUND"}
               for strain in strains for token in shown]
    fig, ax = plt.subplots(figsize=(8.0, max(3.6, 0.32 * len(strains) + 1.8)))
    image = [[lookup.get((strain, token), 0) for token in shown] for strain in strains]
    ax.imshow(image, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(range(len(shown)), shown, rotation=35, ha="right", fontsize=7)
    ax.set_yticks(range(len(strains)), strains, fontsize=7)
    ax.set_xlabel("Diagnostic trigger (rarity rule unbound)")
    ax.set_ylabel("Selected strain", labelpad=12)
    ax.set_title("Diagnostic-chemistry source-scan hits per strain — provisional")
    return fig, plotted, _finish(fig)


def _q019(scan_rows: list[dict[str, str]], resistance_rows: list[dict[str, str]]):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 7.2))
    plotted: list[dict[str, Any]] = []
    for axis, scan, title in zip(axes[:2], ("transporters", "regulators"), ("Transport source-scan hits", "Regulatory source-scan hits")):
        selected = [row for row in scan_rows if row.get("scan") == scan and int(row.get("hit_count") or 0) > 0]
        counts = Counter()
        for row in selected:
            counts[row["token"]] += int(row["hit_count"])
        shown = counts.most_common(10)
        axis.bar([key for key, _ in shown], [value for _, value in shown], color="#0072B2")
        axis.set_title(title, loc="left", fontsize=9)
        axis.tick_params(axis="x", rotation=30, labelsize=7)
        for token, count in shown:
            plotted.append({"panel": scan, "token": token, "count": count,
                            "source_field": f"manifest.json.source_scans.{scan}.hits"})
    resistance = Counter((row.get("resistance_tier") or "NULL") for row in resistance_rows)
    axes[2].bar(list(resistance), list(resistance.values()), color="#D55E00")
    axes[2].set_title("Resistance-routing tier (NULL retained)", loc="left", fontsize=9)
    axes[2].tick_params(axis="x", rotation=25, labelsize=7)
    for token, count in sorted(resistance.items()):
        plotted.append({"panel": "resistance_routing", "token": token, "count": count,
                        "source_field": "_4_triage_board.csv.Resistance_tier"})
    fig.suptitle("Bee/Wasp evidence profiles — provisional cohort binding")
    return fig, plotted, _finish(fig)


def render_tranche_7(owner_inputs: str | Path, outdir: str | Path) -> dict[str, Any]:
    root = Path(owner_inputs).resolve()
    destination = Path(outdir).resolve()
    if destination.exists():
        raise Tranche7Refusal("TRANCHE7_OUTPUT_EXISTS")
    _validate_inputs(root)
    destination.mkdir(parents=True)
    (destination / "figures").mkdir()
    (destination / "data").mkdir()
    boundary = _rows(root / "a8_boundary_inventory.csv")
    architecture = _rows(root / "a8_architecture_features.csv")
    scans = _rows(root / "a8_manifest_scan_counts.csv")
    resistance = _rows(root / "a8_resistance_routing.csv")
    recipes: tuple[tuple[str, Callable[[], tuple[Any, list[dict[str, Any]], dict[str, Any]]]], ...] = (
        ("Q008_BW01", lambda: _q008(boundary)),
        ("Q013_F14", lambda: _q013(architecture)),
        ("Q015_G01", lambda: _q015(scans, boundary)),
        ("Q019_SCI01C_F10R", lambda: _q019(scans, resistance)),
    )
    records = []
    for figure_id, recipe in recipes:
        fig, plotted, qa = recipe()
        data_path = destination / "data" / f"{figure_id}.csv"
        _write_csv(data_path, plotted)
        save_receipt = save_figure(
            fig, figure_id=figure_id, out_stem=destination / "figures" / figure_id,
            renderer="mamey.interactive_figures.figure_set_renderer_tranche7",
            package_dir=destination,
            provenance="PROVISIONAL_BINDING; hash-verified owner-kept Figure Factory inputs",
            binding_state=BINDING_STATE,
        )
        import matplotlib.pyplot as plt
        plt.close(fig)
        records.append({"figure_id": figure_id, "binding_state": BINDING_STATE, "layout_qa": qa,
                        "data": {"logical_locator": data_path.relative_to(destination).as_posix(),
                                 "sha256": _sha(data_path), "bytes": data_path.stat().st_size},
                        "figure_receipt": save_receipt})
    result = {"schema_version": "sapote-mamey.figure-tranche7.v1", "status": "CANDIDATE_ONLY",
              "binding_state": BINDING_STATE, "implemented_ids": list(IMPLEMENTED_IDS_7),
              "held_ids": list(HELD_IDS_7), "figures": records}
    receipt = destination / "TRANCHE7_RECEIPT.json"
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
