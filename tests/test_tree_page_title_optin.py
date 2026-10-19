"""Actual synthetic R pagination: title off by default, explicit1 on, no topology changes."""
from pathlib import Path
import os,sys,json,subprocess,shutil,re,hashlib
import pytest
ROOT=Path(__file__).resolve().parents[1]
R=shutil.which("Rscript")

@pytest.fixture(scope="module")
def tree_inputs(tmp_path_factory):
    p=tmp_path_factory.mktemp("synthetic_tree")
    names=[f"SYN_TIP_{i:03d}" for i in range(47)]
    def clade(labels):
        if len(labels)==1:return labels[0]+":0.01"
        k=len(labels)//2;return "("+clade(labels[:k])+","+clade(labels[k:])+"):0.01"
    tree=p/"tree.nwk";tree.write_text("("+clade(names)+",OUTGROUP_REF:0.08);\n")
    names += ["OUTGROUP_REF"]
    md=p/"metadata.tsv";md.write_text("tip\tlabel\trole\tcategory\tsource\n"+"".join(
        n+"\tSynthetica sp. "+n+" [SYN_"+str(i)+"]\t"+("outgroup" if n=="OUTGROUP_REF" else "reference")+"\tplant-associated\tUS\n"
        for i,n in enumerate(names)))
    return p,tree,md,names

@pytest.mark.parametrize("setting,want",[(None,False),("0",False),("1",True)])
def test_real_r_page_title_is_optin_and_pagination_unchanged(tree_inputs,tmp_path,setting,want):
    PdfReader=pytest.importorskip("pypdf").PdfReader
    if not R:pytest.skip("verified R runtime needed for actual render")
    p,tree,md,names=tree_inputs
    before={q:hashlib.sha256(q.read_bytes()).hexdigest() for q in [tree,md]}
    env=dict(os.environ)
    for k in list(env):
        if k.startswith("GG_"):env.pop(k)
    env.update(SAPOTE_PYTHON=sys.executable,GG_STRIPS="0",GG_PRINT_WIDTH="7.2",GG_FIGID="-",
               GG_METHODS="Synthetic fixed-branch tree for renderer validation.")
    if setting is not None:env["GG_PAGE_TITLE"]=setting
    pre=tmp_path/"tree"
    cp=subprocess.run([R,str(ROOT/"tools/ggtree_rect_heatmap.R"),str(tree),str(md),str(pre)],cwd=tmp_path,
                      env=env,capture_output=True,text=True,timeout=90)
    (tmp_path/"render.log").write_text(cp.stdout+cp.stderr)
    assert cp.returncode==0,cp.stdout+cp.stderr
    rec=json.loads(Path(str(pre)+".pages.json").read_text())
    assert rec["page_titles"] is want
    assert len(rec["pages"])==2
    assert sorted(t for page in rec["pages"] for t in page["tips"])==sorted(names)
    texts=[]
    for i,page in enumerate(rec["pages"],1):
        pdf=tmp_path/page["pdf"];reader=PdfReader(pdf);text=reader.pages[0].extract_text();texts.append(text)
        assert bool(re.search(r"Page\s+"+str(i)+r"\s+of\s+2",text)) is want
        assert abs(float(reader.pages[0].mediabox.width)/72-7.2)<.01
        assert (tmp_path/page["png"]).stat().st_size>100
    combined=PdfReader(Path(str(pre)+".pdf"));assert len(combined.pages)==2
    assert before=={q:hashlib.sha256(q.read_bytes()).hexdigest() for q in before}
    (tmp_path/"validation.json").write_text(json.dumps(dict(setting=setting,titles=want,tip_count=len(names),pages=2,
            inputs=[dict(path=str(q),sha256=h) for q,h in before.items()],page_receipt=str(pre)+".pages.json"),indent=2)+"\n")

@pytest.mark.parametrize("saved,actual,ambient,want",[
    (None,None,"1","0"),("1",None,"0","1"),("0",None,"1","0"),
    ("1",False,"1","0"),("0",True,"0","1"),
    (None,False,"1","0"),(None,True,"0","1"),
    (True,None,"1","0"),(1,None,"1","0"),("true",None,"1","0"),
    ("1","false","0","1"),(None,"true","1","0")])
def test_exported_helper_freezes_page_title_setting(tmp_path,saved,actual,ambient,want):
    src=tmp_path/"source";src.mkdir();stem="SYN_tree"
    for name,body in {stem+"_display.nwk":"(A:0.1,B:0.1);\n",stem+"_rect02.png":"PNG fixture",stem+"_rect02.pdf":"PDF fixture",
                      stem+"_rect02.methods.txt":"Synthetic caption", "display_input.tsv":"tip\tlabel\nA\tA\n",
                      "display_input.fasta":">A\nACGT\n", "METHODS.md":"Methods", "analysis.nwk":"(A:0.1,B:0.1);",
                      "display_tree.nwk":"(A:0.1,B:0.1);", "display_meta.tsv":"tip\tlabel\nA\tA\n"}.items():
        (src/name).write_text(body)
    (src/(stem+"_display_receipt.json")).write_text(json.dumps(dict(inputs=dict(analysis_tree=dict(path="analysis.nwk")),
            outputs=dict(tree=dict(path="display_tree.nwk"),metadata=dict(path="display_meta.tsv")))))
    envrec={} if saved is None else {"GG_PAGE_TITLE":saved}
    (src/"placement_display_receipt.json").write_text(json.dumps(dict(render_environment=envrec)))
    if actual is not None:
        (src/(stem+"_rect02.pages.json")).write_text(json.dumps(dict(page_titles=actual,pages=[])))
    out=tmp_path/"export"
    cp=subprocess.run([sys.executable,"-B",str(ROOT/"tools/export_tree_figure_source_package.py"),str(src),"--out",str(out)],capture_output=True,text=True)
    assert cp.returncode==0,cp.stderr
    fake=tmp_path/"bin";fake.mkdir();exe=fake/"Rscript";exe.write_text('#!/bin/sh\nprintf "%s" "$GG_PAGE_TITLE" > title_setting.txt\n');exe.chmod(0o755)
    env=dict(os.environ,PATH=str(fake)+os.pathsep+os.environ["PATH"],GG_PAGE_TITLE=ambient)
    cp=subprocess.run(["sh",str(out/(stem+"_rerender_captioned.sh"))],cwd=out,env=env,capture_output=True,text=True)
    assert cp.returncode==0,cp.stderr
    assert (out/"title_setting.txt").read_text()==want
