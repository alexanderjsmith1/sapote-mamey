"""Synthetic CSV admission fixtures; no scientific claim-policy changes."""
import csv
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/claim_safety_linter.py'
spec=importlib.util.spec_from_file_location('claim_safety_linter',TARGET)
mod=importlib.util.module_from_spec(spec);sys.modules['claim_safety_linter']=mod;spec.loader.exec_module(mod)
BAD=['','unrelated\n','unrelated\nvalue\n','KCB_top,KCB_top\nREF | examplecompound | rank1,\n','KCB_top,other\nREF | examplecompound | rank1\n','KCB_top\nREF | examplecompound | rank1,extra\n','KCB_top,other\nREF | examplecompound | rank1,valid\nno_columns\n']


def fixture(tmp_path,contents):
    package=tmp_path/'package';package.mkdir();path=package/'SYNTHETIC_4_triage_board.csv';path.write_text(contents);return package,path


@pytest.mark.parametrize('contents',BAD)
def test_malformed_schema_preserves_unavailable_state(tmp_path,contents):
    package,path=fixture(tmp_path,contents);before=path.read_bytes()
    names=mod.derive_compound_names_from_package(package)
    assert getattr(names,'load_error',None)
    assert names.load_error['error_type']=='Error'
    assert names.load_error['path']==str(path)
    assert bool(names) and len(names)==0
    plain=mod.lint_claim_safety('Ordinary engineering note.',compound_names=names)
    assert any('compound-name evidence unreadable' in item for item in plain)
    report=mod.lint_claim_safety_report('Ordinary engineering note.',compound_names=names)
    assert len(report)==1
    assert report[0]['violation_type']=='compound_name_evidence_unreadable'
    assert report[0]['severity']=='HIGH'
    assert path.read_bytes()==before


@pytest.mark.parametrize('contents',['KCB_top\n','KCB_top,other\n,valid\n','KCB_top\nraw unresolved text\n'])
def test_valid_empty_extraction_retains_existing_empty_set(tmp_path,contents):
    package,_=fixture(tmp_path,contents);names=mod.derive_compound_names_from_package(package)
    assert names==set() and not getattr(names,'load_error',None)


def test_valid_quoted_product_text_preserved(tmp_path):
    package=tmp_path/'package';package.mkdir();path=package/'SYNTHETIC_4_triage_board.csv'
    with path.open('w',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(['KCB_top','other']);writer.writerow(['REF | example, product | rank1','valid'])
    assert mod.derive_compound_names_from_package(package)=={'example, product'}


def test_missing_board_existing_fallback_unchanged(tmp_path):
    assert mod.derive_compound_names_from_package(tmp_path)==set()


@pytest.mark.parametrize('mode,expected',[('fail',1),('warn',0)])
def test_existing_cli_reports_unavailable_evidence(tmp_path,capsys,mode,expected):
    from mamey import cli
    package,_=fixture(tmp_path,'unrelated\nvalue\n');text=tmp_path/'report.md';text.write_text('Ordinary engineering note.\n')
    args=SimpleNamespace(path=str(text),package=str(package),compound_names=None,mode=mode,json=True,report=None)
    assert cli.claim_safety_command(args)==expected
    captured=capsys.readouterr()
    assert 'compound_name_evidence_unreadable' in captured.out
    assert '"clean": false' in captured.out
