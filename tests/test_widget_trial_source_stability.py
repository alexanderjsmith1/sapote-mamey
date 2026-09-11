"""Source mutation controls for reader-side widget production."""
import json
import zipfile
import pytest
from mamey import widget_deliverable as widgets


def minimal_package(tmp_path):
    root = tmp_path / 'package'
    root.mkdir()
    (root / 'manifest.json').write_text(json.dumps({'strain_id': 'TEST', 'package_status': 'MAMEY_COMPLETE'}))
    return root


@pytest.mark.parametrize('kind', ['directory', 'zip'])
def test_mutation_during_page_build_cannot_report_unchanged(tmp_path, monkeypatch, kind):
    package = minimal_package(tmp_path)
    source = package
    if kind == 'zip':
        source = tmp_path / 'input.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            archive.write(package / 'manifest.json', 'package/manifest.json')
    original_hub = widgets._hub
    def mutate(model):
        if kind == 'directory':
            (package / 'manifest.json').write_text('{"strain_id":"CHANGED"}')
        else:
            replacement = tmp_path / 'replacement.zip'
            with zipfile.ZipFile(replacement, 'w') as archive:
                archive.writestr('package/manifest.json', '{"strain_id":"CHANGED"}')
            replacement.replace(source)
        return original_hub(model)
    monkeypatch.setattr(widgets, '_hub', mutate)
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        widgets.render_widget_deliverable(source, tmp_path / 'widgets')
    assert not (tmp_path / 'widgets' / 'WIDGET_MANIFEST.json').exists()


@pytest.mark.parametrize('kind', ['directory', 'zip'])
def test_unchanged_source_still_renders(tmp_path, kind):
    package = minimal_package(tmp_path)
    source = package
    if kind == 'zip':
        source = tmp_path / 'input.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            archive.write(package / 'manifest.json', 'package/manifest.json')
    result = widgets.render_widget_deliverable(source, tmp_path / 'widgets')
    assert result['status'] == 'PASS'
    assert result['source']['mutation_check'] == 'PASS'


@pytest.mark.parametrize('change', ['add_unused', 'remove_unused', 'edit_unused', 'delete_manifest'])
def test_directory_snapshot_checks_all_source_files(tmp_path, monkeypatch, change):
    package = minimal_package(tmp_path)
    extra = package / 'notes.txt'
    if change in {'remove_unused', 'edit_unused'}:
        extra.write_text('original')
    original_hub = widgets._hub
    def mutate(model):
        if change == 'delete_manifest':
            (package / 'manifest.json').unlink()
        elif change == 'remove_unused':
            extra.unlink()
        else:
            extra.write_text('changed')
        return original_hub(model)
    monkeypatch.setattr(widgets, '_hub', mutate)
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        widgets.render_widget_deliverable(package, tmp_path / 'widgets')
    assert not (tmp_path / 'widgets' / 'WIDGET_MANIFEST.json').exists()


def test_parent_input_keeps_sibling_output_outside_snapshot(tmp_path):
    minimal_package(tmp_path)
    result = widgets.render_widget_deliverable(tmp_path, tmp_path / 'widgets')
    assert result['status'] == 'PASS'
