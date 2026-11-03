"""Schema parity only; synthetic rows do not establish scientific CNBU validity."""
import csv
import importlib.util
import os
from pathlib import Path
import pytest

TARGET=Path(__file__).resolve().parents[1]/'mamey/cnbu.py'
spec=importlib.util.spec_from_file_location('cnbu_under_test',TARGET)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def inventory(tmp_path, rows, fields=None):
    path=tmp_path/'synthetic_2_inventory.csv'
    fields=fields or list(rows[0])
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)
    return path


@pytest.mark.parametrize('products,length,kwargs', [('NRPS','60',{}),('terpene','30',{}),('other','10',{}),('custom','10',{'priors':{'custom':5},'cap':1.1}),('nrps;terpene','30',{}),('terpene','0',{})])
def test_native_inventory_equals_direct_api(tmp_path,products,length,kwargs):
    native=[{'BGC_ID':'SYNTHETIC_001','Length_kb':length,'Products':products}]
    expected=mod.compute_cnbu([{'bgc_id':'SYNTHETIC_001','length_kb':length,'products':products}],**kwargs)
    assert mod.cnbu_from_inventory_csv(str(inventory(tmp_path,native)),**kwargs)==expected


def test_mixed_rows_and_unknown_preserve_each_identity(tmp_path):
    native=[{'BGC_ID':'SYNTHETIC_001','Length_kb':'60','Products':'NRPS'},{'BGC_ID':'SYNTHETIC_002','Length_kb':'10','Products':'unlisted'}]
    expected=mod.compute_cnbu([{'bgc_id':r['BGC_ID'],'length_kb':r['Length_kb'],'products':r['Products']} for r in native])
    actual=mod.cnbu_from_inventory_csv(str(inventory(tmp_path,native)))
    assert actual==expected
    assert actual['n_known']==actual['n_unknown']==1


@pytest.mark.parametrize('native,api,left,right',[('Length_kb','length_kb','60','15'),('Products','products','NRPS','terpene'),('Length_kb','length_kb','60',''),('Products','products','NRPS','')])
def test_conflicting_headers_refuse_before_compute(tmp_path,monkeypatch,native,api,left,right):
    row={'BGC_ID':'SYNTHETIC_001','length_kb':'15','products':'terpene',native:left,api:right}
    called=[]
    monkeypatch.setattr(mod,'compute_cnbu',lambda *a,**k:called.append(a))
    with pytest.raises(ValueError,match='CNBU_INVENTORY_FIELD_CONFLICT'):
        mod.cnbu_from_inventory_csv(str(inventory(tmp_path,[row])))
    assert called==[]


def test_identical_dual_fields_accepted(tmp_path):
    row={'BGC_ID':'SYNTHETIC_001','length_kb':'60','products':'NRPS','Length_kb':'60','Products':'NRPS'}
    assert mod.cnbu_from_inventory_csv(str(inventory(tmp_path,[row])))==mod.compute_cnbu([row])


def test_lowercase_only_compatibility(tmp_path):
    rows=[{'bgc_id':'SYNTHETIC_001','length_kb':'15','products':'terpene'}]
    assert mod.cnbu_from_inventory_csv(str(inventory(tmp_path,rows)))==mod.compute_cnbu(rows)


def test_empty_native_inventory_is_empty(tmp_path):
    path=inventory(tmp_path,[],['BGC_ID','Length_kb','Products'])
    assert mod.cnbu_from_inventory_csv(str(path))==mod.compute_cnbu([])
