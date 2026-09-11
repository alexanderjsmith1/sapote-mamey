from pathlib import Path


def test_exporter_declares_complete_portable_source_contract():
    root = Path(__file__).resolve().parents[1]
    text = (root / "tools/export_tree_figure_source_package.py").read_text()
    for name in ("_tree.nwk", "_metadata.tsv", "_aligned_sequences.fasta", "_render_figure.R",
                 "_caption.txt", "_methods.md", "_clean.png", "_clean.pdf",
                 "_display_receipt.json", "MANIFEST.json"):
        assert name in text
    assert 'collapse_near_identical.py' in text
    assert '_console.py' in text
    assert 'refresh_figure_source_manifest.py' in text
    assert 'source_dir' in text
    assert 'output exists' in text
    assert 'Paths are relative' in text
    assert 'figure_stem' in text


def test_phylo_report_does_not_mislabel_mixed_reference_panels_as_type_only():
    root = Path(__file__).resolve().parents[1]
    text = (root / "tools/phylo_place.py").read_text()
    assert "Reference backbone = {prov.get('n_ref','?')} reference sequences" in text
    assert "Reference backbone = {prov.get('n_ref','?')} type strains" not in text


def test_every_placement_display_exports_a_standalone_collaborator_package():
    root = Path(__file__).resolve().parents[1]
    text = (root / "tools/placement_display.py").read_text()
    assert "standalone_R_package" in text
    assert "export_tree_figure_source_package.py" in text
    for name in ("_render_figure.R", "_tree.nwk", "_analysis_tree.nwk", "_metadata.tsv",
                 "_aligned_sequences.fasta", "_caption.txt", "_methods.md",
                 "_clean.png", "_clean.pdf", "_rerender_captioned.sh", "MANIFEST.json"):
        assert name in text
    assert "STANDALONE_PACKAGE_INCOMPLETE" in text
