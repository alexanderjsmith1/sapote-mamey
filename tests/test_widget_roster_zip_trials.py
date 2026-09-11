import zipfile,json
import pytest
from mamey.widget_deliverable import PackageSource,_safe_gene_roster


def fixture(tmp_path):
    p=tmp_path/'source';p.mkdir();(p/'manifest.json').write_text(json.dumps({'strain_id':'TEST-01'}))
    (p/'TEST-01_2_inventory.csv').write_text('BGC_ID,Contig,Node_ID,antiSMASH_Region\nBGC001,NODE_1_length_100_cov_2.5,NODE_1_length_100_cov_2,region001\n')
    (p/'locus_maps').mkdir();(p/'locus_maps/BGC001_fixture_locus_data.csv').write_text('locus_tag,start,end,length_aa,strand,role\ngene_1,1,90,30,+,biosynthetic\n')
    return p


@pytest.mark.parametrize('prefix',['','package/'])
def test_zip_directory_roster_parity(tmp_path,prefix):
    root=fixture(tmp_path);archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in root.rglob('*'):
            if p.is_file():z.write(p,prefix+str(p.relative_to(root)))
    results=[]
    for p in [root,archive]:
        source=PackageSource(p)
        try:results.append(_safe_gene_roster(source,'TEST-01'))
        finally:source.close()
    assert len(results[0]['bgcs'])==1
    assert results[0]==results[1]


def test_unsafe_archive_member_refused(tmp_path):
    root=fixture(tmp_path);archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.write(root/'manifest.json','manifest.json');z.writestr('../outside.csv','x')
    source=PackageSource(archive)
    try:
        with pytest.raises(ValueError):_safe_gene_roster(source,'TEST-01')
    finally:source.close()
    assert not (tmp_path/'outside.csv').exists()


def test_populated_zip_full_widget(tmp_path):
    from mamey.widget_deliverable import render_widget_deliverable
    root=fixture(tmp_path);archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in root.rglob('*'):
            if p.is_file():z.write(p,'package/'+str(p.relative_to(root)))
    out=tmp_path/'output';render_widget_deliverable(archive,out)
    data=json.loads((out/'widget_data.json').read_text())
    assert data['gene_roster']['bgcs'][0]['full_identity']=='TEST-01 / NODE_1_length_100_cov_2.5 / region001 / BGC001'


@pytest.mark.parametrize('fail',[False,True])
def test_temporary_roster_cleanup(tmp_path,monkeypatch,fail):
    from mamey import widget_deliverable as w
    root=fixture(tmp_path);archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in root.rglob('*'):
            if p.is_file():z.write(p,str(p.relative_to(root)))
    seen=[]
    def build(path,**kw):
        from pathlib import Path
        seen.append(Path(path));assert seen[-1].exists()
        if fail:raise RuntimeError('injected')
        return {'strain':'TEST-01','channels_present':[],'bgcs':[]}
    monkeypatch.setattr(w.roster_v2,'build_gene_roster',build)
    source=PackageSource(archive)
    try:
        if fail:
            with pytest.raises(ValueError):_safe_gene_roster(source,'TEST-01')
        else:_safe_gene_roster(source,'TEST-01')
    finally:source.close()
    assert seen and not seen[0].exists()


@pytest.mark.parametrize('kind',['symlink','duplicate'])
def test_symlink_and_duplicate_zip_members_refused(tmp_path,kind):
    import stat
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('manifest.json','{}')
        if kind=='symlink':
            info=zipfile.ZipInfo('link.csv');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'../outside.csv')
        else:
            z.writestr('data.csv','one')
            with pytest.warns(UserWarning):z.writestr('data.csv','two')
    source=PackageSource(archive)
    try:
        with pytest.raises(ValueError):_safe_gene_roster(source,'TEST-01')
    finally:source.close()
