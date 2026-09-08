import importlib.util
from pathlib import Path

def test_sync_owner_rewrites_build_stamp_engine_without_touching_stamp():
    path=Path(__file__).resolve().parents[1]/'tools/sync_version.py'
    spec=importlib.util.spec_from_file_location('sync_engine_rule_test',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    rules=[(pattern,replacement) for name,pattern,replacement in mod.RULES if name=='BUILD_STAMP.txt' and pattern.search('engine=0.0.0\n')]
    assert len(rules)==1
    pattern,replacement=rules[0]
    assert pattern.sub(replacement,'build=20990101v999a\nengine=0.0.0\n')=='build=20990101v999a\nengine='+mod.ENGINE+'\n'
