"""Stage an explicitly synthetic, hash-bound Figure Factory example."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def stage(project_dir: Path) -> Path:
    project_dir = project_dir.expanduser().resolve()
    if project_dir.exists():
        raise FileExistsError(f"Choose a new project directory: {project_dir}")
    source = Path(__file__).resolve().parents[1] / "examples" / "figure_factory"
    files = {"aggregate_metrics": "aggregate_metrics.synthetic.tsv",
             "cohort_manifest": "cohort_manifest.synthetic.tsv"}
    project_dir.mkdir(parents=True)
    inputs = project_dir / "inputs"
    inputs.mkdir()
    bindings = []
    for role, name in files.items():
        target = inputs / name
        shutil.copyfile(source / name, target)
        bindings.append({"role": role, "logical_locator": f"inputs/{name}",
                         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    config = {
        "schema_version": "sapote.figure-factory-next.v2",
        "external_data_root": str(project_dir),
        "output_dir": "figure",
        "title": "Synthetic BLASTp channel coverage",
        "figure_question": "What fraction of declared synthetic proteins has a returned record in each channel?",
        "source_release": "synthetic-demonstration-only",
        "software_versions": "Sapote-Mamey Figure Factory Next v2",
        "inputs": bindings,
        "comparison": {"default_genera": ["Genus alpha"], "optional_genera": [],
                       "selected_optional_genera": [],
                       "selected_optional_identities": ["held-alpha-one", "benchmark-alpha-one"]},
        "owner_notes": ["Synthetic example; no biological inference."],
    }
    path = project_dir / "figure_factory_next.json"
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    args = parser.parse_args()
    print(stage(args.project_dir))


if __name__ == "__main__":
    main()
