import importlib.util, pathlib
_m=pathlib.Path(__file__).resolve().parent.parent/"tools"/"zip_hygiene_allowlist.py"
_s=importlib.util.spec_from_file_location("zh",_m); zh=importlib.util.module_from_spec(_s); _s.loader.exec_module(zh)
A={"./big/ok.jsonl":(12_000_000,"reviewed")}
def test_small_passes(): ok,_=zh.check_oversized("./x.py",1000,A); assert ok
def test_oversized_rogue_fails(): ok,_=zh.check_oversized("./big/rogue.bin",9_000_000,A); assert ok is False
def test_allowlisted_under_ceiling(): ok,w=zh.check_oversized("./big/ok.jsonl",10_000_000,A); assert ok and "allowlisted" in w
def test_allowlisted_over_ceiling(): ok,_=zh.check_oversized("./big/ok.jsonl",13_000_000,A); assert ok is False
