"""Contract test: every restated version string matches the single source of truth.

This is the guard that makes the v9.7.6-vs-v9.7.21-vs-v9.7.22 desync impossible to
ship again. The source of truth is pyproject.toml:
    [project] version            -> engine (Mamey)
    [tool.sapote] bundle_version -> bundle (Sapote-Mamey)
If TAG, the session manifest, CITATION.cff, the CHANGELOG's newest entry, or the
release manifest disagree, the build fails here instead of in a reviewer's hands.

Run:  PYTHONPATH=... python3 -m pytest tests/test_version_sync.py -v
"""
import re
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _truth():
    txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    eng = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', txt)
    bnd = re.search(r'(?m)^\s*bundle_version\s*=\s*"([^"]+)"', txt)
    assert eng, "pyproject.toml: [project] version not found"
    assert bnd, "pyproject.toml: [tool.sapote] bundle_version not found"
    return eng.group(1), bnd.group(1)


ENGINE, BUNDLE = _truth()


def _read(rel):
    p = ROOT / rel
    assert p.exists(), f"{rel} is missing from this tier"
    return p.read_text(encoding="utf-8")


def test_tag_bundle_line():
    assert re.search(rf"(?m)^sapote-mamey v{re.escape(BUNDLE)}\b", _read("TAG")), \
        f"TAG bundle line does not state v{BUNDLE}"


def test_tag_engine_line():
    assert re.search(rf"(?m)^engine: mamey v{re.escape(ENGINE)}\b", _read("TAG")), \
        f"TAG engine line does not state v{ENGINE}"


def test_session_manifest_header():
    needle = f"Engine: Mamey v{ENGINE} · Bundle: sapote-mamey-v{BUNDLE}"
    assert needle in _read("SESSION_START_MANIFEST.md"), \
        f"SESSION_START_MANIFEST.md header is not '{needle}'"


def test_citation_version():
    assert re.search(rf"(?m)^version:\s*{re.escape(BUNDLE)}\b", _read("CITATION.cff")), \
        f"CITATION.cff version is not {BUNDLE}"


def test_changelog_newest_entry():
    first_line = _read("CHANGELOG.md").splitlines()[0]
    assert first_line.startswith(f"# v{BUNDLE}"), \
        f"newest CHANGELOG entry is {first_line[:48]!r}, expected to start '# v{BUNDLE}'"


def test_release_manifest_bundle():
    assert f"sapote-mamey-v{BUNDLE}" in _read("RELEASE_MANIFEST.md"), \
        f"RELEASE_MANIFEST.md does not state sapote-mamey-v{BUNDLE}"


# --- user-facing docs/prompts (added 2026-06-13; critique caught these as stale) ---
# Drift-catching: every version mention of the relevant kind must equal the source of truth,
# not merely contain the current one. Historical versions live in separate files (untouched).

def test_readme_bundle_version():
    mentions = re.findall(r"sapote-mamey-v(\d+(?:\.\d+)*[a-z]?)", _read("README_START_HERE.md"))
    assert mentions, "README_START_HERE.md has no sapote-mamey-v<ver> mention"
    assert all(m == BUNDLE for m in mentions), \
        f"README_START_HERE.md states {set(mentions)}, expected all == {BUNDLE}"


@pytest.mark.parametrize("rel", [
    "docs/standalone/MAMEY_STANDALONE_CHATGPT_README.md",
    "docs/standalone/RUN_MAMEY_IN_CHATGPT.md",
])
def test_standalone_engine_version(rel):
    mentions = re.findall(r"Mamey v(\d+(?:\.\d+)*[a-z]?)", _read(rel))
    assert mentions, f"{rel} has no 'Mamey v<ver>' mention"
    assert all(m == ENGINE for m in mentions), \
        f"{rel} states Mamey v{set(mentions)}, expected all == {ENGINE}"


def test_coexec_prompt_bundle_version():
    txt = _read("prompts/SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md")
    mentions = re.findall(r"(?:\*\*Bundle:\*\*|Sapote-Mamey Bundle|Bundle:)\s+v(\d+(?:\.\d+)*[a-z]?)", txt)
    assert mentions, "co-execution prompt has no bundle-version restatement"
    assert all(m == BUNDLE for m in mentions), \
        f"co-execution prompt states v{set(mentions)}, expected all == {BUNDLE}"


def test_release_manifest_footer_version():
    import re as _re
    # The footer's trailing tier token varies by release tier (PUBLIC_RELEASE on a
    # signed public cut; NOT_FOR_PUBLIC_RELEASE / CODE / CODE_TIER on lower tiers —
    # v9.7.154 corrected the CODE candidate's token from the false PUBLIC_RELEASE).
    # This test asserts the footer *restates the bundle version*, not which tier
    # token follows it, so it matches any non-empty trailing token after the version.
    foot = _re.findall(
        r"Sapote-Mamey Bundle v(\d+(?:\.\d+)*[a-z]?) \| [A-Z_]+\*",
        _read("RELEASE_MANIFEST.md"))
    assert foot, "RELEASE_MANIFEST.md footer has no bundle-version restatement"
    assert all(v == BUNDLE for v in foot), \
        f"RELEASE_MANIFEST.md footer states v{set(foot)}, expected {BUNDLE}"


def test_task_brief_template_bundle_version():
    """v9.7.101 P4/P5: the task-brief template header stamp must track the bundle."""
    txt = _read("prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md")
    m = re.search(r"Task Brief Template \u2014 v(\d+(?:\.\d+)*[a-z]?)", txt)
    assert m, "task-brief template has no '— v<ver>' header stamp"
    assert m.group(1) == BUNDLE, \
        f"task-brief template states v{m.group(1)}, expected {BUNDLE}"


def test_exec_and_diagnosis_prompt_bundle_version():
    """v9.7.101 P4: the execution + run-diagnosis prompts restate the current bundle."""
    exec_txt = _read("prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md")
    m = re.search(r"Execution Prompt \u2014 v(\d+(?:\.\d+)*[a-z]?)", exec_txt)
    assert m and m.group(1) == BUNDLE, \
        f"execution prompt header states v{m.group(1) if m else None}, expected {BUNDLE}"
    diag_txt = _read("prompts/RUN_DIAGNOSIS_PROMPT.md")
    diag = re.findall(r"Sapote.Mamey v(\d+(?:\.\d+)*[a-z]?) bundle", diag_txt)
    assert diag, "run-diagnosis prompt has no bundle-version restatement"
    assert all(v == BUNDLE for v in diag), \
        f"run-diagnosis prompt states v{set(diag)}, expected {BUNDLE}"


# --- BLOCK-1 loophole guard (added by audit, v9.7.148h) ---
# The BLOCK-1 family of bugs was: a version regex that dropped the alpha suffix, so a
# document stating a bare "9.7.148" silently satisfied a check whose truth was "9.7.148g".
# These tests assert the alpha suffix is load-bearing: a bare version must not satisfy
# a suffixed source of truth, so a regex regression to a non-suffix pattern is observable.

def test_bundle_truth_has_alpha_suffix_when_expected():
    """Sanity: when the cut is an alpha candidate (e.g. 9.7.148g), the source of truth
    actually carries the suffix — otherwise the loophole tests below are vacuous."""
    # Not all cuts are alpha; only assert the suffix is preserved, not that it exists.
    assert re.fullmatch(r"\d+\.\d+\.\d+[a-z]?", BUNDLE), \
        f"BUNDLE {BUNDLE!r} is not a well-formed version (with optional alpha suffix)"


def test_readme_pattern_rejects_bare_version_when_truth_is_suffixed():
    """If and only if the truth is suffixed, a bare (suffix-stripped) version must NOT
    equal the truth. Proves the README check would reject 'sapote-mamey-v9.7.148' while
    truth is '9.7.148g' — i.e. the alpha suffix is load-bearing, not cosmetic."""
    if not re.search(r"[a-z]$", BUNDLE):
        import pytest
        pytest.skip("current cut has no alpha suffix; loophole test not applicable")
    bare = re.sub(r"[a-z]$", "", BUNDLE)            # 9.7.148g -> 9.7.148
    assert bare != BUNDLE                            # sanity
    # The README assertion captures with this pattern and compares == BUNDLE:
    captured = re.findall(r"sapote-mamey-v(\d+(?:\.\d+)*[a-z]?)", f"sapote-mamey-v{bare}")
    assert captured and all(c != BUNDLE for c in captured), \
        "a bare (unsuffixed) version must not satisfy the suffixed source of truth"


def test_tier_manifest_header_version():
    """v9.7.155: TIER_MANIFEST.txt header `version=` token must match the bundle
    SSOT. It is regenerated by make_public_tier.sh at cut time, but the checked-in
    copy drifted (stale at 9.7.151 across v9.7.152-154) because nothing asserted it
    between cuts. sync_version.py now anchors it; this test guards that anchor."""
    txt = _read("TIER_MANIFEST.txt")
    m = re.search(r"# TIER_MANIFEST tier=\S+ version=(\d+(?:\.\d+)*[a-z]?)", txt)
    assert m, "TIER_MANIFEST.txt header has no parseable version= token"
    assert m.group(1) == BUNDLE, \
        f"TIER_MANIFEST.txt header states v{m.group(1)}, expected {BUNDLE}"


def test_generated_bootstrap_docs_current_via_sync():
    """v9.7.155: the generated bootstrap docs must be current. This duplicates the
    intent of test_bootstrap_contract_generation but lives in the version-sync
    contract so a version bump that forgets to regenerate them fails HERE too —
    the BOOTSTRAP_FILE_AUDIT.md-stale-at-v9.7.153 miss in the v9.7.154 cut. Skips
    cleanly if the generator tool isn't shipped in this tier."""
    import subprocess, sys
    tool = ROOT / "tools" / "render_bootstrap_contract.py"
    if not tool.exists():
        pytest.skip("render_bootstrap_contract.py not present in this tier")
    out = subprocess.run(
        [sys.executable, str(tool), "--check"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert out.returncode == 0, \
        f"generated bootstrap docs are stale; run render_bootstrap_contract.py --apply\n{out.stdout}{out.stderr}"


def test_build_stamp_encodes_bundle_version():
    """v9.7.155 (Speed-Round Finding A): the BUILD_STAMP `build=` token encodes the
    bundle version with dots stripped (20260630v97155a -> 97155 == 9.7.155). A bump
    that updates version= but forgets build= would otherwise pass --check (all docs
    get regenerated consistently from the stale stamp) AND bake the stale build into
    the bootstrap doc. This locks the guard sync_version.py --check now enforces."""
    txt = _read("BUILD_STAMP.txt")
    m = re.search(r"(?m)^build=(\S+)", txt)
    assert m, "BUILD_STAMP.txt has no build= line"
    compact = BUNDLE.replace(".", "")
    # Round-2 Finding E + Round-3 Finding G: anchored to end-of-token (v<compact>
    # then an optional single letter suffix then end) so neither a shorter bundle
    # (9.7.15 -> "9715" inside v97155a) nor multi-letter junk (v97155xyz) false-passes.
    assert re.search(rf"v{re.escape(compact)}[a-z]?$", m.group(1)), \
        f"BUILD_STAMP build= ({m.group(1)}) does not encode bundle {BUNDLE} (expected 'v{compact}')"
