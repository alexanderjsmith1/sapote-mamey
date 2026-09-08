import importlib, json, sys, os, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
cohort = importlib.import_module("cohort_concordance_summary")

def test_cohort_summary(tmp_path):
    idx={"entries":[{"accession":"BGC0000124","compounds":["piericidin"],"mibig_status":"active",
         "architecture_signature":{"region":"PKS","pks_ks":8,"size_kb":49.4,"markers":[]}}]}
    i=tmp_path/"idx.json"; i.write_text(json.dumps(idx))
    led=tmp_path/"led.csv"
    with open(led,"w",newline="") as fh:
        w=csv.writer(fh)
        w.writerow(["source_file","bgc_id","contig","obs_region_type","obs_size_kb","obs_pks_ks","obs_nrps_c","obs_nrps_a","cmp_t43"])
        w.writerow(["DEMO-STRAIN_copy.zip","BGC001","NODE_1","PKS","49.4","8","0","0","none"])
    pref=str(tmp_path/"out")
    rc=cohort.main(["--ledger",str(led),"--mibig-index",str(i),"--adjudications",str(tmp_path/"none.json"),"--out-prefix",pref])
    assert rc==0
    rows=list(csv.DictReader(open(pref+"_summary.csv")))
    assert rows[0]["strain"]=="DEMO-STRAIN" and rows[0]["n_fragments"]=="1" and rows[0]["STRONG"]=="1"
