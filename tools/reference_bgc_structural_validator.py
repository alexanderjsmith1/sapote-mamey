#!/usr/bin/env python3
"""Measure a curated, exact-bound reference-BGC panel with Mamey.

Whole-genome records without a curated, locus-resolved reference BGC are
excluded. They may be genome-profile comparators, but they are not BGC
validation controls.

This operator tool measures the observed structural half of reference-panel
concordance. Expected sizes, genes, markers, and their citations must be
supplied in a versioned local manifest; model output is never reference truth.
The tool is extraction-only: similarity and marker capacity do not establish
product identity, production, activity, or biological validation.
"""

from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


AUTHORITY = "DETERMINISTIC_EXTRACTION_REFERENCE_PANEL_NOT_BIOLOGICAL_VALIDATION"
REQUIRED_MANIFEST_FIELDS = (
    "source_zip",
    "source_zip_sha256",
    "compound",
    "accession",
    "strain",
    "full_contig",
    "region",
    "bgc_alias",
    "evidence_citation",
)
OPTIONAL_EXPECTED_FIELDS = (
    "expected_size_kb_MIBIG",
    "expected_core_genes",
    "reference_marker_set",
)
OUTPUT_FIELDS = (
    # Legacy seed-library columns are retained for downstream compatibility.
    "compound",
    "accession",
    "bgc",
    "found_size_kb",
    "found_n_cds",
    "found_n_domains",
    "engine_markers_fired",
    "n_markers_fired",
    "kcb_anchor",
    "expected_size_kb_MIBIG",
    "expected_core_genes",
    "reference_marker_set",
    "markers_present_of_expected",
    # Exact binding and provenance added in v9.7.390.
    "exact_locus",
    "strain",
    "full_contig",
    "region",
    "bgc_alias",
    "source_zip",
    "source_zip_sha256",
    "observed_bgc_start",
    "observed_bgc_end",
    "found_size_bp",
    "marker_scope",
    "kcb_anchor_raw",
    "evidence_citation",
    "engine_version",
    "bundle_version",
    "authority",
)
FAILURE_FIELDS = (
    "exact_locus",
    "source_zip",
    "hold_code",
    "detail",
    "authority",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REGION_RE = re.compile(r"^region\d+$", re.IGNORECASE)
_BGC_RE = re.compile(r"^BGC\d+$", re.IGNORECASE)


class ManifestError(ValueError):
    """The local reference manifest is malformed or identity-incomplete."""


@dataclass(frozen=True)
class ReferenceSpec:
    source_zip: str
    source_zip_sha256: str
    compound: str
    accession: str
    strain: str
    full_contig: str
    region: str
    bgc_alias: str
    evidence_citation: str
    expected_size_kb_MIBIG: str = ""
    expected_core_genes: str = ""
    reference_marker_set: str = ""

    @property
    def exact_locus(self) -> str:
        return f"{self.strain} / {self.full_contig} / {self.region} / {self.bgc_alias}"


@dataclass(frozen=True)
class Hold:
    exact_locus: str
    source_zip: str
    hold_code: str
    detail: str

    def as_row(self) -> dict[str, str]:
        return {
            "exact_locus": self.exact_locus,
            "source_zip": self.source_zip,
            "hold_code": self.hold_code,
            "detail": self.detail,
            "authority": AUTHORITY,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_identity(value: str, field: str, row_number: int) -> str:
    value = value.strip()
    if not value:
        raise ManifestError(f"row {row_number}: required field {field!r} is empty")
    if " / " in value:
        raise ManifestError(f"row {row_number}: {field!r} contains the exact-locus separator ' / '")
    return value


def load_reference_manifest(path: Path) -> list[ReferenceSpec]:
    """Load an exact-bound, citation-bearing TSV; refuse incomplete identities."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or [])
        missing = [field for field in REQUIRED_MANIFEST_FIELDS if field not in fields]
        if missing:
            raise ManifestError(f"manifest is missing required columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ManifestError("manifest contains no reference rows")

    specs: list[ReferenceSpec] = []
    seen_loci: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        values = {
            field: _clean_identity(str(row.get(field, "")), field, row_number)
            for field in REQUIRED_MANIFEST_FIELDS
        }
        values["source_zip_sha256"] = values["source_zip_sha256"].lower()
        source_locator = Path(values["source_zip"])
        if source_locator.is_absolute() or ".." in source_locator.parts:
            raise ManifestError(f"row {row_number}: source_zip must be a relative locator inside --input-dir")
        if not _SHA256_RE.fullmatch(values["source_zip_sha256"]):
            raise ManifestError(f"row {row_number}: source_zip_sha256 is not a lowercase SHA-256")
        if not _REGION_RE.fullmatch(values["region"]):
            raise ManifestError(f"row {row_number}: region must be formatted like region001")
        if not _BGC_RE.fullmatch(values["bgc_alias"]):
            raise ManifestError(f"row {row_number}: bgc_alias must be formatted like BGC001")
        spec = ReferenceSpec(
            **values,
            **{field: str(row.get(field, "")).strip() for field in OPTIONAL_EXPECTED_FIELDS},
        )
        if spec.exact_locus in seen_loci:
            raise ManifestError(f"row {row_number}: duplicate exact locus {spec.exact_locus}")
        seen_loci.add(spec.exact_locus)
        specs.append(spec)
    return specs


def _bgc_identity(bgc: Any, strain: str) -> tuple[str, str, str, str]:
    contig = str(getattr(bgc, "node_id", "") or getattr(bgc, "contig", "")).strip()
    region = str(getattr(bgc, "antismash_region", "") or "").strip()
    if not region:
        number = int(getattr(bgc, "region_number", 0) or 0)
        region = f"region{number:03d}" if number else ""
    alias = str(getattr(bgc, "bgc_id", "") or "").strip()
    return strain, contig, region, alias


def _display_identity(parts: tuple[str, str, str, str]) -> str:
    return " / ".join(part or "<missing>" for part in parts)


def select_exact_bgc(spec: ReferenceSpec, bgcs: Sequence[Any]) -> Any:
    """Return exactly one four-part-bound BGC; never fall back to parse order."""
    expected = (spec.strain, spec.full_contig, spec.region, spec.bgc_alias)
    matches = [bgc for bgc in bgcs if _bgc_identity(bgc, spec.strain) == expected]
    if len(matches) != 1:
        observed = sorted(_display_identity(_bgc_identity(bgc, spec.strain)) for bgc in bgcs)
        raise ManifestError(
            f"exact target matched {len(matches)} records; expected {spec.exact_locus}; "
            f"observed={observed or ['<none>']}"
        )
    return matches[0]


def _overlaps_inclusive(feature: Any, bgc: Any) -> bool:
    """Parser coordinates are one-based inclusive; endpoint contact overlaps."""
    return (
        getattr(feature, "contig", None) == getattr(bgc, "contig", None)
        and int(feature.start) <= int(bgc.end)
        and int(bgc.start) <= int(feature.end)
    )


def _atomic_write_table(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[dict[str, Any]],
    *,
    delimiter: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = _SafeDictWriter(handle, fieldnames=fieldnames, delimiter=delimiter, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _load_engine() -> tuple[Any, Any, str, str]:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from mamey import BUNDLE_VERSION, __version__, parsers  # noqa: PLC0415
    from mamey.source_scans import run_source_scans  # noqa: PLC0415

    return parsers, run_source_scans, __version__, BUNDLE_VERSION


def _normalized_anchor(raw: str) -> str:
    """Retain the historical first-token field without silently losing raw provenance."""
    return raw.split("/", 1)[0].strip()


def _measure_reference(
    spec: ReferenceSpec,
    zip_path: Path,
    parsers: Any,
    run_source_scans: Any,
    engine_version: str,
    bundle_version: str,
) -> dict[str, Any]:
    bgcs = parsers.parse_bgcs_from_zip(zip_path)
    bgc = select_exact_bgc(spec, bgcs)
    cds = parsers.extract_cds_features(zip_path)
    domains = parsers.extract_domain_features(zip_path)
    contigs = parsers.extract_contig_sequences(zip_path)
    scans = run_source_scans(bgcs, cds, contigs, domains)
    per_bgc = scans.cctt.get("per_bgc", {})
    markers = sorted({str(marker) for marker in (per_bgc.get(bgc.bgc_id, []) or [])})
    marker_text = ", ".join(markers) or "(none)"
    raw_anchor = str(
        getattr(bgc, "closest_candidate_kcb_product", "")
        or getattr(bgc, "kcb_top", "")
        or ""
    )
    found_size_bp = int(bgc.end) - int(bgc.start) + 1
    if found_size_bp <= 0:
        raise ManifestError(f"non-positive inclusive interval {bgc.start}..{bgc.end}")
    expected_markers = {
        token.strip() for token in re.split(r"[,;]", spec.reference_marker_set) if token.strip()
    }
    present_expected = sorted(expected_markers.intersection(markers))
    return {
        "compound": spec.compound,
        "accession": spec.accession,
        "bgc": spec.bgc_alias,
        "found_size_kb": f"{found_size_bp / 1000.0:.3f}",
        "found_n_cds": sum(1 for feature in cds if _overlaps_inclusive(feature, bgc)),
        "found_n_domains": sum(1 for feature in domains if _overlaps_inclusive(feature, bgc)),
        "engine_markers_fired": marker_text,
        "n_markers_fired": len(markers),
        "kcb_anchor": _normalized_anchor(raw_anchor),
        "expected_size_kb_MIBIG": spec.expected_size_kb_MIBIG,
        "expected_core_genes": spec.expected_core_genes,
        "reference_marker_set": spec.reference_marker_set,
        "markers_present_of_expected": ", ".join(present_expected),
        "exact_locus": spec.exact_locus,
        "strain": spec.strain,
        "full_contig": spec.full_contig,
        "region": spec.region,
        "bgc_alias": spec.bgc_alias,
        "source_zip": spec.source_zip,
        "source_zip_sha256": spec.source_zip_sha256,
        "observed_bgc_start": int(bgc.start),
        "observed_bgc_end": int(bgc.end),
        "found_size_bp": found_size_bp,
        "marker_scope": "CCTT_PER_BGC_ONLY",
        "kcb_anchor_raw": raw_anchor,
        "evidence_citation": spec.evidence_citation,
        "engine_version": engine_version,
        "bundle_version": bundle_version,
        "authority": AUTHORITY,
    }


def run_panel(manifest: Path, input_dir: Path, output: Path, failure_output: Path) -> int:
    protected_inputs = {manifest.resolve()}
    if output.resolve() == failure_output.resolve() or {
        output.resolve(),
        failure_output.resolve(),
    }.intersection(protected_inputs):
        print(
            "configuration error: manifest, output, and failure-output must be distinct paths",
            file=sys.stderr,
        )
        return 2
    try:
        specs = load_reference_manifest(manifest)
    except (OSError, ManifestError) as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2

    parsers, run_source_scans, engine_version, bundle_version = _load_engine()
    rows: list[dict[str, Any]] = []
    holds: list[Hold] = []
    for spec in specs:
        zip_path = input_dir / spec.source_zip
        if not zip_path.is_file():
            holds.append(Hold(spec.exact_locus, spec.source_zip, "SOURCE_ZIP_MISSING", str(zip_path)))
            continue
        observed_sha = _sha256(zip_path)
        if observed_sha != spec.source_zip_sha256:
            holds.append(
                Hold(
                    spec.exact_locus,
                    spec.source_zip,
                    "SOURCE_ZIP_SHA256_MISMATCH",
                    f"expected={spec.source_zip_sha256}; observed={observed_sha}",
                )
            )
            continue
        try:
            rows.append(
                _measure_reference(
                    spec,
                    zip_path,
                    parsers,
                    run_source_scans,
                    engine_version,
                    bundle_version,
                )
            )
        except Exception as exc:  # fail closed per exact reference; preserve typed detail
            holds.append(Hold(spec.exact_locus, spec.source_zip, "EXACT_REFERENCE_MEASUREMENT_FAILED", str(exc)))

    _atomic_write_table(
        failure_output,
        FAILURE_FIELDS,
        (hold.as_row() for hold in holds),
        delimiter="\t",
    )
    if holds:
        print(
            f"REFUSING to replace {output}: {len(holds)} of {len(specs)} exact references are held; "
            f"see {failure_output}",
            file=sys.stderr,
        )
        return 2

    # Keep the historical CSV format consumed by seed_reference_library.py.
    _atomic_write_table(output, OUTPUT_FIELDS, rows, delimiter=",")
    print(
        f"wrote {output}: {len(rows)} exact-bound reference BGCs; "
        "CCTT marker capacity only; no product, production, activity, or biological-validation claim"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Versioned exact-reference TSV")
    parser.add_argument("--input-dir", required=True, type=Path, help="Directory containing source ZIPs")
    parser.add_argument("--output", required=True, type=Path, help="Structural output CSV")
    parser.add_argument(
        "--failure-output",
        type=Path,
        help="Typed hold TSV (default: <output>.failures.tsv)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    failure_output = args.failure_output or args.output.with_name(f"{args.output.name}.failures.tsv")
    return run_panel(args.manifest, args.input_dir, args.output, failure_output)


if __name__ == "__main__":
    raise SystemExit(main())
