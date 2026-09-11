from types import SimpleNamespace
import pytest
from mamey import widget_deliverable as w


@pytest.mark.parametrize('error',[ValueError('malformed input'),OSError('unreadable input'),RuntimeError('unexpected failure')])
def test_roster_failure_not_converted_to_absence(tmp_path,monkeypatch,error):
    def fail(*a,**k):raise error
    monkeypatch.setattr(w.roster_v2,'build_gene_roster',fail)
    with pytest.raises(ValueError,match='WIDGET_GENE_ROSTER_INVALID') as exc:
        w._safe_gene_roster(SimpleNamespace(kind='directory',_root=tmp_path,path=tmp_path),'TEST-01')
    assert exc.value.__cause__ is error


def test_valid_empty_roster_is_allowed(tmp_path,monkeypatch):
    empty={'strain':'TEST-01','channels_present':[],'bgcs':[]}
    monkeypatch.setattr(w.roster_v2,'build_gene_roster',lambda *a,**k:empty)
    assert w._safe_gene_roster(SimpleNamespace(kind='directory',_root=tmp_path,path=tmp_path),'TEST-01')==empty
