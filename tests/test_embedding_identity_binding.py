from pathlib import Path
from types import SimpleNamespace
import os,sys,importlib.util,json
import pytest
from tools import protein_pcoa_render as current
C=Path(current.__file__).resolve().parents[1]
p=os.environ.get("LANE06_PPR_CANDIDATE")
if p:
    sp=importlib.util.spec_from_file_location("embedding_binding_candidate",p);ppr=importlib.util.module_from_spec(sp);sp.loader.exec_module(ppr);ppr._ROOT=C;ppr.R_SCRIPT=C/"tools/protein_pcoa_render.R"
else:ppr=current

@pytest.fixture
def data(tmp_path):
    kit=tmp_path/"kit/out_KS";kit.mkdir(parents=True)
    rows=[dict(id="r1",PC1="0",PC2="0",n_represented="1",source="reference",strain="REF"),dict(id="r2",PC1="1",PC2="1",n_represented="1",source="reference",strain="REF"),dict(id="i1",PC1="2",PC2="2",n_represented="1",source="isolate",strain="SYN_QUERY")]
    import csv
    with (kit/"PCOA_KS.tsv").open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]),delimiter="\t");w.writeheader();w.writerows(rows)
    (kit/"RUN_KS.json").write_text('{"pct_axes":[40,20]}')
    (tmp_path/"cohort.tsv").write_text("strain\tcohort\nSYN_QUERY\tg\n")
    e=tmp_path/"coords.tsv";e.write_text("id\tTRIMAP1\tTRIMAP2\nr1\t0\t0\nr2\t1\t1\ni1\t2\t2\n")
    return rows,e

@pytest.mark.parametrize("route",["single","page"])
@pytest.mark.parametrize("fault",["duplicate","nonfinite"])
def test_invalid_embedding_refused_before_panel(data,tmp_path,monkeypatch,route,fault):
    rows,e=data
    if fault=="duplicate":e.write_text(e.read_text()+"i1\t99\t99\n")
    else:e.write_text(e.read_text().replace("i1\t2\t2","i1\tNaN\t2"))
    hit=[]
    def panel(*a,**k):hit.append(True);return {}
    monkeypatch.setattr(ppr,"build_panel",panel)
    if route=="single":
        rc=ppr.main(["--kit",str(tmp_path/"kit"),"--out",str(tmp_path/"out"),"--cohort-table",str(tmp_path/"cohort.tsv"),"--panel","g=g","--layout","trimap","--embedding-table",f"KS={e}","--renderer","matplotlib"])
        assert rc==2 and not hit
    else:
        a=SimpleNamespace(min_text_pt=8,panel=["g=g"],top_strains=0,page="trimap")
        with pytest.raises(ppr.RenderRefusal):ppr.build_page(a,"KS",rows,{},dict(pct_axes=[40,20]),{"SYN_QUERY":"g"},{"KS":str(e)},{e.absolute():ppr.file_binding(e)},{},{},{},tmp_path,set(),[])
        assert not hit

def test_unique_coordinate_join_preserves_kit_order_and_values(data):
    rows,e=data;e.write_text("id\tTSNE1\tTSNE2\ni1\t8.125\t9.5\nr2\t3\t4\nr1\t1\t2\n")
    joined=ppr.embedding_coordinates(e,rows,"TSNE",ppr.file_binding(e))
    assert [x["id"] for x in joined]==["r1","r2","i1"]
    assert [(x["PC1"],x["PC2"]) for x in joined]==[("1","2"),("3","4"),("8.125","9.5")]
    assert [x["source"] for x in joined]==[x["source"] for x in rows]

@pytest.mark.parametrize("fault",["blank_id","missing_column","nonnumeric","extra_id","duplicate_kit"])
def test_other_binding_faults_are_refused(data,fault):
    rows,e=data
    if fault=="blank_id":e.write_text(e.read_text().replace("i1\t2"," \t2"))
    elif fault=="missing_column":e.write_text(e.read_text().replace("TRIMAP2","OTHER"))
    elif fault=="nonnumeric":e.write_text(e.read_text().replace("i1\t2","i1\tbad"))
    elif fault=="extra_id":e.write_text(e.read_text()+"x\t3\t4\n")
    else:rows.append(dict(rows[0]))
    with pytest.raises(ppr.RenderRefusal):ppr.embedding_coordinates(e,rows,"TRIMAP",ppr.file_binding(e))
