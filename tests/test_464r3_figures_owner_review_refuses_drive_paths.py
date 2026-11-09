"""compile_figure_owner_review: drive-qualified and other platform-absolute locators are refused."""
import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "compile_figure_owner_review.py"
spec = importlib.util.spec_from_file_location("compile_figure_owner_review_464r3", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.mark.parametrize("value", ["C:/example/outside.svg", "C:\\example\\outside.svg", "C:outside.svg",
                                   "/abs/x.svg", "\\\\server\\share\\x.svg", "a/../x.svg", "file:x.svg"])
def test_unsafe_locator_is_refused(value):
    with pytest.raises(mod.ReviewCompileError, match="MANIFEST_LOCATOR_UNSAFE"):
        mod._safe_locator(value, "svg")


@pytest.mark.parametrize("value", ["figures/F01.svg", "data/F01.csv", "a b/c:d.md"])
def test_relative_locator_is_kept(value):
    assert mod._safe_locator(value, "svg") == value
