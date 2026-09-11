import importlib.util, pathlib, tempfile, os
_m=pathlib.Path(__file__).resolve().parent.parent/"tools"/"gen_tier_doc.py"
_s=importlib.util.spec_from_file_location("gtd",_m); gtd=importlib.util.module_from_spec(_s); _s.loader.exec_module(gtd)
def test_reads_versions():
    fd,p=tempfile.mkstemp(suffix=".py"); os.close(fd); pathlib.Path(p).write_text('__version__ = "1.9.119"\nBUNDLE_VERSION = "9.7.355"\n')
    e,b=gtd.read_versions(p); assert e=="1.9.119" and b=="9.7.355"; os.unlink(p)
