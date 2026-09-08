import importlib.util, pathlib, tempfile, os
_m=pathlib.Path(__file__).resolve().parent.parent/"tools"/"gen_cut_receipt.py"
_s=importlib.util.spec_from_file_location("gen_cut_receipt",_m); gcr=importlib.util.module_from_spec(_s); _s.loader.exec_module(gcr)
def _w(l):
    fd,p=tempfile.mkstemp(suffix=".txt"); os.close(fd); pathlib.Path(p).write_text("\n".join(l)+"\n"); return p
def test_detects_modified_new_removed():
    o=_w(["aaa  ./keep.py","bbb  ./change.py","ccc  ./gone.py"]); n=_w(["aaa  ./keep.py","zzz  ./change.py","ddd  ./added.py"])
    a,r,m=gcr.diff(gcr.load(o),gcr.load(n)); assert a==["./added.py"] and r==["./gone.py"] and m==["./change.py"]; os.unlink(o); os.unlink(n)
def test_identical_empty():
    s=["aaa  ./a.py"]; o=_w(s); n=_w(s); a,r,m=gcr.diff(gcr.load(o),gcr.load(n)); assert not(a or r or m); os.unlink(o); os.unlink(n)
