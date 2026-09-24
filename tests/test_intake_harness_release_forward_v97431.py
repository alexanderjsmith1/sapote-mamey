"""v9.7.431: the operator's --release must reach the engine, not just the registry TSV.

`tools/intake_harness.py` parsed `--release`, used it for the private-name guard and wrote it
into its own registry TSV row -- but never put it on the `mamey run` argv. The engine therefore
fell back to `dedup_and_guard.derive_release()`, which fails safe to PRIVATE on an unrecognized
strain shape. So a reference-strain batch run with an explicit `--release PUBLIC` produced a
registry row saying PUBLIC beside a package saying PRIVATE: two records of one fact, disagreeing,
with nothing in either artifact to show they had diverged.

SCOPE HONESTY -- what this test does and does not prove. The argv is a LIST LITERAL, so parsing
it with ast and reading the constant strings inspects the exact object that reaches the
subprocess; for a literal there is no gap between structure and behaviour. That is why an AST
check is sufficient HERE. It would NOT be sufficient if the argv were assembled conditionally at
runtime, and it does not prove the engine honours the flag -- `resolve_release()` may still
refuse an unsafe PUBLIC override, which is the leak guard working and is covered by that
module's own tests. This pins one thing: the operator's choice is handed over rather than dropped.
"""
import ast
import pathlib

import pytest

HARNESS = pathlib.Path(__file__).resolve().parent.parent / "tools" / "intake_harness.py"


def _batch_run_argv() -> list[ast.expr]:
    """The argv list literal of the per-strain `mamey run` call (not the --bench smoke call)."""
    tree = ast.parse(HARNESS.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        consts = [e.value for e in node.elts if isinstance(e, ast.Constant)]
        if "run" in consts and "--input-zip" in consts and "--strain" in consts:
            # the bench call hardcodes the fixture + MX_BENCH; the batch call passes names
            if "MX_BENCH" in consts:
                continue
            return node.elts
    pytest.fail("could not locate the batch `mamey run` argv literal in intake_harness.py")


def test_release_flag_is_forwarded_to_the_engine():
    elts = _batch_run_argv()
    consts = [e.value for e in elts if isinstance(e, ast.Constant)]
    assert "--release" in consts, (
        "intake_harness parses --release but does not forward it to `mamey run`; the engine "
        "will derive its own release tag and may disagree with the registry TSV row"
    )


def test_forwarded_release_is_the_same_variable_the_registry_row_uses():
    """The defect was two records of one fact. Pin that they read from ONE source."""
    elts = _batch_run_argv()
    idx = next((i for i, e in enumerate(elts)
                if isinstance(e, ast.Constant) and e.value == "--release"), None)
    if idx is None:
        pytest.fail("--release is not on the batch `mamey run` argv at all (see the test above); "
                    "a bare StopIteration here would hide which of the two defects is present")
    value = elts[idx + 1]
    assert isinstance(value, ast.Attribute) and value.attr == "release", (
        "the forwarded --release value must be the parsed namespace attribute (a.release) -- the "
        "same expression the registry TSV row is built from, so the two cannot drift apart"
    )


def test_private_name_guard_still_precedes_the_run():
    """Forwarding must not be mistaken for relaxing: the harness's own refusal stays upstream."""
    src = HARNESS.read_text()
    guard = src.index("Refusing PUBLIC intake for private-looking strain")
    run_call = src.index('"mamey_run.py"), "run", "--input-zip", izip')  # v9.7.441: launched via the bundle-pinned runner, not `-m mamey`
    assert guard < run_call, "the PUBLIC-intake refusal must still run before any strain is processed"
