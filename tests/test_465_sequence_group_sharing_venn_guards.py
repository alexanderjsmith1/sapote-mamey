"""Generic synthetic provenance and admission regressions; no research data."""
import hashlib
import json
from pathlib import Path

import pytest
import importlib.util
_spec = importlib.util.spec_from_file_location("f01_test_helpers", Path(__file__).with_name("test_465_sequence_group_sharing_venn.py"))
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)
sgsv, MAP, COLS, FULL_TABLE, ARGS, rows, write = (
    getattr(_helpers, name) for name in ("sgsv", "MAP", "COLS", "FULL_TABLE", "ARGS", "rows", "write"))


@pytest.fixture
def case(tmp_path, monkeypatch):
    membership = write(tmp_path / 'membership.tsv', rows())
    mapping = tmp_path / 'map.tsv'
    mapping.write_text('source_group\tcollection\n' + ''.join(f'{k}\t{v}\n' for k, v in MAP.items()))
    check = tmp_path / 'check.tsv'
    check.write_text(FULL_TABLE)
    out = tmp_path / 'out'
    # New provenance/parser tests do not exercise or replace the rendering method.
    # The original module's end-to-end tests exercise the actual bundle renderer.
    monkeypatch.setattr(sgsv, 'draw', lambda result, stem: [])
    args = ['--membership', str(membership), '--collection-map', str(mapping), '--check-table', str(check), *ARGS, '--outdir', str(out)]
    return membership, mapping, check, out, args


def receipt(out):
    return json.loads(next(out.glob('*_receipt.json')).read_text())


def test_receipt_hashes_consumed_bytes_even_if_sources_change_during_draw(case, monkeypatch):
    m, mapping, check, out, args = case
    expected = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in
                [('membership_sha256', m), ('collection_map_sha256', mapping), ('check_table_sha256', check)]}
    def change_sources(result, stem):
        for path in (m, mapping, check):
            path.write_bytes(b'changed after parsing\n')
        return []
    monkeypatch.setattr(sgsv, 'draw', change_sources)
    assert sgsv.main(args) == 0
    rec = receipt(out)
    assert {key: rec[key] for key in expected} == expected
    assert rec['collection_mapping'] == MAP
    assert rec['comparable_isolates'] == 6


@pytest.mark.parametrize('which', [0, 1])
def test_parser_uses_same_snapshot_as_preflight_hash(case, monkeypatch, which):
    m, mapping, check, out, args = case
    target = (m, mapping)[which]
    before = target.read_bytes()
    real_read = Path.read_bytes
    reads = []
    def change_after_read(path):
        data = real_read(path)
        if path == target:
            reads.append(path)
            path.write_bytes(b'not the input we just read\n')
        return data
    monkeypatch.setattr(Path, 'read_bytes', change_after_read)
    assert sgsv.main(args) == 0
    rec = receipt(out)
    key = ('membership_sha256', 'collection_map_sha256')[which]
    assert rec[key] == hashlib.sha256(before).hexdigest()
    assert rec['comparable_isolates'] == 6
    assert len(reads) == 1


@pytest.mark.parametrize('which', [0, 1, 2])
@pytest.mark.parametrize('alias', ['direct', 'symlink_input', 'symlink_output', 'hardlink', 'parent_alias'])
def test_all_input_output_aliases_refused_before_writing(case, which, alias):
    m, mapping, check, out, args = case
    target = (m, mapping, check)[which]
    out.mkdir()
    planned = out / 'Streptomyces_16S_sharing_99pct_complete_linkage_floor500_plotted.tsv'
    original = target.read_bytes()
    flag = ('--membership', '--collection-map', '--check-table')[which]
    if alias in ('direct', 'symlink_input'):
        planned.write_bytes(original)
        new_input = planned
        if alias == 'symlink_input':
            new_input = out.parent / 'input_alias.tsv'
            new_input.symlink_to(planned)
        args[args.index(flag) + 1] = str(new_input)
    elif alias == 'parent_alias':
        planned.write_bytes(original)
        link = out.parent / 'parent_link'
        link.symlink_to(out, target_is_directory=True)
        args[args.index(flag) + 1] = str(link / planned.name)
    elif alias == 'hardlink':
        planned.hardlink_to(target)
    else:
        planned.symlink_to(target)
    with pytest.raises(SystemExit, match='also an input'):
        sgsv.main(args)
    assert target.read_bytes() == original
    assert planned.read_bytes() == original
    assert sorted(p.name for p in out.iterdir()) == [planned.name]


def test_dangling_output_symlink_is_not_followed(case):
    m, mapping, check, out, args = case
    out.mkdir()
    target = out.parent / 'should_not_be_created.tsv'
    link = out / 'Streptomyces_16S_sharing_99pct_complete_linkage_floor500_plotted.tsv'
    link.symlink_to(target)
    with pytest.raises(SystemExit, match='already exist'):
        sgsv.main(args)
    assert link.is_symlink() and not target.exists()


@pytest.mark.parametrize('field', ['isolate', 'group_id'])
@pytest.mark.parametrize('value', ['', ' ', ' A1', 'A1 ', 'A\n1', 'A\t1', 'A\x001'])
def test_invalid_identifiers_fail_closed(field, value):
    rr = [dict(zip(COLS, r)) for r in rows()]
    rr[0][field] = value
    with pytest.raises(SystemExit, match='blank isolate or group_id|invalid'):
        sgsv.count_regions(rr, MAP)


@pytest.mark.parametrize('which', [0, 1, 2])
def test_duplicate_column_keys_are_rejected(case, which):
    m, mapping, check, out, args = case
    path = (m, mapping, check)[which]
    lines = path.read_text().splitlines()
    first = lines[0].split('\t')[0]
    lines[0] += '\t' + first
    for i in range(1, len(lines)):
        lines[i] += '\t' + lines[i].split('\t')[0]
    path.write_text('\n'.join(lines) + '\n')
    with pytest.raises(SystemExit, match='duplicate column keys'):
        sgsv.main(args)
    assert not out.exists()


@pytest.mark.parametrize('which', [0, 1, 2])
@pytest.mark.parametrize('defect', ['missing_header', 'short_row', 'long_row'])
def test_incomplete_table_schema_stops_before_outputs(case, which, defect):
    m, mapping, check, out, args = case
    path = (m, mapping, check)[which]
    lines = path.read_text().splitlines()
    if defect == 'missing_header':
        lines[0] = lines[0].replace(lines[0].split('\t')[0], 'unexpected', 1)
    elif defect == 'short_row':
        lines[1] = lines[1].rsplit('\t', 1)[0]
    else:
        lines[1] += '\textra'
    path.write_text('\n'.join(lines) + '\n')
    with pytest.raises(SystemExit, match='required columns|wrong number of fields'):
        sgsv.main(args)
    assert not out.exists()


@pytest.mark.parametrize('combination', ['Set A | Set A', 'Set A | Set D', ''])
def test_invalid_check_region_keys_are_refused(case, combination):
    m, mapping, check, out, args = case
    check.write_text(FULL_TABLE.replace('Set A\t1\t1', combination + '\t1\t1', 1))
    with pytest.raises(SystemExit, match='collection'):
        sgsv.main(args)
    assert not out.exists()


@pytest.mark.parametrize('value', ['no', '1.5', '-1'])
def test_invalid_check_counts_are_refused(case, value):
    m, mapping, check, out, args = case
    check.write_text(FULL_TABLE.replace('Set A\t1\t1', 'Set A\t' + value + '\t1', 1))
    with pytest.raises(SystemExit, match='nonnegative integers'):
        sgsv.main(args)
    assert not out.exists()


@pytest.mark.parametrize('linkage', ['complete.v2', 'complete/v2', '../complete', 'complete\\v2'])
def test_filename_components_are_not_suffixes_or_paths(case, linkage):
    m, mapping, check, out, args = case
    args += ['--linkage', linkage]
    if linkage == 'complete.v2':
        sgsv.main(args)
        assert next(out.glob('*_receipt.json')).name == 'Streptomyces_16S_sharing_99pct_completepv2_linkage_floor500_receipt.json'
    else:
        with pytest.raises(SystemExit, match='single path components'):
            sgsv.main(args)
        assert not out.exists()
