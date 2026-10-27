"""The public release audit must not decode bundled font binaries as text.

The protein-space viewer ships vendor fonts (assets/protein_space_vendor/*.ttf). The audit's
binary-suffix list lacked font suffixes, so a .458 cut failed with "undecodable tracked text file".
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("public_release_audit_fonts", ROOT / "tools" / "public_release_audit.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def test_font_suffixes_are_binary():
    for suffix in (".ttf", ".otf", ".woff", ".woff2"):
        assert suffix in mod._SKIP_SUFFIX, suffix


def test_real_vendor_fonts_are_not_decoded_as_text():
    fonts = sorted((ROOT / "assets" / "protein_space_vendor").glob("*.ttf"))
    assert fonts, "expected the vendored protein-space fonts"
    for font in fonts:
        assert font.suffix.lower() in mod._SKIP_SUFFIX
