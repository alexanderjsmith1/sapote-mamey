"""Reference accession conflicts carry an actionable refusal without guessing labels."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "tools" / "build_placement_ggtree_inputs.py"

FUSED = (
    "NR_026535_1_Streptomyces_odorifer_strain_DSM_40347_16S_ribosomal_RNA_partial_sequence"
    "_NR_119341_1_Streptomyces_albidoflavus_strain_DSM_40455_16S_ribosomal_RNA_partial_sequence"
    "_NR_119342_1_Streptomyces_coelicolor_strain_DSM_40233_16S_ribosomal_RN"
)
ORDINARY = "Streptomyces_champavatii_strain_NBRC_15392_NR_112451"


def _mod():
    spec = importlib.util.spec_from_file_location("_bpgi_refusal", PRODUCER)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_bpgi_refusal"] = m
    spec.loader.exec_module(m)
    return m


def test_producer_is_present():
    assert PRODUCER.is_file(), f"missing {PRODUCER}"


def test_a_fused_tip_exits_as_a_typed_refusal_not_a_traceback(capsys):
    with pytest.raises(SystemExit) as exc:
        _mod()._ref_label_or_refuse(FUSED, "Streptomyces")
    assert exc.value.code == 2, "a refusal must carry the tool's refusal exit code"
    err = capsys.readouterr().err
    assert "REFERENCE_ACCESSION_CONFLICT" in err, "the typed code must reach the operator"


def test_the_refusal_names_the_offending_tip(capsys):
    """The whole point: a traceback says a conflict happened, not which input caused it."""
    with pytest.raises(SystemExit):
        _mod()._ref_label_or_refuse(FUSED, "Streptomyces")
    err = capsys.readouterr().err
    assert "NR_026535" in err and "NR_119342" in err, (
        "the refusal must list the competing accessions so the tip can be repaired upstream"
    )


def test_an_ordinary_tip_is_untouched():
    """Negative control: the guard must not change any label that already resolved."""
    m = _mod()
    assert m._ref_label_or_refuse(ORDINARY, "Streptomyces") == m._ref_label(ORDINARY, "Streptomyces")


def test_the_parse_rule_is_not_relaxed():
    """This lane deliberately does not touch which tips conflict -- only how the exit is reported."""
    with pytest.raises(ValueError, match="REFERENCE_ACCESSION_CONFLICT"):
        _mod()._ref_accession(FUSED)


def test_an_unrelated_valueerror_is_not_swallowed():
    """The guard must catch only its own contract violation."""
    m = _mod()

    def boom(*a, **k):
        raise ValueError("SOMETHING_ELSE")

    original = m._ref_label
    m._ref_label = boom
    try:
        with pytest.raises(ValueError, match="SOMETHING_ELSE"):
            m._ref_label_or_refuse("x", "y")
    finally:
        m._ref_label = original


@pytest.mark.parametrize('requested', [False, True])
def test_actual_command_names_conflict_and_preserves_outputs(tmp_path, requested):
    import subprocess, sqlite3
    graft = tmp_path / 'tree.nwk'
    graft.write_text(f'({FUSED}:0.1,Ref_valid:0.1,outgroup_X:0.2);')
    prefix = tmp_path / 'result'
    files = [Path(str(prefix)+suffix) for suffix in ['_pruned.nwk','_ggtree_annotation.tsv','_metadata_receipt.json']]
    for p in files: p.write_bytes(b'previous output')
    args = [sys.executable,str(PRODUCER),'--graft',str(graft),'--out-prefix',str(prefix),'--keep-all-refs']
    if requested:
        db = tmp_path / 'source.sqlite'
        with sqlite3.connect(db) as con: con.execute('CREATE TABLE record(acc_base TEXT, isolation_source TEXT, country TEXT)')
        args += ['--ref-source-db',str(db)]
    q = subprocess.run(args,capture_output=True,text=True)
    assert q.returncode == 2, q.stderr
    assert 'REFERENCE_ACCESSION_CONFLICT' in q.stderr and 'NR_026535' in q.stderr
    assert 'Traceback' not in q.stderr
    assert all(p.read_bytes() == b'previous output' for p in files)
