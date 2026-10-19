from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("encoded_profile",ROOT/"tools/audit_documents_wheelhouse.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.mark.parametrize("encoding",["utf-8","utf-8-sig"])
def test_profile_accepts_windows_crlf_and_optional_bom(tmp_path,encoding):
    p=tmp_path/"profile π with spaces.txt"
    p.write_bytes("# local requirements\r\nPyYAML>=6,<7\r\npypdf>=5,<7\r\n".encode(encoding))
    assert m.read_profile(p)==["PyYAML>=6,<7","pypdf>=5,<7"]

def test_bom_does_not_authorize_remote_requirement(tmp_path):
    p=tmp_path/"profile.txt";p.write_bytes("pypdf @ https://example.invalid/test.whl\r\n".encode("utf-8-sig"))
    with pytest.raises(ValueError,match="PROFILE_NAMED_VERSION_REQUIREMENT_ONLY"):
        m.read_profile(p)
