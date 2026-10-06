"""Synthetic input transport/admission tests; extraction only, no analysis engines."""
import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'tools/protein_pcoa_ordinate.py'

def module(monkeypatch):
    spec=importlib.util.spec_from_file_location('protein_admission_447',SCRIPT)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    # Parser stub limits this fixture to transport/identity. Real parser smoke control below.
    def parse(text):
        if not text.startswith('record='): return []
        ident, *loci=text.splitlines()
        return [SimpleNamespace(id=ident.split('=',1)[1],features=[
          SimpleNamespace(type='CDS', location=f'{i}:{i+1}', qualifiers=dict(locus_tag=[locus],translation=['SYNTHETIC']))
          for i,locus in enumerate(loci)])]
    monkeypatch.setattr(mod,'parse_genbank_text',parse)
    return mod


def run(mod, kit, inputs, assembly=None):
    return mod.cmd_extract(argparse.Namespace(kit=str(kit),input=inputs,assembly_table=assembly,genus_table=None,cohort_table=None))


def material(tmp):
    folder=tmp/'extracted';folder.mkdir()
    raw=b'record=synthetic_contig\ngene_a\ngene_b\n'
    (folder/'sample.region001.gbk').write_bytes(raw)
    (folder/'whole_genome.gbk').write_bytes(raw)
    archive=tmp/'sample.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('sample.region001.gbk',raw);z.writestr('whole_genome.gbk',raw)
    return folder,archive


def test_folder_zip_and_mixed_duplicate_population_match(tmp_path,monkeypatch):
    mod=module(monkeypatch); folder,archive=material(tmp_path)
    for i,inputs in enumerate(([f'isolate={folder}'],[f'isolate={archive}'],[f'isolate={folder}',f'isolate={archive}'])):
        kit=tmp_path/f'kit{i}'
        assert run(mod,kit,inputs)['cds_by_source']=={'isolate':2}
        receipt=json.loads((kit/'EXTRACT_RECEIPT.json').read_text())
        assert any(r['status']=='REJECTED_FILE' for r in receipt['admission'])
        if i==2: assert any(r['status']=='DUPLICATE_SOURCE_MATERIAL' for r in receipt['admission'])
        meta=mod.read_tsv(kit/'REGION_CDS_META.tsv')
        assert len({r['locus_identity'] for r in meta})==2
        assert all(r['assembly_binding']=='SOURCE_RECORD_ID' for r in meta)


def test_directory_symlink_traversal_loops_and_file_aliases(tmp_path,monkeypatch,caplog):
    mod=module(monkeypatch);folder,_=material(tmp_path)
    view=tmp_path/'view';view.mkdir();(view/'linked').symlink_to(folder,target_is_directory=True)
    (folder/'loop').symlink_to(view,target_is_directory=True)
    (view/'sample.region001.gbk').symlink_to(folder/'sample.region001.gbk')
    assert run(mod,tmp_path/'kit',[f'isolate={view}'])['cds_by_source']=={'isolate':2}
    receipt=json.loads((tmp_path/'kit/EXTRACT_RECEIPT.json').read_text())
    assert any(r['status']=='DUPLICATE_DIRECTORY' for r in receipt['admission'])
    assert any(r['status']=='DUPLICATE_FILE_ALIAS' for r in receipt['admission'])
    assert 'symlinked folder' in caplog.text and 'linked' in caplog.text


def test_explicit_distinct_assemblies_preserve_identical_material(tmp_path,monkeypatch):
    mod=module(monkeypatch);folder,archive=material(tmp_path)
    table=tmp_path/'assemblies.tsv';table.write_text(f'input\tassembly\n{folder}\tsynthetic_A\n{archive}\tsynthetic_B\n')
    assert run(mod,tmp_path/'kit',[f'isolate={folder}',f'isolate={archive}'],str(table))['cds_by_source']=={'isolate':4}
    meta=mod.read_tsv(tmp_path/'kit/REGION_CDS_META.tsv')
    assert {r['assembly'] for r in meta}=={'synthetic_A','synthetic_B'}
    assert len({r['locus_identity'] for r in meta})==4


def test_conflicting_bound_region_refuses_before_output(tmp_path,monkeypatch):
    mod=module(monkeypatch);folder,archive=material(tmp_path)
    (folder/'sample.region001.gbk').write_text('record=synthetic_contig\nDIFFERENT\n')
    with pytest.raises(mod.OrdinateRefusal,match='CONFLICTING_REGION_IDENTITY'):
        run(mod,tmp_path/'kit',[f'isolate={folder}',f'isolate={archive}'])
    assert not (tmp_path/'kit/REGION_CDS.faa').exists()


def test_unparseable_admitted_region_is_not_silently_empty(tmp_path,monkeypatch):
    mod=module(monkeypatch);folder,_=material(tmp_path)
    (folder/'sample.region001.gbk').write_text('bad fixture')
    with pytest.raises(mod.OrdinateRefusal,match='REGION_PARSE_UNVERIFIED'):
        run(mod,tmp_path/'kit',[f'isolate={folder}'])


def test_traversal_error_fails_closed(tmp_path,monkeypatch):
    mod=module(monkeypatch);tmp_path.mkdir(exist_ok=True)
    def walk(*args,**kwargs):
        kwargs['onerror'](OSError('synthetic unreadable directory'))
        yield
    monkeypatch.setattr(mod.os,'walk',walk)
    with pytest.raises(mod.OrdinateRefusal,match='INPUT_TRAVERSAL_FAILED'):
        list(mod.region_texts(tmp_path))


def test_region_filename_policy_and_real_parser_empty_control(tmp_path):
    spec=importlib.util.spec_from_file_location('protein_real_control_447',SCRIPT)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod._admitted_gbk('x.region001.gbk') and mod._admitted_gbk('BGC0000001.gbk')
    assert not mod._admitted_gbk('complete_genome.gbk')
    assert list(mod.parse_genbank_text('not genbank'))==[]


def test_dangling_alias_and_repeated_zip_member_are_explicit_holds(tmp_path,monkeypatch):
    mod=module(monkeypatch);folder,_=material(tmp_path)
    (folder/'missing_directory').symlink_to(tmp_path/'absent',target_is_directory=True)
    with pytest.raises(mod.OrdinateRefusal,match='BROKEN_INPUT_ALIAS'):
        run(mod,tmp_path/'kit',[f'isolate={folder}'])
    archive=tmp_path/'repeated.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('sample.region001.gbk','record=synthetic\nlocus_a\n')
        with pytest.warns(UserWarning,match='Duplicate name'):
            z.writestr('sample.region001.gbk','record=synthetic\nlocus_b\n')
    with pytest.raises(mod.OrdinateRefusal,match='AMBIGUOUS_ZIP_MEMBER'):
        run(mod,tmp_path/'kit2',[f'isolate={archive}'])
