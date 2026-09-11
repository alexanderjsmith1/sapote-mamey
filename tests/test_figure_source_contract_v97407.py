from __future__ import annotations

import csv
import io
import json
import zipfile

from mamey.interactive_figures.figure_source_bundle import build_source_bundle


def _csv_text(fields, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def test_inventory_resistance_tier_survives_without_deep_profile(tmp_path):
    """The inventory owns this value when optional deep_data.json is absent."""
    strain = "SYNTHETIC-001"
    package_name = f"{strain}_Complete_Package.zip"
    inventory = _csv_text(
        ["BGC_ID", "Boundary", "Length_kb", "Products", "Resistance_tier"],
        [{
            "BGC_ID": "BGC001",
            "Boundary": "Interior",
            "Length_kb": "25",
            "Products": "RiPP",
            "Resistance_tier": "T2_RESISTANCE_LIKE_SOURCE_DERIVED",
        }],
    )
    with zipfile.ZipFile(tmp_path / package_name, "w") as archive:
        archive.writestr(f"package/{strain}_2_inventory.csv", inventory)

    widget = {
        "meta": {"sourceRelease": "synthetic"},
        "strains": {
            strain: {
                "governance": "GOVERNED",
                "package": package_name,
                "bgcRows": 1,
                "uniquePhysicalGenes": 0,
                "machineryGenes": 0,
                "classes": {"RiPP": {"total": 1, "edge": 0, "full": 0, "interior": 1}},
                "machinery": {},
                "hostContext": {"group": "UNRESOLVED", "source": "", "hostSpecies": "", "location": ""},
            }
        },
    }
    widget_path = tmp_path / "widget.json"
    widget_path.write_text(json.dumps(widget), encoding="utf-8")
    out = tmp_path / "bundle"

    receipt = build_source_bundle(widget_path, tmp_path, out)
    assert receipt["status"].startswith("PASS")
    with (out / "BGC_EXTENDED_EVIDENCE.csv").open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["resistance_tier"] == "T2_RESISTANCE_LIKE_SOURCE_DERIVED"
