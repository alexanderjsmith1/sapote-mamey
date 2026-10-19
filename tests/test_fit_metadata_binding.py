from pathlib import Path
import os,importlib.util,json,hashlib
import pytest
from tools import protein_pcoa_render as current
from tools import protein_pcoa_page_docs as current_docs
from tests.test_protein_identity_missingness import page_record
root=os.environ.get("LANE06_FIT_CANDIDATE")
def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
ppr=load("fit_binding_candidate",Path(root)/"protein_pcoa_render.py") if root else current
docs=load("fit_docs_candidate",Path(root)/"protein_pcoa_page_docs.py") if root else current_docs

@pytest.fixture
def table(tmp_path):
    p=tmp_path/"coords.tsv";p.write_text("id\tTRIMAP1\tTRIMAP2\tTSNE1\tTSNE2\np1\t0\t0\t1\t1\n");return p

def sidecar(table,**methods):
    p=table.with_suffix(".json");p.write_text(json.dumps(dict(coordinates_sha256=hashlib.sha256(table.read_bytes()).hexdigest(),**methods)));return p

def caption(meta,lays):
    r=page_record();r["page"]=lays;r["embedding"]=meta;return docs.caption_text(r,[],{},None)

def test_nearby_wrong_method_never_credits_trimap(table):
    (table.parent/"a_unrelated.json").write_text(json.dumps(dict(tsne=dict(version="WRONG_METHOD",seed=17))))
    m=ppr.embedding_meta(table,["pcoa","trimap"])
    assert "WRONG_METHOD" not in caption(m,["pcoa","trimap"])
    assert m["state"]=="NOT_PROVIDED"

def test_unbound_exact_sidecar_never_credits_fit(table):
    p=sidecar(table,trimap=dict(version="UNBOUND",seed=3));x=json.loads(p.read_text());x['coordinates_sha256']='0'*64;p.write_text(json.dumps(x))
    m=ppr.embedding_meta(table,["trimap"]);assert m["state"]=="UNBOUND_METADATA" and "UNBOUND" not in caption(m,["trimap"])

def test_each_method_keeps_own_metadata_and_supplied_scope(table):
    sidecar(table,trimap=dict(version="TRI_VERSION",seed=3),tsne=dict(version="TSNE_VERSION",seed=11))
    m=ppr.embedding_meta(table,["pcoa","trimap","tsne"]);c=caption(m,["pcoa","trimap","tsne"])
    assert "TriMap TRI_VERSION, supplied seed 3" in c and "t-SNE TSNE_VERSION, supplied seed 11" in c
    assert m["fit_execution"]=="NOT_ESTABLISHED_BY_RENDER_REPLAY" and "fit execution not verified" in c

def test_wrong_method_exact_receipt_not_borrowed(table):
    sidecar(table,tsne=dict(version="WRONG_METHOD",seed=17));m=ppr.embedding_meta(table,["trimap"])
    assert m["by_layout"]["trimap"]["state"]=="METHOD_NOT_PROVIDED" and "WRONG_METHOD" not in caption(m,["trimap"])

@pytest.mark.parametrize("seed",[True,-1,"3",None])
def test_incomplete_seed_does_not_become_completed_fit(table,seed):
    sidecar(table,trimap=dict(version="DECLARED",seed=seed));m=ppr.embedding_meta(table,["trimap"])
    assert m["by_layout"]["trimap"]["state"]=="INCOMPLETE_METHOD_METADATA" and "DECLARED" not in caption(m,["trimap"])

def test_metadata_changed_after_admission_is_refused(table):
    p=sidecar(table,trimap=dict(version="v1",seed=3));admitted={table.absolute():ppr.file_binding(table),p.absolute():ppr.file_binding(p)};p.write_text(p.read_text()+" ")
    with pytest.raises(ppr.RenderRefusal,match="admitted binding"):ppr.embedding_meta(table,["trimap"],admitted)

def test_invalid_optional_json_is_typed_refusal(table):
    table.with_suffix(".json").write_text("{")
    with pytest.raises(ppr.RenderRefusal,match="metadata JSON"):ppr.embedding_meta(table,["trimap"])

@pytest.mark.parametrize("appears",[False,True])
def test_optional_fit_sidecar_is_admitted_before_draw(tmp_path,monkeypatch,appears):
    from tools import protein_pcoa_render as original
    C=Path(original.__file__).resolve().parents[1];monkeypatch.setattr(ppr,"_ROOT",C);monkeypatch.setattr(ppr,"R_SCRIPT",C/"tools/protein_pcoa_render.R")
    d=tmp_path/"kit/out_KS";d.mkdir(parents=True);table=tmp_path/"mapped.tsv"
    (d/"PCOA_KS.tsv").write_text("id\tPC1\tPC2\tn_represented\tsource\tstrain\np1\t0\t0\t1\treference\tR\np2\t1\t1\t1\treference\tR\np3\t2\t2\t1\tisolate\tSYN_Q\n")
    (d/"RUN_KS.json").write_text('{"pct_axes":[40,20]}');(tmp_path/"cohort.tsv").write_text("strain\tcohort\nSYN_Q\tg\n")
    table.write_text("id\tTRIMAP1\tTRIMAP2\np1\t0\t0\np2\t1\t1\np3\t2\t2\n")
    def panel(*a,**k):
        if appears:sidecar(table,trimap=dict(version="new",seed=3))
        return {}
    monkeypatch.setattr(ppr,"build_panel",panel)
    rc=ppr.main(["--kit",str(tmp_path/"kit"),"--out",str(tmp_path/"out"),"--cohort-table",str(tmp_path/"cohort.tsv"),"--panel","g=g","--layout","trimap","--embedding-table",f"KS={table}","--renderer","matplotlib"])
    receipt=tmp_path/"out/render_receipt.json"
    if appears:assert rc==2 and not receipt.exists()
    else:
        assert rc==0
        assert any(x["path"]==str(table.with_suffix(".json")) and x["state"]=="NOT_PROVIDED" for x in json.loads(receipt.read_text())["inputs"])
