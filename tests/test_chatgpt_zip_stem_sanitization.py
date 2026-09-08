from pathlib import Path

from mamey.cli import _chatgpt_safe_strain_guess
from mamey.package_inspector import _inspect_strain_guess


def test_chatgpt_upload_suffixes_do_not_become_strain_ids():
    assert _chatgpt_safe_strain_guess("/tmp/TESTSTRAIN385(4).zip") == "TESTSTRAIN385"
    assert _chatgpt_safe_strain_guess("/tmp/TESTSTRAIN441 loose(6).zip") == "TESTSTRAIN441"
    assert _chatgpt_safe_strain_guess("/tmp/TESTSTRAIN705_new copy(2).zip") == "TESTSTRAIN705"


def test_inspect_uses_same_safe_suffix_policy():
    assert _inspect_strain_guess(Path("/tmp/TESTSTRAIN385(4).zip")) == "TESTSTRAIN385"
    assert _inspect_strain_guess(Path("/tmp/TESTSTRAIN441 loose(6).zip")) == "TESTSTRAIN441"
