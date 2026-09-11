"""Present malformed evidence must not become an empty or apparently valid layer."""
import json
import pytest
from mamey.widget_deliverable import PackageSource, render_widget_deliverable


@pytest.mark.parametrize('name', ['gate_validation.json', 'claim_safety_status.json', 'package_status.json', 'TEST_1_intake.json'])
@pytest.mark.parametrize('payload', ['{broken', '[]', 'null'])
def test_present_invalid_json_refuses(tmp_path, name, payload):
    package = tmp_path / 'package'; package.mkdir()
    (package / 'manifest.json').write_text(json.dumps({'strain_id':'TEST','package_status':'MAMEY_COMPLETE'}))
    (package / name).write_text(payload)
    with pytest.raises(ValueError, match='JSON'):
        render_widget_deliverable(package, tmp_path / 'out')
    assert not (tmp_path / 'out/WIDGET_MANIFEST.json').exists()


def test_absent_optional_json_remains_missing(tmp_path):
    (tmp_path / 'manifest.json').write_text('{"strain_id":"TEST"}')
    source = PackageSource(tmp_path)
    try:
        assert source.json('gate_validation.json') == ({}, None)
    finally:
        source.close()


@pytest.mark.parametrize('many', [False, True])
@pytest.mark.parametrize('payload', [b'gene,gene\na,b\n', b'gene,score\na,1,extra\n', b'gene,score\na\n', b'gene,score\n"unterminated,1\n', b'gene,score\n\xff,1\n'])
def test_malformed_csv_refuses_for_single_and_channel_readers(tmp_path, many, payload):
    folder = tmp_path / 'blastp_nr' if many else tmp_path
    folder.mkdir(exist_ok=True)
    (folder / 'TEST_table.csv').write_bytes(payload)
    source = PackageSource(tmp_path)
    try:
        with pytest.raises(ValueError, match='CSV'):
            source.csv_many('blastp_nr') if many else source.csv('_table.csv')
    finally:
        source.close()


@pytest.mark.parametrize('many', [False, True])
def test_quoted_newline_and_explicit_empty_cell_are_valid(tmp_path, many):
    folder = tmp_path / 'blastp_nr' if many else tmp_path; folder.mkdir(exist_ok=True)
    (folder / 'TEST_table.csv').write_text('gene,note\n"gene\nline",\n')
    source = PackageSource(tmp_path)
    try:
        rows = source.csv_many('blastp_nr')[0][0] if many else source.csv('_table.csv')[0]
        assert rows == [{'gene':'gene\nline','note':''}]
    finally:
        source.close()
