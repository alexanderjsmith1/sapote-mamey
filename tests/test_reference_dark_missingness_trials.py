import pytest
from mamey.reference_dark_prior import classify_reference_dark,REFERENCE_DARK


@pytest.mark.parametrize('values',[(10,'',0),(10,0,''),('',0,0),(10,'bad',0),(10,0,'NaN'),(10,0,'Infinity'),(0,0,0),(10,-1,0),(10,11,1),(10,1.5,0.15),(10,1,1.2)])
def test_invalid_evidence_cannot_be_reference_dark(values):
    with pytest.raises(ValueError,match='REFERENCE_DARK_EVIDENCE_INVALID'):
        classify_reference_dark(*values)


def test_observed_zero_hits_stays_reference_dark():
    cls,basis=classify_reference_dark(10,0,0)
    assert cls==REFERENCE_DARK and '(0/10 genes)' in basis


def test_cli_reports_invalid_evidence_without_traceback(tmp_path,capsys):
    from types import SimpleNamespace
    from mamey.reference_dark_prior import reference_dark_command
    pkg=tmp_path/'package';pkg.mkdir()
    (pkg/'TEST-01_3_mibig_profile.csv').write_text('bgc_id,query_gene_count,recognizable_gene_count,recognizable_gene_fraction\nBGC001,10,,0\n')
    out=tmp_path/'out'
    rc=reference_dark_command(SimpleNamespace(root=str(pkg),depth=3,out=str(out)))
    assert rc!=0
    captured=capsys.readouterr()
    assert 'REFERENCE_DARK_EVIDENCE_INVALID' in captured.out+captured.err
    assert not list(out.glob('*.csv'))


@pytest.mark.parametrize('values',[(10,1,0),(10,0,0.5),(10,5,0.1)])
def test_fraction_count_conflict_refused(values):
    with pytest.raises(ValueError,match='REFERENCE_DARK_EVIDENCE_INVALID'):
        classify_reference_dark(*values)


def test_native_fraction_rounding_preserved():
    classify_reference_dark(3,1,0.3333)
