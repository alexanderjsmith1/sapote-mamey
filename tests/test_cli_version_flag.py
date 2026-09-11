"""v9.7.100 quick-audit P1: top-level `mamey --version` must print engine + bundle version."""
import subprocess
import sys


def test_cli_top_level_version():
    from mamey import __version__, BUNDLE_VERSION
    result = subprocess.run(
        [sys.executable, "-m", "mamey", "--version"],
        text=True,
        capture_output=True,
        check=True,
    )
    out = result.stdout + result.stderr
    assert __version__ in out, f"engine version {__version__} missing from --version output: {out!r}"
    assert BUNDLE_VERSION in out, f"bundle version {BUNDLE_VERSION} missing from --version output: {out!r}"
