"""Reproduce Linux path spelling failures without depending on host case sensitivity."""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT
spec = importlib.util.spec_from_file_location('case_exact_scanner', ROOT/'tools/check_dangling_refs.py')
scanner = importlib.util.module_from_spec(spec)
saved_path = list(sys.path)
try:
    sys.path.insert(0, str(ROOT/'tools'))
    spec.loader.exec_module(scanner)
finally:
    sys.path[:] = saved_path


def test_wrong_case_reference_is_detected_on_this_host(tmp_path):
    (tmp_path/'tools').mkdir()
    (tmp_path/'tools/helper.py').write_text('# shipped\n')
    (tmp_path/'guide.md').write_text('Run `Tools/helper.py`.\n')
    assert 'Tools/helper.py' in scanner.scan_tools(tmp_path, strict_paths=True)
    assert scanner.scan_tools(tmp_path, strict_paths=False) == {}


def test_exact_path_still_resolves(tmp_path):
    (tmp_path/'tools').mkdir()
    (tmp_path/'tools/helper.py').write_text('# shipped\n')
    (tmp_path/'guide.md').write_text('Run `tools/helper.py`.\n')
    assert scanner.scan_tools(tmp_path, strict_paths=True) == {}


def test_case_sensitive_view_reproduces_original_two_tool_failure(tmp_path):
    (tmp_path/'tools').mkdir()
    for name in ['check_md_links.py','signoff_check.py']:
        (tmp_path/'tools'/name).write_text('# planted shipped tool\n')
    (tmp_path/'guide.md').write_text('Run `Tools/check_md_links.py` and `Tools/signoff_check.py`.\n')
    unresolved = set(scanner.scan_tools(tmp_path, strict_paths=True))
    assert unresolved == {'Tools/check_md_links.py', 'Tools/signoff_check.py'}
    assert scanner.scan_tools(tmp_path, strict_paths=False) == {}


def test_current_docs_clear_original_failure_without_growing_allowlist():
    docs = ['docs/CATALOG_MAINTENANCE.md','docs/PHYLO_PLACEMENT_WORKFLOW.md','wiki/Phylogenetic-Placement.md']
    strict = set(scanner.scan_tools(SOURCE, strict_paths=True))
    lenient = set(scanner.scan_tools(SOURCE, strict_paths=False))
    assert not {'Tools/check_md_links.py','Tools/signoff_check.py'} & strict
    assert strict-lenient == {'../bootstrap.sh','engine/pyhmmer_scanner_engine.py','directed_studies/pks.py'}
    for name in docs:
        text = (SOURCE/name).read_text()
        assert 'tools/' in text
        assert 'workspace' in text


def test_missing_path_and_wrong_basename_remain_errors(tmp_path):
    (tmp_path/'mamey').mkdir()
    (tmp_path/'mamey/widget.py').write_text('# present in wrong directory\n')
    (tmp_path/'guide.md').write_text('Run `tools/widget.py` and `tools/absent.py`.\n')
    assert set(scanner.scan_tools(tmp_path, strict_paths=True)) == {'tools/widget.py','tools/absent.py'}


def test_external_path_policy_preserved(tmp_path):
    outside = tmp_path/'outside.py'
    outside.write_text('# external\n')
    child = tmp_path/'child';child.mkdir()
    assert scanner._exact_relative_path_exists(child, '../outside.py')
    assert not scanner._exact_relative_path_exists(child, '../missing.py')
