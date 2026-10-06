"""Synthetic archive names/bytes only; no BiG-SCAPE execution."""
import hashlib,importlib.util,json,zipfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bigscape_bound',ROOT/'deliverable_tools/bigscape_run.py');bs=importlib.util.module_from_spec(spec);spec.loader.exec_module(bs)
from mamey.postseal_output import package_binding,resolve_source_archive


def fixture(tmp_path,members=('results/ctg.region001.gbk','results/ctg.region002.gbk')):
    p=tmp_path/'SYN-1'/'package';p.mkdir(parents=True);archive=p.parent/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for member in members:z.writestr(member,b'synthetic region fixture')
    (p/'manifest.json').write_text(json.dumps({'strain_id':'SYN-1','input_zip':'source.zip','input_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
    return p,archive


def test_sealed_package_stages_bound_original_zip_and_preserves_package(tmp_path):
    p,archive=fixture(tmp_path);before=package_binding(p)
    r=bs.run_pipeline(package=str(p),dry_run=True,bigscape_bin='not-run',pfam='not-read')
    assert r['n_gbks']==2 and r['dry_run']
    receipt=json.loads(Path(r['source_receipt']).read_text());assert receipt['sources'][0]['sha256']==hashlib.sha256(archive.read_bytes()).hexdigest()
    assert len(receipt['sources'][0]['members'])==2 and package_binding(p)==before

@pytest.mark.parametrize('kind',['missing','mismatch','ambiguous','multiple_roots','duplicate_members','no_regions'])
def test_bad_source_is_refused_before_execution(tmp_path,kind,monkeypatch):
    members=('a/a.region001.gbk','b/b.region002.gbk') if kind=='multiple_roots' else (('a.region001.gbk','a.region001.gbk') if kind=='duplicate_members' else (('whole.gbk',) if kind=='no_regions' else ('a.region001.gbk',)))
    p,a=fixture(tmp_path,members)
    if kind=='missing':a.unlink()
    if kind=='mismatch':a.write_bytes(b'changed')
    if kind=='ambiguous':(p/'source.zip').write_bytes(a.read_bytes())
    monkeypatch.setattr(bs.subprocess,'run',lambda *a,**kw:pytest.fail('engine must not run'))
    with pytest.raises(ValueError,match='SOURCE_ARCHIVE'):bs.run_pipeline(package=str(p),dry_run=True,out=str(tmp_path/'out'))


def test_renamed_explicit_archive_still_requires_exact_digest(tmp_path):
    p,a=fixture(tmp_path);renamed=tmp_path/'moved.zip';a.rename(renamed)
    path,binding=resolve_source_archive(p,renamed);assert path==renamed and binding['state']=='ARCHIVE_HASH_VERIFIED'
    renamed.write_bytes(b'wrong')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):resolve_source_archive(p,renamed)


def test_sealed_package_zip_uses_manifest_bound_source(tmp_path):
    p,a=fixture(tmp_path);sealed=tmp_path/'package.zip'
    with zipfile.ZipFile(sealed,'w') as z:z.write(p/'manifest.json','package/manifest.json')
    r=bs.run_pipeline(package=str(sealed),source_zip=str(a),out=str(tmp_path/'out'),dry_run=True)
    receipt=json.loads(Path(r['source_receipt']).read_text());assert r['n_gbks']==2 and receipt['sources'][0]['manifest_member']=='package/manifest.json'


def test_explicit_outputs_cannot_mutate_source_package(tmp_path):
    p,a=fixture(tmp_path)
    for key in ['out','work_dir','widgets_out']:
        with pytest.raises(ValueError,match='INSIDE_PACKAGE'):bs.run_pipeline(package=str(p),dry_run=True,**{key:str(p/'inside')})
