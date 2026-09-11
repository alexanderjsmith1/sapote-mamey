import importlib.util, pathlib, tempfile, os
_m=pathlib.Path(__file__).resolve().parent.parent/"tools"/"tree_sanity_check.py"
_s=importlib.util.spec_from_file_location("tsc",_m); tsc=importlib.util.module_from_spec(_s); _s.loader.exec_module(tsc)
def _w(nwk):
    fd,p=tempfile.mkstemp(suffix=".treefile"); os.close(fd); pathlib.Path(p).write_text(nwk); return p
def test_dominating_branch_fails():
    p=_w("((A:0.01,B:0.01):0.01,C:5.0);"); ok,_=tsc.check(p); assert ok is False; os.unlink(p)
def test_balanced_passes():
    p=_w("((((A:0.1,B:0.1):0.1,C:0.1):0.1,D:0.1):0.1,OUTGROUP:0.15);"); ok,_=tsc.check(p); assert ok is True; os.unlink(p)
