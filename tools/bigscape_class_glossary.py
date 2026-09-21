#!/usr/bin/env python3
"""Render the bundled BiG-SCAPE class vocabulary as an undergraduate-facing Markdown key."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_VOCABULARY = Path(__file__).resolve().parents[1] / "mamey" / "data" / "bigscape_class_vocabulary.json"


def render(vocabulary_path=DEFAULT_VOCABULARY):
    payload = json.loads(Path(vocabulary_path).read_text(encoding="utf-8"))
    entries = payload["entries"]
    lines = [
        "# BiG SCAPE Class Glossary",
        "",
        "This key explains the broad biosynthetic class codes shown in Sapote-Mamey BiG-SCAPE reports and widgets. The same bundled vocabulary drives the TSV fields, report headings, network labels, and visible legends.",
        "",
        "## How to read a network",
        "",
        "1. Start with the GCF number and cutoff. They identify one run-specific family, not a universal biological name.",
        "2. Expand the class code with the table below. Treat it as a broad routing label from source antiSMASH annotations.",
        "3. Hover or click a node and record the complete strain, node or contig, region, and BGC alias identity.",
        "4. Read the boundary state. CONTIG_EDGE is a caution that the called region touches a contig boundary.",
        "5. Read direct edge distance as pairwise similarity context. Smaller distance means closer by this run's model; it does not prove the same product.",
        "6. Stop at the claim ceiling. Use gene order, domains, verified searches, chemistry, and experiments for stronger conclusions.",
        "",
        "## Broad class vocabulary",
        "",
        "| Code | Full name | Plain-language meaning | Source basis | Claim ceiling |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        values = [
            entry["code"], entry["full_name"], entry["plain_language_meaning"],
            entry["source_basis"], entry["claim_ceiling"],
        ]
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    policy = payload["reviewed_subtype_policy"]
    lines.extend([
        "",
        "## Reviewed subtype codes",
        "",
        policy["plain_language_meaning"],
        "",
        "A reviewed subtype row must provide `family_id`, `reviewed_subtype_code`, `full_name`, `plain_language_meaning`, `source_basis`, and `claim_ceiling`. The subtype is displayed separately from the broad class code so readers can see which statement comes from the source label and which came from a later review.",
        "",
        "**Subtype claim ceiling.** " + policy["claim_ceiling"],
        "",
        "## Overall claim ceiling",
        "",
        payload["claim_ceiling"],
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocabulary", default=str(DEFAULT_VOCABULARY))
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    Path(args.out).write_text(render(args.vocabulary), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
