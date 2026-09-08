"""v9.7.409: a config-less package auto-emits the Figure Factory with a truthful host.

The Figure Factory auto-emit only fires when a ``figure_factory_next_config.json`` is
discoverable; ``mamey.figure_factory_default_config`` synthesizes that config (and its two
admitted TSVs) straight from a package's own cohort CSVs. These tests pin:

* a package that ships NO Figure Factory config now renders a real figure suite;
* the derived host label is the REAL ecology (a *macrotermitis* / "Macrotermes" strain is
  ``termite``), and is NEVER coerced to ``ATTINE`` or any other wrong category;
* the palette ``cohort`` slot for a host with no honest palette key is the neutral
  ``UNRESOLVED``, not a fabricated ecological bucket;
* metric numbers are computed from the tables (not hand-typed);
* the generator returns a typed skip (never a crash) when the cohort CSVs are absent.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mamey import figure_factory_default_config as dc


# --- A tiny, realistic package: one termite-host study strain + one reference strain. ---

_MASTER_HEADER = [
    "strain", "BGC_ID", "contig", "region", "boundary", "length_kb",
    "products", "n_classes", "arch", "kcb_top", "kcb_score", "safe_claim",
]


def _master_row(strain: str, bgc: str, products: str, kcb: str) -> list[object]:
    return [strain, bgc, "CONTIG1.1", "1", "Interior", "20.0",
            products, "1", "A", kcb, "100.0", "candidate"]


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _plant_package(pkg: Path) -> None:
    """A termite-host STUDY strain and a reference strain, with hand-checkable counts.

    STUDY strain ``Actinomadura_TERM1`` (host: termite):
      3 regions; 2 figure-eligible (1 pure-saccharide omitted); 2 kcb hits; 1 CONFIRM.
    REFERENCE strain ``Actinomadura_REF9``:
      2 regions; 2 eligible; 1 kcb hit; 2 CONFIRM.
    """
    pkg.mkdir(parents=True, exist_ok=True)
    master = [
        _master_row("Actinomadura_TERM1", "BGC001", "NRPS; other", "HIT | x | knownclusterblast #1"),
        _master_row("Actinomadura_TERM1", "BGC002", "ectoine; other", "HIT | y | knownclusterblast #1"),
        _master_row("Actinomadura_TERM1", "BGC003", "saccharide", ""),  # pure-saccharide -> omitted
        _master_row("Actinomadura_REF9", "BGC001", "terpene", "HIT | z | knownclusterblast #1"),
        _master_row("Actinomadura_REF9", "BGC002", "NRPS", ""),
    ]
    _write_csv(pkg / "COHORT_MASTER.csv", _MASTER_HEADER, master)
    _write_csv(
        pkg / "modeb_verdicts.csv",
        ["strain", "bgc", "status", "modeb_class", "note"],
        [
            ["Actinomadura_TERM1", "BGC001", "CONFIRM", "NRPS", "n"],
            ["Actinomadura_TERM1", "BGC002", "DROP", "ectoine", "n"],
            ["Actinomadura_REF9", "BGC001", "CONFIRM", "terpene", "n"],
            ["Actinomadura_REF9", "BGC002", "CONFIRM", "NRPS", "n"],
        ],
    )
    _write_csv(
        pkg / "COHORT_MASTER_strain_summary.csv",
        ["strain", "taxonomy", "genus", "source", "release", "engine_version", "bgc_count"],
        [
            ["Actinomadura_TERM1", "Actinomadura macrotermitis", "Actinomadura",
             "isolated from a Macrotermes fungus-growing termite mound", "PRIVATE", "Mamey v1.9.148", "3"],
            ["Actinomadura_REF9", "Actinomadura rifamycini", "Actinomadura",
             "public reference genome (type strain DSM 43936)", "PRIVATE", "Mamey v1.9.148", "2"],
        ],
    )


def _read_manifest(pkg: Path) -> list[dict[str, str]]:
    path = pkg / dc.INPUTS_SUBDIR / dc.MANIFEST_NAME
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


# --- Host derivation is the load-bearing correctness property. ---------------------

def test_termite_host_is_never_attine() -> None:
    assert dc.derive_host_label("Actinomadura macrotermitis", "Macrotermes mound") == "termite"
    # The palette slot for a termite host is the neutral UNRESOLVED, NOT the ATTINE bucket.
    assert dc.host_palette_slot("termite", "STUDY") == "UNRESOLVED"
    assert dc.host_palette_slot("termite", "STUDY") != "ATTINE"
    # A genuine attine cue still maps to ATTINE; a bee to BEE; unknown -> unassigned/UNRESOLVED.
    assert dc.derive_host_label("Streptomyces sp.", "Acromyrmex leaf-cutter ant garden") == "attine ant"
    assert dc.host_palette_slot("attine ant", "STUDY") == "ATTINE"
    assert dc.derive_host_label("Streptomyces sp.", "soil") == dc.UNASSIGNED_HOST
    assert dc.host_palette_slot(dc.UNASSIGNED_HOST, "STUDY") == "UNRESOLVED"


def test_generate_writes_truthful_manifest(tmp_path: Path) -> None:
    pkg = tmp_path / "package"
    _plant_package(pkg)
    reference_ids = ["Actinomadura_REF9"]

    result = dc.generate_default_config(pkg, reference_ids=reference_ids)
    assert isinstance(result, Path) and result.name == dc.CONFIG_NAME
    assert result.is_file()

    manifest = {row["identity"]: row for row in _read_manifest(pkg)}
    term = manifest["Actinomadura_TERM1"]
    # The REAL host is recorded, and the palette slot is the neutral one -- never ATTINE.
    assert term["host"] == "termite"
    assert term["cohort"] == "UNRESOLVED"
    assert term["role"] == "STUDY" and term["include_by_default"] == "true"
    # No manifest row anywhere claims the ATTINE ecology for this termite cohort.
    manifest_text = (pkg / dc.INPUTS_SUBDIR / dc.MANIFEST_NAME).read_text(encoding="utf-8")
    assert "ATTINE" not in manifest_text
    # Reference strain is default-off and colours by role.
    ref = manifest["Actinomadura_REF9"]
    assert ref["role"] == "REFERENCE" and ref["include_by_default"] == "false"
    assert ref["cohort"] == "REFERENCE"

    # Config is sha256-bound and points at the two admitted inputs.
    config = json.loads(result.read_text(encoding="utf-8"))
    assert config["schema_version"] == dc.SCHEMA_VERSION
    assert {i["role"] for i in config["inputs"]} == {"aggregate_metrics", "cohort_manifest"}
    for item in config["inputs"]:
        assert len(item["sha256"]) == 64
    assert config["comparison"]["default_genera"] == ["Actinomadura"]
    assert config["comparison"]["selected_optional_identities"] == ["Actinomadura_REF9"]


def test_metric_counts_come_from_the_tables(tmp_path: Path) -> None:
    pkg = tmp_path / "package"
    _plant_package(pkg)
    dc.generate_default_config(pkg, reference_ids=["Actinomadura_REF9"])
    metrics_path = pkg / dc.INPUTS_SUBDIR / dc.METRICS_NAME
    with metrics_path.open(newline="", encoding="utf-8") as handle:
        rows = {(r["identity"], r["channel"], r["metric"]): (int(r["numerator"]), int(r["denominator"]))
                for r in csv.DictReader(handle, delimiter="\t")}
    # TERM1: 3 regions; 2 eligible (saccharide omitted); 2 kcb; 1 CONFIRM.
    assert rows[("Actinomadura_TERM1", "antismash", "figure_eligible_regions")] == (2, 3)
    assert rows[("Actinomadura_TERM1", "knownclusterblast", "kcb_hit_regions")] == (2, 3)
    assert rows[("Actinomadura_TERM1", "mode_b", "confirm_verdicts")] == (1, 3)
    # REF9: 2 regions; 2 eligible; 1 kcb; 2 CONFIRM.
    assert rows[("Actinomadura_REF9", "antismash", "figure_eligible_regions")] == (2, 2)
    assert rows[("Actinomadura_REF9", "mode_b", "confirm_verdicts")] == (2, 2)


@pytest.mark.slow
def test_configless_package_emits_figure_with_truthful_host(tmp_path: Path) -> None:
    pkg = tmp_path / "package"
    _plant_package(pkg)
    assert not (pkg / dc.CONFIG_NAME).exists()  # config-less to start

    receipt = dc.emit_default_figure(pkg, reference_ids=["Actinomadura_REF9"])
    assert receipt["status"] == "PASS_PORTABLE_POLICY_RENDERER_CANDIDATE"

    out = pkg / "figure_factory"
    for profile in ("single_column", "double_column"):
        assert (out / f"figure_factory_next_{profile}.svg").is_file()
        assert (out / f"figure_factory_next_{profile}.png").read_bytes().startswith(b"\x89PNG")

    # The rendered/plotted surfaces make no ATTINE claim for the termite cohort.
    for name in ("figure_factory_next_single_column.svg", "figure_factory_next_data.tsv",
                 "figure_factory_next_caption_methods.md"):
        assert "ATTINE" not in (out / name).read_text(encoding="utf-8", errors="replace")

    # A discoverable config was left next to the package for the auto-emit path.
    assert (pkg / dc.CONFIG_NAME).is_file()


def test_typed_skip_when_cohort_csvs_absent(tmp_path: Path) -> None:
    pkg = tmp_path / "empty_package"
    pkg.mkdir()
    result = dc.generate_default_config(pkg)
    assert isinstance(result, dict)
    assert result["status"] == "SKIPPED_NO_COHORT_CSVS"
    # emit_default_figure surfaces the same typed skip (no crash, no figure dir).
    assert dc.emit_default_figure(pkg)["status"] == "SKIPPED_NO_COHORT_CSVS"
    assert not (pkg / "figure_factory").exists()
