"""Unknown similarity must never be reported as a measured high-identity match."""
import csv, importlib.util, json, math, sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"tools")]
spec=importlib.util.spec_from_file_location("identity_missingness_renderer",ROOT/"tools/protein_pcoa_render.py")
ppr=importlib.util.module_from_spec(spec); spec.loader.exec_module(ppr)
from tools.protein_pcoa_page_docs import caption_text, write_page_docs

@pytest.mark.parametrize("raw,state",[(None,"NOT_PROVIDED"),("","NOT_PROVIDED"),("  ","NOT_PROVIDED"),
    ("NaN","NONFINITE"),(float("nan"),"NONFINITE"),("Inf","NONFINITE"),("-Inf","NONFINITE"),
    (float("inf"),"NONFINITE"),("NA","NONNUMERIC"),("unavailable","NONNUMERIC")])
def test_unavailable_identity_has_explicit_state(raw,state):
    assert ppr.identity_measurement(raw)==(None,state)

@pytest.mark.parametrize("raw",["0","69.999","70","84.999","85","100"])
def test_finite_percentage_is_preserved(raw):
    assert ppr.identity_measurement(raw)==(float(raw),"AVAILABLE")

@pytest.mark.parametrize("raw",["-1","100.01"])
def test_invalid_finite_percentage_is_refused(raw):
    with pytest.raises(ppr.RenderRefusal,match="outside"):
        ppr.identity_measurement(raw)

@pytest.mark.parametrize("mid,known_counts",[(None,(2,0,4)),(85.,(2,2,2))])
def test_missingness_excluded_from_known_bins(mid,known_counts,tmp_path):
    vals=["0","69.999","70","84.999","85","100",None,"","NaN","-Inf","NA"]
    rows=[dict(id="r1",PC1=0,PC2=0,n_represented=1,source="reference",strain="REF"),
          dict(id="r2",PC1=1,PC2=1,n_represented=1,source="reference",strain="REF")]
    rows += [dict(id=f"i{k}",PC1=2+k*.1,PC2=2+k*.1,n_represented=1,source="isolate",strain=f"SYN_{k}") for k in range(len(vals))]
    a=SimpleNamespace(drop_origins=None,exclude_strain=[],label_below=70.,mid_below=mid,top_strains=99,quantile=.95,number_above=30)
    b=ppr.build_panel(a,"KS",rows,{f"i{k}":v for k,v in enumerate(vals)}, {},dict.fromkeys([f"SYN_{k}" for k in range(len(vals))],"g"),
                      "audit",{"g"},"#0072B2","Synthetic isolates",{},tmp_path,"r",spec_only=True)
    assert (b["counts"]["n_low"],b["counts"]["n_mid"],b["counts"]["n_high"])==known_counts
    assert b["counts"]["n_unknown"]==5
    assert sum(b["counts"][x] for x in ("n_low","n_mid","n_high","n_unknown"))==len(vals)
    assert [p["layer"] for p in b["spec"]["points"]][-5:]==["iso_unknown"]*5
    assert b["counts"]["identity_missingness"]["states"]==dict(AVAILABLE=6,NOT_PROVIDED=2,NONFINITE=2,NONNUMERIC=1)
    assert b["counts"]["identity_missingness"]["records"][-1]["raw"]=="NA"
    assert "unavailable" in b["spec"]["legend"]["iso_unknown"]
    assert not any("nan%" in x.lower() or "inf%" in x.lower() for x in b["texts"])

@pytest.mark.parametrize("raw",[None,float("nan"),float("inf")])
def test_distance_grouping_keeps_unavailable_separate_from_known(raw):
    pts=[dict(x=2.,y=2.,strain="SYN_A",pid=raw),dict(x=2.001,y=2.001,strain="SYN_A",pid=95.)]
    groups,text,_,_=ppr.choose_labels(pts,[(0.,0.),(.1,.1)],span=10)
    assert len(groups)==2
    unknown_label=text[next(i for i,g in enumerate(groups) if g==[0])]
    assert "95%" not in unknown_label

def page_record():
    return dict(page=["pcoa"],legend={"iso_low":"cohort protein, best match"},cohort_genomes={"SYN_A":4},n_cohort_points=4,
                n_low=1,n_mid=1,n_high=1,n_unknown=1,n_ref_centroids=2,n_ref=2,n_reference_genomes=1,n_mibig_centroids=0,n_mibig=0,
                label_below=70.,mid_below=85.,title="Synthetic coordinates",labels={"pcoa":dict(numbered=False,labelled=0,outlier_groups=0)},
                leader_max_in=.35,prefix="PAGE_KS_audit_PCOA",set="KS",panel="audit",pct_axes=[40,20])

def test_page_caption_reports_high_and_unknown_separately():
    cap=caption_text(page_record(),[],{},None)
    assert "≥ 85% (1)" in cap and "Open diamonds show 1 proteins" in cap
    assert "≥ 85% (2)" not in cap

def test_legacy_caption_count_remains_compatible():
    rec=page_record();rec.pop("n_unknown");rec.pop("n_high")
    cap=caption_text(rec,[],{},None)
    assert "≥ 85% (2)" in cap and "Open diamonds" not in cap

@pytest.mark.parametrize("layout",["pcoa","trimap","tsne"])
@pytest.mark.parametrize("near_mode",["missing_file","blank","nonfinite","known"])
def test_main_receipt_and_label_key_preserve_missingness(tmp_path,monkeypatch,layout,near_mode):
    d=tmp_path/"kit/out_KS";d.mkdir(parents=True)
    (d/"PCOA_KS.tsv").write_text("id\tPC1\tPC2\tn_represented\tsource\tstrain\tlocus_tag\torigin\n"
        "r1\t0\t0\t1\treference\tREF\tr1\tr1.gbk\n"
        "r2\t1\t1\t1\treference\tREF\tr2\tr2.gbk\n"
        "i1\t2\t2\t1\tisolate\tSYN_A\ti1\tSYN_A__N1.region001.gbk\n")
    if near_mode!="missing_file":
        val={"blank":"","nonfinite":"NaN","known":"95"}[near_mode]
        (d/"NEAREST_KS.tsv").write_text("id\tnearest_pident\ni1\t"+val+"\n")
    (d/"RUN_KS.json").write_text('{"pct_axes":[40,20]}')
    (tmp_path/"cohort.tsv").write_text("strain\tcohort\nSYN_A\tg\n")
    out=tmp_path/"render";captured=[]
    def fake_render(spec,prefix):
        captured.append(spec)
        from PIL import Image
        from pypdf import PdfWriter
        Image.new("RGB",(10,10),"white").save(str(prefix)+".png")
        w=PdfWriter();w.add_blank_page(width=72,height=72)
        with open(str(prefix)+".pdf","wb") as f:w.write(f)
        Path(str(prefix)+".svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>KS</text></svg>')
    monkeypatch.setattr(ppr,"render_matplotlib",fake_render)
    args=["--kit",str(tmp_path/"kit"),"--out",str(out),"--cohort-table",str(tmp_path/"cohort.tsv"),"--panel","audit=g",
          "--renderer","matplotlib","--top-strains","3","--layout",layout]
    if layout!="pcoa":
        key="TRIMAP" if layout=="trimap" else "TSNE"
        ep=tmp_path/"embedding.tsv";ep.write_text("id\t"+key+"1\t"+key+"2\nr1\t0\t0\nr2\t1\t1\ni1\t2\t2\n")
        args += ["--embedding-table","KS="+str(ep)]
    assert ppr.main(args)==0
    rec=json.loads((out/"panel_KS_audit.json").read_text())
    assert rec["n_high"]==(1 if near_mode=="known" else 0)
    assert rec["n_unknown"]==(0 if near_mode=="known" else 1)
    assert captured[0]["points"][-1]["layer"]==("iso_high" if near_mode=="known" else "iso_unknown")
    label=list(csv.DictReader((out/"LABELS_KS_audit.tsv").open(),delimiter="\t"))[0]
    assert label["fill"]==("open" if near_mode=="known" else "unknown")
    expected={"known":"AVAILABLE","missing_file":"NOT_PROVIDED","blank":"NOT_PROVIDED","nonfinite":"NONFINITE"}[near_mode]
    assert label["nearest_identity_state"]==expected
    if near_mode!="known":assert label["nearest_identity_pct"]==""
