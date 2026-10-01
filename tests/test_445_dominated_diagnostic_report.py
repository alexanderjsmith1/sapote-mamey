import copy,json,zipfile
import pytest
from mamey import antismash_evidence as a

def hit(domain,e,bits,tier=True,locus="TST_CDS1"):
    return dict(domain_name=domain,evalue=e,bitscore=bits,tier1_diagnostic=tier,locus_tag=locus)

def test_same_cds_weak_diagnostic_reports_without_mutation():
    hits={"TST_CONTIG_c1":[hit("Trp_halogenase","3.2e-08",22),hit("TIGR02032","5.2e-82",200,False)]}
    before=copy.deepcopy(hits);r=a.dominated_diagnostic_flags(hits)
    assert len(r["flags"])==1 and r["flags"][0]["flag"]=="DOMINATED_DIAGNOSTIC"
    assert r["status"]=="CALIBRATION_REQUIRED" and hits==before

@pytest.mark.parametrize("weak,rival",[(hit("Trp_halogenase","1e-8",31),hit("TIGR02032","1e-82",200,False)),
    (hit("Trp_halogenase","1e-8",22),hit("TIGR02032","1e-82",200,False,"TST_CDS2")),
    (hit("Trp_halogenase","1e-8",22),hit("TIGR02032","1e-20",200,False)),
    (hit("Trp_halogenase","0",22),hit("TIGR02032","1e-82",200,False)),
    (hit("Trp_halogenase","nan",22),hit("TIGR02032","1e-82",200,False))])
def test_unassessable_or_undominated_is_not_flagged(weak,rival):
    assert not a.dominated_diagnostic_flags({"TST_CONTIG_c1":[weak,rival]})["flags"]

def test_json_competitor_is_report_only_and_region_bound(tmp_path,monkeypatch):
    rec={"id":"TST_CONTIG","areas":[{"start":0,"end":100},{"start":100,"end":500}],
         "modules":{"antismash.detection.tigrfam":{"hits":[{"identifier":"TIGR02032","locus_tag":"TST_CDS1","location":"[150:250](+)","score":200,"evalue":"1e-82"}]}}}
    competitors={};a._diagnostic_competitors_from_rec(rec,"test.json",competitors)
    assert list(competitors)==["TST_CONTIG_c2"]
    diagnostics={};a._tigrfam_from_rec(rec,"test.json",diagnostics);assert diagnostics=={}
    p=tmp_path/"public.zip"
    with zipfile.ZipFile(p,"w") as z:z.writestr("test.json",json.dumps({"records":[rec]}))
    monkeypatch.setattr(a,"extract_gbk_pfam_hits",lambda path:{"TST_CONTIG_c2":[hit("Trp_halogenase","1e-8",22)]})
    ev=a.parse_antismash_evidence(p,json_mode="off",want_tigrfam=True)
    assert len(ev["dominated_diagnostics"]["flags"])==1 and ev["tigrfam_hits"]=={}

def test_thresholds_are_positive_finite():
    with pytest.raises(ValueError):a.dominated_diagnostic_flags({},max_bitscore=float("nan"))
