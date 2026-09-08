"""v9.7.192 — authored-output verification. Regression guard for two reported failures:
(1) a guide's gate ran on the SKELETON, so a green pass was reported over an empty template;
(2) a hand-built 5-section doc was titled "Mode B Card" though it had no §1-§30 structure.
These tests lock in that the authored verifier fails a blank guide and the naming guard refuses a
non-§ doc named Mode B."""
import os
import re
import tempfile

import pytest

from mamey.bgc_guide import build_guide, render_markdown, verify_authored_guide
from mamey.authored_verify import guard_deliverable_name

_PKG = "/data/mamey-local/work/strain_intake/runs_v184/AS-678/package"
_HAVE_PKG = os.path.isdir(_PKG)


def _write(text, suffix=".md"):
    fd, p = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    open(p, "w").write(text)
    return p


# ---- Item 1: authored-guide verifier reads the FINISHED file ----
@pytest.mark.skipif(not _HAVE_PKG, reason="AS-678 package not present in this env")
def test_blank_skeleton_fails_authored_verify():
    """The core reported failure: an unauthored skeleton must FAIL verify (it passes guide_quality_gate)."""
    skeleton = render_markdown(build_guide(_PKG, "BGC029"))
    p = _write(skeleton)
    try:
        ok, errors, _ = verify_authored_guide(p)
        assert ok is False
        assert any("residual" in e for e in errors)  # residual LAY slots caught
    finally:
        os.unlink(p)


@pytest.mark.skipif(not _HAVE_PKG, reason="AS-678 package not present in this env")
def test_authored_guide_passes():
    """A guide with every LAY slot filled with real prose passes."""
    md = render_markdown(build_guide(_PKG, "BGC029"))
    md = re.sub(r"<!-- LAY: plain-title -->", "the loading module", md)
    md = re.sub(r"<!-- LAY: one to three sentence plain-language summary for (\S+) -->",
                r"Gene \1 encodes an enzyme with a defined job in assembling the molecule; it is one "
                r"link in the pathway and its role is supported by the domains shown below.", md)
    md = re.sub(r"<!-- LAY: one-paragraph identity[^>]*-->", "This cluster builds a peptide. " * 15, md)
    md = re.sub(r"<!-- LAY: genes/proteins/domains[^>]*-->", "Genes are instructions. " * 12, md)
    md = re.sub(r"<!-- LAY: core biosynthetic logic[^>]*-->", "The logic is an assembly line. " * 12, md)
    md = re.sub(r"<!-- LAY: whole-picture read[^>]*-->", "Together this is a credible lead. " * 15, md)
    p = _write(md)
    try:
        ok, errors, _ = verify_authored_guide(p)
        assert ok is True, f"unexpected errors: {errors}"
    finally:
        os.unlink(p)


def test_missing_guide_file_fails():
    ok, errors, _ = verify_authored_guide("/nonexistent/guide.md")
    assert ok is False


# ---- Item 2: naming/write guard refuses a non-§ doc named Mode B ----
_FAKE_MODEB = """# AS-385 BGC021 Mode B Card
## 1 Engine summary
text
## 2 Interpretation
text
## 3 BLASTp evidence
## 4 Precursor peptides
## 5 Claim ceiling
"""


def test_naming_guard_refuses_handbuilt_modeb():
    p = _write(_FAKE_MODEB, suffix="_ModeB_Card.md")
    try:
        allowed, reasons = guard_deliverable_name(p)
        assert allowed is False
        assert reasons  # gives a reason
    finally:
        os.unlink(p)


def test_naming_guard_ignores_non_modeb_names():
    p = _write("just a prose summary", suffix="_summary.md")
    try:
        allowed, _ = guard_deliverable_name(p)
        assert allowed is True  # not claiming to be Mode B
    finally:
        os.unlink(p)


def test_naming_guard_missing_file_named_modeb_refused():
    allowed, reasons = guard_deliverable_name("/nope/AS-1_Mode_B_Card.md")
    assert allowed is False
