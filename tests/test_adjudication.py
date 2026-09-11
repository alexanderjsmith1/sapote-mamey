import importlib, json
adj = importlib.import_module("mamey.adjudication")
MIBIG = {"entries":[
  {"accession":"BGC0000999","compounds":["HSAF"],"architecture_signature":{"region":"NRPS;PKS","pks_ks":3,"nrps_a":1,"nrps_c":1,"size_kb":40.0,"markers":[]},"provenance":"MIBiG-4.0-auto"},
  {"accession":"BGC9999999","compounds":["x"],"architecture_signature":{"region":"terpene","pks_ks":0,"size_kb":20.0,"markers":[]},"provenance":"MIBiG-4.0-auto"},
]}
BY = {"BGC0000999":{"compound":"HSAF","expected_marker_set":["T43-PTM"],"hard_scan_verdict":"STRONG","curated_signature":{"pks_ks":1}}}

def test_matched_becomes_adjudicated():
    e=adj.adjudicate(MIBIG["entries"][0], BY)
    assert e["reference_tier"]=="CURATED-ADJUDICATED"
    assert e["expected_marker_set"]==["T43-PTM"] and e["hard_scan_verdict"]=="STRONG"
    assert e["ks_disagreement"]=={"curated":1,"auto":3}

def test_unmatched_is_auto_no_marker_credit():
    e=adj.adjudicate(MIBIG["entries"][1], BY)
    assert e["reference_tier"]=="MIBIG-AUTO" and e["expected_marker_set"]==[]

def test_build_reference_space_tiers_all():
    assert sorted(x["reference_tier"] for x in adj.build_reference_space(MIBIG, BY))==["CURATED-ADJUDICATED","MIBIG-AUTO"]

def test_load_adjudications(tmp_path):
    f=tmp_path/"a.json"; f.write_text(json.dumps({"by_accession":BY}))
    assert "BGC0000999" in adj.load_adjudications(str(f))
