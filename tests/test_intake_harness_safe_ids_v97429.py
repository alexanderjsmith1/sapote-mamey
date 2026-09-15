import importlib.util, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('intake_harness',ROOT/'tools/intake_harness.py')
tool=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(tool)
SAFE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,59}$')

def test_reference_archive_names_become_engine_safe():
    paths=['/x/Genus species (1).zip','/x/X copy.zip','/x/A B?.zip']
    values=tool.assign_unique_names(paths).values()
    assert all(SAFE.fullmatch(x) for x in values)
    assert all(' ' not in x and '(' not in x for x in values)

def test_sanitize_collisions_remain_unique_and_deterministic():
    paths=['/x/A B.zip','/x/A+B.zip','/x/A?B.zip']
    first=tool.assign_unique_names(paths);second=tool.assign_unique_names(paths)
    assert first==second and len(set(first.values()))==len(paths)

def test_length_and_leading_character_contract():
    assert SAFE.fullmatch(tool._safe_id('-('+('x'*100)))
