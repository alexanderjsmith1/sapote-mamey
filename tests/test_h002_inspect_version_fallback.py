"""v9.7.235 (H-002/F-005): inspect's antiSMASH-version preflight must not contradict the run receipt.
The narrow GBK structured-comment regex misses some antiSMASH 8 variants; inspect now falls back to the
same parsers.extract_antismash_version that `run` uses."""
import sys, pathlib, inspect as _inspect
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

def test_inspect_falls_back_to_run_version_extractor():
    from mamey import package_inspector
    src = _inspect.getsource(package_inspector)
    # the fallback must call the same extractor run uses (parsers.extract_antismash_version)
    assert "extract_antismash_version" in src
    assert "parsers import extract_antismash_version" in src

def test_run_version_extractor_importable_and_callable():
    from mamey.parsers import extract_antismash_version
    assert callable(extract_antismash_version)
