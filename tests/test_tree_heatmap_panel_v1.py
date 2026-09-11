"""tree_heatmap_panel v1 locks (BC-4, Alex-directed heatmap × phylogenomics integration).

Alignment authority (tree tip order, never matrix order), typed refusals (unmatched
tip/row, duplicates, non-numeric, missing caption, unapproved tree), missing != zero,
Other-isolation flag, and vector-with-live-text output. All fixtures synthetic.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mamey.tree_heatmap_panel import PanelHold, build_panel, load_matrix
from mamey.figure_theme import CLAIM_SAFETY

ROOT = Path(__file__).resolve().parents[1]

NEWICK = "(tipC:1,(tipA:1,tipB:1):1);"
# Deliberately NOT in tree order — alignment must follow the tree, not this file.
MATRIX = (
    "strain\tKS_burden\tclass_depth\tOther\n"
    "SYN-B\t4\t2\t9\n"
    "SYN-C\t12\t\t1\n"
    "SYN-A\t0\t5\t3\n"
)
CROSSWALK = (
    "newick_label\tstrain\tdisplay_label\trole\tgenus\n"
    "tipA\tSYN-A\tSynthetic A\tSTUDY\tStreptomyces\n"
    "tipB\tSYN-B\tSynthetic B\tSTUDY\tStreptomyces\n"
    "tipC\tSYN-C\tSynthetic C\tOUTGROUP\tRhodococcus\n"
)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _caption():
    fields = {
        "caption_schema_version": "sapote-mamey.figure-caption-methods.v2",
        "figure_question": "Synthetic alignment lock fixture",
        "source": "synthetic fixture tables",
        "source_release": "fixture-2026",
        "software_versions": "mamey test build",
        "unit_of_analysis": "one strain (one tree tip)",
        "inclusion_exclusion_roles": "STUDY + OUTGROUP tips, all included",
        "denominator": "3 synthetic strains",
        "group_denominators": "STUDY rows=2; OUTGROUP rows=1",
        "typed_missingness": ("blank matrix cells stay MISSING; plotted_rows=3; "
                              "no_typed_state_column_in_plotted_rows; 1 missing class_depth cell"),
        "benchmark_sensitivity": ("no external benchmark plotted; default_off=true; "
                                  "excluded from study n and percentages"),
        "transformation": "linear per column; Other isolated",
        "visual_grammar": "single-hue sequential ramp; hollow dashed cell = missing",
        "statistics_uncertainty": "none computed",
        "comparison_group": "none",
        "genus_control": "genus recorded per tip via crosswalk",
        "contradictions": "none",
        "interpretation_boundary": "display of declared inputs only; judgment deferred",
    }
    return fields


def _stage(tmp_path, *, matrix_text=MATRIX, crosswalk_text=CROSSWALK,
           sanity_status="PASS", caption_overrides=None, evidence_status="PASS_EVIDENCE_WIDGET_READY",
           evidence_tree_sha=None):
    (tmp_path / "tree.nwk").write_text(NEWICK)
    (tmp_path / "crosswalk.tsv").write_text(crosswalk_text)
    (tmp_path / "matrix.tsv").write_text(matrix_text)
    tree_sha = _sha(tmp_path / "tree.nwk")
    (tmp_path / "sanity.json").write_text(json.dumps({"status": sanity_status, "tree_sha256": tree_sha}))
    admitted_tree_sha = evidence_tree_sha or tree_sha
    evidence = {
        "schema_version": "sapote.phylogeny-figure-factory.v1",
        "figure_kind": "phylogeny_evidence_receipt_widget_v1",
        "status": evidence_status,
        "figure_id": "synthetic_phylo_evidence",
        "outgroup_tip": "tipC",
        "bound_inputs": {"tree_evidence": {
            "tree": {"logical_locator": "tree.nwk", "sha256": admitted_tree_sha},
            "admitted_signoff": {"status": "PASS", "tree_sha256": admitted_tree_sha,
                                  "outgroup_tip": "tipC"},
        }},
    }
    (tmp_path / "phylo_evidence.json").write_text(json.dumps(evidence))
    caption = _caption()
    caption["source_bindings"] = f"matrix sha256={_sha(tmp_path / 'matrix.tsv')}"
    if caption_overrides:
        caption.update(caption_overrides)
    config = {
        "panel_id": "synthetic_panel",
        "figure_set_id": "FS009",
        "tree": {"logical_locator": "tree.nwk", "sha256": _sha(tmp_path / "tree.nwk")},
        "tip_crosswalk": {"logical_locator": "crosswalk.tsv", "sha256": _sha(tmp_path / "crosswalk.tsv")},
        "matrix": {"logical_locator": "matrix.tsv", "sha256": _sha(tmp_path / "matrix.tsv")},
        "tree_sanity_receipt": {"logical_locator": "sanity.json", "sha256": _sha(tmp_path / "sanity.json")},
        "phylogeny_evidence_receipt": {"logical_locator": "phylo_evidence.json", "sha256": _sha(tmp_path / "phylo_evidence.json")},
        "column_transforms": {"KS_burden": "log1p"},
        "caption_methods": caption,
    }
    config_path = tmp_path / "panel_config.json"
    config_path.write_text(json.dumps(config))
    return config_path


def _refuses(tmp_path, code, **stage_kwargs):
    config = _stage(tmp_path, **stage_kwargs)
    with pytest.raises(PanelHold) as exc:
        build_panel(config)
    assert exc.value.code == code, f"expected {code}, got {exc.value.code}: {exc.value.detail}"


def test_alignment_follows_tree_order_not_matrix_order(tmp_path):
    receipt = build_panel(_stage(tmp_path))
    svg = (tmp_path / "panel_out" / "synthetic_panel.svg").read_text()
    # Tree tip order is tipC, tipA, tipB — matrix file order was B, C, A.
    order = [svg.index("Synthetic C"), svg.index("Synthetic A"), svg.index("Synthetic B")]
    assert order == sorted(order), "heatmap rows are not in tree tip order"
    assert receipt["row_order_authority"].startswith("tree tip order")
    assert receipt["tip_count"] == 3


def test_missing_cell_stays_missing_not_zero(tmp_path):
    receipt = build_panel(_stage(tmp_path))
    assert receipt["missing_cells_by_column"] == {"KS_burden": 0, "class_depth": 1, "Other": 0}
    svg = (tmp_path / "panel_out" / "synthetic_panel.svg").read_text()
    assert "stroke-dasharray" in svg, "missing cell must render hollow, not as a zero-color cell"


def test_other_column_is_flagged_isolated(tmp_path):
    receipt = build_panel(_stage(tmp_path))
    assert receipt["other_columns_isolated"] == ["Other"]
    svg = (tmp_path / "panel_out" / "synthetic_panel.svg").read_text()
    assert "[isolated]" in svg


def test_vector_output_with_live_text(tmp_path):
    receipt = build_panel(_stage(tmp_path))
    svg = (tmp_path / "panel_out" / "synthetic_panel.svg").read_text()
    assert "<text" in svg and "<image" not in svg
    assert "figure_id=synthetic_panel" in svg
    assert receipt["figure_set_id"] == "FS009"
    assert CLAIM_SAFETY in svg
    assert receipt["outputs"][0]["sha256"] == _sha(tmp_path / "panel_out" / "synthetic_panel.svg")
    assert receipt["outputs"][0]["bytes"] > 0


def test_matrix_row_without_tip_refuses(tmp_path):
    _refuses(tmp_path, "THP_ALIGNMENT_HOLD",
             matrix_text=MATRIX + "SYN-D\t1\t1\t1\n")


def test_tip_without_matrix_row_refuses(tmp_path):
    short = "strain\tKS_burden\tclass_depth\tOther\nSYN-B\t4\t2\t9\nSYN-C\t12\t3\t1\n"
    _refuses(tmp_path, "THP_ALIGNMENT_HOLD", matrix_text=short)


def test_duplicate_matrix_strain_refuses(tmp_path):
    _refuses(tmp_path, "THP_MATRIX_HOLD", matrix_text=MATRIX + "SYN-A\t1\t1\t1\n")


def test_non_numeric_cell_refuses(tmp_path):
    bad = MATRIX.replace("SYN-B\t4", "SYN-B\thigh")
    _refuses(tmp_path, "THP_MATRIX_HOLD", matrix_text=bad)


def test_unapproved_tree_refuses(tmp_path):
    _refuses(tmp_path, "THP_TREE_SANITY_HOLD", sanity_status="FAIL")


def test_generic_pass_receipt_for_another_tree_refuses(tmp_path):
    _refuses(tmp_path, "THP_PHYLO_EVIDENCE_MISMATCH", evidence_tree_sha="0" * 64)


def test_failed_figure_factory_evidence_refuses(tmp_path):
    _refuses(tmp_path, "THP_PHYLO_EVIDENCE_HOLD", evidence_status="FAIL")


def test_outgroup_role_must_match_admitted_receipt(tmp_path):
    crosswalk = CROSSWALK.replace("tipC\tSYN-C\tSynthetic C\tOUTGROUP", "tipC\tSYN-C\tSynthetic C\tREFERENCE")
    _refuses(tmp_path, "THP_OUTGROUP_MISMATCH", crosswalk_text=crosswalk)


def test_svg_escapes_bound_labels(tmp_path):
    crosswalk = CROSSWALK.replace("Synthetic A", "Synthetic & A")
    receipt = build_panel(_stage(tmp_path, crosswalk_text=crosswalk))
    svg = (tmp_path / "panel_out" / receipt["svg"]).read_text()
    assert "Synthetic &amp; A" in svg and "Synthetic & A" not in svg


def test_heatmap_reuses_the_canonical_footer_owner():
    source = (ROOT / "mamey" / "tree_heatmap_panel.py").read_text(encoding="utf-8")
    assert "from .figure_theme import CLAIM_SAFETY" in source
    assert "CLAIM_FOOTER =" not in source


def test_placeholder_caption_refuses(tmp_path):
    _refuses(tmp_path, "THP_CAPTION_HOLD", caption_overrides={"denominator": "tbd"})


def test_registry_row_is_required(tmp_path):
    config = _stage(tmp_path)
    payload = json.loads(config.read_text())
    payload.pop("figure_set_id")
    config.write_text(json.dumps(payload))
    with pytest.raises(PanelHold) as exc:
        build_panel(config)
    assert exc.value.code == "THP_REGISTRY_HOLD"


def test_load_matrix_blank_is_none():
    import io, csv, tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "m.tsv"
        p.write_text("strain\tA\nS1\t\nS2\t3\n")
        columns, rows = load_matrix(p)
        assert rows["S1"]["A"] is None and rows["S2"]["A"] == 3.0
