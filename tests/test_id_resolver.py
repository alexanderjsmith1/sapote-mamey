import importlib
idr = importlib.import_module("mamey.id_resolver")
BANK = [{"sid": "AS-XXX", "organism": "Streptomyces sp.", "bgc_id": "BGC04", "contig": "NODE_12",
         "region": "region004", "source_kcb_file": "NODE_12_clusterblast.txt"}]

def test_resolver_columns():
    assert idr.COLUMNS == ["BGC_ID", "bgc_uid", "contig/NODE", "region", "antiSMASH_file", "workbook_row"]

def test_resolver_derives_uid_and_blanks_row():
    r = idr.resolver_rows(BANK)[0]
    assert r["BGC_ID"] == "BGC04" and r["contig/NODE"] == "NODE_12" and r["region"] == "region004"
    assert r["antiSMASH_file"] == "NODE_12_clusterblast.txt"
    assert "Streptomyces" in r["bgc_uid"] and "derived" in r["bgc_uid"]
    assert r["workbook_row"] == ""  # honest blank without a workbook

def test_resolver_uses_workbook_map():
    wm = {("AS-XXX", "BGC04"): {"bgc_uid": "Streptomyces_Bombus_NRPS_AS-XXX_BGC04", "row": 7}}
    r = idr.resolver_rows(BANK, wm)[0]
    assert r["bgc_uid"] == "Streptomyces_Bombus_NRPS_AS-XXX_BGC04" and r["workbook_row"] == 7

def test_resolver_md_six_columns():
    md = idr.resolver_md(idr.resolver_rows(BANK))
    assert "BGC_ID" in md and "antiSMASH_file" in md and md.count("\n") >= 2
