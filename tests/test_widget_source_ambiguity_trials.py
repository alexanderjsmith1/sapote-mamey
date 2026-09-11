from pathlib import Path
import zipfile
import pytest
from mamey.widget_deliverable import PackageSource


@pytest.mark.parametrize('archive',[False,True])
def test_ambiguous_evidence_refused(tmp_path,archive):
    names=['package/TEST_2_inventory.csv','backup/TEST_2_inventory.csv']
    if archive:
        path=tmp_path/'input.zip'
        with zipfile.ZipFile(path,'w') as z:
            for name in names:z.writestr(name,'BGC_ID\nBGC001\n')
    else:
        path=tmp_path/'input';path.mkdir()
        for name in names:
            p=path/name;p.parent.mkdir();p.write_text('BGC_ID\nBGC001\n')
    source=PackageSource(path)
    try:
        with pytest.raises(ValueError,match='WIDGET_SOURCE_AMBIGUOUS'):source.csv('_2_inventory.csv')
    finally:source.close()


def test_unique_evidence_and_absent_optional_preserved(tmp_path):
    (tmp_path/'TEST_2_inventory.csv').write_text('BGC_ID\nBGC001\n')
    source=PackageSource(tmp_path)
    try:
        assert len(source.csv('_2_inventory.csv')[0])==1
        assert source.locate('_optional.csv') is None
    finally:source.close()
