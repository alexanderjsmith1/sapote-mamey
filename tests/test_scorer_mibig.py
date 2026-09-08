import importlib, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..","tools"))
scorer = importlib.import_module("fragment_concordance_scorer")

def _write(tmp_path):
    idx={"entries":[
      {"accession":"BGC0000999","compounds":["HSAF"],"architecture_signature":{"region":"NRPS;PKS","pks_ks":3,"nrps_a":1,"nrps_c":1,"size_kb":40.0,"markers":[]},"provenance":"MIBiG-4.0-auto"},
      {"accession":"BGC0000124","compounds":["piericidin"],"architecture_signature":{"region":"PKS","pks_ks":8,"size_kb":49.4,"markers":[]},"provenance":"MIBiG-4.0-auto"},
    ]}
    by={"by_accession":{"BGC0000999":{"expected_marker_set":["T43-PTM"],"hard_scan_verdict":"STRONG","curated_signature":{"pks_ks":3}}}}
    i=tmp_path/"idx.json"; a=tmp_path/"adj.json"; i.write_text(json.dumps(idx)); a.write_text(json.dumps(by))
    return str(i),str(a)

def test_mibig_space_tiers(tmp_path):
    i,a=_write(tmp_path); sp=scorer.load_mibig_space(i,a)
    t={r["reference_tier"] for r in sp}; assert "CURATED-ADJUDICATED" in t and "MIBIG-AUTO" in t

def test_adjudicated_match_marker_credit(tmp_path):
    i,a=_write(tmp_path); sp=scorer.load_mibig_space(i,a)
    obs=scorer.obs_signature({"id":"X","region":"NRPS;PKS","pks_ks":3,"nrps_a":1,"nrps_c":1,"size_kb":40.0,"markers":["T43-PTM"]})
    res=scorer.best_match(obs,sp)
    assert res["best_compound"]=="HSAF" and res["reference_tier"]=="CURATED-ADJUDICATED" and res["marker_concordance"]==1.0

def test_auto_match_tier(tmp_path):
    i,a=_write(tmp_path); sp=scorer.load_mibig_space(i,a)
    obs=scorer.obs_signature({"id":"Y","region":"PKS","pks_ks":8,"size_kb":49.4,"markers":[]})
    res=scorer.best_match(obs,sp)
    assert res["best_compound"]=="piericidin" and res["reference_tier"]=="MIBIG-AUTO"

def test_status_filter(tmp_path):
    import json as _j
    idx={"entries":[
      {"accession":"BGC0000001","compounds":["x"],"mibig_status":"active","architecture_signature":{"region":"PKS","pks_ks":1,"size_kb":10.0,"markers":[]}},
      {"accession":"BGC0000002","compounds":["y"],"mibig_status":"pending","architecture_signature":{"region":"NRPS","nrps_a":1,"size_kb":10.0,"markers":[]}},
    ]}
    i=tmp_path/"idx.json"; i.write_text(_j.dumps(idx))
    assert len(scorer.load_mibig_space(str(i), None, {"active"}))==1
    assert len(scorer.load_mibig_space(str(i), None, None))==2

def test_obs_marker_t43_normalization():
    o = scorer.obs_signature({"id":"z","region":"NRPS","markers":"T43-HAL_halogenase; none; T43-NUC_nucleoside"})
    assert o["markers"] == {"T43-HAL","T43-NUC"}   # codes normalized, 'none' dropped
