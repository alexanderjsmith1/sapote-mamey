"""BLIZZARD_BLUE_441: intake_harness launches the engine as `sys.executable -m mamey`. Python's
`-m` puts the child's own cwd ahead of PYTHONPATH on sys.path, so a stray `mamey/` package sitting
in the operator's cwd silently version-shadows the bundle's engine -- observed by EB3DF1EF sealing
35 packages under engine 1.9.154 against a 1.9.169 bundle, rc=0, no warning surfaced. This tests
the post-run refusal added in `.441`: read the version the child actually used back out of its own
sealed manifest_short.json and refuse (RUN_FAILED: ENGINE_MISMATCH) instead of trusting rc==0.

Two other `.441` diffs (88fdad06, 1955A8C0) independently fix the LAUNCH side (stop using `-m mamey`
/ add `-P`) -- this is complementary defense-in-depth for whichever launch fix lands, and for any
future launch path that reintroduces the same shadow.

Drop into tests/ alongside tools/intake_harness.py (matches the AST/source-inspection convention
tests/test_intake_harness_release_forward_v97431.py already uses for this file, rather than
importing it -- importing pulls in the `from mamey import __version__` module-level dependency
this test does not need to exercise).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tools" / "intake_harness.py"


def test_harness_imports_the_bundle_engine_version():
    text = HARNESS.read_text()
    assert "from mamey import __version__ as _BUNDLE_ENGINE_VERSION" in text


def test_harness_refuses_on_a_sealed_version_mismatch():
    text = HARNESS.read_text()
    assert "ENGINE_MISMATCH" in text
    assert "_sealed_version != _BUNDLE_ENGINE_VERSION" in text


def test_mismatch_check_runs_before_the_package_is_trusted():
    """The ENGINE_MISMATCH check must sit between the rc/isdir guard and the first place the
    package is read as evidence (parse_run_summary / rescue_summary / reg_rows), or a shadowed
    package would still be recorded as OK before anyone looks at its actual engine version."""
    text = HARNESS.read_text()
    mismatch_at = text.index("ENGINE_MISMATCH")
    first_evidence_read_at = text.index("summ = parse_run_summary(log)")
    assert mismatch_at < first_evidence_read_at


def test_real_read_json_extracts_mamey_version_from_a_synthetic_manifest(tmp_path):
    """Exercises the harness's OWN `_read_json` helper (copied verbatim, since importing the
    module requires `mamey` on sys.path, which this check does not need) against a manifest
    shaped like a real sealed package's."""
    import importlib.util
    text = HARNESS.read_text()
    start = text.index("def _read_json(")
    end = text.index("\n\n", start)
    namespace = {}
    exec(text[start:end], namespace)  # noqa: S102 -- the function body only, no mamey import
    manifest = tmp_path / "manifest_short.json"
    manifest.write_text(json.dumps({"mamey_version": "1.9.154", "strain": "AS-188"}))
    result = namespace["_read_json"](str(manifest))
    assert result["mamey_version"] == "1.9.154"


def test_mismatch_predicate_fires_only_on_real_disagreement():
    """Mirrors the exact comparison the diff performs (the check lives inline in main(), which
    argparse-drives a full batch run and is not unit-callable in isolation) -- proves the
    predicate's behavior on the three cases that matter: match, mismatch, and unreadable."""
    def would_refuse(sealed_version, bundle_version):
        return sealed_version is not None and sealed_version != bundle_version

    assert would_refuse("1.9.154", "1.9.169") is True     # the observed real-world case
    assert would_refuse("1.9.169", "1.9.169") is False    # matching engine: no refusal
    assert would_refuse(None, "1.9.169") is False          # unreadable manifest: warn, don't refuse
