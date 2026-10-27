"""A path-bound allowlist ceiling binds even for a suffix-exempt file (.pdf/.xlsx/.whl).

_oversized() checked the coarse suffix exemption first, so a .pdf with its own declared
ceiling could grow past it without the release gate noticing.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("preflight_zip_hygiene_458", ROOT / "tools" / "preflight_zip_hygiene.py")
zh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zh)

MB = 1024 * 1024


def test_declared_ceiling_binds_a_pdf():
    allow = {"./docs/GUIDE/manual.pdf": (8 * MB, "reviewed")}
    assert zh._oversized("docs/GUIDE/manual.pdf", 9 * MB, allow) is True
    assert zh._oversized("docs/GUIDE/manual.pdf", 7 * MB, allow) is False


def test_undeclared_pdf_keeps_the_suffix_exemption():
    assert zh._oversized("docs/other.pdf", 9 * MB, {}) is False


def test_undeclared_large_file_still_fails():
    assert zh._oversized("data/blob.bin", 9 * MB, {}) is True
