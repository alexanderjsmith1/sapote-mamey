"""Actual receipt producer -> Figure Factory tree admission, using existing synthetic fixture."""
import hashlib
import json
from pathlib import Path

import pytest
from mamey import phylogeny_figure_factory as factory
from mamey.phylo_evidence import produce_phylo_evidence_receipt, PhyloEvidenceError
from .test_phylo_evidence_producer_v97406 import _fixture


def descriptor(path, root):
    return {'logical_locator': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def setup_evidence(tmp_path, support='90/99'):
    values = _fixture(tmp_path)
    values['tree'].write_text(values['tree'].read_text().replace('90/99', support))
    before = values['tree'].read_bytes()
    receipt = produce_phylo_evidence_receipt(**values)
    root = values['tree'].parent
    payload = json.loads(receipt.read_text())
    roster = root / 'roster.tsv'
    roster.write_text('tree_tip\n' + '\n'.join(row['tree_tip'] for row in payload['package_tree_join']['rows']) + '\n')
    obj = {key: descriptor(path, root) for key, path in {
        'tree': values['tree'], 'alignment': values['alignment'], 'tool_receipt': values['iqtree_receipt'],
        'signoff_receipt': receipt, 'roster': roster}.items()}
    obj.update(tool_name='IQ-TREE', tool_version='3.1.2', model='LG+G', seed='12345', outgroup_tip=values['outgroup_tip'])
    obj['tool_sha256'] = factory.sha256_text(obj['tool_name'] + '\n' + obj['tool_version'])
    for key in ('model', 'seed', 'outgroup_tip'):
        obj[{'outgroup_tip': 'outgroup_sha256'}.get(key, key + '_sha256')] = factory.sha256_text(obj[key])
    return root, values, receipt, obj, before


@pytest.mark.parametrize('support,expected_label', [('90/99', 'SH-aLRT/UFBoot'), ('99', 'single_support')])
def test_native_support_survives_real_producer_and_factory_admission(tmp_path, support, expected_label):
    root, values, receipt, obj, before = setup_evidence(tmp_path, support)
    result = factory.tree(root, obj, 'native')
    assert result['signoff']['support']['label'] == expected_label
    assert len(result['tips']) == 3
    assert values['tree'].read_bytes() == before
    assert obj['tree']['sha256'] == result['signoff']['tree_sha256']
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'schema_version': factory.SCHEMA, 'figure_kind': factory.EVIDENCE_WIDGET_KIND,
        'external_data_root': str(root), 'output_dir': str(tmp_path / 'widget'),
        'figure_id': 'SYNTHETICPHYLO', 'tree_evidence': obj}))
    output_receipt = factory.build(config)
    assert output_receipt['figure_kind'] == factory.EVIDENCE_WIDGET_KIND
    assert (tmp_path / 'widget' / 'SYNTHETICPHYLO_phylogeny_evidence_widget.html').is_file()
    assert values['tree'].read_bytes() == before
    parsed = factory.overlay().parse_newick(before.decode())
    assert parsed.children[0].support == support
    assert parsed.children[0].length == 0.2
    assert [node.length for node in parsed.leaves()] == [0.1, 0.1, 0.3]


def test_missing_support_still_refused_by_actual_producer(tmp_path):
    values = _fixture(tmp_path)
    values['tree'].write_text(values['tree'].read_text().replace('90/99', ''))
    with pytest.raises(PhyloEvidenceError, match='PHYLO_SUPPORT_MISSING'):
        produce_phylo_evidence_receipt(**values)


@pytest.mark.parametrize('replacement', ['weak', '90/99/100', 'NaN', '90[annotation]'])
def test_rehashed_unsupported_support_is_not_admitted(tmp_path, replacement):
    root, values, receipt, obj, before = setup_evidence(tmp_path)
    values['tree'].write_text(before.decode().replace('90/99', replacement))
    payload = json.loads(receipt.read_text())
    payload['tree_sha256'] = hashlib.sha256(values['tree'].read_bytes()).hexdigest()
    receipt.write_text(json.dumps(payload))
    obj['tree'] = descriptor(values['tree'], root)
    obj['signoff_receipt'] = descriptor(receipt, root)
    with pytest.raises(factory.PhylogenyFigureHold, match='PHYLO_TREE_INVALID'):
        factory.tree(root, obj, 'corrupt')


def test_changed_tree_without_matching_signoff_refuses(tmp_path):
    root, values, receipt, obj, before = setup_evidence(tmp_path)
    values['tree'].write_text(before.decode().replace('90/99', '91/99'))
    obj['tree'] = descriptor(values['tree'], root)
    with pytest.raises(factory.PhylogenyFigureHold, match='PHYLO_SIGNOFF_MISMATCH'):
        factory.tree(root, obj, 'changed')


def test_rehashed_negative_branch_length_still_refuses(tmp_path):
    root, values, receipt, obj, before = setup_evidence(tmp_path)
    values['tree'].write_text(before.decode().replace(':0.2', ':-0.2'))
    payload = json.loads(receipt.read_text())
    payload['tree_sha256'] = hashlib.sha256(values['tree'].read_bytes()).hexdigest()
    receipt.write_text(json.dumps(payload))
    obj['tree'] = descriptor(values['tree'], root)
    obj['signoff_receipt'] = descriptor(receipt, root)
    with pytest.raises(factory.PhylogenyFigureHold, match='PHYLO_TREE_INVALID'):
        factory.tree(root, obj, 'negative_length')
