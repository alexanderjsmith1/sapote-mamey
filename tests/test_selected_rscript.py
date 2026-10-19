from pathlib import Path
import os,sys,importlib.util,json
from types import SimpleNamespace
import pytest
from tools import protein_pcoa_render as current
C=Path(current.__file__).resolve().parents[1]
p=os.environ.get("LANE06_PPR_CANDIDATE")
if p:
    sp=importlib.util.spec_from_file_location("selected_r_candidate",p);ppr=importlib.util.module_from_spec(sp);sp.loader.exec_module(ppr);ppr._ROOT=C;ppr.R_SCRIPT=C/"tools/protein_pcoa_render.R"
else:ppr=current

@pytest.fixture
def kit(tmp_path):
    d=tmp_path/"kit/out_KS";d.mkdir(parents=True)
    (d/"PCOA_KS.tsv").write_text("id\tPC1\tPC2\tn_represented\tsource\tstrain\nr1\t0\t0\t1\treference\tREF\nr2\t1\t1\t1\treference\tREF\ni1\t2\t2\t1\tisolate\tSYN_QUERY\n")
    (d/"RUN_KS.json").write_text('{"pct_axes":[40,20]}');(tmp_path/"cohort.tsv").write_text("strain\tcohort\nSYN_QUERY\tg\n")
    return tmp_path

def args(kit):return ["--kit",str(kit/"kit"),"--out",str(kit/"out"),"--cohort-table",str(kit/"cohort.tsv"),"--panel","g=g"]

def test_discovered_executable_survives_path_change(kit,tmp_path,monkeypatch):
    a=tmp_path/"initial/Rscript";a.parent.mkdir();a.write_text("fakeR-A");b=tmp_path/"changed/Rscript";calls=[];lookups=[]
    real_which=ppr.shutil.which;real_run=ppr.subprocess.run
    def which(name,*aa,**kk):
        if name != "Rscript":return real_which(name,*aa,**kk)
        lookups.append(True);return str(a if len(lookups)==1 else b)
    monkeypatch.setattr(ppr.shutil,"which",which)
    def subprocess(cmd,**kwargs):
        if cmd[0] not in (str(a),str(b),"Rscript"):return real_run(cmd,**kwargs)
        calls.append(cmd)
        if "-e" not in cmd:Path(str(cmd[-2])+".stamp").write_text(cmd[-1])
        return SimpleNamespace(returncode=0,stderr="",stdout="")
    monkeypatch.setattr(ppr.subprocess,"run",subprocess)
    def panel(ns,*aa,**kk):
        # Simulate a changed search path after discovery but before actual rendering.
        spec=kit/"spec.json";spec.write_text("{}");pre=kit/"probe"
        ppr.render_r(spec,pre,"abc",**({"rscript":ns._rscript} if hasattr(ns,"_rscript") else {}));return {}
    monkeypatch.setattr(ppr,"build_panel",panel)
    assert ppr.main(args(kit))==0
    assert calls[0][0]==calls[-1][0]==str(a) and len(lookups)==1
    rec=json.loads((kit/"out/render_receipt.json").read_text());assert rec["rendering_runtime"]["r_executable"]["sha256"]

def test_explicit_r_unavailable_is_typed_hold(kit,monkeypatch):
    monkeypatch.setattr(ppr.shutil,"which",lambda *_:None)
    monkeypatch.setattr(ppr,"build_panel",lambda *a,**k:pytest.fail("unavailableR must notplot"))
    assert ppr.main(args(kit)+["--renderer","r"])==2

def test_page_cannot_claim_matplotlib(kit):
    with pytest.raises(SystemExit) as ex:ppr.main(args(kit)+["--page","pcoa","--renderer","matplotlib"])
    assert ex.value.code==2

def test_direct_page_selection_cached(monkeypatch,tmp_path):
    n=[];a=SimpleNamespace()
    monkeypatch.setattr(ppr,"discover_rscript",lambda: n.append(True) or str(tmp_path/"Rscript"))
    assert ppr.selected_rscript(a)==ppr.selected_rscript(a) and len(n)==1
