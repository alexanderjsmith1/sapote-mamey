from pathlib import Path
import importlib.util
import os
import sys
import pytest
ROOT=Path(os.environ.get("PANEL_REVIEW_BASE",Path(__file__).resolve().parents[1]))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module
panel=load('panel_empty_review','tools/build_phylo_panel.py')
plan=load('planner_empty_review','tools/plan_gtotree_iqtree.py')
@pytest.mark.parametrize('data',[b'>gap\n--..\n>real\nACGU\n',b'>real\nACGU\n>gap\n..--\n'])
def test_normalized_empty_record_matches_planner(data):
    parsed=panel.parse_sequence_bytes(data,'.fna')
    assert parsed==['ACGT']
    assert panel.assembly_content_sha256(parsed)==plan.normalized_assembly_sha256(data)

def test_all_normalized_empty_records_are_refused():
    data=b'>gap\n--..\n'
    with pytest.raises(ValueError):plan.normalized_assembly_sha256(data)
    with pytest.raises(panel.PanelError):panel.parse_sequence_bytes(data,'.fna')

def test_nonempty_normalized_records_keep_hash_contract():
    data=b'>second\nGG.CC\n>first\nacgu-acgu\n'
    parsed=panel.parse_sequence_bytes(data,'.fna')
    assert parsed==['GGCC','ACGTACGT']
    assert panel.assembly_content_sha256(parsed)==plan.normalized_assembly_sha256(data)
