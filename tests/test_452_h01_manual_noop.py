"""Duplicate-only manual import preserves bytes while fresh/missing-sheet work saves."""
import csv
import hashlib
import openpyxl
from mamey import blastp_ingest as ingest
from mamey.master_workbook import CANONICAL_V1_HEADERS


def fixture(tmp_path, *, missing_sheet=False, empty=False):
    master=tmp_path/'master.xlsx'
    wb=openpyxl.Workbook()
    if not missing_sheet:
        ws=wb.active;ws.title='B5_BLASTp_Hits'
        ws.append(CANONICAL_V1_HEADERS['B5_BLASTp_Hits'])
    wb.save(master)
    source=tmp_path/'hits.csv'
    with source.open('w',newline='') as f:
        if not empty:
            csv.writer(f).writerow(['SYN-H01M|BGC001|gene=synthetic_1|aa=30','WP_SYN.1',82,30,0,0,1,30,1,30,'1e-9',100])
    return master,source


def test_duplicate_only_import_does_not_publish_workbook(tmp_path,monkeypatch):
    master,source=fixture(tmp_path)
    assert ingest.ingest_blastp(master,'SYN-H01M',source)['rows']==1
    before=hashlib.sha256(master.read_bytes()).hexdigest()
    def refuse(*args,**kwargs):
        raise AssertionError('DUPLICATE_ONLY_WORKBOOK_REWRITE')
    monkeypatch.setattr(ingest,'_save_wb_safely',refuse)
    result=ingest.ingest_blastp(master,'SYN-H01M',source)
    assert result['rows']==0 and result['duplicates_skipped']==1
    assert hashlib.sha256(master.read_bytes()).hexdigest()==before


def test_fresh_rows_still_publish_workbook(tmp_path,monkeypatch):
    master,source=fixture(tmp_path)
    calls=[];save=ingest._save_wb_safely
    def record(*args,**kwargs):
        calls.append(args[1]);return save(*args,**kwargs)
    monkeypatch.setattr(ingest,'_save_wb_safely',record)
    assert ingest.ingest_blastp(master,'SYN-H01M',source)['rows']==1
    assert calls==[master]


def test_missing_b5_sheet_is_created_even_with_no_hits(tmp_path):
    master,source=fixture(tmp_path,missing_sheet=True,empty=True)
    assert ingest.ingest_blastp(master,'SYN-H01M',source)['rows']==0
    wb=openpyxl.load_workbook(master)
    assert 'B5_BLASTp_Hits' in wb.sheetnames
