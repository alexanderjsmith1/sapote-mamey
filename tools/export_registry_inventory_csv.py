#!/usr/bin/env python3
"""Generate the registry inventory CSV from its authoritative JSON."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # mamey from any cwd
from mamey.csv_safety import SafeDictWriter  # noqa: E402  formula-cell guard on every written cell

FIELDS = ['id', 'name', 'library', 'category', 'evidence_tier', 'claim_ceiling', 'targets', 'wet_lab_routes', 'description', 'positive_interpretation', 'negative_interpretation', 'claim_safety', 'citation', 'source_locator', 'version_added', 'synonyms', 'family', 'required_markers', 'optional_markers', 'forbidden_markers']
JOINED = {"wet_lab_routes", "synonyms", "required_markers", "optional_markers", "forbidden_markers"}

def render_csv(entries):
    if not isinstance(entries, list) or not entries:
        raise ValueError("registry must be a nonempty list")
    rows, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("registry entries must be objects")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError("registry IDs must be nonempty and unique")
        seen.add(identifier)
        if set(entry) - set(FIELDS):
            raise ValueError("unmapped registry fields")
        row = {}
        for key in FIELDS:
            value = entry.get(key)
            if value is None:
                row[key] = ""
            elif key in JOINED:
                if not isinstance(value, list) or any(not isinstance(v, str) or ";" in v for v in value):
                    raise ValueError("joined registry fields require strings without semicolons")
                row[key] = ";".join(value)
            elif key == "targets":
                if not isinstance(value, list):
                    raise ValueError("targets must be a list")
                row[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, str):
                row[key] = value
            else:
                raise ValueError("unsupported registry value type")
        rows.append(row)
    import io
    out = io.StringIO(newline="")
    writer = SafeDictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path(__file__).resolve().parents[1] / "bundle_support/registry_inventory_v1.9.4.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.registry.resolve() == args.output.resolve():
            raise ValueError("output must differ from the source JSON")
        content = render_csv(json.loads(args.registry.read_text(encoding="utf-8")))
        args.output.write_text(content, encoding="utf-8", newline="")
    except (ValueError, OSError) as exc:
        sys.stderr.write(f"registry export: {exc}\n")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
