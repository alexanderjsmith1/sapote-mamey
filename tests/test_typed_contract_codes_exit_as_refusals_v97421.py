r"""Every typed contract violation in this producer must exit as a refusal, not a traceback.

`tools/build_placement_ggtree_inputs.py` raises `ValueError("SOME_TYPED_CODE")` at nine sites when
an input breaks a contract. Every other malformed-input path in the same file exits through
`_refuse(code, detail)` -- typed code on stderr, exit 2. The typed raises did not.

Measured end-to-end on sealed v9.7.420 with an aux table carrying the wrong header:

    pristine   exit 1, stderr ends `ValueError: AUX_METADATA_SCHEMA` (a Python traceback)
    patched    exit 2, stderr `AUX_METADATA_SCHEMA: input contract violated; ...`

Eight of the nine were unguarded. The ninth, `REFERENCE_ACCESSION_CONFLICT`, was fixed in
v9.7.420 by wrapping its two call sites -- this guard covers the siblings that fix did not reach,
at the process boundary where one guard serves all of them.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "tools" / "build_placement_ggtree_inputs.py"

# Every ALL-CAPS code this module raises, read from the source so a new one cannot be added
# silently without this list noticing.
def _typed_codes():
    import ast
    tree = ast.parse(PRODUCER.read_text(encoding="utf-8"))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and n.exc.args:
            a = n.exc.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str) \
                    and re.fullmatch(r"[A-Z][A-Z0-9_]{5,}", a.value):
                out.add(a.value)
    return out


def _mod():
    spec = importlib.util.spec_from_file_location("_bpgi_typed", PRODUCER)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_bpgi_typed"] = m
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def test_producer_is_present():
    assert PRODUCER.is_file(), f"missing {PRODUCER}"


def test_the_module_still_raises_typed_codes():
    """If this ever reaches zero the guard below is vacuous and must be re-justified."""
    codes = _typed_codes()
    assert len(codes) >= 8, f"expected the typed-code contract family; found {sorted(codes)}"
    assert "AUX_METADATA_SCHEMA" in codes


def test_declared_registry_exactly_matches_typed_raise_sites():
    """Every typed producer has one boundary disposition and no unrelated code is laundered."""
    m = _mod()
    assert m._TYPED_CODES == _typed_codes()


@pytest.mark.parametrize("code", sorted([
    "BIOASSAY_METADATA_SCHEMA",
    "BIOASSAY_METADATA_IDENTITY",
    "BIOASSAY_METADATA_VALUE",
    "BIOASSAY_METADATA_DUPLICATE",
    "BIOASSAY_METADATA_CONFLICT",
    "AUX_METADATA_SCHEMA",
    "AUX_METADATA_IDENTITY_OR_WIDTH",
    "AUX_METADATA_CONFLICT",
    "REFERENCE_ACCESSION_CONFLICT",
    "REFERENCE_SOURCE_ACCESSION_INVALID",
    "REFERENCE_SOURCE_FIELD_INVALID",
    "REFERENCE_SOURCE_CONFLICT",
    "HOST_METADATA_CONFLICT",
    "METADATA_SOURCE_CHANGED_DURING_RUN",
]))
def test_each_declared_typed_code_routes_to_refusal(monkeypatch, capsys, code):
    """The process-boundary dispatcher covers each producer code explicitly."""
    m = _mod()
    monkeypatch.setattr(m, "main", _raise(code))

    with pytest.raises(SystemExit) as caught:
        m._run_or_refuse()

    assert caught.value.code == 2
    assert capsys.readouterr().err.startswith(code + ":")


def test_a_typed_contract_violation_exits_two_with_its_code(tmp_path):
    """End-to-end at the CLI boundary, which is where the operator meets it."""
    aux = tmp_path / "aux.tsv"
    aux.write_text("not_a_tip\tsomething\nx\ty\n", encoding="utf-8")
    tree = tmp_path / "t.nwk"
    tree.write_text("(A:0.1,B:0.1);\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(PRODUCER), "--graft", str(tree), "--aux-table", str(aux),
         "--out-prefix", str(tmp_path / "o"), "--group", "G"],
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 2, (
        f"a typed contract violation must exit with the tool's refusal code, got "
        f"{proc.returncode}\nstderr:\n{proc.stderr[-800:]}"
    )
    assert "AUX_METADATA_SCHEMA" in proc.stderr
    assert "Traceback" not in proc.stderr, "the operator must not be shown a Python stack"


def _raise(message):
    def _boom():
        raise ValueError(message)
    return _boom


@pytest.mark.parametrize("message,pattern", [
    ("something unexpected went wrong", "something unexpected"),
    ("not_a_typed_code", "not_a_typed_code"),
    ("UNEXPECTED_INTERNAL_FAILURE", "UNEXPECTED_INTERNAL_FAILURE"),
])
def test_a_non_typed_valueerror_keeps_its_traceback(monkeypatch, message, pattern):
    """Negative control, and the reason this guard is narrow.

    Converting every `ValueError` would hide genuine bugs behind a fake refusal. Only codes in
    the explicit registry are contract violations; unrelated messages must propagate.

    `monkeypatch.setattr` rather than a raw assignment: `tests/test_no_raw_module_stub_leaks_v97397.py`
    forbids the raw form because a stub leaks to every later test in the same process (the .398
    kcb_frontpage incident). That guard caught this file's first draft.
    """
    m = _mod()
    monkeypatch.setattr(m, "main", _raise(message))
    with pytest.raises(ValueError, match=pattern):
        m._run_or_refuse()


def test_the_boundary_guard_is_wired_to_the_entry_point():
    """A guard that main() does not go through is not a guard."""
    src = PRODUCER.read_text(encoding="utf-8")
    assert "sys.exit(_run_or_refuse())" in src, "the __main__ entry must call the guarded runner"


def test_cli_refusal_preserves_existing_final_outputs(tmp_path):
    """An early typed refusal may not truncate or replace prior successful artifacts."""
    aux = tmp_path / "aux.tsv"
    aux.write_text("not_a_tip\tsomething\nx\ty\n", encoding="utf-8")
    tree = tmp_path / "t.nwk"
    tree.write_text("(A:0.1,B:0.1);\n", encoding="utf-8")
    prefix = tmp_path / "o"
    finals = [
        tmp_path / "o_pruned.nwk",
        tmp_path / "o_ggtree_annotation.tsv",
        tmp_path / "o_metadata_receipt.json",
    ]
    for index, path in enumerate(finals):
        path.write_bytes(f"sentinel-{index}".encode("ascii"))
    before = {path: path.read_bytes() for path in finals}

    proc = subprocess.run(
        [sys.executable, str(PRODUCER), "--graft", str(tree), "--aux-table", str(aux),
         "--out-prefix", str(prefix), "--group", "G"],
        capture_output=True, text=True, timeout=300,
    )

    assert proc.returncode == 2
    assert {path: path.read_bytes() for path in finals} == before


def test_source_change_refusal_preserves_existing_final_outputs(tmp_path, monkeypatch, capsys):
    """The late source-integrity refusal must occur before any final output is committed."""
    m = _mod()
    tree = tmp_path / "t.nwk"
    tree.write_text("(SID_1:0.1,Streptomyces_coelicolor_NC_003888.3:0.1);\n", encoding="utf-8")
    prefix = tmp_path / "o"
    finals = [
        tmp_path / "o_pruned.nwk",
        tmp_path / "o_ggtree_annotation.tsv",
        tmp_path / "o_metadata_receipt.json",
    ]
    for index, path in enumerate(finals):
        path.write_bytes(f"sentinel-{index}".encode("ascii"))
    before = {path: path.read_bytes() for path in finals}

    from Bio import Phylo
    original_write = Phylo.write

    def _write_then_mutate(*args, **kwargs):
        result = original_write(*args, **kwargs)
        tree.write_text(tree.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
        return result

    monkeypatch.setattr(Phylo, "write", _write_then_mutate)
    monkeypatch.setattr(sys, "argv", [str(PRODUCER), "--graft", str(tree),
                                      "--out-prefix", str(prefix), "--group", "G"])

    with pytest.raises(SystemExit) as caught:
        m._run_or_refuse()

    assert caught.value.code == 2
    assert "METADATA_SOURCE_CHANGED_DURING_RUN" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in finals} == before
    assert list(tmp_path.glob("o_*.tmp")) == []
