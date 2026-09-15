"""Shared fixture builder for the TREES_432 panel-binder tests (not a test module).

Builds a tiny synthetic GToTree panel folder: a 4-tip Newick tree with UFBoot node labels, a
tree.iqtree stub whose "Input data" line declares the INFERENCE genome count, and a
figure_metadata.tsv with one QUERY, two REFERENCE rows and one OUTGROUP. No owner data:
synthetic ids only. The colour-strip renderer (tools/render_tree_COLOR_STRIPS.R) is the only
sanctioned GToTree panel renderer; this fixture feeds the binder and receipt tools, not a render.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COLUMNS = ["tip", "identifier", "role", "reference_class", "label_concise", "label_experiment",
           "Candida", "MRSA", "source_display", "geography_display", "source_category",
           "location_raw", "metadata_status"]

TREE = "((QRY-1:0.01,GCF_000000001.1:0.02)95:0.03,(GCF_000000002.1:0.04,OUT_OUTGROUP:0.05)88:0.01);"


def rows():
    return [
        dict(tip="QRY-1", identifier="QRY-1", role="QUERY", reference_class="Owner query",
             label_concise="Genus sp. QRY-1 [Wasp; US] (PX000001)", label_experiment="Genus sp. QRY-1 [Wasp; US] (PX000001)",
             Candida="+", MRSA="-", source_display="wasp", geography_display="US", source_category="Wasp",
             location_raw="USA: somewhere", metadata_status="synthetic"),
        dict(tip="GCF_000000001.1", identifier="GCF_000000001.1", role="REFERENCE", reference_class="Type",
             label_concise="Genus alpha DSM 1 [Type] (GCF_000000001.1)", label_experiment="Genus alpha DSM 1 [Type] (GCF_000000001.1)",
             Candida="", MRSA="", source_display="soil", geography_display="Asia", source_category="Soil",
             location_raw="China", metadata_status="synthetic"),
        dict(tip="GCF_000000002.1", identifier="GCF_000000002.1", role="REFERENCE", reference_class="Reference",
             label_concise="Genus sp. X-2 (GCF_000000002.1)", label_experiment="Genus sp. X-2 (GCF_000000002.1)",
             Candida="", MRSA="", source_display="", geography_display="", source_category="",
             location_raw="", metadata_status="synthetic"),
        dict(tip="OUT_OUTGROUP", identifier="GCF_000000009.1", role="OUTGROUP", reference_class="Type",
             label_concise="Outer beta DSM 9 [Type; outgroup] (GCF_000000009.1)", label_experiment="Outer beta DSM 9 [Type; outgroup] (GCF_000000009.1)",
             Candida="", MRSA="", source_display="marine sediment", geography_display="Pacific Ocean", source_category="Marine",
             location_raw="Pacific", metadata_status="synthetic"),
    ]


def write_metadata(panel: Path, data=None) -> None:
    with (panel / "figure_metadata.tsv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(data if data is not None else rows())


def make_panel(root: Path, panel_id: str, *, n_inferred: int = 4, sites: int = 1000,
               spec_taxon: str | None = None, data=None) -> Path:
    panel = root / panel_id
    panel.mkdir(parents=True, exist_ok=True)
    (panel / "tree.treefile").write_text(TREE + "\n")
    (panel / "tree.iqtree").write_text(
        "IQ-TREE 3.1.3 stub\n"
        f"Input data: {n_inferred} sequences with {sites} amino-acid sites\n"
        "Model of substitution: LG+G4\n"
    )
    write_metadata(panel, data)
    if spec_taxon is not None:
        (panel / "TREE_SPEC.json").write_text(
            '{\n "title": "synthetic",\n "scope": "genus",\n "taxon": "%s",\n "outgroup": "OUTGROUP"\n}\n' % spec_taxon)
    return panel
