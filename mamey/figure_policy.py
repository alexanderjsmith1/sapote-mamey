"""figure_policy.py — canonical figure-content policy for Sapote-Mamey.

POLICY (v9.7.27): **pure-saccharide BGCs are omitted from ALL figures.** Saccharide is the largest, least
discriminating class (sugar-biosynthesis / tailoring machinery) and a known misanchor source; including it
in plots distorts every per-strain / cross-strain count and class breakdown. An individually interesting
saccharide BGC may still be discussed in TEXT (Mode B / synopsis) — it just never appears in a figure.

"Pure saccharide" = a region whose only specialist signal is saccharide (i.e. `saccharide` present AND no
specialist class). A BGC that carries a specialist class plus a saccharide tailoring arm (e.g. `NRPS;
saccharide`) is NOT pure-saccharide — it is plotted under its specialist class.

All figure tools should import `is_pure_saccharide` / `omit_saccharides` from here rather than re-deriving
the specialist set, so the omission is identical everywhere.
"""
from __future__ import annotations

import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree

# # Specialist (figure-worthy) product classes used to distinguish "pure saccharide" (omit) from
# "saccharide + real class" (keep, plotted under the real class). This set is NOT the same as the
# lead-board CONFIRM set: ectoine, redox-cofactor, siderophore etc. appear here so a BGC carrying
# "NRPS;ectoine" is plotted under NRPS rather than dropped. They are still DOWN-RANKED or excluded
# on the lead board by the DAPR/standing-rule layer. Do not interpret presence here as lead-worthy.
SPECIALIST_CLASSES = frozenset({
    "t1pks", "t2pks", "t3pks", "transat-pks", "hr-t2pks", "pks", "pks-like",
    "nrps", "nrps-like", "ripp", "ripp-like", "lanthipeptide", "lassopeptide", "thiopeptide",
    "lap", "sactipeptide", "linaridin", "lipolanthine", "thioamitide",
    "nrp-metallophore", "siderophore", "ni-siderophore", "betalactone", "ectoine", "butyrolactone", "indole",
    "phosphonate", "nucleoside", "enediyne", "redox-cofactor", "cdps", "crocagin", "amglyccycl",
    "terpene", "aminocoumarin", "oligosaccharide-lipid",
})

FIGURE_OMIT_SACCHARIDE = True  # the policy switch; figures never plot pure-saccharide regions

FIGURE_PREFLIGHT_SCHEMA = "sapote-mamey.figure-preflight.v1"
CAPTION_METHOD_SCHEMA = "sapote-mamey.figure-caption-methods.v2"
ALL_ZERO_SEMANTICS = {
    "OBSERVED_ZERO_NOT_MISSING": (
        "Every plotted zero is an explicitly observed zero state; missing or "
        "unmeasured values use a separate typed state."
    ),
    "NONE_ABOVE_DECLARED_CEILING": (
        "Zero means that no included observation exceeded the explicitly declared "
        "display ceiling; missing or unmeasured values are not encoded as zero."
    ),
}
CAPTION_METHOD_FIELDS = (
    "caption_schema_version",
    "figure_question",
    "source",
    "source_bindings",
    "source_release",
    "software_versions",
    "unit_of_analysis",
    "inclusion_exclusion_roles",
    "denominator",
    "group_denominators",
    "typed_missingness",
    "benchmark_sensitivity",
    "transformation",
    "visual_grammar",
    "statistics_uncertainty",
    "comparison_group",
    "genus_control",
    "contradictions",
    "interpretation_boundary",
)
CAPTION_PLACEHOLDERS = frozenset({
    "-", "--", "...", "n/a", "na", "none", "null", "placeholder", "tbd", "todo",
    "unknown", "x", "xx", "xxx",
})
GENUS_COMPARISON_SCOPES = frozenset({"WITHIN_GENUS", "CROSS_GENUS", "NOT_APPLICABLE"})
CROSS_GENUS_CONTROLS = frozenset({"STRATIFIED", "MATCHED", "MODELLED", "COMPOSITION_SHOWN"})

COHORT_MANIFEST_SCHEMA = "sapote-mamey.figure-cohort-manifest.v1"
COHORT_ROLES = frozenset({"STUDY", "REFERENCE", "EXTERNAL_BENCHMARK", "OUTGROUP"})
ASSEMBLY_STATES = frozenset({"PASS", "FLAG", "DEFAULT_OFF", "UNRESOLVED"})
PUBLICATION_PROFILES = {
    "SINGLE_COLUMN": {"width_in": 3.5, "minimum_text_pt": 8.0, "minimum_raster_dpi": 300.0},
    "DOUBLE_COLUMN": {"width_in": 7.2, "minimum_text_pt": 8.0, "minimum_raster_dpi": 300.0},
}
COHORT_PALETTE = {
    "BEE": "#0072B2",
    "WASP": "#56B4E9",
    "ATTINE": "#8C510A",
    "MOSS": "#009E73",
    "REFERENCE": "#666666",
    "EXTERNAL_BENCHMARK": "#CC79A7",
    "UNRESOLVED": "#1A1A1A",
}
SEPARATE_HEATMAP_CATEGORIES = frozenset({"OTHER"})


class FigurePolicyError(ValueError):
    """Typed fail-before-write refusal from the shared figure-policy owner."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _manifest_bool(value: Any, *, field: str, row_number: int) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise FigurePolicyError(
        "FIGURE_COHORT_BOOLEAN_INVALID",
        f"row {row_number} field {field!r} must be true or false",
    )


def validate_cohort_manifest(
    rows: Sequence[Mapping[str, Any]],
    *,
    selected_optional_identities: Sequence[str] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate authoritative identity roles without inferring them from names.

    Assembly-sensitive study entries may be retained with ``FLAG`` or held with
    ``DEFAULT_OFF``.  A selected default-off entry is returned as a sensitivity
    row but never becomes a study-denominator member.
    """
    required = (
        "identity", "role", "include_by_default", "genus", "cohort",
        "assembly_state", "assembly_reason",
    )
    if not rows:
        raise FigurePolicyError("FIGURE_COHORT_MANIFEST_EMPTY", "no cohort rows were supplied")
    selected = {str(value).strip() for value in selected_optional_identities if str(value).strip()}
    normalized_rows: list[dict[str, Any]] = []
    identities: set[str] = set()
    for row_number, row in enumerate(rows, 1):
        missing = [field for field in required if not str(row.get(field, "")).strip()]
        if missing:
            raise FigurePolicyError(
                "FIGURE_COHORT_MANIFEST_INCOMPLETE",
                f"row {row_number} is missing: {', '.join(missing)}",
            )
        identity = str(row["identity"]).strip()
        if identity in identities:
            raise FigurePolicyError("FIGURE_COHORT_IDENTITY_DUPLICATE", identity)
        identities.add(identity)
        role = str(row["role"]).strip().upper()
        assembly_state = str(row["assembly_state"]).strip().upper()
        if role not in COHORT_ROLES:
            raise FigurePolicyError("FIGURE_COHORT_ROLE_INVALID", f"row {row_number}: {role}")
        if assembly_state not in ASSEMBLY_STATES:
            raise FigurePolicyError(
                "FIGURE_ASSEMBLY_STATE_INVALID", f"row {row_number}: {assembly_state}"
            )
        cohort = str(row["cohort"]).strip().upper()
        if cohort not in COHORT_PALETTE:
            raise FigurePolicyError(
                "FIGURE_COHORT_PALETTE_ROLE_INVALID",
                f"row {row_number}: {cohort}; expected one of {sorted(COHORT_PALETTE)}",
            )
        include_by_default = _manifest_bool(
            row["include_by_default"], field="include_by_default", row_number=row_number
        )
        if role in {"EXTERNAL_BENCHMARK", "OUTGROUP"} and include_by_default:
            raise FigurePolicyError(
                "FIGURE_EXTERNAL_ROLE_DEFAULT_ON",
                f"row {row_number} role {role} must be default-off",
            )
        if assembly_state == "DEFAULT_OFF" and include_by_default:
            raise FigurePolicyError(
                "FIGURE_ASSEMBLY_HOLD_DEFAULT_ON",
                f"row {row_number} assembly-sensitive hold must be default-off",
            )
        normalized_rows.append({
            "identity": identity,
            "role": role,
            "include_by_default": include_by_default,
            "genus": str(row["genus"]).strip(),
            "cohort": cohort,
            "assembly_state": assembly_state,
            "assembly_reason": str(row["assembly_reason"]).strip(),
            "selected_optional": identity in selected,
            "study_denominator_member": role == "STUDY" and include_by_default,
        })
    undeclared = sorted(selected - identities)
    if undeclared:
        raise FigurePolicyError(
            "FIGURE_OPTIONAL_IDENTITY_UNDECLARED", ", ".join(undeclared)
        )
    return normalized_rows, {
        "schema_version": COHORT_MANIFEST_SCHEMA,
        "status": "PASS",
        "identity_count": len(normalized_rows),
        "default_study_count": sum(row["study_denominator_member"] for row in normalized_rows),
        "default_off_count": sum(not row["include_by_default"] for row in normalized_rows),
        "assembly_flag_count": sum(row["assembly_state"] == "FLAG" for row in normalized_rows),
        "assembly_default_off_count": sum(
            row["assembly_state"] == "DEFAULT_OFF" for row in normalized_rows
        ),
        "selected_optional_count": sum(row["selected_optional"] for row in normalized_rows),
        "role_counts": dict(sorted(Counter(row["role"] for row in normalized_rows).items())),
    }


def _hex_rgb(value: str) -> tuple[int, int, int]:
    text = str(value).strip()
    if len(text) != 7 or not text.startswith("#"):
        raise FigurePolicyError("FIGURE_PALETTE_COLOR_INVALID", text)
    try:
        return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise FigurePolicyError("FIGURE_PALETTE_COLOR_INVALID", text) from exc


def validate_cohort_palette(
    palette: Mapping[str, str] | None = None,
    *,
    hatches: Mapping[str, str] | None = None,
    owner_pattern_override: bool = False,
) -> dict[str, Any]:
    """Require distinct cohort colors and solid fills unless owner-overridden."""
    chosen = {str(key).upper(): value for key, value in (palette or COHORT_PALETTE).items()}
    missing = sorted(set(COHORT_PALETTE) - set(chosen))
    if missing:
        raise FigurePolicyError("FIGURE_PALETTE_ROLE_MISSING", ", ".join(missing))
    rgb = {key: _hex_rgb(value) for key, value in chosen.items()}
    if len(set(rgb.values())) != len(rgb):
        raise FigurePolicyError("FIGURE_PALETTE_COLOR_DUPLICATE", "cohort colors must be unique")
    bee = rgb["BEE"]
    wasp = rgb["WASP"]
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(bee, wasp)))
    if distance < 60:
        raise FigurePolicyError(
            "FIGURE_BEE_WASP_COLORS_TOO_SIMILAR", f"RGB distance={distance:.1f}"
        )
    nonempty_hatches = {
        str(key).upper(): str(value) for key, value in (hatches or {}).items() if str(value)
    }
    if nonempty_hatches and not owner_pattern_override:
        raise FigurePolicyError(
            "FIGURE_PATTERN_NOT_OWNER_AUTHORIZED",
            "solid fills are required by default",
        )
    return {
        "status": "PASS",
        "palette": dict(sorted(chosen.items())),
        "fill_mode": "OWNER_PATTERN_OVERRIDE" if nonempty_hatches else "SOLID",
        "bee_wasp_rgb_distance": round(distance, 3),
    }


def _publication_profile(profile: str) -> tuple[str, dict[str, float]]:
    key = str(profile or "").strip().upper().replace("-", "_")
    if key not in PUBLICATION_PROFILES:
        raise FigurePolicyError(
            "FIGURE_PUBLICATION_PROFILE_INVALID",
            f"profile must be one of {sorted(PUBLICATION_PROFILES)}",
        )
    return key, PUBLICATION_PROFILES[key]


def validate_publication_profile(
    profile: str,
    *,
    plot_minimum_text_pt: float,
    caption_text_pt: float,
) -> dict[str, Any]:
    """Validate legibility and plot-to-caption scale at a physical width."""
    key, contract = _publication_profile(profile)
    plot_text = _finite_number(plot_minimum_text_pt, "plot_minimum_text_pt", 1)
    caption_text = _finite_number(caption_text_pt, "caption_text_pt", 1)
    if plot_text < contract["minimum_text_pt"]:
        raise FigurePolicyError(
            "FIGURE_TEXT_TOO_SMALL_AT_PHYSICAL_SIZE",
            f"{key} requires at least {contract['minimum_text_pt']:.1f} pt; observed {plot_text:.1f} pt",
        )
    ratio = caption_text / plot_text
    if ratio > 1.25:
        raise FigurePolicyError(
            "FIGURE_CAPTION_SCALE_DOMINATES_PLOT",
            f"caption/plot text ratio {ratio:.3f} exceeds 1.25",
        )
    return {
        "status": "PASS",
        "profile": key,
        "width_in": contract["width_in"],
        "minimum_text_pt": contract["minimum_text_pt"],
        "plot_minimum_text_pt": plot_text,
        "caption_text_pt": caption_text,
        "caption_to_plot_ratio": round(ratio, 6),
    }


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise FigurePolicyError("FIGURE_RASTER_INVALID", f"not a valid PNG header: {path.name}")
    return struct.unpack(">II", header[16:24])


def validate_publication_artwork(
    path: Path,
    *,
    profile: str,
    embedded_width_in: float | None = None,
    plot_minimum_text_pt: float = 8.0,
    caption_text_pt: float = 9.0,
    source_kind: str = "SOURCE_ARTWORK",
) -> dict[str, Any]:
    """Gate vector/raster artwork before document embedding.

    PDF-derived screenshots are review evidence only.  SVG must contain live
    text and vector geometry and may not hide a raster image.  PNG is accepted
    only when its native width supports the declared physical width at 300 dpi;
    metadata DPI and thumbnail upscaling cannot satisfy this calculation.
    """
    if str(source_kind).strip().upper() == "PDF_REVIEW_SCREENSHOT":
        raise FigurePolicyError(
            "FIGURE_PDF_SCREENSHOT_NOT_SOURCE_ARTWORK",
            "PDF-derived screenshots are review evidence only",
        )
    profile_key, contract = _publication_profile(profile)
    profile_receipt = validate_publication_profile(
        profile_key,
        plot_minimum_text_pt=plot_minimum_text_pt,
        caption_text_pt=caption_text_pt,
    )
    width_in = contract["width_in"] if embedded_width_in is None else _finite_number(
        embedded_width_in, "embedded_width_in", 1
    )
    if width_in <= 0 or width_in > contract["width_in"]:
        raise FigurePolicyError(
            "FIGURE_EMBEDDED_WIDTH_INVALID",
            f"declared width must be >0 and <= {contract['width_in']} in",
        )
    suffix = path.suffix.casefold()
    if suffix == ".svg":
        try:
            root = ElementTree.parse(path).getroot()
        except (OSError, ElementTree.ParseError) as exc:
            raise FigurePolicyError("FIGURE_VECTOR_INVALID", path.name) from exc
        elements = [element.tag.rsplit("}", 1)[-1].casefold() for element in root.iter()]
        if "image" in elements:
            raise FigurePolicyError(
                "FIGURE_VECTOR_CONTAINS_RASTER", "embedded raster images are not vector artwork"
            )
        if "text" not in elements:
            raise FigurePolicyError(
                "FIGURE_VECTOR_LIVE_TEXT_REQUIRED", "SVG requires live text for embedding QA"
            )
        if not set(elements) & {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}:
            raise FigurePolicyError(
                "FIGURE_VECTOR_GEOMETRY_REQUIRED", "SVG contains no vector geometry"
            )
        text_probes = []
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1].casefold() == "text":
                probe = " ".join("".join(element.itertext()).split())
                if len(probe) >= 3 and probe not in text_probes:
                    text_probes.append(probe)
                if len(text_probes) == 3:
                    break
        return {
            **profile_receipt,
            "artwork_type": "VECTOR_SVG",
            "vector_preserved": True,
            "live_text": True,
            "live_text_probes": text_probes,
            "embedded_width_in": width_in,
            "effective_dpi": "NOT_APPLICABLE_VECTOR",
        }
    if suffix != ".png":
        raise FigurePolicyError(
            "FIGURE_ARTWORK_FORMAT_UNSUPPORTED", "publication artwork must be SVG or PNG"
        )
    pixel_width, pixel_height = _png_dimensions(path)
    effective_dpi = pixel_width / width_in
    if effective_dpi < contract["minimum_raster_dpi"]:
        raise FigurePolicyError(
            "FIGURE_EFFECTIVE_DPI_INSUFFICIENT",
            f"native width {pixel_width}px at {width_in:.3f}in is {effective_dpi:.1f} dpi; "
            f"requires {contract['minimum_raster_dpi']:.0f} dpi",
        )
    return {
        **profile_receipt,
        "artwork_type": "RASTER_PNG",
        "vector_preserved": False,
        "live_text": False,
        "embedded_width_in": width_in,
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "effective_dpi": round(effective_dpi, 3),
        "minimum_raster_dpi": contract["minimum_raster_dpi"],
    }


def _quantile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise FigurePolicyError("FIGURE_HEATMAP_SCALE_EMPTY", "no normalization values")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def plan_heatmap_scale(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_field: str,
    category_field: str,
    separate_categories: Sequence[str] = tuple(SEPARATE_HEATMAP_CATEGORIES),
    lower_quantile: float = 0.02,
    upper_quantile: float = 0.98,
) -> dict[str, Any]:
    """Preserve raw values while excluding special buckets from robust color normalization."""
    if not 0 <= lower_quantile < upper_quantile <= 1:
        raise FigurePolicyError("FIGURE_HEATMAP_QUANTILE_INVALID", "invalid quantile bounds")
    separated_names = {str(value).strip().casefold() for value in separate_categories}
    normalization: list[float] = []
    separated: list[float] = []
    raw: list[float] = []
    for row_number, row in enumerate(rows, 1):
        value = _finite_number(row.get(value_field), value_field, row_number)
        raw.append(value)
        category = str(row.get(category_field, "")).strip().casefold()
        (separated if category in separated_names else normalization).append(value)
    if not normalization:
        raise FigurePolicyError(
            "FIGURE_HEATMAP_SCALE_NO_INFORMATIVE_VALUES",
            "all cells belong to separately displayed categories",
        )
    low = _quantile(normalization, lower_quantile)
    high = _quantile(normalization, upper_quantile)
    if low == high:
        low, high = min(normalization), max(normalization)
    if low == high:
        high = low + 1.0
    return {
        "status": "PASS",
        "mode": "ROBUST_QUANTILE_WITH_SEPARATE_CATEGORIES",
        "raw_minimum": min(raw),
        "raw_maximum": max(raw),
        "normalization_minimum": low,
        "normalization_maximum": high,
        "normalization_value_count": len(normalization),
        "separated_value_count": len(separated),
        "separate_categories": sorted(str(value).upper() for value in separate_categories),
        "clipped_low_count": sum(value < low for value in normalization),
        "clipped_high_count": sum(value > high for value in normalization),
        "raw_values_preserved": True,
    }


def validate_layout_rectangles(
    rectangles: Sequence[Mapping[str, Any]],
    *,
    canvas_width_px: float,
    canvas_height_px: float,
    minimum_gap_px: float = 0.5,
) -> dict[str, Any]:
    """Reject label collisions, touching boxes, and canvas overflow."""
    checked: list[dict[str, Any]] = []
    for row_number, rectangle in enumerate(rectangles, 1):
        try:
            x0, y0, x1, y1 = (
                float(rectangle[field]) for field in ("x0", "y0", "x1", "y1")
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FigurePolicyError("FIGURE_LAYOUT_BOX_INVALID", f"row {row_number}") from exc
        if x0 < 0 or y0 < 0 or x1 > canvas_width_px or y1 > canvas_height_px or x1 <= x0 or y1 <= y0:
            raise FigurePolicyError(
                "FIGURE_LAYOUT_OVERFLOW", str(rectangle.get("id", row_number))
            )
        checked.append({
            "id": str(rectangle.get("id", row_number)),
            "group": str(rectangle.get("group", "labels")),
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
        })
    for index, left in enumerate(checked):
        for right in checked[index + 1:]:
            if left["group"] != right["group"]:
                continue
            separated = (
                left["x1"] + minimum_gap_px < right["x0"]
                or right["x1"] + minimum_gap_px < left["x0"]
                or left["y1"] + minimum_gap_px < right["y0"]
                or right["y1"] + minimum_gap_px < left["y0"]
            )
            if not separated:
                raise FigurePolicyError(
                    "FIGURE_LAYOUT_COLLISION", f"{left['id']} touches or overlaps {right['id']}"
                )
    return {"status": "PASS", "rectangle_count": len(checked), "minimum_gap_px": minimum_gap_px}


def validate_tick_label_data_clearance(
    tick_label_rectangles: Sequence[Mapping[str, Any]],
    axes_data_rectangles: Sequence[Mapping[str, Any]],
    *,
    canvas_width_px: float,
    canvas_height_px: float,
    minimum_clearance_px: float = 0.0,
) -> dict[str, Any]:
    """Reject final-width tick labels that touch or enter their axes data rectangle.

    Rectangle coordinates are display-space pixels measured after the renderer's
    final layout pass. Every rectangle must carry an ``axis_id`` so labels are
    compared only with the data rectangle belonging to the same axes.
    """
    try:
        clearance_px = float(minimum_clearance_px)
    except (TypeError, ValueError) as exc:
        raise FigurePolicyError(
            "FIGURE_LAYOUT_CLEARANCE_INVALID", str(minimum_clearance_px)
        ) from exc
    if not math.isfinite(clearance_px) or clearance_px < 0:
        raise FigurePolicyError(
            "FIGURE_LAYOUT_CLEARANCE_INVALID", str(minimum_clearance_px)
        )

    def checked_rectangle(
        rectangle: Mapping[str, Any], *, row_number: int, kind: str
    ) -> dict[str, Any]:
        try:
            x0, y0, x1, y1 = (
                float(rectangle[field]) for field in ("x0", "y0", "x1", "y1")
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FigurePolicyError(
                "FIGURE_LAYOUT_BOX_INVALID", f"{kind} row {row_number}"
            ) from exc
        if (
            not all(math.isfinite(value) for value in (x0, y0, x1, y1))
            or x0 < 0
            or y0 < 0
            or x1 > canvas_width_px
            or y1 > canvas_height_px
            or x1 <= x0
            or y1 <= y0
        ):
            raise FigurePolicyError(
                "FIGURE_LAYOUT_OVERFLOW", str(rectangle.get("id", row_number))
            )
        axis_id = str(rectangle.get("axis_id", "")).strip()
        if not axis_id:
            raise FigurePolicyError(
                "FIGURE_LAYOUT_AXIS_ID_MISSING", str(rectangle.get("id", row_number))
            )
        return {
            "id": str(rectangle.get("id", row_number)),
            "axis_id": axis_id,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
        }

    data_by_axis: dict[str, dict[str, Any]] = {}
    for row_number, rectangle in enumerate(axes_data_rectangles, 1):
        checked = checked_rectangle(rectangle, row_number=row_number, kind="axes data")
        if checked["axis_id"] in data_by_axis:
            raise FigurePolicyError(
                "FIGURE_LAYOUT_AXIS_DATA_RECT_DUPLICATE", checked["axis_id"]
            )
        data_by_axis[checked["axis_id"]] = checked
    if not data_by_axis:
        raise FigurePolicyError("FIGURE_LAYOUT_AXIS_DATA_RECT_MISSING", "no axes data rectangles")

    labels = [
        checked_rectangle(rectangle, row_number=row_number, kind="tick label")
        for row_number, rectangle in enumerate(tick_label_rectangles, 1)
    ]
    for label in labels:
        data_rectangle = data_by_axis.get(label["axis_id"])
        if data_rectangle is None:
            raise FigurePolicyError(
                "FIGURE_LAYOUT_TICK_AXIS_UNBOUND",
                f"{label['id']} references {label['axis_id']}",
            )
        separated = (
            label["x1"] + clearance_px < data_rectangle["x0"]
            or data_rectangle["x1"] + clearance_px < label["x0"]
            or label["y1"] + clearance_px < data_rectangle["y0"]
            or data_rectangle["y1"] + clearance_px < label["y0"]
        )
        if not separated:
            raise FigurePolicyError(
                "FIGURE_LAYOUT_TICK_DATA_INTRUSION",
                f"{label['id']} touches or overlaps {data_rectangle['id']}",
            )
    return {
        "status": "PASS",
        "tick_label_rectangle_count": len(labels),
        "axes_data_rectangle_count": len(data_by_axis),
        "minimum_clearance_px": clearance_px,
        "axis_ids": sorted(data_by_axis),
    }


def _finite_number(value: Any, field: str, row_number: int) -> float:
    if value is None or value == "":
        raise FigurePolicyError(
            "FIGURE_DATA_MISSING_VALUE",
            f"row {row_number} has no value for numeric field {field!r}",
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise FigurePolicyError(
            "FIGURE_DATA_NOT_NUMERIC",
            f"row {row_number} field {field!r} is not numeric",
        ) from exc
    if not math.isfinite(number):
        raise FigurePolicyError(
            "FIGURE_DATA_NOT_FINITE",
            f"row {row_number} field {field!r} is not finite",
        )
    return number


def preflight_chart_data(
    rows: Sequence[Mapping[str, Any]],
    *,
    chart_kind: str,
    numeric_fields: Sequence[str],
    allow_all_zero: bool = False,
    all_zero_semantics: str | None = None,
    all_zero_meaning: str | None = None,
) -> dict[str, Any]:
    """Validate plotted values before any output directory is created.

    The gate targets known meaningless-output modes rather than judging whether
    a scientifically valid null result is interesting.  Nonzero constant bars
    are allowed, while empty inputs, missing/non-finite values, all-zero
    quantitative panels and one-point scatters are refused. A constant scatter
    with two or more observations is retained as a
    typed warning because equality across real observations can be a valid null
    result. A typed-state heatmap may opt into ``allow_all_zero`` because an
    observed-zero state can itself be the reported result.
    """
    zero_semantics = str(all_zero_semantics or "").strip()
    zero_explanation = str(all_zero_meaning or "").strip()
    if allow_all_zero:
        canonical = ALL_ZERO_SEMANTICS.get(zero_semantics)
        if canonical is None:
            raise FigurePolicyError(
                "FIGURE_ALL_ZERO_SEMANTICS_INVALID",
                "an all-zero exception requires one registered semantic code",
            )
        if zero_explanation != canonical:
            raise FigurePolicyError(
                "FIGURE_ALL_ZERO_EXPLANATION_INVALID",
                "the configured explanation must exactly match the registered semantic code",
            )
    if not rows:
        raise FigurePolicyError("FIGURE_DATA_EMPTY", "no plotted rows were supplied")
    fields = tuple(dict.fromkeys(str(field) for field in numeric_fields if str(field)))
    if not fields:
        raise FigurePolicyError("FIGURE_NUMERIC_FIELDS_EMPTY", "no numeric fields were declared")

    values: dict[str, list[float]] = {field: [] for field in fields}
    for row_number, row in enumerate(rows, 1):
        for field in fields:
            if field not in row:
                raise FigurePolicyError(
                    "FIGURE_DATA_MISSING_FIELD",
                    f"row {row_number} does not contain numeric field {field!r}",
                )
            values[field].append(_finite_number(row[field], field, row_number))

    flat = [value for field in fields for value in values[field]]
    if not allow_all_zero and all(value == 0 for value in flat):
        raise FigurePolicyError(
            "FIGURE_DATA_ALL_ZERO",
            "every declared quantitative value is zero",
        )
    warnings: list[dict[str, str]] = []
    if chart_kind == "scatter":
        if len(rows) < 2:
            raise FigurePolicyError(
                "FIGURE_SCATTER_TOO_FEW_POINTS",
                f"scatter requires at least 2 plotted rows; observed {len(rows)}",
            )
        if all(len(set(values[field])) == 1 for field in fields):
            warnings.append({
                "code": "FIGURE_SCATTER_NO_VARIATION",
                "detail": "all declared scatter axes are constant; retain only if the null result is useful",
            })

    return {
        "schema_version": FIGURE_PREFLIGHT_SCHEMA,
        "status": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "chart_kind": chart_kind,
        "row_count": len(rows),
        "numeric_fields": list(fields),
        "allow_all_zero": bool(allow_all_zero),
        "all_zero_semantics": zero_semantics or "NOT_APPLICABLE",
        "all_zero_meaning": zero_explanation or "NOT_APPLICABLE",
        "warnings": warnings,
        "field_summaries": {
            field: {
                "minimum": min(series),
                "maximum": max(series),
                "unique_values": len(set(series)),
                "zero_values": sum(value == 0 for value in series),
            }
            for field, series in values.items()
        },
    }


def validate_caption_methods(
    metadata: Mapping[str, Any],
    *,
    nonstandard_visual: bool = False,
) -> dict[str, Any]:
    """Require the owner-selected methods fields used beneath review figures."""
    missing = [field for field in CAPTION_METHOD_FIELDS if not str(metadata.get(field, "")).strip()]
    if missing:
        raise FigurePolicyError(
            "FIGURE_CAPTION_METHODS_INCOMPLETE",
            "missing required field(s): " + ", ".join(missing),
        )
    if str(metadata.get("caption_schema_version")) != CAPTION_METHOD_SCHEMA:
        raise FigurePolicyError(
            "FIGURE_CAPTION_SCHEMA_INVALID",
            f"caption schema must be {CAPTION_METHOD_SCHEMA}",
        )
    source_bindings = str(metadata.get("source_bindings") or "")
    digest_tokens = [
        token.split(";", 1)[0].strip().lower()
        for token in source_bindings.split("sha256=")[1:]
    ]
    if not any(
        len(token) == 64 and all(character in "0123456789abcdef" for character in token)
        for token in digest_tokens
    ):
        raise FigurePolicyError(
            "FIGURE_CAPTION_SOURCE_BINDING_INVALID",
            "caption source bindings require at least one exact SHA-256 digest",
        )
    semantic_fields = {
        "unit_of_analysis": "FIGURE_CAPTION_UNIT_INVALID",
        "denominator": "FIGURE_CAPTION_DENOMINATOR_INVALID",
        "group_denominators": "FIGURE_CAPTION_GROUP_DENOMINATOR_INVALID",
        "typed_missingness": "FIGURE_CAPTION_TYPED_MISSINGNESS_INVALID",
    }
    semantic_values: dict[str, str] = {}
    for field, code in semantic_fields.items():
        value = str(metadata.get(field) or "").strip()
        if len(value) < 4 or value.casefold() in CAPTION_PLACEHOLDERS:
            raise FigurePolicyError(code, f"caption field {field!r} contains a placeholder")
        semantic_values[field] = value
    unit_letters = [character.casefold() for character in semantic_values["unit_of_analysis"] if character.isalpha()]
    if len(set(unit_letters)) < 2:
        raise FigurePolicyError(
            "FIGURE_CAPTION_UNIT_INVALID",
            "the unit of analysis must be a substantive typed description",
        )
    if not any(character.isdigit() for character in semantic_values["denominator"]):
        raise FigurePolicyError(
            "FIGURE_CAPTION_DENOMINATOR_INVALID",
            "the overall denominator must carry an explicit numeric count",
        )
    group_denominators = semantic_values["group_denominators"].casefold()
    if "rows=" not in group_denominators or not any(
        character.isdigit() for character in group_denominators
    ):
        raise FigurePolicyError(
            "FIGURE_CAPTION_GROUP_DENOMINATOR_INVALID",
            "group denominators must carry explicit plotted-row counts",
        )
    typed_missingness = semantic_values["typed_missingness"]
    typed_missingness_folded = typed_missingness.casefold()
    if "plotted_rows=" not in typed_missingness_folded or not any(
        character.isdigit() for character in typed_missingness
    ):
        raise FigurePolicyError(
            "FIGURE_CAPTION_TYPED_MISSINGNESS_INVALID",
            "typed missingness must declare coverage against all plotted rows",
        )
    if "no_typed_state_column_in_plotted_rows" not in typed_missingness_folded and (
        "typed_rows=" not in typed_missingness_folded
        or "rows_missing_state_key=" not in typed_missingness_folded
    ):
        raise FigurePolicyError(
            "FIGURE_CAPTION_TYPED_MISSINGNESS_INVALID",
            "typed state summaries must count typed rows and rows missing the state key",
        )
    benchmark_sensitivity = str(metadata.get("benchmark_sensitivity") or "").strip()
    benchmark_folded = " ".join(benchmark_sensitivity.casefold().split())
    if (
        benchmark_folded.count("default_off=") != 1
        or "default_off=true" not in benchmark_folded
        or "excluded from study n and percentages" not in benchmark_folded
    ):
        raise FigurePolicyError(
            "FIGURE_CAPTION_BENCHMARK_SENSITIVITY_INVALID",
            "external benchmarks must be default-off and excluded from study n and percentages",
        )
    if nonstandard_visual and len(str(metadata.get("visual_grammar", "")).strip()) < 20:
        raise FigurePolicyError(
            "FIGURE_VISUAL_GRAMMAR_INADEQUATE",
            "a nonstandard visual must substantively explain its rows, columns, marks, colors, and summary values",
        )
    return {
        "schema_version": CAPTION_METHOD_SCHEMA,
        "status": "PASS",
        "required_fields": list(CAPTION_METHOD_FIELDS),
        "nonstandard_visual": bool(nonstandard_visual),
        "visual_grammar_present": bool(str(metadata.get("visual_grammar", "")).strip()),
    }


def validate_genus_comparison(scope: str, control: str | None = None) -> dict[str, Any]:
    """Default to within-genus comparisons and type every cross-genus control."""
    normalized_scope = str(scope or "").strip().upper()
    normalized_control = str(control or "").strip().upper()
    if normalized_scope not in GENUS_COMPARISON_SCOPES:
        raise FigurePolicyError(
            "FIGURE_GENUS_SCOPE_INVALID",
            f"scope must be one of {sorted(GENUS_COMPARISON_SCOPES)}",
        )
    if normalized_scope == "CROSS_GENUS" and normalized_control not in CROSS_GENUS_CONTROLS:
        raise FigurePolicyError(
            "FIGURE_CROSS_GENUS_CONTROL_MISSING",
            "cross-genus figures must be stratified, matched, modelled, or show genus composition",
        )
    return {
        "schema_version": FIGURE_PREFLIGHT_SCHEMA,
        "status": "PASS",
        "scope": normalized_scope,
        "control": normalized_control or "NOT_APPLICABLE",
    }


def apply_genus_preset(
    rows: Iterable[Mapping[str, Any]],
    *,
    genus_field: str,
    default_genera: Sequence[str],
    optional_genera: Sequence[str] = (),
    selected_optional: Sequence[str] = (),
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    """Apply an explicit default genus roster plus independently selectable options.

    The function contains no project cohort and no built-in taxonomy list.  A
    caller may therefore define an actinomycete-only default and expose other
    genera as named options without silently pooling them.
    """
    default = {str(value).strip().casefold() for value in default_genera if str(value).strip()}
    optional = {str(value).strip().casefold() for value in optional_genera if str(value).strip()}
    selected = {str(value).strip().casefold() for value in selected_optional if str(value).strip()}
    undeclared = sorted(selected - optional)
    if undeclared:
        raise FigurePolicyError(
            "FIGURE_GENUS_OPTION_UNDECLARED",
            "selected optional genus is not declared: " + ", ".join(undeclared),
        )
    if default & optional:
        raise FigurePolicyError(
            "FIGURE_GENUS_PRESET_OVERLAP",
            "a genus cannot be both default and optional",
        )
    accepted = default | selected
    input_rows = list(rows)
    kept = [row for row in input_rows if str(row.get(genus_field, "")).strip().casefold() in accepted]
    observed = Counter(str(row.get(genus_field, "")).strip() or "UNRESOLVED" for row in input_rows)
    return kept, {
        "schema_version": FIGURE_PREFLIGHT_SCHEMA,
        "status": "PASS",
        "input_rows": len(input_rows),
        "included_rows": len(kept),
        "excluded_rows": len(input_rows) - len(kept),
        "default_genera": sorted(default),
        "optional_genera": sorted(optional),
        "selected_optional": sorted(selected),
        "observed_genus_counts": dict(sorted(observed.items())),
    }


def _classes(products) -> set[str]:
    """Normalise a products value (';'-delimited string OR list) to a lowercase class set."""
    if products is None:
        return set()
    if isinstance(products, str):
        parts = products.split(";")
    else:
        parts = list(products)
    return {str(p).strip().lower() for p in parts if str(p).strip()}


def is_pure_saccharide(products) -> bool:
    """True iff the region's only specialist signal is saccharide (→ omit from figures)."""
    c = _classes(products)
    return ("saccharide" in c) and not (c & SPECIALIST_CLASSES)


def omit_saccharides(bgcs, get_products=lambda b: b.get("products"), enabled: bool = FIGURE_OMIT_SACCHARIDE):
    """Return bgcs with pure-saccharide regions removed (for figure input). `get_products` extracts the
    products value from each item. Set enabled=False to bypass (e.g. an explicit saccharide-only figure)."""
    if not enabled:
        return list(bgcs)
    return [b for b in bgcs if not is_pure_saccharide(get_products(b))]
