"""Print-size block titles wrap inside their own delimiters."""
import importlib.util
from pathlib import Path
import pytest
import json, os, subprocess, sys
from matplotlib.figure import Figure

spec=importlib.util.spec_from_file_location("block_fixture",Path(__file__).with_name("test_452_blastp_identity_figures_alex_notes.py"))
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
world=f.world

@pytest.mark.parametrize("figure",["by-genome","by-class"])
def test_block_titles_wrap_at_print_size(world,monkeypatch,figure):
    path=world["genomes"]
    value=path.read_text().replace("Comparators","Synthetic comparison specimen group")
    path.write_text(value)
    seen=[];original=Figure.savefig
    def save(fig,path,*args,**kwargs):
        if str(path).endswith(".pdf"):
            fig.canvas.draw();renderer=fig.canvas.get_renderer()
            tight=fig.get_tightbbox(renderer);pad=kwargs.get("pad_inches",0.1)
            for ax in fig.axes:
                for t in ax.texts:
                    if t.get_gid()!="block-title":continue
                    left,right=t._block_bounds
                    bounds=[(ax.transData.transform((v,0))[0]/fig.dpi-tight.x0+pad)*72 for v in (left,right)]
                    box=t.get_window_extent(renderer)
                    assert box.x0>=ax.transData.transform((left,0))[0]-0.5
                    assert box.x1<=ax.transData.transform((right,0))[0]+0.5
                    seen.append((t.get_text(),bounds))
        return original(fig,path,*args,**kwargs)
    monkeypatch.setattr(Figure,"savefig",save)
    out=world["tmp"]/"wrapped"
    assert f._run(world,out,"--figure",figure,"--omit-class","Other")==0
    assert any("\n" in text for text,_ in seen)
    assert any(text=="Isolates" for text,_ in seen)
    pdf=next(out.glob("*.pdf"))
    command = "import json,pdfplumber,sys; p=pdfplumber.open(sys.argv[1]).pages[0]; print(json.dumps({'words':p.extract_words(),'chars':p.chars}))"
    result=subprocess.run([os.environ.get("PDF_CHECK_PYTHON",sys.executable),"-c",command,str(pdf)],capture_output=True,text=True,check=True)
    data=json.loads(result.stdout)
    for text,(left,right) in seen:
        for word in text.split():
            found=[w for w in data["words"] if w["text"]==word]
            assert any(w["x0"]>=left-0.5 and w["x1"]<=right+0.5 for w in found),(word,left,right,found)
    assert all(c["size"]>=7.95 for c in data["chars"] if c["upright"])


def test_unbreakable_title_refuses(world):
    path=world["genomes"];path.write_text(path.read_text().replace("Comparators","W"*100))
    with pytest.raises(ValueError,match="BLOCK_LABEL_DOES_NOT_FIT"):
        f._run(world,world["tmp"]/"bad","--figure","by-genome")
