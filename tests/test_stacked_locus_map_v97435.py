import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("stacked_locus_map_test", ROOT / "deliverable_tools/stacked_locus_map.py")
locus_map = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(locus_map)


def fixture():
    return {
        "schema_version": "1.0",
        "query_identity": "DEMO-A / contig_alpha / region001 / BGC001",
        "title": "Neutral locus comparison",
        "tracks": [
            {"track_id": "query", "label": "Query", "boundary_left": "contig start", "boundary_right": "contig end", "genes": [
                {"id": "q1", "symbol": "geneA", "start": 0, "end": 900, "strand": 1, "role": "core_biosynthesis"},
                {"id": "q2", "symbol": "geneB", "start": 1000, "end": 1800, "strand": -1, "role": "tailoring_redox"},
            ]},
            {"track_id": "reference", "label": "Characterized comparator", "boundary_left": "segment boundary", "boundary_right": "segment boundary", "genes": [
                {"id": "r1", "symbol": "refA", "start": 50, "end": 850, "strand": 1, "role": "core_biosynthesis"},
                {"id": "r2", "symbol": "refB", "start": 980, "end": 1760, "strand": -1, "role": "tailoring_redox"},
            ]},
        ],
        "ribbons": [
            {"upper_track": "query", "upper_gene": "q1", "lower_track": "reference", "lower_gene": "r1", "identity_pct": 72.4}
        ],
    }


def test_renderer_emits_vector_and_manuscript_outputs(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(fixture()))
    receipt = locus_map.render(path, tmp_path / "figure.v1", tmp_path / "receipt.json")
    assert receipt["status"] == "PASS"
    assert receipt["query_identity"] == "DEMO-A / contig_alpha / region001 / BGC001"
    assert receipt["label_collision_gate"].startswith("PASS")
    for suffix in ("svg", "png", "pdf"):
        assert (tmp_path / f"figure.v1.{suffix}").stat().st_size > 100
        assert not Path(receipt["outputs"][suffix]["file"]).is_absolute()


def test_renderer_rejects_incomplete_identity():
    data = fixture()
    data["query_identity"] = "DEMO-A / contig_alpha / region001"
    with pytest.raises(ValueError, match="four-part|strain / full"):
        locus_map.validate_spec(data)


def test_renderer_rejects_unknown_ribbon_gene():
    data = fixture()
    data["ribbons"][0]["lower_gene"] = "missing"
    with pytest.raises(ValueError, match="unknown track or gene"):
        locus_map.validate_spec(data)


def test_label_collision_gate_fails_closed():
    genes = [{"id": f"g{i}", "symbol": "extremely_long_gene_symbol", "start": i, "end": i + 1} for i in range(8)]
    with pytest.raises(ValueError, match="LOCUS_MAP_LABEL_COLLISION"):
        locus_map.label_lanes(genes, maximum_lanes=2)
