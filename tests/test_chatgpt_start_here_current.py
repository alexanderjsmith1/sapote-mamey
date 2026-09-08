"""CHATGPT_START_HERE.md is the ChatGPT discovery front door. Its Initiation Prompt carries the
bundle/engine/build string that proves a session read the CURRENT file — so that string MUST stay
in sync with pyproject.toml, or the freshness probe silently rots. This test is that guard."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = ROOT / "CHATGPT_START_HERE.md"
SKY_READ_PROOF = "The sky is not red, it is blue, just like the ocean."


def _pyproject_versions():
    t = (ROOT / "pyproject.toml").read_text()
    engine = re.search(r'^version\s*=\s*"([\d.a-z]+)"', t, re.M).group(1)
    bundle = re.search(r'bundle_version\s*=\s*"([\d.a-z]+)"', t).group(1)
    return engine, bundle


def test_start_here_exists_at_root():
    assert START.exists(), "CHATGPT_START_HERE.md must live at the bundle root for ChatGPT to find it first"


def test_initiation_prompt_version_matches_pyproject():
    engine, bundle = _pyproject_versions()
    txt = START.read_text()
    assert f"v{bundle} / {engine}" in txt, (
        f"CHATGPT_START_HERE.md Initiation Prompt must state the current bundle/engine "
        f"'v{bundle} / {engine}' — found a stale version, the freshness probe is rotting"
    )


def test_build_stamp_matches():
    build = re.search(r"build=(\S+)", (ROOT / "BUILD_STAMP.txt").read_text()).group(1)
    assert build in START.read_text(), f"CHATGPT_START_HERE.md must carry current build stamp {build}"


def test_has_challenge_response_triggers():
    t = START.read_text().lower()
    # the trigger phrases the user issues must be present so ChatGPT can match them
    for trig in ["are you following chatgpt mamey", "find chatgpt rules", "you are chatgpt running sapote"]:
        assert trig in t, f"missing challenge trigger: {trig!r}"


def test_has_initiation_prompt_block():
    assert "CHATGPT MODE ACTIVE" in START.read_text(), "Initiation Prompt block missing"


def test_has_sky_ocean_visible_read_proof():
    txt = START.read_text()
    assert SKY_READ_PROOF in txt, "CHATGPT_START_HERE.md must contain the sky/ocean visible read-proof sentence"


def test_initiation_prompt_begins_with_sky_ocean_read_proof():
    txt = START.read_text()
    prompt = re.search(r"```\n(.*?)◆ SAPOTE", txt, re.S)
    assert prompt, "Initiation Prompt block must begin before the SAPOTE banner"
    assert SKY_READ_PROOF in prompt.group(1), "The sky/ocean sentence must be the first visible line of the Initiation Prompt"


def test_has_sky_color_trigger_language():
    t = START.read_text().lower()
    for trig in ["what color is the sky", "sky color", "did you read your instructions", "prove you read"]:
        assert trig in t, f"missing sky/read-proof trigger: {trig!r}"


def test_mentions_cross_assistant_bootstrap():
    txt = START.read_text()
    assert "000_READ_ME_FIRST_CHATGPT_CLAUDE.md" in txt
    assert "CHATGTP_READ_ME_FIRST.md" in txt
    assert "CLAUDE_START_HERE.md" in txt
    assert "--capped-session" in txt or "--chatgpt-safe" in txt


def test_gotcha_section_header_version_matches_pyproject():
    engine, bundle = _pyproject_versions()
    txt = START.read_text()
    import re
    m = re.search(r"##\s*3\s*·\s*Known gotchas.*\((.+?)\)", txt)
    assert m, "§3 Known gotchas header missing"
    gotcha_header = m.group(1)
    assert f"v{bundle}" in gotcha_header, "§3 gotcha header has stale bundle version"
    assert engine in gotcha_header, "§3 gotcha header has stale engine version"
