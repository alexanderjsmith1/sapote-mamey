"""Synthesize a Figure Factory Next config plus its admitted inputs from a package.

This is the zero-config bridge for the Figure Factory. The auto-emit path only fires
when a ``figure_factory_next_config.json`` is discoverable next to a sealed package;
this module *produces* that config (and the two admitted TSVs it binds) directly from a
package/cohort's own authoritative CSVs, so a package that ships no Figure Factory config
can still emit the manifest-governed aggregate-evidence figure.

Contract (deterministic, offline, extraction-only):

* Reads only ``COHORT_MASTER.csv`` (+ ``COHORT_MASTER_strain_summary.csv`` when present)
  and ``modeb_verdicts.csv`` from the package/cohort dir. Never touches scores, boards,
  or the sealed core, and never reaches the network.
* Derives, per strain, three real evidence channels against the strain's antiSMASH
  region count as the denominator:
  - ``antismash / figure_eligible_regions`` (non-pure-saccharide regions, via
    :func:`mamey.figure_policy.is_pure_saccharide`),
  - ``knownclusterblast / kcb_hit_regions`` (regions carrying a knownclusterblast top hit),
  - ``mode_b / confirm_verdicts`` (Mode B ``CONFIRM`` verdicts).
* Derives each strain's **real host label** from its taxonomy/source text
  (e.g. *Actinomadura macrotermitis* / "Macrotermes" -> ``termite``) and records it in a
  dedicated ``host`` column of the manifest. The host label is NEVER coerced into a
  different real ecological category: a termite symbiont is ``termite``, not ``ATTINE``.
  When the host cannot be determined it is ``unassigned`` -- never a wrong category.
* Assigns each row a palette-valid ``cohort`` slot for colouring only. A host that has an
  honest existing palette key (bee/wasp/attine/moss) uses it; every other host (termite,
  free-living, unassigned) uses ``UNRESOLVED`` -- a neutral slot that makes no ecological
  claim. Ordered per-host colour assignment is the palette module's job (sibling lane
  ``palette_host_ordering``); this module only guarantees the ``host`` column is truthful
  and the ``cohort`` slot is never a fabricated ecology.
* Writes the two TSVs, computes their SHA-256 *after* writing, and stamps those digests
  into a ``sapote.figure-factory-next.v2`` config -- the content-addressing the Factory's
  ``build()`` enforces.

If the required CSVs are absent the module returns a *typed skip* dict rather than
raising, so a package without cohort tables is a silent no-op by design.

The default figure question is a documented module constant
(:data:`DEFAULT_FIGURE_QUESTION`) that the owner can retune in one place.
"""
from __future__ import annotations
from contextlib import suppress as _suppress

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .figure_factory_next import SCHEMA_VERSION, build, sha256_file
from .figure_policy import COHORT_PALETTE, is_pure_saccharide

# --- Documented, owner-retunable defaults -----------------------------------------

#: The default scientific question the auto-emitted figure answers. This is a single
#: constant so the owner can retune the auto-emit's framing in exactly one place.
DEFAULT_FIGURE_QUESTION = (
    "For each strain, what fraction of its antiSMASH regions is observed on each "
    "declared evidence channel -- figure-eligible (non-pure-saccharide) regions, "
    "knownclusterblast top-hit regions, and Mode B CONFIRM verdicts?"
)

#: Denominator label carried on every metric row (per-strain antiSMASH region count).
DENOMINATOR_KEY = "antismash_regions"

#: Conventional filenames written into the package for the auto-emit to discover.
CONFIG_NAME = "figure_factory_next_config.json"
INPUTS_SUBDIR = "figure_factory_inputs"
METRICS_NAME = "figure_metrics.tsv"
MANIFEST_NAME = "cohort_manifest.tsv"

METRIC_FIELDS = ("identity", "channel", "metric", "numerator", "denominator", "denominator_key")
# The Factory requires exactly COHORT_FIELDS; `host`/`host_source` are extra, tolerated
# columns that carry the truthful ecology alongside the palette slot.
MANIFEST_FIELDS = (
    "identity", "role", "include_by_default", "genus", "cohort",
    "assembly_state", "assembly_reason", "host", "host_source",
)

# --- Host derivation ---------------------------------------------------------------

# Ordered (label, keyword-substrings) table. First hit on the lowercased
# taxonomy+source text wins. Keep specific insect/host cues ahead of generic ones.
# CRITICAL: termite cues are their OWN label; they must never fall through to `attine ant`.
_HOST_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("termite", (
        "macrotermit", "macrotermes", "odontotermes", "nasutitermes",
        "microtermes", "termite", "termitomyces", "isoptera",
    )),
    ("attine ant", (
        "attine", "attini", "acromyrmex", "trachymyrmex", "apterostigma",
        "cyphomyrmex", "mycetomoellerius", "sericomyrmex", "leaf-cutter",
        "leafcutter", "fungus-growing ant", "fungus growing ant",
    )),
    ("bee", (
        "apis mellifera", "apis cerana", "bombus", "megachile", "melissococcus",
        "honeybee", "honey bee", "bumblebee", "bumble bee", "solitary bee",
    )),
    ("wasp", (
        "vespa", "vespula", "polistes", "philanthus", "beewolf", "digger wasp",
        "parasitoid wasp", "sphecid",
    )),
    ("moss", (
        "moss", "bryophyt", "sphagnum", "physcomitr", "hypnum", "dicranum",
    )),
)

# Honest host -> existing palette-key map. Only ecologies with a genuine palette key are
# mapped; every other host uses the neutral UNRESOLVED slot (no fabricated ecology).
_HOST_TO_PALETTE = {
    "bee": "BEE",
    "wasp": "WASP",
    "attine ant": "ATTINE",
    "moss": "MOSS",
}

UNASSIGNED_HOST = "unassigned"
NEUTRAL_COHORT_SLOT = "UNRESOLVED"


def derive_host_label(taxonomy: str, source: str = "") -> str:
    """Derive a strain's real host label from its taxonomy/source text.

    Returns a lowercase host label (e.g. ``termite``, ``attine ant``, ``bee``) or
    ``unassigned`` when no cue matches. Never returns a category the text does not
    support -- in particular a termite cue never yields ``attine ant``.
    """
    haystack = f"{taxonomy or ''} {source or ''}".casefold()
    for label, keywords in _HOST_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return label
    return UNASSIGNED_HOST


def host_palette_slot(host_label: str, role: str) -> str:
    """Map a (host_label, role) to a palette-valid ``cohort`` slot for colouring only.

    Non-STUDY roles colour by role; STUDY rows colour by host where an honest palette key
    exists, else the neutral ``UNRESOLVED`` slot. This function never returns a palette key
    for an ecology the host does not belong to.
    """
    role_up = (role or "").strip().upper()
    if role_up == "REFERENCE":
        return "REFERENCE"
    if role_up in {"EXTERNAL_BENCHMARK", "OUTGROUP"}:
        return "EXTERNAL_BENCHMARK" if role_up == "EXTERNAL_BENCHMARK" else NEUTRAL_COHORT_SLOT
    slot = _HOST_TO_PALETTE.get(host_label, NEUTRAL_COHORT_SLOT)
    # Defensive: only ever emit a real palette key.
    return slot if slot in COHORT_PALETTE else NEUTRAL_COHORT_SLOT


# --- CSV discovery + parsing -------------------------------------------------------

def _locate(package_dir: Path) -> dict[str, Path] | None:
    """Find the cohort CSVs in the package dir or its ``cohort/`` subdir.

    Returns a mapping with ``master`` and ``modeb`` keys (both required) and an optional
    ``summary`` key, or ``None`` when the two required tables are not both present.
    """
    package_dir = Path(package_dir)
    search = [package_dir, package_dir / "cohort"]
    found: dict[str, Path] = {}
    wanted = {
        "master": "COHORT_MASTER.csv",
        "modeb": "modeb_verdicts.csv",
        "summary": "COHORT_MASTER_strain_summary.csv",
    }
    for key, name in wanted.items():
        for base in search:
            candidate = base / name
            if candidate.is_file():
                found[key] = candidate
                break
    if "master" not in found or "modeb" not in found:
        return None
    return found


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _strain_summaries(summary_path: Path | None) -> dict[str, dict[str, str]]:
    if summary_path is None:
        return {}
    out: dict[str, dict[str, str]] = {}
    for row in _read_csv(summary_path):
        strain = str(row.get("strain", "")).strip()
        if strain:
            out[strain] = row
    return out


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


# --- Metric + manifest derivation --------------------------------------------------

def _derive_metrics(master_rows: Sequence[Mapping[str, str]],
                    modeb_rows: Sequence[Mapping[str, str]]) -> tuple[
                        list[str], dict[str, dict[str, int]]]:
    """Return (ordered strain ids, per-strain channel counts).

    Counts are computed from the authoritative tables, never hand-typed:
    total regions, figure-eligible (non-pure-saccharide) regions, knownclusterblast
    hit regions, and Mode B CONFIRM verdicts.
    """
    counts: dict[str, dict[str, int]] = {}
    order: list[str] = []
    for row in master_rows:
        strain = str(row.get("strain", "")).strip()
        if not strain:
            continue
        if strain not in counts:
            counts[strain] = {"regions": 0, "eligible": 0, "kcb": 0, "confirm": 0}
            order.append(strain)
        bucket = counts[strain]
        bucket["regions"] += 1
        if not is_pure_saccharide(row.get("products")):
            bucket["eligible"] += 1
        if str(row.get("kcb_top", "")).strip():
            bucket["kcb"] += 1
    for row in modeb_rows:
        strain = str(row.get("strain", "")).strip()
        if strain in counts and str(row.get("status", "")).strip().upper() == "CONFIRM":
            counts[strain]["confirm"] += 1
    return order, counts


def _metric_rows(order: Sequence[str], counts: Mapping[str, Mapping[str, int]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strain in order:
        bucket = counts[strain]
        denom = bucket["regions"]
        if denom <= 0:
            # A strain with no regions cannot satisfy denominator > 0; skip it (typed
            # out of the figure) rather than emit an invalid metric row.
            continue
        channels = (
            ("antismash", "figure_eligible_regions", bucket["eligible"]),
            ("knownclusterblast", "kcb_hit_regions", bucket["kcb"]),
            ("mode_b", "confirm_verdicts", bucket["confirm"]),
        )
        for channel, metric, numerator in channels:
            rows.append({
                "identity": strain,
                "channel": channel,
                "metric": metric,
                "numerator": min(max(numerator, 0), denom),
                "denominator": denom,
                "denominator_key": DENOMINATOR_KEY,
            })
    return rows


def _manifest_rows(order: Sequence[str],
                   counts: Mapping[str, Mapping[str, int]],
                   summaries: Mapping[str, Mapping[str, str]],
                   reference_ids: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strain in order:
        if counts[strain]["regions"] <= 0:
            continue
        summary = summaries.get(strain, {})
        taxonomy = str(summary.get("taxonomy", "")).strip()
        source = str(summary.get("source", "")).strip()
        genus = str(summary.get("genus", "")).strip() or (taxonomy.split(" ")[0] if taxonomy else strain)
        host = derive_host_label(taxonomy, source)
        is_reference = strain in reference_ids
        role = "REFERENCE" if is_reference else "STUDY"
        cohort = host_palette_slot(host, role)
        rows.append({
            "identity": strain,
            "role": role,
            "include_by_default": "false" if is_reference else "true",
            "genus": genus,
            "cohort": cohort,
            # Assembly QC is not evaluated by the zero-config generator; UNRESOLVED is the
            # honest state (no PASS/FLAG claim). Supply a roles override to set it.
            "assembly_state": "UNRESOLVED",
            "assembly_reason": "assembly QC not evaluated by default_config generator",
            "host": host,
            "host_source": "derived from taxonomy/source" if host != UNASSIGNED_HOST else "no host cue in taxonomy/source",
        })
    return rows


def _write_tsv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# --- Public API --------------------------------------------------------------------

def generate_default_config(package_dir: Path | str,
                            dest_dir: Path | str | None = None,
                            *,
                            reference_ids: Sequence[str] = (),
                            figure_question: str = DEFAULT_FIGURE_QUESTION,
                            title: str = "Evidence-channel coverage per strain") -> Any:
    """Synthesize the admitted TSVs + a sha256-bound v2 config from a package.

    Writes ``figure_metrics.tsv`` and ``cohort_manifest.tsv`` into
    ``<dest_dir>/figure_factory_inputs/`` and a discoverable
    ``figure_factory_next_config.json`` into ``<dest_dir>``. ``dest_dir`` defaults to the
    package dir, so the auto-emit's existing discovery finds the config next to the package.

    Returns the config :class:`~pathlib.Path` on success, or a typed skip dict
    ``{"status": "SKIPPED_...", ...}`` when the required cohort CSVs are absent or no
    strain yields a valid (denominator > 0) metric row. Never raises for a missing package.
    """
    package_dir = Path(package_dir)
    dest_dir = Path(dest_dir) if dest_dir is not None else package_dir
    located = _locate(package_dir)
    if located is None:
        return {"status": "SKIPPED_NO_COHORT_CSVS", "reason":
                "COHORT_MASTER.csv and modeb_verdicts.csv are both required"}

    master_rows = _read_csv(located["master"])
    modeb_rows = _read_csv(located["modeb"])
    summaries = _strain_summaries(located.get("summary"))
    order, counts = _derive_metrics(master_rows, modeb_rows)

    reference_set = {str(r).strip() for r in reference_ids if str(r).strip()}
    metric_rows = _metric_rows(order, counts)
    manifest_rows = _manifest_rows(order, counts, summaries, reference_set)
    if not metric_rows or not manifest_rows:
        return {"status": "SKIPPED_NO_ELIGIBLE_STRAINS", "reason":
                "no strain carried a positive antiSMASH region count"}

    inputs_dir = dest_dir / INPUTS_SUBDIR
    inputs_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = inputs_dir / METRICS_NAME
    manifest_path = inputs_dir / MANIFEST_NAME
    _write_tsv(metrics_path, METRIC_FIELDS, metric_rows)
    _write_tsv(manifest_path, MANIFEST_FIELDS, manifest_rows)

    # Content-address the two inputs *after* writing them.
    metrics_sha = sha256_file(metrics_path)
    manifest_sha = sha256_file(manifest_path)

    # default_genera = the genera of the default-on study rows (within-genus comparison).
    default_genera = sorted({
        row["genus"] for row in manifest_rows
        if row["role"] == "STUDY" and row["include_by_default"] == "true"
    })
    selected_optional_identities = [
        row["identity"] for row in manifest_rows if row["role"] == "REFERENCE"
    ]

    # Source release / software version from the package summary when available; both must
    # be non-blank for the caption gate.
    any_summary = next(iter(summaries.values()), {}) if summaries else {}
    source_release = str(any_summary.get("release", "")).strip() or "package-derived"
    software_versions = str(any_summary.get("engine_version", "")).strip() or "Sapote-Mamey"

    config = {
        "schema_version": SCHEMA_VERSION,
        "external_data_root": INPUTS_SUBDIR,
        "output_dir": "figure_factory",
        "title": title,
        "figure_question": figure_question,
        "source_release": source_release,
        "software_versions": software_versions,
        "inputs": [
            {"role": "aggregate_metrics", "logical_locator": METRICS_NAME, "sha256": metrics_sha},
            {"role": "cohort_manifest", "logical_locator": MANIFEST_NAME, "sha256": manifest_sha},
        ],
        "comparison": {
            "default_genera": default_genera,
            "optional_genera": [],
            "selected_optional_genera": [],
            "selected_optional_identities": selected_optional_identities,
        },
        "owner_notes": [
            "Auto-synthesized by figure_factory_default_config from the package cohort CSVs.",
            "cohort column is a palette slot only; the truthful host is the manifest `host` column.",
        ],
    }
    config_path = dest_dir / CONFIG_NAME
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return config_path


def emit_default_figure(package_dir: Path | str,
                        output_dir: Path | str | None = None,
                        **kwargs: Any) -> Any:
    """End-to-end zero-config path: synthesize the config, then render the figure.

    Generates the admitted inputs + config from ``package_dir``, resolves the config's
    (relative) ``external_data_root`` and ``output_dir`` to absolute paths, and drives
    :func:`mamey.figure_factory_next.build`. Returns the build receipt on success, or the
    generator's typed skip dict when the cohort CSVs are absent.

    ``output_dir`` overrides the config's default (``<package>/figure_factory``).
    ``reference_ids`` / ``figure_question`` / ``title`` pass through to
    :func:`generate_default_config`.
    """
    package_dir = Path(package_dir)
    result = generate_default_config(package_dir, **kwargs)
    if isinstance(result, dict):
        return result  # typed skip
    config_path = result
    config = json.loads(config_path.read_text(encoding="utf-8"))
    # Absolutize relative roots against the config's own directory (mirrors the auto-emit).
    root = Path(config["external_data_root"])
    if not root.is_absolute():
        config["external_data_root"] = str((config_path.parent / root).resolve())
    out = Path(output_dir) if output_dir is not None else (config_path.parent / config["output_dir"])
    config["output_dir"] = str(Path(out).resolve())
    resolved = config_path.with_name(".figure_factory_next_config.resolved.json")
    resolved.write_text(json.dumps(config, sort_keys=True) + "\n", encoding="utf-8")
    try:
        return build(resolved)
    finally:
        with _suppress(OSError):  # v9.7.409: best-effort cleanup, intent explicit (was except: pass)
            resolved.unlink()
