"""Reviewed v2 mapping-key contract controls; external analysis is fabricated.

These tests do not import the installed GToTree tree or run native phylogeny.
The independent key lookup below models the named reviewed upstream owners.
"""
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from .test_m5_gtotree_runtime_admission import (
    synthetic, make_plan, planner, runner, rt, watch_owner, put, json_put,
)
from .test_m5_gtotree_governed_route import (
    _approve, _runner_args, _completed_native_route,
)


def native_v2_key_lookup(provided_paths):
    """Independent transcription of GenomeData.from_path/build_mapping_key_lookup.

    Source: reviewed v2 general.py353-373 and preflight_checks.py838-860.
    Do not call the bundle's mapping helper to construct the expected keys.
    """
    lookup = {}
    for provided in provided_paths:
        genome_id = Path(provided).name
        if genome_id.lower().endswith('.gz'):
            genome_id = genome_id[:-3]
        for extension in ('.gb', '.gbk', '.gbff', '.fasta', '.fna', '.fa', '.faa'):
            if genome_id.lower().endswith(extension):
                genome_id = genome_id[:-len(extension)]
                break
        lookup.setdefault(provided, genome_id)
        lookup.setdefault(genome_id, genome_id)
    return lookup


def test_reviewed_native_key_known_answers_reject_extension_basenames():
    provided = ['/synthetic/objects/query.sha.fna', '/synthetic/objects/out.sha.FNA.gz']
    lookup = native_v2_key_lookup(provided)
    assert lookup == {provided[0]: 'query.sha', 'query.sha': 'query.sha',
                      provided[1]: 'out.sha', 'out.sha': 'out.sha'}
    assert 'query.sha.fna' not in lookup and 'out.sha.FNA.gz' not in lookup


def test_v2_exact_provided_path_mapping_keeps_full_labels_and_v1_contract(tmp_path):
    entries = ['/synthetic/query.sha.fna', '/synthetic/out.sha.fna']
    labels = ['SYNTHETIC_QUERY.accession.1', 'SYNTHETIC_OUTGROUP.accession.2']
    mapping = put(tmp_path / 'mapping.tsv', ''.join(
        entry + '\t' + label + '\n' for entry, label in zip(entries, labels)))
    assert runner.mapped_tips(entries, mapping, version_text='GToTree v2.0.0') == labels
    with pytest.raises(ValueError, match='MAPPING_ROSTER'):
        runner.mapped_tips(entries, mapping, version_text='1.8.19')
    put(mapping, ''.join(Path(entry).name + '\t' + label + '\n'
                        for entry, label in zip(entries, labels)))
    assert runner.mapped_tips(entries, mapping) == labels
    with pytest.raises(ValueError, match='MAPPING_ROSTER'):
        runner.mapped_tips(entries, mapping, version_text='2.0.0')
    # Exact supplied spelling is the native key; resolution cannot supply an alias.
    put(mapping, '/synthetic/other/../query.sha.fna\t' + labels[0] + '\n' +
        entries[1] + '\t' + labels[1] + '\n')
    with pytest.raises(ValueError, match='MAPPING_ROSTER'):
        runner.mapped_tips(entries, mapping, version_text='2.0.0')


def test_actual_v2_planner_keys_are_accepted_by_independent_native_contract(synthetic, monkeypatch):
    root, proof, iq = make_plan(synthetic, monkeypatch)
    manifest = json.loads((root / 'RUN_MANIFEST.json').read_text())
    provided = (root / 'input_view/genomes_absolute.txt').read_text().splitlines()
    mapping = [line.split('\t') for line in (root / 'input_view/labels.tsv').read_text().splitlines()]
    expected = [row['object_path'] for row in manifest['assemblies']]
    assert provided == expected == [key for key, label in mapping]
    assert all(Path(key).is_absolute() for key in provided)
    lookup = native_v2_key_lookup(provided)
    assert all(key in lookup for key, label in mapping)
    assert all(Path(key).name not in lookup for key in provided)
    assert [label for key, label in mapping] == [row['label'] for row in manifest['assemblies']]
    assert all(rt.sha256(Path(row['object_path'])) == row['object_sha256']
               for row in manifest['assemblies'])
    assert len(synthetic.calls) == 1  # software proof only; no native analysis


@pytest.mark.parametrize('mutation,exit_code', [
    ('basename', 2), ('different_path', 2), ('relabel', 3), ('order', 3),
    ('duplicate_key', 2), ('input_content', 3), ('role_flag', 3),
])
def test_actual_v2_runner_refuses_drift_before_native_output(synthetic, monkeypatch, mutation, exit_code):
    root, proof, iq = make_plan(synthetic, monkeypatch)
    _approve(root)
    args = _runner_args(root, synthetic, iq, fresh_probe=synthetic.root / 'unused_fresh_probe')
    mapping = root / 'input_view/labels.tsv'
    lines = [line.split('\t') for line in mapping.read_text().splitlines()]
    if mutation == 'basename':
        lines = [[Path(key).name, label] for key, label in lines]
    elif mutation == 'different_path':
        lines[0][0] = str(synthetic.root / 'not_the_provided_input.fna')
    elif mutation == 'relabel':
        lines[0][1] = 'CHANGED_QUERY.1'
        args[args.index('--query-tips') + 1] = 'CHANGED_QUERY.1'
    elif mutation == 'order':
        lines.reverse()
    elif mutation == 'duplicate_key':
        lines[1][0] = lines[0][0]
    elif mutation == 'input_content':
        manifest = json.loads((root / 'RUN_MANIFEST.json').read_text())
        put(Path(manifest['assemblies'][0]['object_path']), '>CHANGED_SYNTHETIC\nACAC\n')
    else:
        args[args.index('--query-tips') + 1] = 'SYNTHETIC_REFERENCE'
    put(mapping, ''.join(key + '\t' + label + '\n' for key, label in lines))
    snapshot = {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}
    monkeypatch.setattr(watch_owner, 'run_watched', lambda *a, **kw:
                        pytest.fail('native child before mapping/input/role admission'))
    assert runner.main(args) == exit_code
    assert not (root / 'outputs/governed_run').exists()
    assert {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()} == snapshot


def test_governed_discovery_refuses_basename_even_with_rehashed_mapping_receipts(synthetic, monkeypatch):
    root, work, status = _completed_native_route(synthetic, monkeypatch)
    mapping = root / 'input_view/labels.tsv'
    lines = [line.split('\t') for line in mapping.read_text().splitlines()]
    put(mapping, ''.join(Path(key).name + '\t' + label + '\n' for key, label in lines))
    status['plan_binding']['mapping_sha256'] = rt.sha256(mapping)
    bindings_path = work / 'EXECUTION_BINDINGS.json'
    bindings = json.loads(bindings_path.read_text())
    bindings['files'][str(mapping)]['sha256'] = rt.sha256(mapping)
    json_put(bindings_path, bindings)
    status['execution_bindings_sha256'] = rt.sha256(bindings_path)
    json_put(work / 'run_status.json', status)
    snapshot = {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}
    result = planner.discover_governed_outputs(root,
        json.loads((root / 'RUN_MANIFEST.json').read_text()), len(lines))
    assert result['status'] == 'HOLD_GOVERNED_OUTPUT_BINDING'
    assert 'GOVERNED_MAPPING_DRIFT' in result['detail']
    assert {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()} == snapshot
