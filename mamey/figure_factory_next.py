"""Portable, manifest-governed aggregate evidence figures."""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import shutil
import tempfile
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .figure_policy import (
    CAPTION_METHOD_SCHEMA, COHORT_PALETTE, PUBLICATION_PROFILES,
    apply_genus_preset, validate_caption_methods, validate_cohort_manifest,
    validate_cohort_palette, validate_genus_comparison,
    validate_layout_rectangles, validate_publication_artwork,
    validate_tick_label_data_clearance,
)
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

SCHEMA_VERSION = "sapote.figure-factory-next.v2"
LEGACY_SCHEMA_VERSION = "sapote.figure-factory-next.v1"
METRIC_FIELDS = ("identity", "channel", "metric", "numerator", "denominator", "denominator_key")
COHORT_FIELDS = (
    "identity", "role", "include_by_default", "genus", "cohort",
    "assembly_state", "assembly_reason",
)
CLAIM_CEILING = (
    "Evidence coverage and workflow readiness only; similarity is not identity, "
    "capacity is not production, and missingness is not biological absence."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute():
        raise ValueError("Input locators must be relative to external_data_root")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Input locator escapes external_data_root") from exc
    if not path.is_file():
        raise FileNotFoundError(f"Required input is missing: {locator}")
    return path


def _read_tsv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or any(field not in reader.fieldnames for field in fields):
            raise ValueError("TSV is missing a required field")
        return list(reader)


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    # v9.7.410 (CLAUDE_410 ff csv sidecar): same tidy schema as _write_tsv, comma-delimited, so the
    # R/ggplot2 figure templates (which read `_data.csv`) consume the plotted-data sidecar uniformly
    # with the rest of the figure set. Deterministic newline; additive alongside the .tsv.
    #
    # Uses SafeDictWriter (shipped in .409 as mamey/csv_safety.py), NOT a plain csv.DictWriter: this
    # sidecar is a deliverable opened directly in Excel/LibreOffice and read by the R templates, so
    # it is exactly the formula-injection surface csv_safety exists to close. The same binding is
    # what CLAUDE_410_csv_writer_coverage's coverage-lock test requires outside its allowlist.
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter=",", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@dataclass(frozen=True)
class Metric:
    identity: str
    channel: str
    metric: str
    numerator: int
    denominator: int
    denominator_key: str


def _metrics(rows: list[dict[str, str]]) -> list[Metric]:
    result: list[Metric] = []
    keys: set[tuple[str, str, str, str]] = set()
    for row in rows:
        values = [row[field].strip() for field in ("identity", "channel", "metric", "denominator_key")]
        if not all(values):
            raise ValueError("Identity, channel, metric, and denominator_key must be nonblank")
        try:
            numerator, denominator = int(row["numerator"]), int(row["denominator"])
        except ValueError as exc:
            raise ValueError("Numerator and denominator must be integers") from exc
        if numerator < 0 or denominator <= 0 or numerator > denominator:
            raise ValueError("Metrics require 0 <= numerator <= denominator and denominator > 0")
        key = tuple(values)
        if key in keys:
            raise ValueError("Duplicate identity/channel/metric/denominator_key row")
        keys.add(key)
        result.append(Metric(*values[:3], numerator, denominator, values[3]))
    return result


def _bindings(config: Mapping[str, Any], root: Path) -> dict[str, dict[str, Any]]:
    inputs = list(config.get("inputs", []))
    by_role = {str(row.get("role", "")): dict(row) for row in inputs}
    if len(inputs) != 2 or set(by_role) != {"aggregate_metrics", "cohort_manifest"}:
        raise ValueError("Exactly one aggregate_metrics and one cohort_manifest input are required")
    for role, row in by_role.items():
        expected = str(row.get("sha256", "")).lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise ValueError(f"{role} requires an exact lowercase SHA-256 receipt")
        path = _safe_file(root, str(row.get("logical_locator", "")))
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"{role} SHA-256 mismatch")
        row.update(path=path, actual_hash=actual, bytes=path.stat().st_size)
    return by_role


def _aggregate(metrics: list[Metric], policy_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str]]:
    by_identity = {row["identity"]: row for row in policy_rows}
    metric_ids, policy_ids = {row.identity for row in metrics}, set(by_identity)
    if metric_ids != policy_ids:
        raise ValueError(
            f"Metrics/cohort identity mismatch: missing_manifest={sorted(metric_ids-policy_ids)}; "
            f"missing_metrics={sorted(policy_ids-metric_ids)}"
        )
    default_ids = {row["identity"] for row in policy_rows if row["study_denominator_member"]}
    selected_ids = {row["identity"] for row in policy_rows if row["selected_optional"]}
    if not default_ids:
        raise ValueError("No default-on STUDY identities remain")
    included = default_ids | selected_ids
    buckets: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    members: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for row in metrics:
        if row.identity not in included:
            continue
        policy = by_identity[row.identity]
        sensitivity = row.identity not in default_ids
        key = (
            "SENSITIVITY" if sensitivity else "STUDY",
            row.identity if sensitivity else "",
            policy["cohort"], policy["genus"], row.channel, row.metric, row.denominator_key,
        )
        bucket = buckets[key]
        bucket[0] += row.numerator
        bucket[1] += row.denominator
        bucket[2] += int(policy["assembly_state"] == "FLAG")
        bucket[3] += int(policy["assembly_state"] == "DEFAULT_OFF")
        bucket[4] += 1
        members[key].add(row.identity)
    output = []
    for key, values in sorted(buckets.items()):
        kind, identity, cohort, genus, channel, metric, denominator_key = key
        output.append({
            "group_kind": kind, "sensitivity_identity": identity, "cohort": cohort,
            "genus": genus, "channel": channel, "metric": metric,
            "denominator_key": denominator_key, "identity_count": len(members[key]),
            "numerator": values[0], "denominator": values[1],
            "percent": round(100 * values[0] / values[1], 6),
            "assembly_flagged_metric_rows": values[2],
            "assembly_default_off_metric_rows": values[3], "source_metric_rows": values[4],
        })
    if not output:
        raise ValueError("No eligible rows remain after cohort policy")
    return output, policy_ids - included


def _boxes(texts: list[Any], renderer: Any, group: str) -> list[dict[str, Any]]:
    output = []
    for index, item in enumerate(texts):
        if item.get_visible() and item.get_text().strip():
            box = item.get_window_extent(renderer=renderer)
            output.append({
                "id": f"{group}-{index}", "group": group,
                "x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1,
            })
    return output


def _render(rows: list[dict[str, Any]], output: Path, title: str, profile: str) -> tuple[list[Path], dict[str, Any]]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["svg.hashsalt"] = "sapote-figure-factory-next-v2"
        matplotlib.rcParams["svg.fonttype"] = "none"
        matplotlib.rcParams["pdf.fonttype"] = 42
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Figure Factory Next requires the figures extra") from exc
    width = PUBLICATION_PROFILES[profile]["width_in"]
    height = max(3.4, 0.62 * len(rows) + 1.8)
    wrap = 34 if profile == "SINGLE_COLUMN" else 68
    labels = [textwrap.fill(
        ("sensitivity | " if row["group_kind"] == "SENSITIVITY" else "")
        + f"{row['cohort']} | {row['genus']} | {row['channel']} | {row['metric']}",
        width=wrap, break_long_words=False,
    ) for row in rows]
    colors = [COHORT_PALETTE[row["cohort"]] for row in rows]
    fig, axis = plt.subplots(figsize=(width, height), layout="constrained")
    positions = list(range(len(rows)))
    axis.barh(positions, [row["percent"] for row in rows], color=colors,
              edgecolor="#1A1A1A", linewidth=0.5)
    axis.set_yticks(positions, labels=labels, fontsize=8)
    axis.tick_params(axis="x", labelsize=8)
    axis.invert_yaxis(); axis.set_xlim(0, 115); axis.set_xticks([0, 20, 40, 60, 80, 100])
    axis.set_xlabel("Observed / declared denominator (%)", fontsize=8)
    axis.set_title(title, fontsize=9); axis.grid(axis="x", color="#D9E1E8", linewidth=0.8)
    annotations = []
    for position, row in zip(positions, rows):
        annotations.append(axis.text(min(row["percent"] + 1, 103), position,
                                     f"{row['numerator']}/{row['denominator']}",
                                     va="center", fontsize=8))
        marker = "D" if row["assembly_flagged_metric_rows"] else (
            "x" if row["assembly_default_off_metric_rows"] else None)
        if marker == "D":
            axis.scatter([min(row["percent"] + 9, 111)], [position], marker=marker,
                         s=26, facecolors="none",
                         edgecolors="#D55E00", linewidths=1.1, zorder=4)
        elif marker == "x":
            axis.scatter([min(row["percent"] + 9, 111)], [position], marker=marker,
                         s=26, color="#D55E00", linewidths=1.1, zorder=4)
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    boxes = _boxes(list(axis.get_yticklabels()), renderer, "yticks") + _boxes(annotations, renderer, "annotations")
    layout = validate_layout_rectangles(
        boxes, canvas_width_px=fig.bbox.width, canvas_height_px=fig.bbox.height,
        minimum_gap_px=0.5,
    )
    tick_boxes = _boxes(
        list(axis.get_xticklabels()) + list(axis.get_yticklabels()),
        renderer,
        "tick-labels",
    )
    for tick_box in tick_boxes:
        tick_box["axis_id"] = "main"
    axes_box = axis.get_window_extent(renderer=renderer)
    layout["tick_label_data_clearance"] = validate_tick_label_data_clearance(
        tick_boxes,
        [{
            "id": "main-data", "axis_id": "main",
            "x0": axes_box.x0, "y0": axes_box.y0,
            "x1": axes_box.x1, "y1": axes_box.y1,
        }],
        canvas_width_px=fig.bbox.width,
        canvas_height_px=fig.bbox.height,
    )
    stem = f"figure_factory_next_{profile.casefold()}"
    svg, png = output / f"{stem}.svg", output / f"{stem}.png"
    fig.savefig(svg, metadata={"Date": None, "Creator": "Sapote-Mamey Figure Factory Next"})
    fig.savefig(png, dpi=_safe_dpi(fig, 300), metadata={"Software": "Sapote-Mamey Figure Factory Next"})
    plt.close(fig)
    artwork = {
        "svg": validate_publication_artwork(svg, profile=profile),
        "png": validate_publication_artwork(png, profile=profile),
    }
    return [svg, png], {"profile": profile, "layout": layout, "artwork": artwork}


def _caption(config: Mapping[str, Any], bindings: Mapping[str, Mapping[str, Any]],
             rows: list[dict[str, Any]], cohort: Mapping[str, Any], genus: Mapping[str, Any],
             role_by_identity: Mapping[str, str]) -> dict[str, Any]:
    groups = "; ".join(
        f"{row['cohort']}/{row['genus']}/{row['channel']}/{row['metric']}"
        f"(rows={row['identity_count']}; denominator={row['denominator']})" for row in rows
    )
    benchmark_count = int(cohort["role_counts"].get("EXTERNAL_BENCHMARK", 0))
    reference_count = int(cohort["role_counts"].get("REFERENCE", 0))
    # v9.7.409: attribute every SENSITIVITY row to its authoritative manifest role
    # (from the cohort manifest), not to the visual cohort field. The prior field
    # keyed on row["cohort"] == "EXTERNAL_BENCHMARK", so REFERENCE-role sensitivity
    # rows contributed sensitivity data that the caption silently dropped. Count
    # sensitivity rows per role deterministically and report both benchmark and
    # REFERENCE contributions, matching how group_denominators reports every row.
    sensitivity_role_counts: dict[str, int] = {}
    for row in rows:
        if row["group_kind"] != "SENSITIVITY":
            continue
        role = role_by_identity.get(row["sensitivity_identity"], "UNKNOWN")
        sensitivity_role_counts[role] = sensitivity_role_counts.get(role, 0) + 1
    selected_benchmarks = sensitivity_role_counts.get("EXTERNAL_BENCHMARK", 0)
    selected_references = sensitivity_role_counts.get("REFERENCE", 0)
    sensitivity_rows_by_role = ",".join(
        f"{role}={count}" for role, count in sorted(sensitivity_role_counts.items())
    ) or "none"
    metadata = {
        "caption_schema_version": CAPTION_METHOD_SCHEMA,
        "figure_question": str(config.get("figure_question", "")).strip(),
        "source": "content-addressed aggregate metrics plus authoritative cohort-role manifest",
        "source_bindings": "; ".join(
            f"{role}:{item['logical_locator']}; sha256={item['actual_hash']}; bytes={item['bytes']}"
            for role, item in sorted(bindings.items())),
        "source_release": str(config.get("source_release", "")).strip(),
        "software_versions": str(config.get("software_versions", "")).strip(),
        "unit_of_analysis": "one within-genus cohort/channel/metric aggregate or one optional sensitivity identity",
        "inclusion_exclusion_roles": f"default study identities={cohort['default_study_count']}; default-off identities={cohort['default_off_count']}; selected sensitivity identities={cohort['selected_optional_count']}",
        "denominator": f"{cohort['default_study_count']} default-on study identities; optional sensitivity rows excluded from study n",
        "group_denominators": groups,
        "typed_missingness": f"plotted_rows={len(rows)}; no_typed_state_column_in_plotted_rows; assembly state is supplied by the cohort manifest",
        "benchmark_sensitivity": f"benchmark_available={benchmark_count}; benchmark_selected={selected_benchmarks}; reference_available={reference_count}; reference_selected={selected_references}; sensitivity_rows_by_role={sensitivity_rows_by_role}; default_off=true; benchmark and REFERENCE sensitivity rows remain excluded from study n and percentages",
        "transformation": "sum numerators and denominators within cohort/genus/channel/metric groups, then compute 100*numerator/denominator",
        "visual_grammar": "Horizontal solid-color bars encode percentages; exact ratios are text; open diamonds mark included assembly flags and x marks selected default-off assembly sensitivity rows.",
        "statistics_uncertainty": "No inferential statistic or uncertainty interval is computed.",
        "comparison_group": "within-genus study groups; optional identities shown only as sensitivity rows",
        "genus_control": f"WITHIN_GENUS; included genera={','.join(genus['default_genera'] + genus['selected_optional'])}",
        "contradictions": f"assembly_flagged={cohort['assembly_flag_count']}; assembly_default_off={cohort['assembly_default_off_count']}",
        "interpretation_boundary": CLAIM_CEILING,
    }
    validate_caption_methods(metadata, nonstandard_visual=True)
    return metadata


def build(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") == LEGACY_SCHEMA_VERSION:
        raise ValueError(f"{LEGACY_SCHEMA_VERSION} is refused: migrate to {SCHEMA_VERSION}")
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    root = Path(config["external_data_root"]).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError("external_data_root is not a directory")
    bindings = _bindings(config, root)
    metrics = _metrics(_read_tsv(bindings["aggregate_metrics"]["path"], METRIC_FIELDS))
    comparison = dict(config.get("comparison", {}))
    policy_rows, cohort_receipt = validate_cohort_manifest(
        _read_tsv(bindings["cohort_manifest"]["path"], COHORT_FIELDS),
        selected_optional_identities=comparison.get("selected_optional_identities", []),
    )
    if not comparison.get("default_genera"):
        raise ValueError("comparison.default_genera is required")
    defaults = [row for row in policy_rows if row["study_denominator_member"]]
    kept, genus_receipt = apply_genus_preset(
        defaults, genus_field="genus", default_genera=comparison["default_genera"],
        optional_genera=comparison.get("optional_genera", []),
        selected_optional=comparison.get("selected_optional_genera", []),
    )
    kept_ids = {row["identity"] for row in kept}
    manifest_default_study_count = cohort_receipt["default_study_count"]
    for row in policy_rows:
        if row["study_denominator_member"] and row["identity"] not in kept_ids:
            row["study_denominator_member"] = False
    cohort_receipt["manifest_default_study_count"] = manifest_default_study_count
    cohort_receipt["default_study_count"] = sum(
        row["study_denominator_member"] for row in policy_rows
    )
    cohort_receipt["genus_excluded_default_study_count"] = (
        manifest_default_study_count - cohort_receipt["default_study_count"]
    )
    validate_genus_comparison("WITHIN_GENUS"); validate_cohort_palette(COHORT_PALETTE)
    rows, excluded = _aggregate(metrics, policy_rows)
    role_by_identity = {row["identity"]: row["role"] for row in policy_rows}
    caption = _caption(config, bindings, rows, cohort_receipt, genus_receipt, role_by_identity)

    output = Path(config["output_dir"])
    if not output.is_absolute():
        output = (config_path.parent / output).resolve()
    if output.exists():
        raise FileExistsError(f"Output directory already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".figure_factory_next.", dir=output.parent))
    try:
        graphics, profiles = [], []
        for profile in ("SINGLE_COLUMN", "DOUBLE_COLUMN"):
            created, receipt = _render(rows, stage, str(config.get("title", "Evidence readiness")), profile)
            graphics.extend(created); profiles.append(receipt)
        fields = list(rows[0])
        data = stage / "figure_factory_next_data.tsv"; _write_tsv(data, fields, rows)
        # v9.7.410 (CLAUDE_410 ff csv sidecar): emit a comma-delimited twin of the plotted-data
        # sidecar for the R/ggplot2 templates. Additive — the .tsv and its receipt hash are unchanged.
        data_csv = stage / "figure_factory_next_data.csv"; _write_csv(data_csv, fields, rows)
        by_identity = {row["identity"]: row for row in policy_rows}
        exclusions = [{
            "excluded_identity": identity, "role": by_identity[identity]["role"],
            "genus": by_identity[identity]["genus"], "cohort": by_identity[identity]["cohort"],
            "assembly_state": by_identity[identity]["assembly_state"],
            "assembly_reason": by_identity[identity]["assembly_reason"],
            "consumer_effect": "EXCLUDED_FROM_RENDER_AND_STUDY_DENOMINATOR",
        } for identity in sorted(excluded)]
        exclusion_path = stage / "figure_factory_next_exclusions.tsv"
        _write_tsv(exclusion_path, list(exclusions[0]) if exclusions else [
            "excluded_identity", "role", "genus", "cohort", "assembly_state", "assembly_reason", "consumer_effect"
        ], exclusions)
        caption_json = stage / "figure_factory_next_caption_methods.json"
        caption_json.write_text(json.dumps(caption, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        caption_md = stage / "figure_factory_next_caption_methods.md"
        caption_md.write_text("# Figure Factory Next caption and methods\n\n" + "\n\n".join(
            f"## {key.replace('_', ' ').title()}\n\n{value}" for key, value in caption.items()) + "\n", encoding="utf-8")
        owner_notes = stage / "figure_factory_next_owner_notes.json"
        owner_notes.write_text(json.dumps({
            "owner_notes": config.get("owner_notes", []),
            "scientific_caption_inclusion": False, "plotted_canvas_inclusion": False,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for path in graphics + [data, data_csv, caption_json, caption_md]:
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(identity in text for identity in excluded):
                raise ValueError("FAIL_CLOSED_EXCLUDED_IDENTITY_RENDER_LEAK")
        artifacts = graphics + [data, data_csv, exclusion_path, caption_json, caption_md, owner_notes]
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS_PORTABLE_POLICY_RENDERER_CANDIDATE",
            "inputs": [{"role": role, "logical_locator": item["logical_locator"],
                        "sha256": item["actual_hash"], "bytes": item["bytes"]}
                       for role, item in sorted(bindings.items())],
            "cohort_policy": cohort_receipt, "genus_policy": genus_receipt,
            "palette": validate_cohort_palette(COHORT_PALETTE), "profiles": profiles,
            "denominators": rows, "owner_notes_separate_from_scientific_caption": True,
            "pdf_embedding_qa": "REQUIRED_DOWNSTREAM_NOT_ESTABLISHED_BY_STANDALONE_ARTWORK",
            "outputs": [{"logical_locator": path.name, "sha256": sha256_file(path),
                         "bytes": path.stat().st_size} for path in artifacts],
            "claim_ceiling": CLAIM_CEILING,
            "authority_state": "ENGINEERING_CANDIDATE_ONLY_NOT_ACCEPTED_NOT_INTEGRATED_NOT_RELEASED",
        }
        (stage / "figure_factory_next_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.replace(output)
        return receipt
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
