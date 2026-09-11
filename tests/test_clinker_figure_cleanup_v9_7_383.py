import importlib.util
import sys
import types
from pathlib import Path


_MISSING = object()


def _load_module():
    fake = types.ModuleType("_bigscape_data")
    fake.DB_DEFAULT = "unused.db"
    fake.family_members = lambda *a, **k: {}
    fake.genes_for_gbk = lambda *a, **k: []
    fake.sm_annotation_index = lambda *a, **k: {}
    # Insert the fake ONLY for the widget's exec, then restore: a permanently-replaced
    # sys.modules entry leaks the empty-lambda stubs to every later in-process consumer
    # (e.g. widgets exec'd by other tests import `from _bigscape_data import ...` and
    # silently get empty results — the raw-stub/silent-empty leak class, .398/.399 rounds).
    prior = sys.modules.get("_bigscape_data", _MISSING)
    sys.modules["_bigscape_data"] = fake
    try:
        # widget ships in deliverable_tools/, not beside this test (fold-integration fix)
        path = Path(__file__).resolve().parents[1] / "deliverable_tools" / "bigscape_clinker_widget.py"
        spec = importlib.util.spec_from_file_location("clinker_cleanup_candidate", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        if prior is _MISSING:
            sys.modules.pop("_bigscape_data", None)
        else:
            sys.modules["_bigscape_data"] = prior
    return mod


def test_fake_bigscape_data_does_not_leak_to_later_tests():
    """Leak guard: after loading the widget with the fake, sys.modules must not retain it."""
    _load_module()
    leaked = sys.modules.get("_bigscape_data")
    # The entry must be either absent or a REAL file-backed module — never the fake
    # (the fake is a bare types.ModuleType with no __file__).
    assert leaked is None or getattr(leaked, "__file__", None) is not None, \
        "the empty-lambda fake leaked into sys.modules (silent-empty hazard for later tests)"


def test_figure_defaults_hide_distant_hairlines_and_expose_opt_in():
    mod = _load_module()
    assert 'id="distant"' in mod.TEMPLATE
    assert "distant:0" in mod.TEMPLATE
    assert "Math.abs(ax-bx)>140" in mod.TEMPLATE
    assert "distant/paralog links" in mod.TEMPLATE


def test_visible_figure_omits_status_badge_and_judgment_slogan():
    mod = _load_module()
    visible = mod.TEMPLATE + mod.INDEX_TEMPLATE
    assert "<span class=\"tag priv\">AS-private</span>" not in visible
    assert "Judgment deferred" not in visible
    assert "AS-private =" not in visible


def test_complete_locus_display_map_is_loaded_and_formatted(tmp_path):
    mod = _load_module()
    p = tmp_path / "map.tsv"
    p.write_text(
        "gbk_basename\tstrain\tfull_node_or_contig\tregion\tbgc_alias\n"
        "query.region001.gbk\tEX-1\tNODE_1_length_1000_cov_10.0\tregion001\tBGC001\n"
    )
    got = mod.load_locus_display_map(p)
    assert got["query.region001.gbk"]["display_locus"] == (
        "EX-1 / NODE_1_length_1000_cov_10.0 / region001 / BGC001"
    )


def test_complete_locus_display_map_fails_closed_on_missing_field(tmp_path):
    mod = _load_module()
    p = tmp_path / "map.tsv"
    p.write_text(
        "gbk_basename\tstrain\tfull_node_or_contig\tregion\tbgc_alias\n"
        "query.region001.gbk\tEX-1\tNODE_1_length_1000_cov_10.0\tregion001\t\n"
    )
    try:
        mod.load_locus_display_map(p)
    except ValueError as exc:
        assert "empty required field" in str(exc)
    else:
        raise AssertionError("incomplete locus identity did not fail closed")


def test_template_uses_complete_locus_label_when_bound():
    mod = _load_module()
    assert "t.display_locus||t.strain" in mod.TEMPLATE
    assert "t.display_parts.full_node_or_contig" in mod.TEMPLATE
    assert "t.display_parts.region" in mod.TEMPLATE
    assert "t.display_parts.bgc_alias" in mod.TEMPLATE


def test_caption_sidecar_retains_claim_ceiling_and_exact_locus_contract():
    mod = _load_module()
    text = mod._caption_methods({"family_id": 17, "cutoff": 0.3, "tracks": [{}, {}]})
    assert "Similarity and neighborhood conservation do not establish" in text
    assert "run- and cutoff-specific" in text
    assert "strain / full node-or-contig / region / BGC alias" in text


def test_index_omits_private_badge(tmp_path):
    mod = _load_module()
    mod._write_index(
        [{
            "path": str(tmp_path / "GCF_17_clinker_c0.3.html"),
            "family_id": 17,
            "private": True,
            "tracks": 2,
            "n_shared": 3,
            "class_summary": "AS 2",
            "product_summary": "NRPS x2",
        }],
        0.3,
        str(tmp_path),
    )
    html = (tmp_path / "index.html").read_text()
    assert "AS-private" not in html
    assert "Judgment deferred" not in html

